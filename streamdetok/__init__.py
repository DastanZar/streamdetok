"""Incremental UTF-8 over context-independent byte payload vocabularies.

Not a full BPE/SentencePiece detokenizer: tokenizer-specific whitespace,
special tokens, normalization and context-dependent rendering are outside
the API. Python codecs is the independent reference."""

from .detok import Detok, Vocab, toy_vocab

__all__ = ["Detok", "Vocab", "toy_vocab"]
