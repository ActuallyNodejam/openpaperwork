"""Offline tests for zotero.py against a small library built with the table shapes Zotero uses."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import zotero

DDL = """
CREATE TABLE libraries (libraryID INTEGER PRIMARY KEY, type TEXT NOT NULL);
CREATE TABLE groups (groupID INTEGER PRIMARY KEY, libraryID INT, name TEXT);
CREATE TABLE itemTypesCombined (itemTypeID INT PRIMARY KEY, typeName TEXT);
CREATE TABLE fieldsCombined (fieldID INT PRIMARY KEY, fieldName TEXT);
CREATE TABLE creatorTypes (creatorTypeID INTEGER PRIMARY KEY, creatorType TEXT);
CREATE TABLE items (itemID INTEGER PRIMARY KEY, itemTypeID INT, dateAdded TIMESTAMP DEFAULT CURRENT_TIMESTAMP, libraryID INT, key TEXT);
CREATE TABLE itemDataValues (valueID INTEGER PRIMARY KEY, value UNIQUE);
CREATE TABLE itemData (itemID INT, fieldID INT, valueID, PRIMARY KEY (itemID, fieldID));
CREATE TABLE creators (creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT, fieldMode INT);
CREATE TABLE itemCreators (itemID INT, creatorID INT, creatorTypeID INT, orderIndex INT);
CREATE TABLE collections (collectionID INTEGER PRIMARY KEY, collectionName TEXT, parentCollectionID INT, libraryID INT, key TEXT);
CREATE TABLE collectionItems (collectionID INT, itemID INT, orderIndex INT DEFAULT 0);
CREATE TABLE itemAttachments (itemID INTEGER PRIMARY KEY, parentItemID INT, linkMode INT, contentType TEXT, path TEXT);
CREATE TABLE itemNotes (itemID INTEGER PRIMARY KEY, parentItemID INT, note TEXT, title TEXT);
CREATE TABLE deletedItems (itemID INTEGER PRIMARY KEY);
CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE itemTags (itemID INT, tagID INT, type INT);
"""
FIELDS = {1: 'title', 2: 'abstractNote', 3: 'date', 4: 'publicationTitle', 5: 'volume', 6: 'issue', 7: 'pages', 8: 'DOI', 9: 'bookTitle', 10: 'publisher'}
TYPES = {1: 'journalArticle', 2: 'bookSection', 3: 'attachment', 4: 'note'}


def build(folder):
    db = sqlite3.connect(folder / 'zotero.sqlite')
    db.executescript(DDL)
    db.execute("INSERT INTO libraries VALUES (1, 'user')")
    db.executemany('INSERT INTO itemTypesCombined VALUES (?, ?)', TYPES.items())
    db.executemany('INSERT INTO fieldsCombined VALUES (?, ?)', FIELDS.items())
    db.executemany('INSERT INTO creatorTypes VALUES (?, ?)', [(1, 'author'), (2, 'editor')])
    values = {}

    def item(item_id, type_id, key, fields):
        db.execute('INSERT INTO items (itemID, itemTypeID, libraryID, key) VALUES (?, ?, 1, ?)', (item_id, type_id, key))
        for name, value in fields.items():
            if value not in values:
                values[value] = len(values) + 1
                db.execute('INSERT INTO itemDataValues VALUES (?, ?)', (values[value], value))
            db.execute('INSERT INTO itemData VALUES (?, ?, ?)', (item_id, next(k for k, v in FIELDS.items() if v == name), values[value]))
    item(1, 1, 'AAAA1111', dict(title='Sleep duration and next-day recall', abstractNote='Each extra hour helped recall.', date='2021-03-00 March 2021',
                                publicationTitle='Journal of Student Sleep Research', volume='14', issue='2', pages='101-118', DOI='10.5555/jssr.14.2.101'))
    item(2, 2, 'BBBB2222', dict(title='Sleep and consolidation of declarative memory', date='2018', bookTitle='Memory in everyday learning', pages='77-98', publisher='Harbourview Academic'))
    item(3, 1, 'CCCC3333', dict(title='A deleted article about naps', date='2010'))
    item(4, 3, 'DDDD4444', {})
    item(5, 4, 'EEEE5555', {})
    db.executemany('INSERT INTO creators VALUES (?, ?, ?, ?)', [(1, 'Annika', 'Lindqvist', 0), (2, 'Kwame', 'Osei', 0), (3, '', 'Student Wellbeing Group', 1), (4, 'Sunita', 'Patel', 0)])
    db.executemany('INSERT INTO itemCreators VALUES (?, ?, ?, ?)', [(1, 1, 1, 0), (1, 2, 1, 1), (2, 3, 1, 0), (2, 4, 2, 1)])
    db.executemany('INSERT INTO collections VALUES (?, ?, ?, 1, ?)', [(1, 'Thesis', None, 'K1'), (2, 'Chapter 2', 1, 'K2')])
    db.executemany('INSERT INTO collectionItems (collectionID, itemID) VALUES (?, ?)', [(2, 1), (1, 2), (1, 3)])
    db.execute("INSERT INTO itemAttachments VALUES (4, 1, 0, 'application/pdf', 'storage:lindqvist.pdf')")
    db.execute("INSERT INTO itemNotes VALUES (5, 1, '<p>Correlational, <b>96</b> students.</p>', 'n')")
    db.execute('INSERT INTO deletedItems VALUES (3)')
    db.execute("INSERT INTO tags VALUES (1, 'to-cite')")
    db.execute('INSERT INTO itemTags VALUES (1, 1, 0)')
    db.commit()
    db.close()
    (folder / 'storage' / 'DDDD4444').mkdir(parents=True)
    (folder / 'storage' / 'DDDD4444' / 'lindqvist.pdf').write_bytes(b'%PDF-1.4')


class ZoteroLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        build(Path(self.tmp.name))
        os.environ['ZOTERO_DATA_DIR'] = self.tmp.name
        self.lib = zotero.Library()

    def tearDown(self):
        self.lib.close()
        self.tmp.cleanup()
        os.environ.pop('ZOTERO_DATA_DIR')

    def test_collections_count_only_live_works(self):
        cols = {c['path']: c['items'] for c in self.lib.collections()}
        self.assertEqual(cols, {'Thesis': 1, 'Thesis / Chapter 2': 1})

    def test_collection_includes_subcollections_and_skips_deleted(self):
        keys = sorted(self.lib.record(i)['key'] for i in self.lib.item_ids('Thesis'))
        self.assertEqual(keys, ['AAAA1111', 'BBBB2222'])

    def test_record(self):
        r = self.lib.by_key('AAAA1111')
        self.assertEqual((r['year'], r['venue'], r['pages'], r['doi'], r['type']), (2021, 'Journal of Student Sleep Research', '101–118', '10.5555/jssr.14.2.101', 'article'))
        self.assertEqual(r['authors'], ['Annika Lindqvist', 'Kwame Osei'])
        self.assertEqual(r['notes'], ['Correlational, 96 students.'])
        self.assertEqual(r['tags'], ['to-cite'])
        self.assertTrue(r['files'][0]['exists'])

    def test_chapter_group_author_and_editor(self):
        r = self.lib.by_key('BBBB2222')
        self.assertEqual((r['type'], r['venue'], r['authors'], r['editors']), ('chapter', 'Memory in everyday learning', ['Student Wellbeing Group'], ['Sunita Patel']))

    def test_search(self):
        self.assertEqual([r['key'] for r in self.lib.search('recall sleep')], ['AAAA1111'])
        self.assertEqual(self.lib.search('naps'), [])

    def test_tag_and_missing(self):
        self.assertEqual(len(self.lib.item_ids(tag='to-cite')), 1)
        with self.assertRaises(LookupError):
            self.lib.collection_ids('Nope')

    def test_library_is_not_changed(self):
        before = (Path(self.tmp.name) / 'zotero.sqlite').read_bytes()
        self.lib.search('sleep')
        self.assertEqual(before, (Path(self.tmp.name) / 'zotero.sqlite').read_bytes())

    def test_cli_no_library(self):
        os.environ['ZOTERO_DATA_DIR'] = '/nonexistent'
        self.assertEqual(zotero.main(['collections']), 1)
        os.environ['ZOTERO_DATA_DIR'] = self.tmp.name


if __name__ == '__main__':
    unittest.main()
