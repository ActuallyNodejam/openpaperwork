#!/usr/bin/env python3
"""Read the person's own Zotero library from this computer. Read-only, standard library only, no key, no login.

  zotero.py where
  zotero.py collections
  zotero.py items [--collection "<name>"] [--tag "<tag>"] [--limit N]
  zotero.py search "<words>" [--collection "<name>"] [--limit N]
  zotero.py item <key> [<key> ...]

Every command prints JSON. Records use the same fields as the literature-search tool (title, authors, year,
venue, volume, issue, pages, doi, type, url, abstract) plus key, collections, tags, notes and the paths of
attached files. The library is never changed: the database is copied to a temporary file and opened read-only,
so it works while Zotero is open.
"""
import glob
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

TYPES = {'journalArticle': 'article', 'conferencePaper': 'article', 'magazineArticle': 'article', 'newspaperArticle': 'article',
         'book': 'book', 'bookSection': 'chapter', 'preprint': 'preprint', 'report': 'report', 'thesis': 'thesis',
         'webpage': 'webpage', 'dataset': 'dataset', 'computerProgram': 'software'}
VENUE = ('publicationTitle', 'proceedingsTitle', 'bookTitle', 'conferenceName', 'repository', 'institution', 'university', 'websiteTitle', 'publisher')
SKIP = ('attachment', 'note', 'annotation')


def data_dir():
    """The Zotero data folder: ZOTERO_DATA_DIR, a custom folder set in Zotero's own settings, or ~/Zotero."""
    env = os.environ.get('ZOTERO_DATA_DIR')
    if env:
        return Path(env).expanduser()
    home = Path.home()
    profiles = [home / 'Library/Application Support/Zotero/Profiles', home / '.zotero/zotero',
                Path(os.environ.get('APPDATA', home / 'AppData/Roaming')) / 'Zotero/Zotero/Profiles']
    for root in profiles:
        for prefs in glob.glob(str(root / '*' / 'prefs.js')):
            text = Path(prefs).read_text(errors='replace')
            if re.search(r'user_pref\("extensions\.zotero\.useDataDir",\s*true\)', text):
                m = re.search(r'user_pref\("extensions\.zotero\.dataDir",\s*"((?:[^"\\]|\\.)*)"\)', text)
                if m:
                    return Path(m.group(1).replace('\\\\', '\\'))
    return home / 'Zotero'


class Library:
    def __init__(self, folder=None):
        self.dir = Path(folder) if folder else data_dir()
        src = self.dir / 'zotero.sqlite'
        if not src.is_file():
            raise FileNotFoundError('No Zotero library found at %s' % self.dir)
        self.tmp = Path(tempfile.mkdtemp(prefix='zotero-read-'))
        copy = self.tmp / 'zotero.sqlite'
        shutil.copyfile(src, copy)
        self.db = sqlite3.connect('file:%s?mode=ro' % copy, uri=True)
        try:
            self.db.execute('SELECT 1 FROM items LIMIT 1').fetchall()
        except sqlite3.DatabaseError:  # copied mid-write; Zotero keeps its own backup beside the database
            self.db.close()
            shutil.copyfile(self.dir / 'zotero.sqlite.bak', copy)
            self.db = sqlite3.connect('file:%s?mode=ro' % copy, uri=True)
        self.db.row_factory = sqlite3.Row

    def close(self):
        self.db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def q(self, sql, args=()):
        return self.db.execute(sql, args).fetchall()

    def libraries(self):
        names = {r['libraryID']: r['name'] for r in self.q('SELECT libraryID, name FROM groups')}
        return {r['libraryID']: names.get(r['libraryID'], 'My Library') for r in self.q("SELECT libraryID FROM libraries WHERE type IN ('user', 'group')")}

    def collections(self):
        rows = self.q('SELECT c.collectionID, c.collectionName, c.parentCollectionID, c.libraryID, '
                      '(SELECT COUNT(*) FROM collectionItems ci JOIN items i USING (itemID) JOIN itemTypesCombined t USING (itemTypeID) '
                      ' WHERE ci.collectionID = c.collectionID AND t.typeName NOT IN (?, ?, ?) '
                      ' AND i.itemID NOT IN (SELECT itemID FROM deletedItems)) AS n FROM collections c ORDER BY c.collectionName', SKIP)
        by = {r['collectionID']: r for r in rows}
        libs = self.libraries()

        def path(r):
            parts = [r['collectionName']]
            while r['parentCollectionID'] in by:
                r = by[r['parentCollectionID']]
                parts.insert(0, r['collectionName'])
            return ' / '.join(parts)
        return [dict(id=r['collectionID'], name=r['collectionName'], path=path(r), library=libs.get(r['libraryID'], 'My Library'), items=r['n']) for r in rows]

    def collection_ids(self, name):
        cols = self.collections()
        hit = [c for c in cols if name.lower() in (c['name'].lower(), c['path'].lower())] or [c for c in cols if name.lower() in c['path'].lower()]
        if not hit:
            raise LookupError('No collection named %r. Collections: %s' % (name, ', '.join(c['path'] for c in cols) or 'none'))
        ids, grew = {c['id'] for c in hit}, True
        while grew:  # sub-collections belong to their parent
            kids = {r['collectionID'] for r in self.q('SELECT collectionID, parentCollectionID FROM collections') if r['parentCollectionID'] in ids}
            grew = not kids <= ids
            ids |= kids
        return ids

    def item_ids(self, collection=None, tag=None):
        sql = ('SELECT i.itemID FROM items i JOIN itemTypesCombined t USING (itemTypeID) WHERE t.typeName NOT IN (?, ?, ?) '
               'AND i.itemID NOT IN (SELECT itemID FROM deletedItems)')
        args = list(SKIP)
        if collection:
            ids = sorted(self.collection_ids(collection))
            sql += ' AND i.itemID IN (SELECT itemID FROM collectionItems WHERE collectionID IN (%s))' % ','.join('?' * len(ids))
            args += ids
        if tag:
            sql += ' AND i.itemID IN (SELECT itemID FROM itemTags JOIN tags USING (tagID) WHERE name = ? COLLATE NOCASE)'
            args.append(tag)
        return [r['itemID'] for r in self.q(sql + ' ORDER BY i.dateAdded DESC', args)]

    def record(self, item_id, full=False):
        base = self.q('SELECT i.key, i.libraryID, i.dateAdded, t.typeName FROM items i JOIN itemTypesCombined t USING (itemTypeID) WHERE i.itemID = ?', (item_id,))[0]
        f = {r['fieldName']: r['value'] for r in self.q('SELECT f.fieldName, v.value FROM itemData d JOIN fieldsCombined f USING (fieldID) '
                                                         'JOIN itemDataValues v USING (valueID) WHERE d.itemID = ?', (item_id,))}
        people = self.q('SELECT c.firstName, c.lastName, c.fieldMode, ct.creatorType FROM itemCreators ic JOIN creators c USING (creatorID) '
                        'JOIN creatorTypes ct USING (creatorTypeID) WHERE ic.itemID = ? ORDER BY ic.orderIndex', (item_id,))
        name = lambda p: p['lastName'] if p['fieldMode'] == 1 or not p['firstName'] else '%s %s' % (p['firstName'], p['lastName'])
        date = str(f.get('date') or '')
        year = re.match(r'(\d{4})', date)
        doi = (f.get('DOI') or '').replace('https://doi.org/', '') or None
        if not doi:
            m = re.search(r'\bDOI:\s*(10\.\S+)', f.get('extra') or '', re.I)
            doi = m.group(1) if m else None
        files = []
        for a in self.q('SELECT ia.path, ia.contentType, i.key FROM itemAttachments ia JOIN items i ON i.itemID = ia.itemID WHERE ia.parentItemID = ? '
                        'AND ia.itemID NOT IN (SELECT itemID FROM deletedItems)', (item_id,)):
            if a['path'] and a['path'].startswith('storage:'):
                p = self.dir / 'storage' / a['key'] / a['path'][8:]
                files.append(dict(path=str(p), type=a['contentType'], exists=p.is_file()))
            elif a['path']:
                files.append(dict(path=a['path'], type=a['contentType'], exists=Path(a['path']).is_file()))
        out = dict(source='zotero', id=base['key'], key=base['key'], title=f.get('title') or '', date=date.split(' ')[0] or None,
                   year=int(year.group(1)) if year else None, authors=[name(p) for p in people if p['creatorType'] == 'author'],
                   editors=[name(p) for p in people if p['creatorType'] == 'editor'], venue=next((f[k] for k in VENUE if f.get(k)), None),
                   volume=f.get('volume'), issue=f.get('issue'), pages=(f.get('pages') or '').replace('-', '–') or None,
                   publisher=f.get('publisher'), type=TYPES.get(base['typeName'], base['typeName']), doi=doi, url=f.get('url') or ('https://doi.org/' + doi if doi else None),
                   library=self.libraries().get(base['libraryID'], 'My Library'), added=base['dateAdded'], files=files,
                   collections=[r['collectionName'] for r in self.q('SELECT collectionName FROM collections JOIN collectionItems USING (collectionID) WHERE itemID = ?', (item_id,))],
                   tags=[r['name'] for r in self.q('SELECT name FROM tags JOIN itemTags USING (tagID) WHERE itemID = ?', (item_id,))])
        if full:
            out['abstract'] = f.get('abstractNote') or ''
            out['notes'] = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', r['note'] or '')).strip()
                            for r in self.q('SELECT note FROM itemNotes WHERE parentItemID = ? AND itemID NOT IN (SELECT itemID FROM deletedItems)', (item_id,))]
            out['fields'] = {k: v for k, v in f.items() if k not in ('abstractNote',)}
        return out

    def search(self, words, collection=None):
        terms = [w.lower() for w in re.findall(r'\w+', words)]
        hits = []
        for i in self.item_ids(collection):
            r = self.record(i, full=True)
            hay = ' '.join([r['title'], r['abstract'], ' '.join(r['authors']), r['venue'] or '', ' '.join(r['tags']), ' '.join(r['notes']), str(r['year'] or '')]).lower()
            score = sum(hay.count(t) for t in terms) + 3 * sum(t in r['title'].lower() for t in terms)
            if all(t in hay for t in terms):
                r.pop('fields'), r.pop('notes')
                hits.append((score, r))
        return [r for _, r in sorted(hits, key=lambda x: -x[0])]

    def by_key(self, key):
        rows = self.q('SELECT itemID FROM items WHERE key = ?', (key,))
        if not rows:
            raise LookupError('No item with key %s' % key)
        return self.record(rows[0]['itemID'], full=True)


def main(argv):
    try:
        cmd, rest = argv[0], argv[1:]
        opt = dict(collection=None, tag=None, limit=50)
        pos = []
        while rest:
            a = rest.pop(0)
            if a.startswith('--'):
                opt[a[2:]] = int(rest.pop(0)) if a == '--limit' else rest.pop(0)
            else:
                pos.append(a)
        if cmd == 'where':
            d = data_dir()
            print(json.dumps(dict(folder=str(d), found=(d / 'zotero.sqlite').is_file())))
            return 0
        lib = Library()
    except IndexError:
        print(__doc__, file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(json.dumps(dict(error='no_library', detail=str(e))))
        return 1
    try:
        if cmd == 'collections':
            out = lib.collections()
        elif cmd == 'items':
            ids = lib.item_ids(opt['collection'], opt['tag'])
            out = dict(total=len(ids), items=[lib.record(i) for i in ids[:opt['limit']]])
        elif cmd == 'search':
            found = lib.search(pos[0], opt['collection'])
            out = dict(total=len(found), items=found[:opt['limit']])
        elif cmd == 'item':
            out = [lib.by_key(k) for k in pos]
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except LookupError as e:
        print(json.dumps(dict(error='not_found', detail=str(e))))
        return 1
    finally:
        lib.close()
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
