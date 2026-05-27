# Simple test suite for Cookie.py

from test.test_support import run_unittest, run_doctest, check_warnings
from test import support
import unittest
import Cookie
import pickle


class CookieTests(unittest.TestCase):

    def test_control_characters_rejected(self):
        # CVE-2026-0672: control characters (e.g. CR/LF) in cookie values or
        # attributes must be rejected to prevent Set-Cookie header injection.
        M = Cookie.Morsel()
        self.assertRaises(Cookie.CookieError, M.set,
                          'key', 'value\r\nInjected: header', 'value')
        self.assertRaises(Cookie.CookieError, M.set,
                          'key', 'value', 'coded\nvalue')
        self.assertRaises(Cookie.CookieError, M.__setitem__,
                          'path', '/\r\nSet-Cookie: pwned=1')
        # Benign values still work.
        M.set('key', 'value', 'value')
        M['path'] = '/ok'

    # Currently this only tests SimpleCookie
    def test_basic(self):
        cases = [
            { 'data': 'chips=ahoy; vienna=finger',
              'dict': {'chips':'ahoy', 'vienna':'finger'},
              'repr': "<SimpleCookie: chips='ahoy' vienna='finger'>",
              'output': 'Set-Cookie: chips=ahoy\nSet-Cookie: vienna=finger',
            },

            # Control characters in cookie values are now rejected
            # (CVE-2026-0672); see test_control_characters_rejected.

            # Check illegal cookies that have an '=' char in an unquoted value
            { 'data': 'keebler=E=mc2',
              'dict': {'keebler' : 'E=mc2'},
              'repr': "<SimpleCookie: keebler='E=mc2'>",
              'output': 'Set-Cookie: keebler=E=mc2',
            },

            # issue22931 - Adding '[' and ']' as valid characters in cookie
            # values as defined in RFC 6265
            {
                'data': 'a=b; c=[; d=r; f=h',
                'dict': {'a':'b', 'c':'[', 'd':'r', 'f':'h'},
                'repr': "<SimpleCookie: a='b' c='[' d='r' f='h'>",
                'output': '\n'.join((
                    'Set-Cookie: a=b',
                    'Set-Cookie: c=[',
                    'Set-Cookie: d=r',
                    'Set-Cookie: f=h'
                ))
            }
        ]

        for case in cases:
            C = Cookie.SimpleCookie()
            C.load(case['data'])
            self.assertEqual(repr(C), case['repr'])
            self.assertEqual(C.output(sep='\n'), case['output'])
            for k, v in sorted(case['dict'].iteritems()):
                self.assertEqual(C[k].value, v)

    def test_load(self):
        C = Cookie.SimpleCookie()
        C.load('Customer="WILE_E_COYOTE"; Version=1; Path=/acme')

        self.assertEqual(C['Customer'].value, 'WILE_E_COYOTE')
        self.assertEqual(C['Customer']['version'], '1')
        self.assertEqual(C['Customer']['path'], '/acme')

        self.assertEqual(C.output(['path']),
            'Set-Cookie: Customer="WILE_E_COYOTE"; Path=/acme')
        self.assertEqual(C.js_output(), r"""
        <script type="text/javascript">
        <!-- begin hiding
        document.cookie = "Customer=\"WILE_E_COYOTE\"; Path=/acme; Version=1";
        // end hiding -->
        </script>
        """)
        self.assertEqual(C.js_output(['path']), r"""
        <script type="text/javascript">
        <!-- begin hiding
        document.cookie = "Customer=\"WILE_E_COYOTE\"; Path=/acme";
        // end hiding -->
        </script>
        """)

        # loading 'expires'
        C = Cookie.SimpleCookie()
        C.load('Customer="W"; expires=Wed, 01 Jan 2010 00:00:00 GMT')
        self.assertEqual(C['Customer']['expires'],
                         'Wed, 01 Jan 2010 00:00:00 GMT')
        C = Cookie.SimpleCookie()
        C.load('Customer="W"; expires=Wed, 01 Jan 98 00:00:00 GMT')
        self.assertEqual(C['Customer']['expires'],
                         'Wed, 01 Jan 98 00:00:00 GMT')

    def test_extended_encode(self):
        # Issue 9824: some browsers don't follow the standard; we now
        # encode , and ; to keep them from tripping up.
        C = Cookie.SimpleCookie()
        C['val'] = "some,funky;stuff"
        self.assertEqual(C.output(['val']),
            'Set-Cookie: val="some\\054funky\\073stuff"')

    def test_set_secure_httponly_attrs(self):
        C = Cookie.SimpleCookie('Customer="WILE_E_COYOTE"')
        C['Customer']['secure'] = True
        C['Customer']['httponly'] = True
        self.assertEqual(C.output(),
            'Set-Cookie: Customer="WILE_E_COYOTE"; httponly; secure')

    def test_secure_httponly_false_if_not_present(self):
        C = Cookie.SimpleCookie()
        C.load('eggs=scrambled; Path=/bacon')
        self.assertFalse(C['eggs']['httponly'])
        self.assertFalse(C['eggs']['secure'])

    def test_secure_httponly_true_if_present(self):
        # Issue 16611
        C = Cookie.SimpleCookie()
        C.load('eggs=scrambled; httponly; secure; Path=/bacon')
        self.assertTrue(C['eggs']['httponly'])
        self.assertTrue(C['eggs']['secure'])

    def test_secure_httponly_true_if_have_value(self):
        # This isn't really valid, but demonstrates what the current code
        # is expected to do in this case.
        C = Cookie.SimpleCookie()
        C.load('eggs=scrambled; httponly=foo; secure=bar; Path=/bacon')
        self.assertTrue(C['eggs']['httponly'])
        self.assertTrue(C['eggs']['secure'])
        # Here is what it actually does; don't depend on this behavior.  These
        # checks are testing backward compatibility for issue 16611.
        self.assertEqual(C['eggs']['httponly'], 'foo')
        self.assertEqual(C['eggs']['secure'], 'bar')

    def test_bad_attrs(self):
        # Issue 16611: make sure we don't break backward compatibility.
        C = Cookie.SimpleCookie()
        C.load('cookie=with; invalid; version; second=cookie;')
        self.assertEqual(C.output(),
            'Set-Cookie: cookie=with\r\nSet-Cookie: second=cookie')

    def test_extra_spaces(self):
        C = Cookie.SimpleCookie()
        C.load('eggs  =  scrambled  ;  secure  ;  path  =  bar   ; foo=foo   ')
        self.assertEqual(C.output(),
            'Set-Cookie: eggs=scrambled; Path=bar; secure\r\nSet-Cookie: foo=foo')

    def test_quoted_meta(self):
        # Try cookie with quoted meta-data
        C = Cookie.SimpleCookie()
        C.load('Customer="WILE_E_COYOTE"; Version="1"; Path="/acme"')
        self.assertEqual(C['Customer'].value, 'WILE_E_COYOTE')
        self.assertEqual(C['Customer']['version'], '1')
        self.assertEqual(C['Customer']['path'], '/acme')

    def test_invalid_cookies(self):
        # Accepting these could be a security issue
        C = Cookie.SimpleCookie()
        for s in (']foo=x', '[foo=x', 'blah]foo=x', 'blah[foo=x'):
            C.load(s)
            self.assertEqual(dict(C), {})
            self.assertEqual(C.output(), '')

    def test_unquote(self):
        cases = [
            (r'a="b=\""', 'b="'),
            (r'a="b=\\"', 'b=\\'),
            (r'a="b=\="', 'b=='),
            (r'a="b=\n"', 'b=n'),
            (r'a="b=\042"', 'b="'),
            (r'a="b=\134"', 'b=\\'),
            (r'a="b=\377"', 'b=\xff'),
            (r'a="b=\400"', 'b=400'),
            (r'a="b=\42"', 'b=42'),
            (r'a="b=\\042"', 'b=\\042'),
            (r'a="b=\\134"', 'b=\\134'),
            (r'a="b=\\\""', 'b=\\"'),
            (r'a="b=\\\042"', 'b=\\"'),
            (r'a="b=\134\""', 'b=\\"'),
            (r'a="b=\134\042"', 'b=\\"'),
        ]
        for encoded, decoded in cases:
            # with self.subTest(encoded):
            C = Cookie.SimpleCookie()
            C.load(encoded)
            self.assertEqual(C['a'].value, decoded)

    @support.requires_resource('cpu')
    def test_unquote_large(self):
        n = 10**6
        for encoded in r'\\', r'\134':
            # with self.subTest(encoded):
            data = 'a="b=' + encoded*n + ';"'
            C = Cookie.SimpleCookie()
            C.load(data)
            value = C['a'].value
            self.assertEqual(value[:3], 'b=\\')
            self.assertEqual(value[-2:], '\\;')
            self.assertEqual(len(value), n + 3)


    def test_pickle(self):
        rawdata = 'Customer="WILE_E_COYOTE"; Path=/acme; Version=1'
        expected_output = 'Set-Cookie: %s' % rawdata

        C = Cookie.SimpleCookie()
        C.load(rawdata)
        self.assertEqual(C.output(), expected_output)

        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            C1 = pickle.loads(pickle.dumps(C, protocol=proto))
            self.assertEqual(C1.output(), expected_output)


def test_main():
    run_unittest(CookieTests)
    if Cookie.__doc__ is not None:
        with check_warnings(('.+Cookie class is insecure; do not use it',
                             DeprecationWarning)):
            run_doctest(Cookie)

if __name__ == '__main__':
    test_main()
