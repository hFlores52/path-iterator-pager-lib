import os
import tempfile
import unittest

from path_iterator_pager_lib import PathIteratorPager


class PathIteratorPagerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name

    def _touch(self, name):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
            fh.write("")

    def test_empty_directory_yields_no_pages(self):
        pager = PathIteratorPager(self.root, page_size=4)
        self.assertEqual(list(pager), [])

    def test_exact_multiple_of_page_size(self):
        for i in range(8):
            self._touch(f"f{i:02d}")
        pager = PathIteratorPager(self.root, page_size=4)
        pages = list(pager)
        self.assertEqual(len(pages), 2)
        self.assertEqual([len(p) for p in pages], [4, 4])

    def test_remainder_page(self):
        for i in range(5):
            self._touch(f"f{i:02d}")
        pager = PathIteratorPager(self.root, page_size=2)
        pages = list(pager)
        self.assertEqual([len(p) for p in pages], [2, 2, 1])

    def test_page_size_larger_than_directory(self):
        for i in range(3):
            self._touch(f"f{i:02d}")
        pager = PathIteratorPager(self.root, page_size=100)
        pages = list(pager)
        self.assertEqual(len(pages), 1)
        self.assertEqual(len(pages[0]), 3)

    def test_page_size_one(self):
        for i in range(3):
            self._touch(f"f{i:02d}")
        pager = PathIteratorPager(self.root, page_size=1)
        pages = list(pager)
        self.assertEqual([len(p) for p in pages], [1, 1, 1])

    def test_entries_are_dir_entries(self):
        self._touch("only")
        pager = PathIteratorPager(self.root, page_size=10)
        (page,) = list(pager)
        (entry,) = page
        self.assertIsInstance(entry, os.DirEntry)
        self.assertEqual(entry.name, "only")

    def test_all_names_appear_exactly_once(self):
        names = [f"n{i:03d}" for i in range(17)]
        for name in names:
            self._touch(name)
        pager = PathIteratorPager(self.root, page_size=5)
        seen = [entry.name for page in pager for entry in page]
        self.assertEqual(sorted(seen), sorted(names))

    def test_invalid_page_size_rejected(self):
        with self.assertRaises(ValueError):
            PathIteratorPager(self.root, page_size=0)
        with self.assertRaises(ValueError):
            PathIteratorPager(self.root, page_size=-1)

    def test_path_and_page_size_properties(self):
        pager = PathIteratorPager(self.root, page_size=7)
        self.assertEqual(pager.page_size, 7)
        self.assertEqual(pager.path, self.root)

    def test_path_accepts_pathlike(self):
        import pathlib

        pager = PathIteratorPager(pathlib.Path(self.root), page_size=2)
        self.assertEqual(pager.path, self.root)

    def test_reiterable_after_exhaustion(self):
        self._touch("a")
        self._touch("b")
        pager = PathIteratorPager(self.root, page_size=1)
        first = [entry.name for page in pager for entry in page]
        second = [entry.name for page in pager for entry in page]
        self.assertEqual(sorted(first), ["a", "b"])
        self.assertEqual(sorted(second), ["a", "b"])

    def test_context_manager(self):
        self._touch("x")
        with PathIteratorPager(self.root, page_size=3) as pager:
            pages = list(pager)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0][0].name, "x")

    def test_missing_directory_raises(self):
        missing = os.path.join(self.root, "does-not-exist")
        pager = PathIteratorPager(missing, page_size=4)
        with self.assertRaises(FileNotFoundError):
            list(pager)


if __name__ == "__main__":
    unittest.main()
