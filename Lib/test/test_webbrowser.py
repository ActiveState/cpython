import unittest
import webbrowser

from test import test_support


class FakeUnixBrowser(webbrowser.UnixBrowser):
    # Concrete UnixBrowser with string actions so open() can run far enough
    # to perform URL validation without launching anything.
    remote_args = ['%action', '%s']
    remote_action = ""
    remote_action_newwin = "-new-window"
    remote_action_newtab = "-new-tab"


class CheckURLTest(unittest.TestCase):
    # CVE-2026-4519 / CVE-2026-4786: webbrowser.open() must not let an
    # attacker-controlled URL be turned into a command-line option
    # (argument injection).

    def test_check_url_rejects_leading_dash(self):
        for bad in ("-remote", "--incognito", "  -leadingspace", "\t-tab"):
            self.assertRaises(ValueError,
                              webbrowser.BaseBrowser._check_url, bad)

    def test_check_url_allows_normal(self):
        for ok in ("http://example.com", "https://x/-dash-inside", ""):
            # Must not raise.
            webbrowser.BaseBrowser._check_url(ok)

    def test_generic_browser_rejects_dash_url(self):
        browser = webbrowser.GenericBrowser(["true", "%s"])
        self.assertRaises(ValueError, browser.open, "-dangerous")

    def test_unix_browser_rejects_dash_url(self):
        browser = FakeUnixBrowser("fakebrowser")
        self.assertRaises(ValueError, browser.open, "-dangerous")

    def test_unix_browser_rejects_action_bypass(self):
        # The %action substitution must not be usable to smuggle a leading
        # dash past the check (CVE-2026-4786). With new=1 the action expands
        # to "-new-window", so a "%action" URL would become a bare flag.
        browser = FakeUnixBrowser("fakebrowser")
        self.assertRaises(ValueError, browser.open, "%action", 1)


def test_main():
    test_support.run_unittest(CheckURLTest)


if __name__ == "__main__":
    test_main()
