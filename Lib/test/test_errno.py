"""Test the errno module
   Roger E. Masse
"""

import errno
import sys
from test import test_support
import unittest

std_c_errors = frozenset(['EDOM', 'ERANGE'])

class ErrnoAttributeTests(unittest.TestCase):

    def test_for_improper_attributes(self):
        # No unexpected attributes should be on the module.
        for error_code in std_c_errors:
            self.assertTrue(hasattr(errno, error_code),
                            "errno is missing %s" % error_code)

    def test_using_errorcode(self):
        # Every key value in errno.errorcode should be on the module.
        for value in errno.errorcode.itervalues():
            self.assertTrue(hasattr(errno, value), 'no %s attr in errno' % value)


class ErrorcodeTests(unittest.TestCase):

    def test_attributes_in_errorcode(self):
        for attribute in errno.__dict__.iterkeys():
            if attribute.isupper():
                self.assertIn(getattr(errno, attribute), errno.errorcode,
                              'no %s attr in errno.errorcode' % attribute)


@unittest.skipUnless(sys.platform == 'win32', 'Windows specific')
class WinsockErrnoTests(unittest.TestCase):

    # VS2010+ errno.h defines its own values for these; sockets report the
    # Winsock ones, so the errno module must use those.
    names = ['EADDRINUSE', 'EADDRNOTAVAIL', 'EAFNOSUPPORT', 'EALREADY',
             'ECONNABORTED', 'ECONNREFUSED', 'ECONNRESET', 'EDESTADDRREQ',
             'EHOSTUNREACH', 'EINPROGRESS', 'EISCONN', 'ELOOP', 'EMSGSIZE',
             'ENETDOWN', 'ENETRESET', 'ENETUNREACH', 'ENOBUFS', 'ENOPROTOOPT',
             'ENOTCONN', 'ENOTSOCK', 'EOPNOTSUPP', 'EPROTONOSUPPORT',
             'EPROTOTYPE', 'ETIMEDOUT', 'EWOULDBLOCK']

    def test_socket_constants_are_winsock_values(self):
        for name in self.names:
            self.assertEqual(getattr(errno, name), getattr(errno, 'WSA' + name),
                             name)

    def test_socket_error_matches_errno(self):
        import socket
        s = socket.socket()
        try:
            s.setblocking(False)
            # Connecting to a non-routable address does not complete at once.
            self.assertEqual(s.connect_ex(('10.255.255.1', 80)),
                             errno.EWOULDBLOCK)
        finally:
            s.close()


def test_main():
    test_support.run_unittest(ErrnoAttributeTests, ErrorcodeTests,
                              WinsockErrnoTests)


if __name__ == '__main__':
    test_main()
