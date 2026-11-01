"""Offline tests for papers.py: id routing, record mapping, reference strings, the claim check and the
reference graph. No network."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import papers

RECORD = dict(source='openalex', id='W1', title='Deep learning', abstract='', date='2015-05-27', year=2015,
              authors=['Yann LeCun', 'Yoshua Bengio', 'Geoffrey E. Hinton'], venue='Nature', volume='521', issue='7553',
              pages='436–444', type='article', doi='10.1038/nature14539', pmid=None, citations=1, open_access_url=None, url='')


class Kind(unittest.TestCase):
    def test_routes(self):
        self.assertEqual(papers.kind('https://arxiv.org/abs/1706.03762v5'), ('arxiv', '1706.03762'))
        self.assertEqual(papers.kind('arXiv:2401.12345'), ('arxiv', '2401.12345'))
        self.assertEqual(papers.kind('https://pubmed.ncbi.nlm.nih.gov/38308006/'), ('pubmed', '38308006'))
        self.assertEqual(papers.kind('W2919115771'), ('openalex', 'W2919115771'))
        self.assertEqual(papers.kind('https://doi.org/10.1038/nature14539.'), ('doi', '10.1038/nature14539'))
        with self.assertRaises(ValueError):
            papers.kind('not an id')

    def test_doi_keeps_balanced_brackets(self):
        asce = '10.1061/(asce)0733-9364(2002)128:1(18)'
        self.assertEqual(papers.kind(asce), ('doi', asce))
        self.assertEqual(papers.kind('https://doi.org/' + asce + '.'), ('doi', asce))
        self.assertEqual(papers.kind('(see 10.1038/nature14539)'), ('doi', '10.1038/nature14539'))
        self.assertEqual(papers.kind('(see ' + asce + ').'), ('doi', asce))


class Mapping(unittest.TestCase):
    def test_abstract_from_inverted_index(self):
        self.assertEqual(papers.abstract_of({'sleep': [1], 'Short': [0], 'common': [3], 'is': [2]}), 'Short sleep is common')
        self.assertEqual(papers.abstract_of(None), '')

    def test_openalex_record(self):
        r = papers.from_openalex({'id': 'https://openalex.org/W1', 'doi': 'https://doi.org/10.1/x', 'title': 'A <i>title</i>',
                                  'publication_date': '2020-01-02', 'publication_year': 2020, 'cited_by_count': 3, 'type': 'article',
                                  'authorships': [{'author': {'display_name': 'Ann Lee'}}], 'biblio': {'volume': '1', 'first_page': '3', 'last_page': '9'},
                                  'primary_location': {'source': {'display_name': 'J. Test'}}, 'open_access': {'oa_url': None}, 'ids': {}})
        self.assertEqual((r['id'], r['doi'], r['title'], r['pages'], r['venue']), ('W1', '10.1/x', 'A title', '3–9', 'J. Test'))

    def test_rerank(self):
        rows = [dict(date='2019', citations=5), dict(date='2021', citations=1)]
        self.assertEqual(papers.rerank(list(rows), 'recency')[0]['date'], '2021')
        self.assertEqual(papers.rerank(list(rows), 'popular')[0]['citations'], 5)


class Cite(unittest.TestCase):
    def test_initials_keep_every_part(self):
        self.assertEqual(papers.initials(['Peter', 'E.D.']), 'P. E. D.')
        self.assertEqual(papers.initials(['E.', 'D.']), 'E. D.')
        love = dict(RECORD, authors=['Peter E.D. Love'])
        self.assertTrue(papers.cite_apa(love).startswith('Love, P. E. D. (2015).'))
        self.assertTrue(papers.cite_ieee(love).startswith('P. E. D. Love,'))

    def test_year_is_crossref_print_year(self):
        # 10.1061/(asce)cf.1943-5509.0000415: online first in 2012, vol 28 no 2 in April 2014
        msg = {'published-online': {'date-parts': [[2012, 6, 1]]}, 'published-print': {'date-parts': [[2014, 4]]},
               'issued': {'date-parts': [[2012, 6, 1]]}, 'journal-issue': {'issue': '2', 'published-print': {'date-parts': [[2014, 4]]}}}
        self.assertEqual(papers.crossref_year(msg), 2014)
        self.assertEqual(papers.crossref_year({'issued': {'date-parts': [[2019]]}}), 2019)
        self.assertIsNone(papers.crossref_year({}))
        rec = dict(RECORD, doi='10.1061/(asce)cf.1943-5509.0000415', year=2012)
        real = papers.get
        papers.get = lambda url, tries=3: json.dumps({'message': msg}).encode()
        try:
            self.assertEqual(papers.with_published_year(rec)['year'], 2014)
            self.assertIn('(2014)', papers.cite_apa(papers.with_published_year(rec)))
            self.assertEqual(papers.with_published_year(dict(rec, type='preprint'))['year'], 2012)
        finally:
            papers.get = real

    def test_apa(self):
        self.assertEqual(papers.cite_apa(RECORD), 'LeCun, Y., Bengio, Y., & Hinton, G. E. (2015). Deep learning. *Nature, 521*(7553), 436–444. '
                                                  'https://doi.org/10.1038/nature14539')

    def test_ieee(self):
        self.assertEqual(papers.cite_ieee(RECORD), 'Y. LeCun, Y. Bengio, and G. E. Hinton, "Deep learning," *Nature*, vol. 521, no. 7553, pp. 436–444, 2015. '
                                                   'doi: 10.1038/nature14539.')
        many = dict(RECORD, authors=['A B'] * 7)
        self.assertTrue(papers.cite_ieee(many).startswith('A. B et al.,'))

    def test_bibtex(self):
        out = papers.cite_bibtex(RECORD)
        self.assertIn('@article{lecun2015,', out)
        self.assertIn('pages = {436--444}', out)


ARXIV_PAGE = """<html><head><title>T</title><script>var x = 1;</script></head><body><nav>Menu</nav>
<article class="ltx_document ltx_authors_1line"><h1>A title</h1><div class="ltx_authors">Ann Lee</div>
<p>We train a model with <math alttext="7" display="inline"><semantics><mn>7</mn><annotation>7</annotation></semantics></math> billion
parameters. It beats the 13B baseline on every benchmark we tried.</p>
<section class="ltx_bibliography"><p>Smith, J. A cited paper that should not count.</p></section></article>
<footer>arXiv footer</footer></body></html>"""

JATS = b"""<article><front><p>front matter</p></front><body><sec><title>Results</title>
<p>Short sleep was common in the sample. It rose with age (<xref>3</xref>).</p></sec></body></article>"""


class Check(unittest.TestCase):
    def test_spans_carry_exact_offsets(self):
        text = 'Short sleep is common in adults. It rose with age e.g. after 60. The rate was 31.5% overall!\nResults improved later on.'
        for s, e, sent in papers.sentences(text):
            self.assertEqual(text[s:e], sent)
        self.assertEqual([x[2] for x in papers.sentences(text)][-1], 'Results improved later on.')

    def test_norm_matches_curly_quotes_and_spaces(self):
        self.assertEqual(papers.norm('it\u2019s  \u201cfine\u201d\n now'), 'it\'s "fine" now')

    def test_arxiv_html_text(self):
        text = papers.arxiv_text(ARXIV_PAGE)
        self.assertIn('We train a model with 7 billion parameters.', text)
        for gone in ('var x', 'Menu', 'Ann Lee', 'Smith', 'footer'):
            self.assertNotIn(gone, text)

    def test_jats_text(self):
        self.assertEqual(papers.jats_text(JATS), 'Results\nShort sleep was common in the sample. It rose with age (3).')

    def test_check_finds_quote_and_ranks_spans(self):
        rec = dict(RECORD, source='arxiv', id='2401.00001', type='preprint', doi='10.48550/arXiv.2401.00001', pmcid=None,
                   abstract='We study a small model. Our model beats the larger baseline on reasoning tasks.')
        real_paper, real_get = papers.paper, papers.get
        papers.paper = lambda ref: rec
        papers.get = lambda url, tries=3: ARXIV_PAGE.encode()
        try:
            out = papers.check('2401.00001', 'The 7 billion parameter model beats the 13B baseline',
                               'It beats the 13B baseline on every benchmark we tried.')
            self.assertTrue(out['quote_found'])
            self.assertEqual(out['field'], 'full_text')
            first = out['spans'][0]
            self.assertEqual(first['field'], 'full_text')
            self.assertLessEqual(first['start_char'], out['start_char'])
            self.assertGreaterEqual(first['end_char'], out['end_char'])
            self.assertEqual(out['full_text_source'], 'https://arxiv.org/html/2401.00001')
            self.assertIsNone(out['status'])
            self.assertEqual(out['statuses'], ['supported', 'partial', 'unsupported', 'contradicted'])
            self.assertTrue(out['judge'][0].startswith('1.') and 'contradict' in out['judge'][1])
            missing = papers.check('2401.00001', 'claim', 'a sentence nobody wrote')
            self.assertFalse(missing['quote_found'])
            self.assertIn('quote_note', missing)
            self.assertLessEqual(len(missing['spans']), 3)
        finally:
            papers.paper, papers.get = real_paper, real_get

    def test_check_without_full_text(self):
        rec = dict(RECORD, abstract='Deep learning allows models to learn representations of data.', pmcid=None)
        real, real_get = papers.paper, papers.get
        papers.paper = lambda ref: rec
        papers.get = lambda url, tries=3: b'{"resultList": {"result": [{"pmid": "1"}]}}'
        try:
            out = papers.check('10.1038/nature14539', 'models learn representations')
            self.assertEqual(out['chars']['full_text'], 0)
            self.assertIn('full_text_note', out)
            self.assertEqual(out['spans'][0]['field'], 'abstract')
        finally:
            papers.paper, papers.get = real, real_get

    def test_europe_pmc_full_text_by_doi(self):
        rec = dict(RECORD, abstract='Short sleep is common.', pmcid=None, pmid=None)
        seen = []

        def fake(url, tries=3):
            seen.append(url)
            return b'{"resultList": {"result": [{"pmcid": "PMC123"}]}}' if '/search?' in url else JATS
        real, real_get = papers.paper, papers.get
        papers.paper, papers.get = (lambda ref: rec), fake
        try:
            out = papers.check('10.1038/nature14539', 'short sleep rose with age', 'It rose with age (3).')
        finally:
            papers.paper, papers.get = real, real_get
        self.assertIn('DOI%3A%2210.1038%2Fnature14539%22', seen[0])
        self.assertEqual(out['full_text_source'], papers.EUROPEPMC + 'PMC123/fullTextXML')
        self.assertEqual((out['quote_found'], out['field']), (True, 'full_text'))


class Graph(unittest.TestCase):
    def test_refs_keep_reference_order(self):
        def fake(url, tries=3):
            if '/works/W1001?' in url:
                return json.dumps({'id': 'https://openalex.org/W1001', 'referenced_works': ['https://openalex.org/W1003', 'https://openalex.org/W1002']}).encode()
            return json.dumps({'results': [
                {'id': 'https://openalex.org/W1002', 'doi': 'https://doi.org/10.1/b', 'title': 'B', 'publication_year': 2001, 'cited_by_count': 4},
                {'id': 'https://openalex.org/W1003', 'doi': None, 'title': 'C', 'publication_year': 2002, 'cited_by_count': 1}]}).encode()
        real = papers.get
        papers.get = fake
        try:
            out = papers.refs('W1001')
        finally:
            papers.get = real
        self.assertEqual([r['id'] for r in out['results']], ['W1003', 'W1002'])
        self.assertEqual((out['count'], out['results'][1]['url']), (2, 'https://doi.org/10.1/b'))

    def test_cited_by_filters_on_cites(self):
        seen = []

        def fake(url, tries=3):
            seen.append(url)
            if '/works/W1001?' in url:
                return json.dumps({'id': 'https://openalex.org/W1001', 'cited_by_count': 9}).encode()
            return json.dumps({'meta': {'count': 9}, 'results': [{'id': 'https://openalex.org/W1005', 'title': 'E', 'cited_by_count': 2}]}).encode()
        real = papers.get
        papers.get = fake
        try:
            out = papers.cited_by('W1001', 5)
        finally:
            papers.get = real
        self.assertIn('filter=cites%3AW1', seen[-1])
        self.assertIn('per-page=5', seen[-1])
        self.assertEqual((out['count'], out['results'][0]['id']), (9, 'W1005'))


if __name__ == '__main__':
    unittest.main()
