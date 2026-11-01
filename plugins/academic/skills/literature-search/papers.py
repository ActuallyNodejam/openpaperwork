#!/usr/bin/env python3
"""Find and read research papers through open indexes. Standard library only, no login, no key.

  papers.py search openalex|pubmed|arxiv "<query>" [--after YYYY-MM-DD] [--before YYYY-MM-DD]
                                                  [--prioritize default|recency|historical|popular] [--limit N]
  papers.py paper <DOI | OpenAlex W id | PMID | arXiv id | URL of any of these>
  papers.py cite apa|ieee|bibtex <id> [<id> ...]
  papers.py verify <DOI> [<DOI> ...]
  papers.py check <id> "<claim>" ["<exact quote>"]
  papers.py refs <id>
  papers.py cited-by <id> [--limit N]

Every command prints JSON. search results share one shape: source, id, title, abstract, date,
authors, venue, doi, citations, url. The command interface follows `orx discover` and `orx paper`
in alphaXiv OpenResearch (MIT); this file is a new implementation and uses none of its code.

`check`, `refs` and `cited-by` are ported from scholar-mcp by Gonzalo Gorbalan (MIT,
github.com/wolverin0/scholar-mcp, commit 9d4a05c): the four claim statuses and their two-question
order (scholar/jev/gates.py), sentence spans with exact character offsets (scholar/retrieval/engine.py)
and the OpenAlex reference and citing-work lookups (scholar/sources/openalex.py). Its paid scorer is
not ported: the agent judges. Notice: licenses/scholar-mcp-mit.txt.
"""
import html.parser
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET

UA = 'OpenPaperwork-papers/0.1 (+https://github.com/ActuallyNodejam/openpaperwork)'
OPENALEX = 'https://api.openalex.org'
EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
ARXIV = 'https://export.arxiv.org/api/query'
ARXIV_HTML = 'https://arxiv.org/html/'
EUROPEPMC = 'https://www.ebi.ac.uk/europepmc/webservices/rest/'
CROSSREF = 'https://api.crossref.org'
ATOM = '{http://www.w3.org/2005/Atom}'
WORK_FIELDS = ('id,doi,title,publication_date,publication_year,cited_by_count,type,authorships,primary_location,'
               'biblio,open_access,abstract_inverted_index,ids')


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json, */*'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise LookupError('not found: ' + url)
            last = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
        time.sleep(1.5 * (i + 1))
    raise ConnectionError('%s (%s)' % (last, url.split('?')[0]))


def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()


# ---------- OpenAlex ----------

def abstract_of(index):
    if not index:
        return ''
    words = sorted((pos, w) for w, places in index.items() for pos in places)
    return ' '.join(w for _, w in words)


def from_openalex(w):
    src = ((w.get('primary_location') or {}).get('source') or {})
    b = w.get('biblio') or {}
    authors = []
    for a in w.get('authorships') or []:
        name = (a.get('author') or {}).get('display_name')
        if name:
            authors.append(name)
    doi = (w.get('doi') or '').replace('https://doi.org/', '') or None
    pmid = ((w.get('ids') or {}).get('pmid') or '').rstrip('/').split('/')[-1] or None
    pmcid = ((w.get('ids') or {}).get('pmcid') or '').rstrip('/').split('/')[-1] or None
    pages = '–'.join(x for x in (b.get('first_page'), b.get('last_page')) if x) if b.get('first_page') else None
    return dict(source='openalex', id=w['id'].rsplit('/', 1)[-1], title=clean(w.get('title')), abstract=abstract_of(w.get('abstract_inverted_index')),
                date=w.get('publication_date'), year=w.get('publication_year'), authors=authors, venue=src.get('display_name'),
                volume=b.get('volume'), issue=b.get('issue'), pages=pages, type=w.get('type'), doi=doi, pmid=pmid, pmcid=pmcid,
                citations=w.get('cited_by_count'), open_access_url=(w.get('open_access') or {}).get('oa_url'),
                url='https://doi.org/' + doi if doi else w['id'])


def search_openalex(q, after, before, prioritize, limit):
    filt = []
    if after:
        filt.append('from_publication_date:' + after)
    if before:
        filt.append('to_publication_date:' + before)
    p = {'search': q, 'per-page': str(min(max(limit, 1), 50)), 'select': WORK_FIELDS}
    if filt:
        p['filter'] = ','.join(filt)
    rows = [from_openalex(w) for w in json.loads(get(OPENALEX + '/works?' + urllib.parse.urlencode(p)))['results']]
    return rerank(rows, prioritize)


def rerank(rows, prioritize):
    """The index returns relevance order; recency, historical and popular reorder that pool, as OpenResearch does."""
    if prioritize == 'recency':
        rows.sort(key=lambda r: r.get('date') or '', reverse=True)
    elif prioritize == 'historical':
        rows.sort(key=lambda r: r.get('date') or '9999')
    elif prioritize == 'popular':
        rows.sort(key=lambda r: r.get('citations') or 0, reverse=True)
    return rows


# ---------- PubMed ----------

def pubmed_records(pmids):
    if not pmids:
        return []
    xml = ET.fromstring(get(EUTILS + '/efetch.fcgi?' + urllib.parse.urlencode({'db': 'pubmed', 'retmode': 'xml', 'id': ','.join(pmids)})))
    out = {}
    for art in xml.findall('.//PubmedArticle'):
        pmid = art.findtext('.//MedlineCitation/PMID')
        a = art.find('.//Article')
        j = a.find('Journal')
        ji = j.find('JournalIssue') if j is not None else None
        pd = ji.find('PubDate') if ji is not None else None
        year = (pd.findtext('Year') or (pd.findtext('MedlineDate') or '')[:4]) if pd is not None else None
        authors = []
        for au in a.findall('.//AuthorList/Author'):
            if au.findtext('LastName'):
                authors.append(('%s %s' % (au.findtext('ForeName') or au.findtext('Initials') or '', au.findtext('LastName'))).strip())
            elif au.findtext('CollectiveName'):
                authors.append(au.findtext('CollectiveName'))
        doi = next((i.text for i in art.findall('.//ArticleIdList/ArticleId') if i.get('IdType') == 'doi'), None)
        pmc = next((i.text for i in art.findall('.//ArticleIdList/ArticleId') if i.get('IdType') == 'pmc'), None)
        abstract = ' '.join(clean(''.join(t.itertext())) for t in a.findall('.//Abstract/AbstractText'))
        out[pmid] = dict(source='pubmed', id=pmid, title=clean(''.join(a.find('ArticleTitle').itertext())).rstrip('.'), abstract=abstract,
                         date=year, year=int(year) if year and year.isdigit() else None, authors=authors,
                         venue=j.findtext('Title') if j is not None else None, volume=ji.findtext('Volume') if ji is not None else None,
                         issue=ji.findtext('Issue') if ji is not None else None,
                         pages=(a.findtext('.//Pagination/MedlinePgn') or '').replace('-', '–') or None, type='article', doi=doi, pmid=pmid, pmcid=pmc,
                         citations=None, open_access_url='https://pmc.ncbi.nlm.nih.gov/articles/%s/' % pmc if pmc else None,
                         url='https://pubmed.ncbi.nlm.nih.gov/%s/' % pmid)
    return [out[p] for p in pmids if p in out]


def search_pubmed(q, after, before, prioritize, limit):
    p = {'db': 'pubmed', 'retmode': 'json', 'retmax': str(min(max(limit, 1), 50)), 'sort': 'relevance', 'term': q}
    if after or before:
        p.update(datetype='pdat', mindate=(after or '1800-01-01').replace('-', '/'), maxdate=(before or '3000-12-31').replace('-', '/'))
    ids = json.loads(get(EUTILS + '/esearch.fcgi?' + urllib.parse.urlencode(p)))['esearchresult']['idlist']
    return rerank(pubmed_records(ids), prioritize if prioritize != 'popular' else 'default')


# ---------- arXiv ----------

def from_arxiv(e):
    aid = re.sub(r'v\d+$', '', e.findtext(ATOM + 'id').rsplit('/abs/', 1)[-1])
    doi = e.findtext('{http://arxiv.org/schemas/atom}doi')
    date = (e.findtext(ATOM + 'published') or '')[:10]
    return dict(source='arxiv', id=aid, title=clean(e.findtext(ATOM + 'title')), abstract=clean(e.findtext(ATOM + 'summary')), date=date,
                year=int(date[:4]) if date else None, authors=[a.findtext(ATOM + 'name') for a in e.findall(ATOM + 'author')],
                venue='arXiv', volume=None, issue=None, pages=None, type='preprint', doi=doi or '10.48550/arXiv.' + aid, pmid=None, pmcid=None,
                citations=None, open_access_url='https://arxiv.org/pdf/' + aid, url='https://arxiv.org/abs/' + aid)


def arxiv_query(params):
    feed = ET.fromstring(get(ARXIV + '?' + urllib.parse.urlencode(params)))
    return [from_arxiv(e) for e in feed.findall(ATOM + 'entry') if e.findtext(ATOM + 'id')]


def search_arxiv(q, after, before, prioritize, limit):
    sort = {'recency': 'submittedDate'}.get(prioritize, 'relevance')
    rows = arxiv_query({'search_query': 'all:' + q, 'max_results': str(min(max(limit, 1), 50)), 'sortBy': sort, 'sortOrder': 'descending'})
    rows = [r for r in rows if (not after or r['date'] >= after) and (not before or r['date'] <= before)]
    return rerank(rows, prioritize if prioritize in ('historical',) else 'default')


# ---------- one paper ----------

def kind(ref):
    ref = ref.strip()
    m = re.search(r'arxiv\.org/(?:abs|pdf)/([\w.\-/]+?)(?:v\d+)?(?:\.pdf)?/?(?:\?.*)?$', ref) or re.fullmatch(r'(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?', ref, re.I)
    if m:
        return 'arxiv', m.group(1)
    m = re.search(r'pubmed[^/]*/(\d+)', ref) or re.fullmatch(r'(?:PMID:?\s*)?(\d{5,9})', ref, re.I)
    if m:
        return 'pubmed', m.group(1)
    m = re.search(r'\b(W\d{4,})\b', ref)
    if m and ('openalex' in ref or ref.startswith('W')):
        return 'openalex', m.group(1)
    m = re.search(r'(10\.\d{4,9}/\S+)', ref)
    if m:
        return 'doi', trim_doi(m.group(1))
    raise ValueError('not a DOI, OpenAlex id, PMID or arXiv id: ' + ref)


def trim_doi(doi):
    """Drop trailing punctuation from a DOI found in running text. A closing bracket goes only when it has no
    opening partner, so older ASCE DOIs such as 10.1061/(asce)0733-9364(2002)128:1(18) keep theirs."""
    doi = doi.rstrip('.,;')
    while doi.endswith(')') and doi.count(')') > doi.count('('):
        doi = doi[:-1].rstrip('.,;')
    return doi


def paper(ref):
    k, v = kind(ref)
    if k == 'arxiv':
        rows = arxiv_query({'id_list': v})
        if not rows:
            raise LookupError('arXiv has no paper ' + v)
        return rows[0]
    if k == 'pubmed':
        rows = pubmed_records([v])
        if not rows:
            raise LookupError('PubMed has no record ' + v)
        return rows[0]
    path = '/works/' + (v if k == 'openalex' else 'https://doi.org/' + urllib.parse.quote(v, safe='/'))
    return from_openalex(json.loads(get(OPENALEX + path + '?select=' + WORK_FIELDS)))


def verify(doi):
    """Does this DOI exist? Crossref first, then OpenAlex, which also covers DataCite and arXiv DOIs."""
    doi = kind(doi)[1] if not doi.startswith('10.') else doi
    m = re.fullmatch(r'10\.48550/arxiv\.(.+)', doi, re.I)
    if m:  # arXiv DOIs live in DataCite, which neither registry below serves
        rows = arxiv_query({'id_list': m.group(1)})
        if not rows:
            return dict(doi=doi, found=False)
        r = rows[0]
        return dict(doi=doi, found=True, registry='arxiv', title=r['title'], year=r['year'], venue='arXiv',
                    authors=[a.split()[-1] for a in r['authors']])
    try:
        m = json.loads(get(CROSSREF + '/works/' + urllib.parse.quote(doi, safe='/')))['message']
        year = ((m.get('issued') or {}).get('date-parts') or [[None]])[0][0]
        return dict(doi=doi, found=True, registry='crossref', title=clean((m.get('title') or [''])[0]), year=year,
                    venue=(m.get('container-title') or [None])[0], authors=[a.get('family') for a in m.get('author', []) if a.get('family')])
    except LookupError:
        pass
    try:
        w = from_openalex(json.loads(get(OPENALEX + '/works/https://doi.org/' + urllib.parse.quote(doi, safe='/') + '?select=' + WORK_FIELDS)))
        return dict(doi=doi, found=True, registry='openalex', title=w['title'], year=w['year'], venue=w['venue'],
                    authors=[a.split()[-1] for a in w['authors']])
    except LookupError:
        return dict(doi=doi, found=False)


# ---------- reference strings ----------

def split_name(name):
    parts = name.replace(',', ' ').split()
    return (parts[-1], parts[:-1]) if ',' not in name else (name.split(',')[0].strip(), name.split(',')[1].split())


def initials(given, sep=' '):
    """One initial per name part: 'E.D.' and 'E. D.' both give E. D."""
    return sep.join(part[0].upper() + '.' for g in given for part in g.split('.') if part)


def crossref_year(message):
    """The year a reference cites: Crossref's print publication, else its issue's, else the issued date.
    OpenAlex's publication_year is the online-first year, which can run years ahead of the issue."""
    for d in (message.get('published-print'), (message.get('journal-issue') or {}).get('published-print'),
              message.get('issued'), message.get('published')):
        y = ((d or {}).get('date-parts') or [[None]])[0][0]
        if y:
            return y
    return None


def with_published_year(r):
    """Set a journal record's year from Crossref when Crossref holds the DOI; keep the index year otherwise."""
    if r.get('type') == 'preprint' or not r.get('doi') or re.match(r'10\.48550/', r['doi'], re.I):
        return r
    try:
        y = crossref_year(json.loads(get(CROSSREF + '/works/' + urllib.parse.quote(r['doi'], safe='/')))['message'])
    except (LookupError, ConnectionError, ValueError, KeyError):
        return r
    return dict(r, year=y) if y else r


def sentence_case(title):
    """Leave titles as the index gives them; most indexes already hold sentence case. Never invent capitals."""
    return title.rstrip('.')


def cite_apa(r):
    names = [split_name(a) for a in r['authors'][:20]]
    auth = ['%s, %s' % (s, initials(g)) if g else s for s, g in names]
    who = auth[0] if len(auth) == 1 else ', '.join(auth[:-1]) + ', & ' + auth[-1] if auth else r['title']
    out = '%s (%s). ' % (who, r.get('year') or 'n.d.')
    if r['type'] == 'preprint':
        out += '*%s* [Preprint]. %s.' % (sentence_case(r['title']), r['venue'])
    elif r.get('venue'):
        out += '%s. *%s' % (sentence_case(r['title']), r['venue'])
        out += ', %s*' % r['volume'] if r.get('volume') else '*'
        out += '(%s)' % r['issue'] if r.get('issue') and r.get('volume') else ''
        out += ', %s.' % r['pages'] if r.get('pages') else '.'
    else:
        out += '*%s*.' % sentence_case(r['title'])
    return out + (' https://doi.org/' + r['doi'] if r.get('doi') else '')


def cite_ieee(r):
    names = [split_name(a) for a in r['authors']]
    auth = [('%s %s' % (initials(g), s)).strip() for s, g in names]
    if len(auth) > 6:
        who = auth[0] + ' et al.'
    else:
        who = auth[0] if len(auth) == 1 else ' and '.join(auth) if len(auth) == 2 else ', '.join(auth[:-1]) + ', and ' + auth[-1] if auth else ''
    out = '%s, "%s," ' % (who, sentence_case(r['title']))
    if r['type'] == 'preprint':
        out += '%s, %s.' % ('arXiv:' + r['id'] if r['source'] == 'arxiv' else r['venue'], r.get('year'))
    else:
        out += '*%s*' % r['venue'] if r.get('venue') else ''
        out += ', vol. %s' % r['volume'] if r.get('volume') else ''
        out += ', no. %s' % r['issue'] if r.get('issue') else ''
        out += ', pp. %s' % r['pages'] if r.get('pages') else ''
        out += ', %s.' % r.get('year')
    return out + (' doi: ' + r['doi'] + '.' if r.get('doi') and r['type'] != 'preprint' else '')


def cite_bibtex(r):
    names = [split_name(a) for a in r['authors']]
    key = re.sub(r'\W', '', (names[0][0] if names else 'anon').lower()) + str(r.get('year') or '')
    fields = [('author', ' and '.join('%s, %s' % (s, ' '.join(g)) if g else '{%s}' % s for s, g in names)), ('title', '{%s}' % r['title']),
              ('journal', r.get('venue')), ('year', r.get('year')), ('volume', r.get('volume')), ('number', r.get('issue')),
              ('pages', (r.get('pages') or '').replace('–', '--') or None), ('doi', r.get('doi'))]
    body = ',\n'.join('  %s = {%s}' % (k, v) for k, v in fields if v)
    return '@%s{%s,\n%s\n}' % ('misc' if r['type'] == 'preprint' else 'article', key, body)


# ---------- claim check (statuses and spans after scholar-mcp, MIT) ----------

STATUSES = ['supported', 'partial', 'unsupported', 'contradicted']
JUDGE = ['1. Does the span support the claim directly, without extrapolation? Fully: supported. In part: partial.',
         '2. Only if not: does the span contradict the claim? Yes: contradicted. Otherwise: unsupported.']
STOP = set('the a an and or of in on for to with by from at as is are was were be been this that these those it its '
           'we our their they than then which who whom also not no but into over under between among per via'.split())


def norm(s):
    """One space for any run of white space, straight quotes for curly ones: what a quote is matched against."""
    s = (s or '').replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
    return re.sub(r'\s+', ' ', s.replace('\u00a0', ' ')).strip()


def sentences(text):
    """Sentences with exact offsets: [(start_char, end_char, sentence)]. Text is split per line, then after
    . ! or ? followed by a space and a capital, digit, bracket or quote."""
    out = []
    for line in re.finditer(r'[^\n]+', text):
        start = line.start()
        for piece in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"(\[])', line.group()):
            i = text.index(piece, start)
            if len(piece.strip()) > 20:
                out.append((i, i + len(piece), piece))
            start = i + len(piece)
    return out


def words(s):
    return {w for w in re.findall(r"[a-z0-9][a-z0-9%.\-]*[a-z0-9%]|[a-z0-9]", s.lower()) if w not in STOP and (len(w) > 2 or w.isdigit())}


class _Text(html.parser.HTMLParser):
    """Running text of an arXiv HTML paper: the article only, a formula as its TeX alt text, no bibliography."""
    SKIP = {'script', 'style', 'nav', 'header', 'footer', 'button', 'annotation', 'annotation-xml'}
    BLOCK = {'p', 'div', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'figcaption', 'td', 'th', 'tr', 'br', 'table'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.inside, self.skip = [], False, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.skip:
            self.skip[1] += tag == self.skip[0]
            return
        if tag == 'article':
            self.inside = True
        if not self.inside:
            return
        if tag == 'math':
            self.parts.append(' %s ' % (a.get('alttext') or ''))
            self.skip = [tag, 1]
        elif tag in self.SKIP or {'ltx_bibliography', 'ltx_authors'} & set((a.get('class') or '').split()):
            self.skip = [tag, 1]
        elif tag in self.BLOCK:
            self.parts.append('\n')

    def handle_startendtag(self, tag, attrs):
        if self.inside and not self.skip and tag == 'br':
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[0]:
                self.skip[1] -= 1
                if not self.skip[1]:
                    self.skip = None
            return
        if tag == 'article':
            self.inside = False
        elif self.inside and tag in self.BLOCK:
            self.parts.append('\n')

    def handle_data(self, data):
        if self.inside and not self.skip:
            self.parts.append(data.replace('\n', ' '))


def paragraphs(chunks):
    return '\n'.join(p for p in (norm(c) for c in chunks) if p)


def arxiv_text(page):
    t = _Text()
    t.feed(page.decode('utf-8', 'replace') if isinstance(page, bytes) else page)
    return paragraphs(''.join(t.parts).split('\n'))


def jats_text(xml):
    """Running text of a Europe PMC full-text XML: every paragraph and heading in the body, in order."""
    body = ET.fromstring(xml).find('body')
    out = []

    def walk(el):
        if el.tag in ('p', 'title'):
            out.append(''.join(el.itertext()))
            return
        for child in el:
            walk(child)
    if body is not None:
        walk(body)
    return paragraphs(out)


def europepmc_pmcid(r):
    """The PMCID Europe PMC files a paper under, found by PMID or DOI; None when it holds no full text."""
    q = 'EXT_ID:%s AND SRC:MED' % r['pmid'] if r.get('pmid') else 'DOI:"%s"' % r['doi'] if r.get('doi') else None
    if not q:
        return None
    try:
        hits = json.loads(get(EUROPEPMC + 'search?' + urllib.parse.urlencode({'query': q, 'format': 'json', 'resultType': 'lite'})))
    except (LookupError, ConnectionError, ValueError):
        return None
    return next((h['pmcid'] for h in (hits.get('resultList') or {}).get('result') or [] if h.get('pmcid')), None)


def full_text(r):
    """(text, source url, note): arXiv HTML for arXiv papers, Europe PMC XML for papers with a PMCID."""
    aid = r['id'] if r.get('source') == 'arxiv' else None
    m = re.fullmatch(r'10\.48550/arxiv\.(.+)', r.get('doi') or '', re.I)
    aid = aid or (m.group(1) if m else None)
    if not aid and not r.get('pmcid'):
        r = dict(r, pmcid=europepmc_pmcid(r))
    tries = ([(ARXIV_HTML + aid, arxiv_text)] if aid else []) + ([(EUROPEPMC + r['pmcid'] + '/fullTextXML', jats_text)] if r.get('pmcid') else [])
    if not tries:
        return '', None, 'no open full text this tool can read (arXiv HTML or Europe PMC); open_access_url may have one'
    notes = []
    for url, parse in tries:
        try:
            text = parse(get(url))
        except (LookupError, ConnectionError, ET.ParseError) as e:
            notes.append(str(e))
            continue
        if text:
            return text, url, None
        notes.append('no text in ' + url)
    return '', None, '; '.join(notes)


def check(ref, claim, quote=None, top=3):
    """Spans a finding can be judged against. Gives the status vocabulary and the order; never a status."""
    r = paper(ref)
    fields = [('abstract', norm(r.get('abstract')))]
    text, src, note = full_text(r)
    fields.append(('full_text', text))
    out = dict(id=ref, title=r['title'], doi=r.get('doi'), claim=claim, quote=quote,
               chars={f: len(t) for f, t in fields}, full_text_source=src)
    if note:
        out['full_text_note'] = note
    q = norm(quote) if quote else None
    found = next(((f, t.find(q)) for f, t in fields if q and t.find(q) >= 0), None)
    out.update(quote_found=bool(found), field=found[0] if found else None,
               start_char=found[1] if found else None, end_char=found[1] + len(q) if found else None)
    want = words(claim) | (words(quote) if quote else set())
    ranked = []
    for f, t in fields:
        for s, e, sent in sentences(t):
            holds = bool(found) and f == found[0] and s <= out['start_char'] < e
            ranked.append((not holds, -len(want & words(sent)), f != 'abstract', s, dict(field=f, start_char=s, end_char=e, text=sent,
                                                                                          shared_words=len(want & words(sent)))))
    ranked.sort(key=lambda x: x[:4])
    out['spans'] = [x[4] for x in ranked[:top]]
    if quote and not found:
        out['quote_note'] = 'the quote is not in the abstract or the full text: fix it from a span or drop it'
    out.update(status=None, statuses=STATUSES, judge=JUDGE)
    return out


# ---------- references and citing works (OpenAlex) ----------

LINK_FIELDS = 'id,doi,title,publication_year,cited_by_count'


def link_row(w):
    doi = (w.get('doi') or '').replace('https://doi.org/', '') or None
    return dict(id=w['id'].rsplit('/', 1)[-1], doi=doi, title=clean(w.get('title')), year=w.get('publication_year'),
                citations=w.get('cited_by_count'), url='https://doi.org/' + doi if doi else w['id'])


def openalex_work(ref, select):
    """The OpenAlex record for any id. An arXiv paper is matched by exact title, the most cited match first."""
    k, v = kind(ref)
    if k == 'openalex':
        return json.loads(get(OPENALEX + '/works/' + v + '?select=' + select)), 'id'
    if k == 'doi':
        return json.loads(get(OPENALEX + '/works/https://doi.org/' + urllib.parse.quote(v, safe='/') + '?select=' + select)), 'doi'
    if k == 'pubmed':
        return json.loads(get(OPENALEX + '/works/pmid:' + v + '?select=' + select)), 'pmid'
    r = paper(ref)
    p = {'filter': 'title.search:' + re.sub(r'[,:|]', ' ', r['title']), 'select': select + ',title', 'per-page': '25'}
    hits = [w for w in json.loads(get(OPENALEX + '/works?' + urllib.parse.urlencode(p)))['results']
            if norm(clean(w.get('title'))).lower() == norm(r['title']).lower()]
    if not hits:
        raise LookupError('OpenAlex has no work titled ' + r['title'])
    return max(hits, key=lambda w: w.get('cited_by_count') or 0), 'title'


def works_by_id(ids):
    rows = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        p = {'filter': 'openalex:' + '|'.join(chunk), 'select': LINK_FIELDS, 'per-page': '50'}
        for w in json.loads(get(OPENALEX + '/works?' + urllib.parse.urlencode(p)))['results']:
            rows[w['id'].rsplit('/', 1)[-1]] = link_row(w)
    return [rows[i] for i in ids if i in rows]


def refs(ref):
    w, by = openalex_work(ref, 'id,referenced_works')
    ids = [u.rsplit('/', 1)[-1] for u in w.get('referenced_works') or []]
    out = dict(id=ref, openalex_id=w['id'].rsplit('/', 1)[-1], matched_by=by, count=len(ids), results=works_by_id(ids))
    if not ids:
        out['note'] = 'OpenAlex holds no reference list for this work; read the references in its full text'
    return out


def cited_by(ref, limit=25):
    w, by = openalex_work(ref, 'id,cited_by_count')
    wid = w['id'].rsplit('/', 1)[-1]
    p = {'filter': 'cites:' + wid, 'select': LINK_FIELDS, 'sort': 'cited_by_count:desc', 'per-page': str(min(max(limit, 1), 200))}
    data = json.loads(get(OPENALEX + '/works?' + urllib.parse.urlencode(p)))
    return dict(id=ref, openalex_id=wid, matched_by=by, count=data['meta']['count'], results=[link_row(x) for x in data['results']])


# ---------- command line ----------

def main(argv):
    try:
        cmd = argv[0]
        if cmd == 'search':
            src, q, rest = argv[1], argv[2], argv[3:]
            opt = dict(after=None, before=None, prioritize='default', limit=15)
            while rest:
                k = rest.pop(0).lstrip('-').replace('published-', '')
                opt[k] = int(rest.pop(0)) if k == 'limit' else rest.pop(0)
            fn = dict(openalex=search_openalex, pubmed=search_pubmed, arxiv=search_arxiv)[src]
            out = dict(source=src, query=q, results=fn(q, opt['after'], opt['before'], opt['prioritize'], opt['limit']))
        elif cmd == 'paper':
            out = paper(argv[1])
        elif cmd == 'cite':
            fn = dict(apa=cite_apa, ieee=cite_ieee, bibtex=cite_bibtex)[argv[1]]
            out = []
            for ref in argv[2:]:
                r = with_published_year(paper(ref))
                out.append(dict(id=ref, reference=fn(r), record=r))
        elif cmd == 'verify':
            out = [verify(d) for d in argv[1:]]
        elif cmd == 'check':
            out = check(argv[1], argv[2], argv[3] if len(argv) > 3 else None)
        elif cmd == 'refs':
            out = refs(argv[1])
        elif cmd == 'cited-by':
            out = cited_by(argv[1], int(argv[3]) if len(argv) > 3 and argv[2] == '--limit' else 25)
        else:
            raise KeyError(cmd)
    except (IndexError, KeyError, ValueError) as e:
        print(__doc__, file=sys.stderr)
        print('error: %s' % e, file=sys.stderr)
        return 2
    except LookupError as e:
        print(json.dumps(dict(error='not_found', detail=str(e))))
        return 1
    except ConnectionError as e:
        print(json.dumps(dict(error='service_unavailable', detail=str(e))))
        return 3
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
