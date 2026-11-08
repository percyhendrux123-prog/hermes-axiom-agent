"""Read-only file access that checks the opened descriptor, not a path it may race with."""
import codecs
import errno
import os
import re
import stat


_CLOEXEC = getattr(os, 'O_CLOEXEC', 0)
_NOFOLLOW = getattr(os, 'O_NOFOLLOW', 0)
_FILE_FLAGS = os.O_RDONLY | _NOFOLLOW | getattr(os, 'O_NONBLOCK', 0) | _CLOEXEC
_DIR_FLAGS = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | _CLOEXEC
_CHUNK = 65536


class NotRegular(ValueError):
    """The entry is a symbolic link, special file or wrong kind of entry."""


def _open(name, flags: int, parent: int | None) -> int:
    try:
        return os.open(name, flags) if parent is None else os.open(name, flags, dir_fd=parent)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR, errno.EMLINK):
            raise NotRegular('Non-regular entry') from None
        raise


def open_dir(name, parent: int | None = None, follow: bool = False) -> int:
    """Open a directory descriptor; a symlink is refused unless *follow* is set."""
    fd = _open(name, _DIR_FLAGS | (0 if follow else _NOFOLLOW), parent)
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise NotRegular('Non-directory entry')
    return fd


def read_text(parent: int, name: str, cap: int | None = None) -> str:
    """Read a regular file below *parent* without following a symlink.

    Returns at most ``cap + 1`` characters, so callers can detect overflow. FIFOs and devices are
    rejected after a non-blocking open, before any read. Newlines are normalised like ``open()``.
    """
    fd = _open(name, _FILE_FLAGS, parent)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise NotRegular('Non-regular file')
        limit = None if cap is None else 4 * (cap + 1)
        chunks, total = [], 0
        while limit is None or total < limit:
            data = os.read(fd, _CHUNK if limit is None else min(_CHUNK, limit - total))
            if not data:
                break
            chunks.append(data)
            total += len(data)
        hit_limit = limit is not None and total >= limit
        text = codecs.getincrementaldecoder('utf-8')().decode(b''.join(chunks), final=not hit_limit)
    finally:
        os.close(fd)
    text = re.sub(r'\r\n?', '\n', text)
    return text if cap is None else text[:cap + 1]


def close(fd: int | None) -> None:
    if fd is not None:
        os.close(fd)
