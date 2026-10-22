"""Incremental UTF-8 decoding of context-independent byte payload tokens.

Invalid spans are reported and dropped, never replaced. This is lossy
recovery, not full tokenizer detokenization or a Unicode grapheme segmenter.
"""

from __future__ import annotations

from typing import List

from .core import UTF8, scan


class Vocab:
    def __init__(self, token_bytes: List[bytes]):
        self.token_bytes = tuple(token_bytes)

    def first_bytes(self) -> set[int]:
        return {tb[0] for tb in self.token_bytes if tb}


class Detok:
    """push(tok) -> str to emit now; flush() at end of turn."""

    def __init__(self, vocab: Vocab):
        self.vocab = vocab
        self.buf = bytearray()
        self.dropped = 0  # number of reporting events, not bytes
        self.dropped_bytes = 0
        self.reported: List[str] = []

    def push(self, tok: int) -> str:
        if not 0 <= tok < len(self.vocab.token_bytes):
            raise IndexError(tok)
        self.buf.extend(self.vocab.token_bytes[tok])
        raw = bytes(self.buf)
        dead = scan(raw)[2]
        if dead:
            self.dropped += 1
            self.dropped_bytes += len(dead)
            self.reported.append("dead-bytes:" + bytes(raw[i] for i in dead).hex())
        complete, tail = UTF8.pending(raw)
        self.buf = bytearray(tail)
        return complete.decode("utf-8")

    def flush(self, eos: bool = True) -> str:
        """Nonfinal flush preserves the tail; EOS reports and drops truncation."""
        if eos and self.buf:
            self.dropped += 1
            self.dropped_bytes += len(self.buf)
            self.reported.append("unterminated-at-eos:" + bytes(self.buf).hex())
            self.buf.clear()
        return ""


def toy_vocab() -> Vocab:
    """An ASCII + multibyte world, tokenized adversarially: whole codepoints,
    lead-then-tail splits, and bare continuation bytes."""
    euro = "€".encode()  # E2 82 AC (3)
    skull = "💀".encode()  # F0 9F 92 80 (4)
    acc = "é".encode()  # C3 A9 (2)
    toks = [
        b"A",
        b"ab",
        b" hello",
        euro,
        skull,
        skull[:1],
        skull[1:],
        euro[:2],
        euro[2:],
        skull[1:2],
        acc[:1],
        acc[1:],
    ]
    return Vocab(toks)
