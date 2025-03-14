# Copyright (C) 2001-2010 Python Software Foundation
# Author: Barry Warsaw
# Contact: email-sig@python.org

"""Miscellaneous utilities."""

__all__ = [
    'collapse_rfc2231_value',
    'decode_params',
    'decode_rfc2231',
    'encode_rfc2231',
    'formataddr',
    'formatdate',
    'getaddresses',
    'make_msgid',
    'mktime_tz',
    'parseaddr',
    'parsedate',
    'parsedate_tz',
    'unquote',
    ]

import os
import re
import time
import base64
import random
import socket
import urllib
import warnings

from email._parseaddr import quote
from email._parseaddr import AddressList as _AddressList
from email._parseaddr import mktime_tz

# We need wormarounds for bugs in these methods in older Pythons (see below)
from email._parseaddr import parsedate as _parsedate
from email._parseaddr import parsedate_tz as _parsedate_tz

from quopri import decodestring as _qdecode

# Intrapackage imports
from email.encoders import _bencode, _qencode

COMMASPACE = ', '
EMPTYSTRING = ''
UEMPTYSTRING = u''
CRLF = '\r\n'
TICK = "'"

specialsre = re.compile(r'[][\\()<>@,:;".]')
escapesre = re.compile(r'[][\\()"]')



# Helpers

def _identity(s):
    return s


def _bdecode(s):
    """Decodes a base64 string.

    This function is equivalent to base64.decodestring and it's retained only
    for backward compatibility. It used to remove the last \\n of the decoded
    string, if it had any (see issue 7143).
    """
    if not s:
        return s
    return base64.decodestring(s)



def fix_eols(s):
    """Replace all line-ending characters with \\r\\n."""
    # Fix newlines with no preceding carriage return
    s = re.sub(r'(?<!\r)\n', CRLF, s)
    # Fix carriage returns with no following newline
    s = re.sub(r'\r(?!\n)', CRLF, s)
    return s



def formataddr(pair):
    """The inverse of parseaddr(), this takes a 2-tuple of the form
    (realname, email_address) and returns the string value suitable
    for an RFC 2822 From, To or Cc header.

    If the first element of pair is false, then the second element is
    returned unmodified.
    """
    name, address = pair
    if name:
        quotes = ''
        if specialsre.search(name):
            quotes = '"'
        name = escapesre.sub(r'\\\g<0>', name)
        return '%s%s%s <%s>' % (quotes, name, quotes, address)
    return address

def _iter_escaped_chars(addr):
    pos = 0
    escape = False
    for pos, ch in enumerate(addr):
        if escape:
            yield (pos, '\\' + ch)
            escape = False
        elif ch == '\\':
            escape = True
        else:
            yield (pos, ch)
    if escape:
        yield (pos, '\\')


def _strip_quoted_realnames(addr):
    """Strip real names between quotes."""
    if '"' not in addr:
        # Fast path
        return addr

    start = 0
    open_pos = None
    result = []
    for pos, ch in _iter_escaped_chars(addr):
        if ch == '"':
            if open_pos is None:
                open_pos = pos
            else:
                if start != open_pos:
                    result.append(addr[start:open_pos])
                start = pos + 1
                open_pos = None

    if start < len(addr):
        result.append(addr[start:])

    return ''.join(result)


supports_strict_parsing = True

def getaddresses(fieldvalues, strict=True):
    """Return a list of (REALNAME, EMAIL) or ('','') for each fieldvalue.
    When parsing fails for a fieldvalue, a 2-tuple of ('', '') is returned in
    its place.
    If strict is true, use a strict parser which rejects malformed inputs.
    """

    # If strict is true, if the resulting list of parsed addresses is greater
    # than the number of fieldvalues in the input list, a parsing error has
    # occurred and consequently a list containing a single empty 2-tuple [('',
    # '')] is returned in its place. This is done to avoid invalid output.
    #
    # Malformed input: getaddresses(['alice@example.com <bob@example.com>'])
    # Invalid output: [('', 'alice@example.com'), ('', 'bob@example.com')]
    # Safe output: [('', '')]

    if not strict:
        all = COMMASPACE.join(str(v) for v in fieldvalues)
        a = _AddressList(all)
        return a.addresslist

    fieldvalues = [str(v) for v in fieldvalues]
    fieldvalues = _pre_parse_validation(fieldvalues)
    addr = COMMASPACE.join(fieldvalues)
    a = _AddressList(addr)
    result = _post_parse_validation(a.addresslist)

    # Treat output as invalid if the number of addresses is not equal to the
    # expected number of addresses.
    n = 0
    for v in fieldvalues:
        # When a comma is used in the Real Name part it is not a deliminator.
        # So strip those out before counting the commas.
        v = _strip_quoted_realnames(v)
        # Expected number of addresses: 1 + number of commas
        n += 1 + v.count(',')
    if len(result) != n:
        return [('', '')]

    return result


def _check_parenthesis(addr):
    # Ignore parenthesis in quoted real names.
    addr = _strip_quoted_realnames(addr)

    opens = 0
    for pos, ch in _iter_escaped_chars(addr):
        if ch == '(':
            opens += 1
        elif ch == ')':
            opens -= 1
            if opens < 0:
                return False
    return (opens == 0)


def _pre_parse_validation(email_header_fields):
    accepted_values = []
    for v in email_header_fields:
        if not _check_parenthesis(v):
            v = "('', '')"
        accepted_values.append(v)

    return accepted_values


def _post_parse_validation(parsed_email_header_tuples):
    accepted_values = []
    # The parser would have parsed a correctly formatted domain-literal
    # The existence of an [ after parsing indicates a parsing failure
    for v in parsed_email_header_tuples:
        if '[' in v[1]:
            v = ('', '')
        accepted_values.append(v)

    return accepted_values


ecre = re.compile(r'''
  =\?                   # literal =?
  (?P<charset>[^?]*?)   # non-greedy up to the next ? is the charset
  \?                    # literal ?
  (?P<encoding>[qb])    # either a "q" or a "b", case insensitive
  \?                    # literal ?
  (?P<atom>.*?)         # non-greedy up to the next ?= is the atom
  \?=                   # literal ?=
  ''', re.VERBOSE | re.IGNORECASE)



def formatdate(timeval=None, localtime=False, usegmt=False):
    """Returns a date string as specified by RFC 2822, e.g.:

    Fri, 09 Nov 2001 01:08:47 -0000

    Optional timeval if given is a floating point time value as accepted by
    gmtime() and localtime(), otherwise the current time is used.

    Optional localtime is a flag that when True, interprets timeval, and
    returns a date relative to the local timezone instead of UTC, properly
    taking daylight savings time into account.

    Optional argument usegmt means that the timezone is written out as
    an ascii string, not numeric one (so "GMT" instead of "+0000"). This
    is needed for HTTP, and is only used when localtime==False.
    """
    # Note: we cannot use strftime() because that honors the locale and RFC
    # 2822 requires that day and month names be the English abbreviations.
    if timeval is None:
        timeval = time.time()
    if localtime:
        now = time.localtime(timeval)
        # Calculate timezone offset, based on whether the local zone has
        # daylight savings time, and whether DST is in effect.
        if time.daylight and now[-1]:
            offset = time.altzone
        else:
            offset = time.timezone
        hours, minutes = divmod(abs(offset), 3600)
        # Remember offset is in seconds west of UTC, but the timezone is in
        # minutes east of UTC, so the signs differ.
        if offset > 0:
            sign = '-'
        else:
            sign = '+'
        zone = '%s%02d%02d' % (sign, hours, minutes // 60)
    else:
        now = time.gmtime(timeval)
        # Timezone offset is always -0000
        if usegmt:
            zone = 'GMT'
        else:
            zone = '-0000'
    return '%s, %02d %s %04d %02d:%02d:%02d %s' % (
        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][now[6]],
        now[2],
        ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][now[1] - 1],
        now[0], now[3], now[4], now[5],
        zone)



def make_msgid(idstring=None):
    """Returns a string suitable for RFC 2822 compliant Message-ID, e.g:

    <142480216486.20800.16526388040877946887@nightshade.la.mastaler.com>

    Optional idstring if given is a string used to strengthen the
    uniqueness of the message id.
    """
    timeval = int(time.time()*100)
    pid = os.getpid()
    randint = random.getrandbits(64)
    if idstring is None:
        idstring = ''
    else:
        idstring = '.' + idstring
    idhost = socket.getfqdn()
    msgid = '<%d.%d.%d%s@%s>' % (timeval, pid, randint, idstring, idhost)
    return msgid



# These functions are in the standalone mimelib version only because they've
# subsequently been fixed in the latest Python versions.  We use this to worm
# around broken older Pythons.
def parsedate(data):
    if not data:
        return None
    return _parsedate(data)


def parsedate_tz(data):
    if not data:
        return None
    return _parsedate_tz(data)


def parseaddr(addr, strict=True):
    """
    Parse addr into its constituent realname and email address parts.

    Return a tuple of realname and email address, unless the parse fails, in
    which case return a 2-tuple of ('', '').

    If strict is True, use a strict parser which rejects malformed inputs.
    """
    if not strict:
        addrs = _AddressList(addr).addresslist
        if not addrs:
            return ('', '')
        return addrs[0]

    if isinstance(addr, list):
        addr = addr[0]

    if not isinstance(addr, str):
        return ('', '')

    addr = _pre_parse_validation([addr])[0]
    addrs = _post_parse_validation(_AddressList(addr).addresslist)

    if not addrs or len(addrs) > 1:
        return ('', '')

    return addrs[0]



# rfc822.unquote() doesn't properly de-backslash-ify in Python pre-2.3.
def unquote(str):
    """Remove quotes from a string."""
    if len(str) > 1:
        if str.startswith('"') and str.endswith('"'):
            return str[1:-1].replace('\\\\', '\\').replace('\\"', '"')
        if str.startswith('<') and str.endswith('>'):
            return str[1:-1]
    return str



# RFC2231-related functions - parameter encoding and decoding
def decode_rfc2231(s):
    """Decode string according to RFC 2231"""
    parts = s.split(TICK, 2)
    if len(parts) <= 2:
        return None, None, s
    return parts


def encode_rfc2231(s, charset=None, language=None):
    """Encode string according to RFC 2231.

    If neither charset nor language is given, then s is returned as-is.  If
    charset is given but not language, the string is encoded using the empty
    string for language.
    """
    import urllib
    s = urllib.quote(s, safe='')
    if charset is None and language is None:
        return s
    if language is None:
        language = ''
    return "%s'%s'%s" % (charset, language, s)


rfc2231_continuation = re.compile(r'^(?P<name>\w+)\*((?P<num>[0-9]+)\*?)?$')

def decode_params(params):
    """Decode parameters list according to RFC 2231.

    params is a sequence of 2-tuples containing (param name, string value).
    """
    # Copy params so we don't mess with the original
    params = params[:]
    new_params = []
    # Map parameter's name to a list of continuations.  The values are a
    # 3-tuple of the continuation number, the string value, and a flag
    # specifying whether a particular segment is %-encoded.
    rfc2231_params = {}
    name, value = params.pop(0)
    new_params.append((name, value))
    while params:
        name, value = params.pop(0)
        if name.endswith('*'):
            encoded = True
        else:
            encoded = False
        value = unquote(value)
        mo = rfc2231_continuation.match(name)
        if mo:
            name, num = mo.group('name', 'num')
            if num is not None:
                num = int(num)
            rfc2231_params.setdefault(name, []).append((num, value, encoded))
        else:
            new_params.append((name, '"%s"' % quote(value)))
    if rfc2231_params:
        for name, continuations in rfc2231_params.items():
            value = []
            extended = False
            # Sort by number
            continuations.sort()
            # And now append all values in numerical order, converting
            # %-encodings for the encoded segments.  If any of the
            # continuation names ends in a *, then the entire string, after
            # decoding segments and concatenating, must have the charset and
            # language specifiers at the beginning of the string.
            for num, s, encoded in continuations:
                if encoded:
                    s = urllib.unquote(s)
                    extended = True
                value.append(s)
            value = quote(EMPTYSTRING.join(value))
            if extended:
                charset, language, value = decode_rfc2231(value)
                new_params.append((name, (charset, language, '"%s"' % value)))
            else:
                new_params.append((name, '"%s"' % value))
    return new_params

def collapse_rfc2231_value(value, errors='replace',
                           fallback_charset='us-ascii'):
    if isinstance(value, tuple):
        rawval = unquote(value[2])
        charset = value[0] or 'us-ascii'
        try:
            return unicode(rawval, charset, errors)
        except LookupError:
            # XXX charset is unknown to Python.
            return unicode(rawval, fallback_charset, errors)
    else:
        return unquote(value)
