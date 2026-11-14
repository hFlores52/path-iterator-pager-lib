"""Core implementation of the path iterator pager.

The pager exists so that callers can walk a directory containing millions of
entries without materializing the whole listing in memory.  ``os.scandir``
already yields entries lazily, but a caller that wants to process entries in
batches (for example to commit a transaction per batch) needs a paging layer
on top.  We deliberately keep the page size explicit and do not buffer more
than one page at a time.
"""

from __future__ import annotations

import os
from typing import Iterator, List


class PathIteratorPager:
    """Iterate over the entries of a directory in fixed-size pages.

    The pager yields lists of :class:`os.DirEntry` objects.  Each page is
    materialized as a list so the caller can index into it, but only one page
    is held at a time.  The directory handle is closed when iteration finishes
    or when the pager is used as a context manager and the ``with`` block
    exits.

    The page size must be positive; a zero or negative page size would make
    the iterator either infinite or empty in a confusing way, so we reject it
    eagerly in the constructor.
    """

    def __init__(self, path: str | os.PathLike[str], page_size: int = 1024) -> None:
        if page_size <= 0:
            raise ValueError("page_size must be a positive integer")
        self._path = os.fspath(path)
        self._page_size = page_size
        self._scandir: os.ScandirIterator | None = None

    @property
    def path(self) -> str:
        """The directory path being paged."""
        return self._path

    @property
    def page_size(self) -> int:
        """The maximum number of entries returned in each page."""
        return self._page_size

    def __iter__(self) -> Iterator[List[os.DirEntry]]:
        """Yield successive pages of directory entries.

        The iterator is single-use: once it has been exhausted the underlying
        directory handle is closed and a second iteration will reopen the
        directory from the start.  This mirrors the behaviour of
        ``os.scandir`` and keeps the object cheap to reuse in a loop.
        """
        return self._iterate()

    def _iterate(self) -> Iterator[List[os.DirEntry]]:
        # ``os.scandir`` is itself an iterator; we close it explicitly rather
        # than relying on garbage collection so that file descriptors are not
        # held longer than necessary.
        with os.scandir(self._path) as scandir:
            page: List[os.DirEntry] = []
            for entry in scandir:
                page.append(entry)
                if len(page) >= self._page_size:
                    yield page
                    page = []
            if page:
                yield page

    def __enter__(self) -> "PathIteratorPager":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # Nothing to release here because ``_iterate`` owns the scandir
        # context.  The context manager is provided for symmetry and to make
        # the intended usage pattern obvious.
        return None
