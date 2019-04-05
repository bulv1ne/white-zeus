import unittest

from white_zeus.utils import partial_find


class TestApp(unittest.TestCase):
    def test_middle_match(self):
        self.assertEqual(
            partial_find(b"Niels loves Tisse and Juna", b"Tisse"),
            (b"Niels loves Tisse", b" and Juna"),
        )

    def test_end_match(self):
        self.assertEqual(
            partial_find(b"Niels loves Tisse", b"Tisse"), (b"Niels loves Tisse", b"")
        )

    def test_partial_end_match(self):
        self.assertEqual(
            partial_find(b"Niels loves Tiss", b"Tisse"), (b"Niels loves ", b"Tiss")
        )
        self.assertEqual(
            partial_find(b"Niels loves Tis", b"Tisse"), (b"Niels loves ", b"Tis")
        )
        self.assertEqual(
            partial_find(b"Niels loves Ti", b"Tisse"), (b"Niels loves ", b"Ti")
        )
        self.assertEqual(
            partial_find(b"Niels loves T", b"Tisse"), (b"Niels loves ", b"T")
        )

        self.assertEqual(partial_find(b"", b"Tisse"), (b"", b""))
        self.assertEqual(partial_find(b"T", b"Tisse"), (b"", b"T"))
        self.assertEqual(partial_find(b"Ti", b"Tisse"), (b"", b"Ti"))
        self.assertEqual(partial_find(b"Tis", b"Tisse"), (b"", b"Tis"))
        self.assertEqual(partial_find(b"Tiss", b"Tisse"), (b"", b"Tiss"))
        self.assertEqual(partial_find(b"Tisse", b"Tisse"), (b"Tisse", b""))

    def test_no_match(self):
        self.assertEqual(
            partial_find(b"Nothing here is found", b"Tisse"),
            (b"Nothing here is found", b""),
        )
        self.assertEqual(partial_find(b"Tiss ", b"Tisse"), (b"Tiss ", b""))
