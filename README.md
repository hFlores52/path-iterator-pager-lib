# path-iterator-pager-lib

Iterate over the entries of a directory in fixed-size pages so that a listing
with millions of files does not have to fit in memory all at once.

```python
from path_iterator_pager_lib import PathIteratorPager

pager = PathIteratorPager("/var/log", page_size=1000)
for page in pager:
    # page is a list of os.DirEntry objects, at most 1000 long
    for entry in page:
        print(entry.name)
```

The constructor takes the directory path (a string or any `os.PathLike`) and a
positive integer `page_size`.  `PathIteratorPager` is itself iterable and
yields `list[os.DirEntry]`; the `path` and `page_size` attributes are exposed
as read-only properties.  The object can be reused: iterating it again reopens
the directory from the start.

## Why this exists

`os.scandir` already streams entries one at a time, but many callers need to
process work in batches: commit a database transaction per batch, write one
output file per batch, or hand a bounded chunk to a worker pool.  Buffering the
whole directory with `os.listdir` defeats the purpose on large directories,
and wrapping `os.scandir` in a manual counter is easy to get subtly wrong.

This library makes the page boundary explicit and holds exactly one page at a
time.  The trade-off is that a page is materialized as a list, so the caller
can index into it, which means peak memory is one page rather than one entry.
For a page size of a few thousand that is negligible; for a page size of a
million it is not, so choose the page size deliberately.

## Edge cases

An empty directory produces no pages at all, not a single empty page.  A page
size that divides the entry count evenly produces only full pages; a remainder
produces a final shorter page.  A page size of zero or a negative number
raises `ValueError` from the constructor rather than producing an iterator that
silently yields nothing.  A missing directory raises `FileNotFoundError` when
iteration begins, matching `os.scandir`.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

