r"""plistlib.py -- a tool to generate and parse MacOSX .plist files.

The PropertyList (.plist) file format is a simple XML pickle supporting
basic object types, like dictionaries, lists, numbers and strings.
Usually the top level object is a dictionary.

To write out a plist file, use the writePlist(rootObject, pathOrFile)
function. 'rootObject' is the top level object, 'pathOrFile' is a
filename or a (writable) file object.

To parse a plist from a file, use the readPlist(pathOrFile) function,
with a file name or a (readable) file object as the only argument. It
returns the top level object (again, usually a dictionary).

To work with plist data in strings, you can use readPlistFromString()
and writePlistToString().

Values can be strings, integers, floats, booleans, tuples, lists,
dictionaries, Data or datetime.datetime objects. String values (including
dictionary keys) may be unicode strings -- they will be written out as
UTF-8.

The <data> plist type is supported through the Data class. This is a
thin wrapper around a Python string.

Generate Plist example:

    pl = dict(
        aString="Doodah",
        aList=["A", "B", 12, 32.1, [1, 2, 3]],
        aFloat=0.1,
        anInt=728,
        aDict=dict(
            anotherString="<hello & hi there!>",
            aUnicodeValue=u'M\xe4ssig, Ma\xdf',
            aTrueValue=True,
            aFalseValue=False,
        ),
        someData=Data("<binary gunk>"),
        someMoreData=Data("<lots of binary gunk>" * 10),
        aDate=datetime.datetime.fromtimestamp(time.mktime(time.gmtime())),
    )
    # unicode keys are possible, but a little awkward to use:
    pl[u'\xc5benraa'] = "That was a unicode key."
    writePlist(pl, fileName)

Parse Plist example:

    pl = readPlist(pathOrFile)
    print pl["aKey"]
"""


__all__ = [
    "readPlist", "writePlist", "readPlistFromString", "writePlistToString",
    "readPlistFromResource", "writePlistToResource",
    "Plist", "Data", "Dict"
]
# Note: the Plist and Dict classes have been deprecated.

import binascii
import datetime
from cStringIO import StringIO
import re
import warnings


def readPlist(pathOrFile):
    """Read a .plist file. 'pathOrFile' may either be a file name or a
    (readable) file object. Return the unpacked root object (which
    usually is a dictionary).
    """
    didOpen = 0
    if isinstance(pathOrFile, (str, unicode)):
        pathOrFile = open(pathOrFile)
        didOpen = 1
    p = PlistParser()
    rootObject = p.parse(pathOrFile)
    if didOpen:
        pathOrFile.close()
    return rootObject


def writePlist(rootObject, pathOrFile):
    """Write 'rootObject' to a .plist file. 'pathOrFile' may either be a
    file name or a (writable) file object.
    """
    didOpen = 0
    if isinstance(pathOrFile, (str, unicode)):
        pathOrFile = open(pathOrFile, "w")
        didOpen = 1
    writer = PlistWriter(pathOrFile)
    writer.writeln("<plist version=\"1.0\">")
    writer.writeValue(rootObject)
    writer.writeln("</plist>")
    if didOpen:
        pathOrFile.close()


def readPlistFromString(data):
    """Read a plist data from a string. Return the root object.
    """
    return readPlist(StringIO(data))


def writePlistToString(rootObject):
    """Return 'rootObject' as a plist-formatted string.
    """
    f = StringIO()
    writePlist(rootObject, f)
    return f.getvalue()


def readPlistFromResource(path, restype='plst', resid=0):
    """Read plst resource from the resource fork of path.
    """
    warnings.warnpy3k("In 3.x, readPlistFromResource is removed.",
                      stacklevel=2)
    from Carbon.File import FSRef, FSGetResourceForkName
    from Carbon.Files import fsRdPerm
    from Carbon import Res
    fsRef = FSRef(path)
    resNum = Res.FSOpenResourceFile(fsRef, FSGetResourceForkName(), fsRdPerm)
    Res.UseResFile(resNum)
    plistData = Res.Get1Resource(restype, resid).data
    Res.CloseResFile(resNum)
    return readPlistFromString(plistData)


def writePlistToResource(rootObject, path, restype='plst', resid=0):
    """Write 'rootObject' as a plst resource to the resource fork of path.
    """
    warnings.warnpy3k("In 3.x, writePlistToResource is removed.", stacklevel=2)
    from Carbon.File import FSRef, FSGetResourceForkName
    from Carbon.Files import fsRdWrPerm
    from Carbon import Res
    plistData = writePlistToString(rootObject)
    fsRef = FSRef(path)
    resNum = Res.FSOpenResourceFile(fsRef, FSGetResourceForkName(), fsRdWrPerm)
    Res.UseResFile(resNum)
    try:
        Res.Get1Resource(restype, resid).RemoveResource()
    except Res.Error:
        pass
    res = Res.Resource(plistData)
    res.AddResource(restype, resid, '')
    res.WriteResource()
    Res.CloseResFile(resNum)


class DumbXMLWriter:

    def __init__(self, file, indentLevel=0, indent="\t"):
        self.file = file
        self.stack = []
        self.indentLevel = indentLevel
        self.indent = indent

    def beginElement(self, element):
        self.stack.append(element)
        self.writeln("<%s>" % element)
        self.indentLevel += 1

    def endElement(self, element):
        assert self.indentLevel > 0
        assert self.stack.pop() == element
        self.indentLevel -= 1
        self.writeln("</%s>" % element)

    def simpleElement(self, element, value=None):
        if value is not None:
            value = _escapeAndEncode(value)
            self.writeln("<%s>%s</%s>" % (element, value, element))
        else:
            self.writeln("<%s/>" % element)

    def writeln(self, line):
        if line:
            self.file.write(self.indentLevel * self.indent + line + "\n")
        else:
            self.file.write("\n")


# Contents should conform to a subset of ISO 8601
# (in particular, YYYY '-' MM '-' DD 'T' HH ':' MM ':' SS 'Z'.  Smaller units may be omitted with
#  a loss of precision)
_dateParser = re.compile(r"(?P<year>\d\d\d\d)(?:-(?P<month>\d\d)(?:-(?P<day>\d\d)(?:T(?P<hour>\d\d)(?::(?P<minute>\d\d)(?::(?P<second>\d\d))?)?)?)?)?Z")

def _dateFromString(s):
    order = ('year', 'month', 'day', 'hour', 'minute', 'second')
    gd = _dateParser.match(s).groupdict()
    lst = []
    for key in order:
        val = gd[key]
        if val is None:
            break
        lst.append(int(val))
    return datetime.datetime(*lst)

def _dateToString(d):
    return '%04d-%02d-%02dT%02d:%02d:%02dZ' % (
        d.year, d.month, d.day,
        d.hour, d.minute, d.second
    )


# Regex to find any control chars, except for \t \n and \r
_controlCharPat = re.compile(
    r"[\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"
    r"\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f]")

def _escapeAndEncode(text):
    m = _controlCharPat.search(text)
    if m is not None:
        raise ValueError("strings can't contains control characters; "
                         "use plistlib.Data instead")
    text = text.replace("\r\n", "\n")       # convert DOS line endings
    text = text.replace("\r", "\n")         # convert Mac line endings
    text = text.replace("&", "&amp;")       # escape '&'
    text = text.replace("<", "&lt;")        # escape '<'
    text = text.replace(">", "&gt;")        # escape '>'
    return text.encode("utf-8")             # encode as UTF-8


PLISTHEADER = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
"""

class PlistWriter(DumbXMLWriter):

    def __init__(self, file, indentLevel=0, indent="\t", writeHeader=1):
        if writeHeader:
            file.write(PLISTHEADER)
        DumbXMLWriter.__init__(self, file, indentLevel, indent)

    def writeValue(self, value):
        if isinstance(value, (str, unicode)):
            self.simpleElement("string", value)
        elif isinstance(value, bool):
            # must switch for bool before int, as bool is a
            # subclass of int...
            if value:
                self.simpleElement("true")
            else:
                self.simpleElement("false")
        elif isinstance(value, (int, long)):
            self.simpleElement("integer", "%d" % value)
        elif isinstance(value, float):
            self.simpleElement("real", repr(value))
        elif isinstance(value, dict):
            self.writeDict(value)
        elif isinstance(value, Data):
            self.writeData(value)
        elif isinstance(value, datetime.datetime):
            self.simpleElement("date", _dateToString(value))
        elif isinstance(value, (tuple, list)):
            self.writeArray(value)
        else:
            raise TypeError("unsuported type: %s" % type(value))

    def writeData(self, data):
        self.beginElement("data")
        self.indentLevel -= 1
        maxlinelength = max(16, 76 - len(self.indent.replace("\t", " " * 8) *
                                 self.indentLevel))
        for line in data.asBase64(maxlinelength).split("\n"):
            if line:
                self.writeln(line)
        self.indentLevel += 1
        self.endElement("data")

    def writeDict(self, d):
        self.beginElement("dict")
        items = d.items()
        items.sort()
        for key, value in items:
            if not isinstance(key, (str, unicode)):
                raise TypeError("keys must be strings")
            self.simpleElement("key", key)
            self.writeValue(value)
        self.endElement("dict")

    def writeArray(self, array):
        self.beginElement("array")
        for value in array:
            self.writeValue(value)
        self.endElement("array")


class _InternalDict(dict):

    # This class is needed while Dict is scheduled for deprecation:
    # we only need to warn when a *user* instantiates Dict or when
    # the "attribute notation for dict keys" is used.

    def __getattr__(self, attr):
        try:
            value = self[attr]
        except KeyError:
            raise AttributeError, attr
        from warnings import warn
        warn("Attribute access from plist dicts is deprecated, use d[key] "
             "notation instead", PendingDeprecationWarning, 2)
        return value

    def __setattr__(self, attr, value):
        from warnings import warn
        warn("Attribute access from plist dicts is deprecated, use d[key] "
             "notation instead", PendingDeprecationWarning, 2)
        self[attr] = value

    def __delattr__(self, attr):
        try:
            del self[attr]
        except KeyError:
            raise AttributeError, attr
        from warnings import warn
        warn("Attribute access from plist dicts is deprecated, use d[key] "
             "notation instead", PendingDeprecationWarning, 2)

class Dict(_InternalDict):

    def __init__(self, **kwargs):
        from warnings import warn
        warn("The plistlib.Dict class is deprecated, use builtin dict instead",
             PendingDeprecationWarning, 2)
        super(Dict, self).__init__(**kwargs)


class Plist(_InternalDict):

    """This class has been deprecated. Use readPlist() and writePlist()
    functions instead, together with regular dict objects.
    """

    def __init__(self, **kwargs):
        from warnings import warn
        warn("The Plist class is deprecated, use the readPlist() and "
             "writePlist() functions instead", PendingDeprecationWarning, 2)
        super(Plist, self).__init__(**kwargs)

    def fromFile(cls, pathOrFile):
        """Deprecated. Use the readPlist() function instead."""
        rootObject = readPlist(pathOrFile)
        plist = cls()
        plist.update(rootObject)
        return plist
    fromFile = classmethod(fromFile)

    def write(self, pathOrFile):
        """Deprecated. Use the writePlist() function instead."""
        writePlist(self, pathOrFile)


def _encodeBase64(s, maxlinelength=76):
    # copied from base64.encodestring(), with added maxlinelength argument
    maxbinsize = (maxlinelength//4)*3
    pieces = []
    for i in range(0, len(s), maxbinsize):
        chunk = s[i : i + maxbinsize]
        pieces.append(binascii.b2a_base64(chunk))
    return "".join(pieces)

class Data:

    """Wrapper for binary data."""

    def __init__(self, data):
        self.data = data

    def fromBase64(cls, data):
        # base64.decodestring just calls binascii.a2b_base64;
        # it seems overkill to use both base64 and binascii.
        return cls(binascii.a2b_base64(data))
    fromBase64 = classmethod(fromBase64)

    def asBase64(self, maxlinelength=76):
        return _encodeBase64(self.data, maxlinelength)

    def __cmp__(self, other):
        if isinstance(other, self.__class__):
            return cmp(self.data, other.data)
        elif isinstance(other, str):
            return cmp(self.data, other)
        else:
            return cmp(id(self), id(other))

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.data))


class PlistParser:

    def __init__(self):
        self.stack = []
        self.currentKey = None
        self.root = None

    def parse(self, fileobj):
        from xml.parsers.expat import ParserCreate
        parser = ParserCreate()
        parser.StartElementHandler = self.handleBeginElement
        parser.EndElementHandler = self.handleEndElement
        parser.CharacterDataHandler = self.handleData
        parser.EntityDeclHandler = self.handle_entity_decl
        parser.ParseFile(fileobj)
        return self.root

    def handle_entity_decl(self, entity_name, is_parameter_entity, value, base, system_id, public_id, notation_name):
        # Reject plist files with entity declarations to avoid XML vulnerabilies in expat.
        # Regular plist files don't contain those declerations, and Apple's plutil tool does not
        # accept them either.
        raise InvalidFileException("XML entity declarations are not supported in plist files")

    def handleBeginElement(self, element, attrs):
        self.data = []
        handler = getattr(self, "begin_" + element, None)
        if handler is not None:
            handler(attrs)

    def handleEndElement(self, element):
        handler = getattr(self, "end_" + element, None)
        if handler is not None:
            handler()

    def handleData(self, data):
        self.data.append(data)

    def addObject(self, value):
        if self.currentKey is not None:
            self.stack[-1][self.currentKey] = value
            self.currentKey = None
        elif not self.stack:
            # this is the root object
            self.root = value
        else:
            self.stack[-1].append(value)

    def getData(self):
        data = "".join(self.data)
        try:
            data = data.encode("ascii")
        except UnicodeError:
            pass
        self.data = []
        return data

    # element handlers

    def begin_dict(self, attrs):
        d = _InternalDict()
        self.addObject(d)
        self.stack.append(d)
    def end_dict(self):
        self.stack.pop()

    def end_key(self):
        self.currentKey = self.getData()

    def begin_array(self, attrs):
        a = []
        self.addObject(a)
        self.stack.append(a)
    def end_array(self):
        self.stack.pop()

    def end_true(self):
        self.addObject(True)
    def end_false(self):
        self.addObject(False)
    def end_integer(self):
        self.addObject(int(self.getData()))
    def end_real(self):
        self.addObject(float(self.getData()))
    def end_string(self):
        self.addObject(self.getData())
    def end_data(self):
        self.addObject(Data.fromBase64(self.getData()))
    def end_date(self):
        self.addObject(_dateFromString(self.getData()))


class InvalidFileException (ValueError):
    def __init__(self, message="Invalid file"):
        ValueError.__init__(self, message)

_BINARY_FORMAT = {1: 'B', 2: 'H', 4: 'L', 8: 'Q'}

_undefined = object()

class _BinaryPlistParser:
    """
    Read or write a binary plist file, following the description of the binary
    format.  Raise InvalidFileException in case of error, otherwise return the
    root object.

    see also: http://opensource.apple.com/source/CF/CF-744.18/CFBinaryPList.c
    """
    def __init__(self, use_builtin_types, dict_type):
        self._use_builtin_types = use_builtin_types
        self._dict_type = dict_type

    def parse(self, fp):
        try:
            # The basic file format:
            # HEADER
            # object...
            # refid->offset...
            # TRAILER
            self._fp = fp
            self._fp.seek(-32, os.SEEK_END)
            trailer = self._fp.read(32)
            if len(trailer) != 32:
                raise InvalidFileException()
            (
                offset_size, self._ref_size, num_objects, top_object,
                offset_table_offset
            ) = struct.unpack('>6xBBQQQ', trailer)
            self._fp.seek(offset_table_offset)
            self._object_offsets = self._read_ints(num_objects, offset_size)
            self._objects = [_undefined] * num_objects
            return self._read_object(top_object)

        except (OSError, IndexError, struct.error, OverflowError,
                ValueError):
            raise InvalidFileException()

    def _get_size(self, tokenL):
        """ return the size of the next object."""
        if tokenL == 0xF:
            m = self._fp.read(1)[0] & 0x3
            s = 1 << m
            f = '>' + _BINARY_FORMAT[s]
            return struct.unpack(f, self._fp.read(s))[0]

        return tokenL

    def _read_ints(self, n, size):
        data = self._fp.read(size * n)
        if size in _BINARY_FORMAT:
            return struct.unpack(f'>{n}{_BINARY_FORMAT[size]}', data)
        else:
            if not size or len(data) != size * n:
                raise InvalidFileException()
            return tuple(int.from_bytes(data[i: i + size], 'big')
                         for i in range(0, size * n, size))

    def _read_refs(self, n):
        return self._read_ints(n, self._ref_size)

    def _read_object(self, ref):
        """
        read the object by reference.

        May recursively read sub-objects (content of an array/dict/set)
        """
        result = self._objects[ref]
        if result is not _undefined:
            return result

        offset = self._object_offsets[ref]
        self._fp.seek(offset)
        token = self._fp.read(1)[0]
        tokenH, tokenL = token & 0xF0, token & 0x0F

        if token == 0x00:
            result = None

        elif token == 0x08:
            result = False

        elif token == 0x09:
            result = True

        # The referenced source code also mentions URL (0x0c, 0x0d) and
        # UUID (0x0e), but neither can be generated using the Cocoa libraries.

        elif token == 0x0f:
            result = b''

        elif tokenH == 0x10:  # int
            result = int.from_bytes(self._fp.read(1 << tokenL),
                                    'big', signed=tokenL >= 3)

        elif token == 0x22: # real
            result = struct.unpack('>f', self._fp.read(4))[0]

        elif token == 0x23: # real
            result = struct.unpack('>d', self._fp.read(8))[0]

        elif token == 0x33:  # date
            f = struct.unpack('>d', self._fp.read(8))[0]
            # timestamp 0 of binary plists corresponds to 1/1/2001
            # (year of Mac OS X 10.0), instead of 1/1/1970.
            result = (datetime.datetime(2001, 1, 1) +
                      datetime.timedelta(seconds=f))

        elif tokenH == 0x40:  # data
            s = self._get_size(tokenL)
            result = self._fp.read(s)
            if len(result) != s:
                raise InvalidFileException()
            if not self._use_builtin_types:
                result = Data(result)

        elif tokenH == 0x50:  # ascii string
            s = self._get_size(tokenL)
            data = self._fp.read(s)
            if len(data) != s:
                raise InvalidFileException()
            result = data.decode('ascii')

        elif tokenH == 0x60:  # unicode string
            s = self._get_size(tokenL) * 2
            data = self._fp.read(s)
            if len(data) != s:
                raise InvalidFileException()
            result = data.decode('utf-16be')

        # tokenH == 0x80 is documented as 'UID' and appears to be used for
        # keyed-archiving, not in plists.

        elif tokenH == 0xA0:  # array
            s = self._get_size(tokenL)
            obj_refs = self._read_refs(s)
            result = []
            self._objects[ref] = result
            result.extend(self._read_object(x) for x in obj_refs)

        # tokenH == 0xB0 is documented as 'ordset', but is not actually
        # implemented in the Apple reference code.

        # tokenH == 0xC0 is documented as 'set', but sets cannot be used in
        # plists.

        elif tokenH == 0xD0:  # dict
            s = self._get_size(tokenL)
            key_refs = self._read_refs(s)
            obj_refs = self._read_refs(s)
            result = self._dict_type()
            self._objects[ref] = result
            try:
                for k, o in zip(key_refs, obj_refs):
                    result[self._read_object(k)] = self._read_object(o)
            except TypeError:
                raise InvalidFileException()
        else:
            raise InvalidFileException()

        self._objects[ref] = result
        return result

def _count_to_size(count):
    if count < 1 << 8:
        return 1

    elif count < 1 << 16:
        return 2

    elif count << 1 << 32:
        return 4

    else:
        return 8

_scalars = (str, int, float, datetime.datetime, bytes)

class _BinaryPlistWriter (object):
    def __init__(self, fp, sort_keys, skipkeys):
        self._fp = fp
        self._sort_keys = sort_keys
        self._skipkeys = skipkeys

    def write(self, value):

        # Flattened object list:
        self._objlist = []

        # Mappings from object->objectid
        # First dict has (type(object), object) as the key,
        # second dict is used when object is not hashable and
        # has id(object) as the key.
        self._objtable = {}
        self._objidtable = {}

        # Create list of all objects in the plist
        self._flatten(value)

        # Size of object references in serialized containers
        # depends on the number of objects in the plist.
        num_objects = len(self._objlist)
        self._object_offsets = [0]*num_objects
        self._ref_size = _count_to_size(num_objects)

        self._ref_format = _BINARY_FORMAT[self._ref_size]

        # Write file header
        self._fp.write(b'bplist00')

        # Write object list
        for obj in self._objlist:
            self._write_object(obj)

        # Write refnum->object offset table
        top_object = self._getrefnum(value)
        offset_table_offset = self._fp.tell()
        offset_size = _count_to_size(offset_table_offset)
        offset_format = '>' + _BINARY_FORMAT[offset_size] * num_objects
        self._fp.write(struct.pack(offset_format, *self._object_offsets))

        # Write trailer
        sort_version = 0
        trailer = (
            sort_version, offset_size, self._ref_size, num_objects,
            top_object, offset_table_offset
        )
        self._fp.write(struct.pack('>5xBBBQQQ', *trailer))

    def _flatten(self, value):
        # First check if the object is in the object table, not used for
        # containers to ensure that two subcontainers with the same contents
        # will be serialized as distinct values.
        if isinstance(value, _scalars):
            if (type(value), value) in self._objtable:
                return

        elif isinstance(value, Data):
            if (type(value.data), value.data) in self._objtable:
                return

        elif id(value) in self._objidtable:
            return

        # Add to objectreference map
        refnum = len(self._objlist)
        self._objlist.append(value)
        if isinstance(value, _scalars):
            self._objtable[(type(value), value)] = refnum
        elif isinstance(value, Data):
            self._objtable[(type(value.data), value.data)] = refnum
        else:
            self._objidtable[id(value)] = refnum

        # And finally recurse into containers
        if isinstance(value, dict):
            keys = []
            values = []
            items = value.items()
            if self._sort_keys:
                items = sorted(items)

            for k, v in items:
                if not isinstance(k, str):
                    if self._skipkeys:
                        continue
                    raise TypeError("keys must be strings")
                keys.append(k)
                values.append(v)

            for o in itertools.chain(keys, values):
                self._flatten(o)

        elif isinstance(value, (list, tuple)):
            for o in value:
                self._flatten(o)

    def _getrefnum(self, value):
        if isinstance(value, _scalars):
            return self._objtable[(type(value), value)]
        elif isinstance(value, Data):
            return self._objtable[(type(value.data), value.data)]
        else:
            return self._objidtable[id(value)]

    def _write_size(self, token, size):
        if size < 15:
            self._fp.write(struct.pack('>B', token | size))

        elif size < 1 << 8:
            self._fp.write(struct.pack('>BBB', token | 0xF, 0x10, size))

        elif size < 1 << 16:
            self._fp.write(struct.pack('>BBH', token | 0xF, 0x11, size))

        elif size < 1 << 32:
            self._fp.write(struct.pack('>BBL', token | 0xF, 0x12, size))

        else:
            self._fp.write(struct.pack('>BBQ', token | 0xF, 0x13, size))

    def _write_object(self, value):
        ref = self._getrefnum(value)
        self._object_offsets[ref] = self._fp.tell()
        if value is None:
            self._fp.write(b'\x00')

        elif value is False:
            self._fp.write(b'\x08')

        elif value is True:
            self._fp.write(b'\x09')

        elif isinstance(value, int):
            if value < 0:
                try:
                    self._fp.write(struct.pack('>Bq', 0x13, value))
                except struct.error:
                    raise OverflowError(value) from None
            elif value < 1 << 8:
                self._fp.write(struct.pack('>BB', 0x10, value))
            elif value < 1 << 16:
                self._fp.write(struct.pack('>BH', 0x11, value))
            elif value < 1 << 32:
                self._fp.write(struct.pack('>BL', 0x12, value))
            elif value < 1 << 63:
                self._fp.write(struct.pack('>BQ', 0x13, value))
            elif value < 1 << 64:
                self._fp.write(b'\x14' + value.to_bytes(16, 'big', signed=True))
            else:
                raise OverflowError(value)

        elif isinstance(value, float):
            self._fp.write(struct.pack('>Bd', 0x23, value))

        elif isinstance(value, datetime.datetime):
            f = (value - datetime.datetime(2001, 1, 1)).total_seconds()
            self._fp.write(struct.pack('>Bd', 0x33, f))

        elif isinstance(value, Data):
            self._write_size(0x40, len(value.data))
            self._fp.write(value.data)

        elif isinstance(value, (bytes, bytearray)):
            self._write_size(0x40, len(value))
            self._fp.write(value)

        elif isinstance(value, str):
            try:
                t = value.encode('ascii')
                self._write_size(0x50, len(value))
            except UnicodeEncodeError:
                t = value.encode('utf-16be')
                self._write_size(0x60, len(t) // 2)

            self._fp.write(t)

        elif isinstance(value, (list, tuple)):
            refs = [self._getrefnum(o) for o in value]
            s = len(refs)
            self._write_size(0xA0, s)
            self._fp.write(struct.pack('>' + self._ref_format * s, *refs))

        elif isinstance(value, dict):
            keyRefs, valRefs = [], []

            if self._sort_keys:
                rootItems = sorted(value.items())
            else:
                rootItems = value.items()

            for k, v in rootItems:
                if not isinstance(k, str):
                    if self._skipkeys:
                        continue
                    raise TypeError("keys must be strings")
                keyRefs.append(self._getrefnum(k))
                valRefs.append(self._getrefnum(v))

            s = len(keyRefs)
            self._write_size(0xD0, s)
            self._fp.write(struct.pack('>' + self._ref_format * s, *keyRefs))
            self._fp.write(struct.pack('>' + self._ref_format * s, *valRefs))

        else:
            raise TypeError(value)


def _is_fmt_binary(header):
    return header[:8] == b'bplist00'


#
# Generic bits
#

_FORMATS={
    FMT_XML: dict(
        detect=_is_fmt_xml,
        parser=_PlistParser,
        writer=_PlistWriter,
    ),
    FMT_BINARY: dict(
        detect=_is_fmt_binary,
        parser=_BinaryPlistParser,
        writer=_BinaryPlistWriter,
    )
}


def load(fp, *, fmt=None, use_builtin_types=True, dict_type=dict):
    """Read a .plist file. 'fp' should be (readable) file object.
    Return the unpacked root object (which usually is a dictionary).
    """
    if fmt is None:
        header = fp.read(32)
        fp.seek(0)
        for info in _FORMATS.values():
            if info['detect'](header):
                P = info['parser']
                break

        else:
            raise InvalidFileException()

    else:
        P = _FORMATS[fmt]['parser']

    p = P(use_builtin_types=use_builtin_types, dict_type=dict_type)
    return p.parse(fp)


def loads(value, *, fmt=None, use_builtin_types=True, dict_type=dict):
    """Read a .plist file from a bytes object.
    Return the unpacked root object (which usually is a dictionary).
    """
    fp = BytesIO(value)
    return load(
        fp, fmt=fmt, use_builtin_types=use_builtin_types, dict_type=dict_type)


def dump(value, fp, *, fmt=FMT_XML, sort_keys=True, skipkeys=False):
    """Write 'value' to a .plist file. 'fp' should be a (writable)
    file object.
    """
    if fmt not in _FORMATS:
        raise ValueError("Unsupported format: %r"%(fmt,))

    writer = _FORMATS[fmt]["writer"](fp, sort_keys=sort_keys, skipkeys=skipkeys)
    writer.write(value)


def dumps(value, *, fmt=FMT_XML, skipkeys=False, sort_keys=True):
    """Return a bytes object with the contents for a .plist file.
    """
    fp = BytesIO()
    dump(value, fp, fmt=fmt, skipkeys=skipkeys, sort_keys=sort_keys)
    return fp.getvalue()
