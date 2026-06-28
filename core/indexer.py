"""File walking + chunking + metadata extraction. Used by build_index.py."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterator, List, Tuple


@dataclass
class Chunk:
    chunk_id: str        # "<rel_path>::<idx>"
    rel_path: str
    ext: str
    start_line: int
    end_line: int
    text: str

    def to_metadata(self) -> Dict:
        d = asdict(self)
        d.pop("text")
        return d


def iter_source_files(root: Path, include_ext: List[str], exclude_dirs: List[str],
                      min_bytes: int, max_bytes: int) -> Iterator[Path]:
    exclude = set(exclude_dirs)
    inc_ext = set(include_ext)
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter excluded dirs in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if d not in exclude and not d.startswith(".")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() not in inc_ext:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if size < min_bytes or size > max_bytes:
                continue
            yield p


def _split_into_chunks(text: str, chunk_size: int, overlap: int) -> List[Tuple[int, int, str]]:
    """Line-aware chunking. Returns (start_line_1based, end_line_1based, chunk_text)."""
    lines = text.splitlines(keepends=True)
    if not lines:
        return []
    chunks: List[Tuple[int, int, str]] = []
    line_lens = [len(l) for l in lines]
    n = len(lines)
    i = 0
    while i < n:
        buf_chars = 0
        j = i
        while j < n and buf_chars < chunk_size:
            buf_chars += line_lens[j]
            j += 1
        # j is exclusive end. start_line is i+1, end_line is j.
        chunk_text = "".join(lines[i:j])
        chunks.append((i + 1, j, chunk_text))
        if j >= n:
            break
        # Step forward, leaving `overlap` characters of overlap roughly
        back_chars = 0
        back = j
        while back > i and back_chars < overlap:
            back -= 1
            back_chars += line_lens[back]
        i = max(back, i + 1)
    return chunks


def chunk_file(path: Path, root: Path, chunk_size: int, overlap: int) -> List[Chunk]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rel = str(path.relative_to(root))
    out: List[Chunk] = []
    for idx, (s, e, t) in enumerate(_split_into_chunks(text, chunk_size, overlap)):
        out.append(Chunk(
            chunk_id=f"{rel}::{idx}",
            rel_path=rel,
            ext=path.suffix.lower(),
            start_line=s,
            end_line=e,
            text=t,
        ))
    return out
