# Copyright (C) 2003 Python Software Foundation

import struct
import unittest
import plistlib
import os
import datetime
from test import test_support


# This test data was generated through Cocoa's NSDictionary class
TESTDATA = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
        <key>aDate</key>
        <date>2004-10-26T10:33:33Z</date>
        <key>aDict</key>
        <dict>
                <key>aFalseValue</key>
                <false/>
                <key>aTrueValue</key>
                <true/>
                <key>aUnicodeValue</key>
                <string>M\xc3\xa4ssig, Ma\xc3\x9f</string>
                <key>anotherString</key>
                <string>&lt;hello &amp; 'hi' there!&gt;</string>
                <key>deeperDict</key>
                <dict>
                        <key>a</key>
                        <integer>17</integer>
                        <key>b</key>
                        <real>32.5</real>
                        <key>c</key>
                        <array>
                                <integer>1</integer>
                                <integer>2</integer>
                                <string>text</string>
                        </array>
                </dict>
        </dict>
        <key>aFloat</key>
        <real>0.5</real>
        <key>aList</key>
        <array>
                <string>A</string>
                <string>B</string>
                <integer>12</integer>
                <real>32.5</real>
                <array>
                        <integer>1</integer>
                        <integer>2</integer>
                        <integer>3</integer>
                </array>
        </array>
        <key>aString</key>
        <string>Doodah</string>
        <key>anInt</key>
        <integer>728</integer>
        <key>nestedData</key>
        <array>
                <data>
                PGxvdHMgb2YgYmluYXJ5IGd1bms+AAECAzxsb3RzIG9mIGJpbmFyeSBndW5r
                PgABAgM8bG90cyBvZiBiaW5hcnkgZ3Vuaz4AAQIDPGxvdHMgb2YgYmluYXJ5
                IGd1bms+AAECAzxsb3RzIG9mIGJpbmFyeSBndW5rPgABAgM8bG90cyBvZiBi
                aW5hcnkgZ3Vuaz4AAQIDPGxvdHMgb2YgYmluYXJ5IGd1bms+AAECAzxsb3Rz
                IG9mIGJpbmFyeSBndW5rPgABAgM8bG90cyBvZiBiaW5hcnkgZ3Vuaz4AAQID
                PGxvdHMgb2YgYmluYXJ5IGd1bms+AAECAw==
                </data>
        </array>
        <key>someData</key>
        <data>
        PGJpbmFyeSBndW5rPg==
        </data>
        <key>someMoreData</key>
        <data>
        PGxvdHMgb2YgYmluYXJ5IGd1bms+AAECAzxsb3RzIG9mIGJpbmFyeSBndW5rPgABAgM8
        bG90cyBvZiBiaW5hcnkgZ3Vuaz4AAQIDPGxvdHMgb2YgYmluYXJ5IGd1bms+AAECAzxs
        b3RzIG9mIGJpbmFyeSBndW5rPgABAgM8bG90cyBvZiBiaW5hcnkgZ3Vuaz4AAQIDPGxv
        dHMgb2YgYmluYXJ5IGd1bms+AAECAzxsb3RzIG9mIGJpbmFyeSBndW5rPgABAgM8bG90
        cyBvZiBiaW5hcnkgZ3Vuaz4AAQIDPGxvdHMgb2YgYmluYXJ5IGd1bms+AAECAw==
        </data>
        <key>\xc3\x85benraa</key>
        <string>That was a unicode key.</string>
</dict>
</plist>
""".replace(" " * 8, "\t")  # Apple as well as plistlib.py output hard tabs

XML_PLIST_WITH_ENTITY=b'''\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd" [
   <!ENTITY entity "replacement text">
  ]>
<plist version="1.0">
  <dict>
    <key>A</key>
    <string>&entity;</string>
  </dict>
</plist>
'''

INVALID_BINARY_PLISTS = [
    ('too short data',
        b''
    ),
    ('too large offset_table_offset and offset_size = 1',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x2a'
    ),
    ('too large offset_table_offset and nonstandard offset_size',
        b'\x00\x00\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x03\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x2c'
    ),
    ('integer overflow in offset_table_offset',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\xff\xff\xff\xff\xff\xff\xff\xff'
    ),
    ('too large top_object',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('integer overflow in top_object',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\xff\xff\xff\xff\xff\xff\xff\xff'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('too large num_objects and offset_size = 1',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\xff'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('too large num_objects and nonstandard offset_size',
        b'\x00\x00\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x03\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\xff'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('extremally large num_objects (32 bit)',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x7f\xff\xff\xff'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('extremally large num_objects (64 bit)',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\xff\xff\xff\xff\xff'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('integer overflow in num_objects',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\xff\xff\xff\xff\xff\xff\xff\xff'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('offset_size = 0',
        b'\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('ref_size = 0',
        b'\xa1\x01\x00\x08\x0a'
        b'\x00\x00\x00\x00\x00\x00\x01\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x02'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0b'
    ),
    ('too large offset',
        b'\x00\x2a'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('integer overflow in offset',
        b'\x00\xff\xff\xff\xff\xff\xff\xff\xff'
        b'\x00\x00\x00\x00\x00\x00\x08\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x09'
    ),
    ('too large array size',
        b'\xaf\x00\x01\xff\x00\x08\x0c'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x02'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0d'
    ),
    ('extremally large array size (32-bit)',
        b'\xaf\x02\x7f\xff\xff\xff\x01\x00\x08\x0f'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x02'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x10'
    ),
    ('extremally large array size (64-bit)',
        b'\xaf\x03\x00\x00\x00\xff\xff\xff\xff\xff\x01\x00\x08\x13'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x02'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x14'
    ),
    ('integer overflow in array size',
        b'\xaf\x03\xff\xff\xff\xff\xff\xff\xff\xff\x01\x00\x08\x13'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x02'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x14'
    ),
    ('too large reference index',
        b'\xa1\x02\x00\x08\x0a'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x02'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0b'
    ),
    ('integer overflow in reference index',
        b'\xa1\xff\xff\xff\xff\xff\xff\xff\xff\x00\x08\x11'
        b'\x00\x00\x00\x00\x00\x00\x01\x08'
        b'\x00\x00\x00\x00\x00\x00\x00\x02'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x12'
    ),
    ('too large bytes size',
        b'\x4f\x00\x23\x41\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0c'
    ),
    ('extremally large bytes size (32-bit)',
        b'\x4f\x02\x7f\xff\xff\xff\x41\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0f'
    ),
    ('extremally large bytes size (64-bit)',
        b'\x4f\x03\x00\x00\x00\xff\xff\xff\xff\xff\x41\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x13'
    ),
    ('integer overflow in bytes size',
        b'\x4f\x03\xff\xff\xff\xff\xff\xff\xff\xff\x41\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x13'
    ),
    ('too large ASCII size',
        b'\x5f\x00\x23\x41\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0c'
    ),
    ('extremally large ASCII size (32-bit)',
        b'\x5f\x02\x7f\xff\xff\xff\x41\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0f'
    ),
    ('extremally large ASCII size (64-bit)',
        b'\x5f\x03\x00\x00\x00\xff\xff\xff\xff\xff\x41\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x13'
    ),
    ('integer overflow in ASCII size',
        b'\x5f\x03\xff\xff\xff\xff\xff\xff\xff\xff\x41\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x13'
    ),
    ('invalid ASCII',
        b'\x51\xff\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0a'
    ),
    ('too large UTF-16 size',
        b'\x6f\x00\x13\x20\xac\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0e'
    ),
    ('extremally large UTF-16 size (32-bit)',
        b'\x6f\x02\x4f\xff\xff\xff\x20\xac\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x11'
    ),
    ('extremally large UTF-16 size (64-bit)',
        b'\x6f\x03\x00\x00\x00\xff\xff\xff\xff\xff\x20\xac\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x15'
    ),
    ('integer overflow in UTF-16 size',
        b'\x6f\x03\xff\xff\xff\xff\xff\xff\xff\xff\x20\xac\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x15'
    ),
    ('invalid UTF-16',
        b'\x61\xd8\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0b'
    ),
    ('non-hashable key',
        b'\xd1\x01\x01\xa0\x08\x0b'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x02'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x0c'
    ),
    ('too large datetime (datetime overflow)',
        b'\x33\x42\x50\x00\x00\x00\x00\x00\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x11'
    ),
    ('too large datetime (timedelta overflow)',
        b'\x33\x42\xe0\x00\x00\x00\x00\x00\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x11'
    ),
    ('invalid datetime (Infinity)',
        b'\x33\x7f\xf0\x00\x00\x00\x00\x00\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x11'
    ),
    ('invalid datetime (NaN)',
        b'\x33\x7f\xf8\x00\x00\x00\x00\x00\x00\x08'
        b'\x00\x00\x00\x00\x00\x00\x01\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x01'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x11'
    ),
]


class TestPlistlib(unittest.TestCase):

    def tearDown(self):
        try:
            os.unlink(test_support.TESTFN)
        except:
            pass

    def _create(self):
        pl = dict(
            aString="Doodah",
            aList=["A", "B", 12, 32.5, [1, 2, 3]],
            aFloat = 0.5,
            anInt = 728,
            aDict=dict(
                anotherString="<hello & 'hi' there!>",
                aUnicodeValue=u'M\xe4ssig, Ma\xdf',
                aTrueValue=True,
                aFalseValue=False,
                deeperDict=dict(a=17, b=32.5, c=[1, 2, "text"]),
            ),
            someData = plistlib.Data("<binary gunk>"),
            someMoreData = plistlib.Data("<lots of binary gunk>\0\1\2\3" * 10),
            nestedData = [plistlib.Data("<lots of binary gunk>\0\1\2\3" * 10)],
            aDate = datetime.datetime(2004, 10, 26, 10, 33, 33),
        )
        pl[u'\xc5benraa'] = "That was a unicode key."
        return pl

    def test_create(self):
        pl = self._create()
        self.assertEqual(pl["aString"], "Doodah")
        self.assertEqual(pl["aDict"]["aFalseValue"], False)

    def test_io(self):
        pl = self._create()
        plistlib.writePlist(pl, test_support.TESTFN)
        pl2 = plistlib.readPlist(test_support.TESTFN)
        self.assertEqual(dict(pl), dict(pl2))

    def test_string(self):
        pl = self._create()
        data = plistlib.writePlistToString(pl)
        pl2 = plistlib.readPlistFromString(data)
        self.assertEqual(dict(pl), dict(pl2))
        data2 = plistlib.writePlistToString(pl2)
        self.assertEqual(data, data2)

    def test_indentation_array(self):
        data = [[[[[[[[{'test': plistlib.Data(b'aaaaaa')}]]]]]]]]
        self.assertEqual(plistlib.readPlistFromString(plistlib.writePlistToString(data)), data)

    def test_indentation_dict(self):
        data = {'1': {'2': {'3': {'4': {'5': {'6': {'7': {'8': {'9': plistlib.Data(b'aaaaaa')}}}}}}}}}
        self.assertEqual(plistlib.readPlistFromString(plistlib.writePlistToString(data)), data)

    def test_indentation_dict_mix(self):
        data = {'1': {'2': [{'3': [[[[[{'test': plistlib.Data(b'aaaaaa')}]]]]]}]}}
        self.assertEqual(plistlib.readPlistFromString(plistlib.writePlistToString(data)), data)

    def test_appleformatting(self):
        pl = plistlib.readPlistFromString(TESTDATA)
        data = plistlib.writePlistToString(pl)
        self.assertEqual(data, TESTDATA,
                         "generated data was not identical to Apple's output")

    def test_appleformattingfromliteral(self):
        pl = self._create()
        pl2 = plistlib.readPlistFromString(TESTDATA)
        self.assertEqual(dict(pl), dict(pl2),
                         "generated data was not identical to Apple's output")

    def test_stringio(self):
        from StringIO import StringIO
        f = StringIO()
        pl = self._create()
        plistlib.writePlist(pl, f)
        pl2 = plistlib.readPlist(StringIO(f.getvalue()))
        self.assertEqual(dict(pl), dict(pl2))

    def test_cstringio(self):
        from cStringIO import StringIO
        f = StringIO()
        pl = self._create()
        plistlib.writePlist(pl, f)
        pl2 = plistlib.readPlist(StringIO(f.getvalue()))
        self.assertEqual(dict(pl), dict(pl2))

    def test_controlcharacters(self):
        for i in range(128):
            c = chr(i)
            testString = "string containing %s" % c
            if i >= 32 or c in "\r\n\t":
                # \r, \n and \t are the only legal control chars in XML
                plistlib.writePlistToString(testString)
            else:
                self.assertRaises(ValueError,
                                  plistlib.writePlistToString,
                                  testString)

    def test_nondictroot(self):
        test1 = "abc"
        test2 = [1, 2, 3, "abc"]
        result1 = plistlib.readPlistFromString(plistlib.writePlistToString(test1))
        result2 = plistlib.readPlistFromString(plistlib.writePlistToString(test2))
        self.assertEqual(test1, result1)
        self.assertEqual(test2, result2)

    def test_xml_plist_with_entity_decl(self):
        with self.assertRaisesRegexp(plistlib.InvalidFileException,
                                    "XML entity declarations are not supported"):
            plistlib.readPlistFromString(XML_PLIST_WITH_ENTITY)


class TestBinaryPlistlib(unittest.TestCase):

    @staticmethod
    def decode(*objects, offset_size=1, ref_size=1):
        data = [b'bplist00']
        offset = 8
        offsets = []
        for x in objects:
            offsets.append(offset.to_bytes(offset_size, 'big'))
            data.append(x)
            offset += len(x)
        tail = struct.pack('>6xBBQQQ', offset_size, ref_size,
                           len(objects), 0, offset)
        data.extend(offsets)
        data.append(tail)
        return plistlib.loads(b''.join(data), fmt=plistlib.FMT_BINARY)

    def test_nonstandard_refs_size(self):
        # Issue #21538: Refs and offsets are 24-bit integers
        data = (b'bplist00'
                b'\xd1\x00\x00\x01\x00\x00\x02QaQb'
                b'\x00\x00\x08\x00\x00\x0f\x00\x00\x11'
                b'\x00\x00\x00\x00\x00\x00'
                b'\x03\x03'
                b'\x00\x00\x00\x00\x00\x00\x00\x03'
                b'\x00\x00\x00\x00\x00\x00\x00\x00'
                b'\x00\x00\x00\x00\x00\x00\x00\x13')
        self.assertEqual(plistlib.loads(data), {'a': 'b'})

    def test_dump_duplicates(self):
        # Test effectiveness of saving duplicated objects
        for x in (None, False, True, 12345, 123.45, 'abcde', 'абвгд', b'abcde',
                  datetime.datetime(2004, 10, 26, 10, 33, 33),
                  plistlib.Data(b'abcde'), bytearray(b'abcde'),
                  [12, 345], (12, 345), {'12': 345}):
            with self.subTest(x=x):
                data = plistlib.dumps([x]*1000, fmt=plistlib.FMT_BINARY)
                self.assertLess(len(data), 1100, repr(data))

    def test_identity(self):
        for x in (None, False, True, 12345, 123.45, 'abcde', b'abcde',
                  datetime.datetime(2004, 10, 26, 10, 33, 33),
                  plistlib.Data(b'abcde'), bytearray(b'abcde'),
                  [12, 345], (12, 345), {'12': 345}):
            with self.subTest(x=x):
                data = plistlib.dumps([x]*2, fmt=plistlib.FMT_BINARY)
                a, b = plistlib.loads(data)
                if isinstance(x, tuple):
                    x = list(x)
                self.assertEqual(a, x)
                self.assertEqual(b, x)
                self.assertIs(a, b)

    def test_cycles(self):
        # recursive list
        a = []
        a.append(a)
        b = plistlib.loads(plistlib.dumps(a, fmt=plistlib.FMT_BINARY))
        self.assertIs(b[0], b)
        # recursive tuple
        a = ([],)
        a[0].append(a)
        b = plistlib.loads(plistlib.dumps(a, fmt=plistlib.FMT_BINARY))
        self.assertIs(b[0][0], b)
        # recursive dict
        a = {}
        a['x'] = a
        b = plistlib.loads(plistlib.dumps(a, fmt=plistlib.FMT_BINARY))
        self.assertIs(b['x'], b)

    def test_deep_nesting(self):
        for N in [300, 100000]:
            chunks = [b'\xa1' + (i + 1).to_bytes(4, 'big') for i in range(N)]
            try:
                result = self.decode(*chunks, b'\x54seed', offset_size=4, ref_size=4)
            except RecursionError:
                pass
            else:
                for i in range(N):
                    self.assertIsInstance(result, list)
                    self.assertEqual(len(result), 1)
                    result = result[0]
                self.assertEqual(result, 'seed')

    def test_large_timestamp(self):
        # Issue #26709: 32-bit timestamp out of range
        for ts in -2**31-1, 2**31:
            with self.subTest(ts=ts):
                d = (datetime.datetime.utcfromtimestamp(0) +
                     datetime.timedelta(seconds=ts))
                data = plistlib.dumps(d, fmt=plistlib.FMT_BINARY)
                self.assertEqual(plistlib.loads(data), d)

    def test_load_singletons(self):
        self.assertIs(self.decode(b'\x00'), None)
        self.assertIs(self.decode(b'\x08'), False)
        self.assertIs(self.decode(b'\x09'), True)
        self.assertEqual(self.decode(b'\x0f'), b'')

    def test_load_int(self):
        self.assertEqual(self.decode(b'\x10\x00'), 0)
        self.assertEqual(self.decode(b'\x10\xfe'), 0xfe)
        self.assertEqual(self.decode(b'\x11\xfe\xdc'), 0xfedc)
        self.assertEqual(self.decode(b'\x12\xfe\xdc\xba\x98'), 0xfedcba98)
        self.assertEqual(self.decode(b'\x13\x01\x23\x45\x67\x89\xab\xcd\xef'),
                         0x0123456789abcdef)
        self.assertEqual(self.decode(b'\x13\xfe\xdc\xba\x98\x76\x54\x32\x10'),
                         -0x123456789abcdf0)

    def test_unsupported(self):
        unsupported = [*range(1, 8), *range(10, 15),
                       0x20, 0x21, *range(0x24, 0x33), *range(0x34, 0x40)]
        for i in [0x70, 0x90, 0xb0, 0xc0, 0xe0, 0xf0]:
            unsupported.extend(i + j for j in range(16))
        for token in unsupported:
            with self.subTest(f'token {token:02x}'):
                with self.assertRaises(plistlib.InvalidFileException):
                    self.decode(bytes([token]) + b'\x00'*16)

    def test_invalid_binary(self):
        for name, data in INVALID_BINARY_PLISTS:
            with self.subTest(name):
                with self.assertRaises(plistlib.InvalidFileException):
                    plistlib.loads(b'bplist00' + data, fmt=plistlib.FMT_BINARY)


class TestPlistlibDeprecated(unittest.TestCase):
    def test_io_deprecated(self):
        pl_in = {
            'key': 42,
            'sub': {
                'key': 9,
                'alt': 'value',
                'data': b'buffer',
            }
        }
        pl_out = plistlib._InternalDict({
            'key': 42,
            'sub': plistlib._InternalDict({
                'key': 9,
                'alt': 'value',
                'data': plistlib.Data(b'buffer'),
            })
        })

        self.addCleanup(support.unlink, support.TESTFN)
        with self.assertWarns(DeprecationWarning):
            plistlib.writePlist(pl_in, support.TESTFN)

        with self.assertWarns(DeprecationWarning):
            pl2 = plistlib.readPlist(support.TESTFN)

        self.assertEqual(pl_out, pl2)

        os.unlink(support.TESTFN)

        with open(support.TESTFN, 'wb') as fp:
            with self.assertWarns(DeprecationWarning):
                plistlib.writePlist(pl_in, fp)

        with open(support.TESTFN, 'rb') as fp:
            with self.assertWarns(DeprecationWarning):
                pl2 = plistlib.readPlist(fp)

        self.assertEqual(pl_out, pl2)

    def test_bytes_deprecated(self):
        pl = {
            'key': 42,
            'sub': {
                'key': 9,
                'alt': 'value',
                'data': b'buffer',
            }
        }
        with self.assertWarns(DeprecationWarning):
            data = plistlib.writePlistToBytes(pl)

        with self.assertWarns(DeprecationWarning):
            pl2 = plistlib.readPlistFromBytes(data)

        self.assertIsInstance(pl2, plistlib._InternalDict)
        self.assertEqual(pl2, plistlib._InternalDict(
            key=42,
            sub=plistlib._InternalDict(
                key=9,
                alt='value',
                data=plistlib.Data(b'buffer'),
            )
        ))

        with self.assertWarns(DeprecationWarning):
            data2 = plistlib.writePlistToBytes(pl2)
        self.assertEqual(data, data2)

    def test_dataobject_deprecated(self):
        in_data = { 'key': plistlib.Data(b'hello') }
        out_data = { 'key': b'hello' }

        buf = plistlib.dumps(in_data)

        cur = plistlib.loads(buf)
        self.assertEqual(cur, out_data)
        self.assertEqual(cur, in_data)

        cur = plistlib.loads(buf, use_builtin_types=False)
        self.assertEqual(cur, out_data)
        self.assertEqual(cur, in_data)

        with self.assertWarns(DeprecationWarning):
            cur = plistlib.readPlistFromBytes(buf)
        self.assertEqual(cur, out_data)
        self.assertEqual(cur, in_data)


class MiscTestCase(unittest.TestCase):
    def test__all__(self):
        blacklist = {"PlistFormat", "PLISTHEADER"}
        support.check__all__(self, plistlib, blacklist=blacklist)


if __name__ == '__main__':
    unittest.main()
