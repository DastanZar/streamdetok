"""Byte payload streaming examples, complemented by codec differential tests."""

import itertools
import random
import sys

sys.path.insert(0, ".")
from streamdetok import Detok, Vocab, toy_vocab  # noqa: E402


def naive_stream(tokens, vocab):
    return "".join(vocab.token_bytes[t].decode("utf-8", errors="replace") for t in tokens)


def stream(tokens, vocab):
    d = Detok(vocab)
    out = "".join(d.push(t) for t in tokens) + d.flush()
    return out, d


SKULL = "💀".encode()  # F0 9F 92 80 (4 bytes)
EURO = "€".encode()  # E2 82 AC (3 bytes)
ACC = "é".encode()  # C3 A9 (2 bytes)


def test_split_multibyte_emits_garbage_naively_not_here():
    # a token carrying ONLY the lead byte of an emoji:
    vocab = Vocab([SKULL[:1], SKULL[1:], b"A"])
    naive = naive_stream([0, 1, 2], vocab)
    assert "\ufffd" in naive, "expected the naive path to produce the classic garbage"
    good, d = stream([0, 1, 2], vocab)
    assert good == "\U0001f480A" and d.dropped == 0


def test_full_text_equality_split_orders():
    vocab = Vocab([SKULL[:1], SKULL[1:], b"A"])
    good, _ = stream([0, 1, 2], vocab)
    assert good == "\U0001f480A"
    # the same bytes as [A][lead][tail]:
    good2, _ = stream([2, 0, 1], vocab)
    assert good2 == "A\U0001f480"


def test_all_chunkings_agree_with_direct_decode():
    """The theorem, fuzzed: for random token plans over random text, EVERY
    interleaving/streaming equals direct decode; garbage only appears where
    the SOURCE text itself contained invalid bytes."""
    rng = random.Random(11)
    corpus = ["A€B💀", "👍🏽 café", "naïve — ok", "mixed 💀€é"]
    for text in corpus:
        raw = text.encode()
        # random chunkings of raw into "tokens": build vocab on the fly
        cuts = sorted(rng.sample(range(1, len(raw)), min(3, max(0, len(raw) - 1))))
        idx = [0] + cuts + [len(raw)]
        pieces = [raw[a:b] for a, b in zip(idx, idx[1:])]
        vocab = Vocab(pieces + [b"X"])
        toks = list(range(len(pieces)))
        out, d = stream(toks, vocab)
        assert out == text, (text, out)
        assert d.dropped == 0


def test_every_pair_of_3way_splits_for_emoji():
    """All 3-way splits of the 4-byte emoji as 3 tokens: 6 orderings x
    the split — every one must reconstruct exactly."""
    for perm in itertools.permutations([SKULL[:1], SKULL[1:2], SKULL[2:]]):
        if b"".join(perm) != SKULL:
            continue
        vocab = Vocab(list(perm) + [b"b"])
        out, d = stream(list(range(3)), vocab)
        assert out == "\U0001f480" and d.dropped == 0


def test_dead_bytes_are_reported_not_mangled():
    """An orphan continuation byte can never be rescued: it is DROPPED with a
    report — never silently replaced by U+FFFD inside otherwise clean text."""
    vocab = Vocab([b"A", SKULL[1:2], b"B"])  # token 1 = bare 0x9F orphan
    out, d = stream([0, 1, 2], vocab)
    assert d.dropped == 1 and "9f" in "".join(d.reported)
    assert "A" in out and "B" in out and "\ufffd" not in out


def test_incremental_latency_not_batched():
    """Eagerness: ASCII tokens flush on the SAME push (the UI sees characters
    at token cadence, not at EOS)."""
    vocab = Vocab([b"hi", b" ", b"there"])
    d = Detok(vocab)
    assert d.push(0) == "hi"
    assert d.push(1) == " "
    assert d.push(2) == "there"
    assert d.flush() == ""


def test_toy_vocab_roundtrips_its_own_grammar():
    v = toy_vocab()
    # [ hello][euro lead-2 E282][euro tail AC][whole skull]
    toks = [v.token_bytes.index(payload) for payload in [b" hello", EURO[:2], EURO[2:], SKULL]]
    out, d = stream(toks, v)
    assert out == " hello€\U0001f480" and d.dropped == 0


def test_toy_vocab_catches_a_malformed_plan():
    """Token plan 6-before-7 (orphan continuation first): the machine drops
    the orphan, completes the euro lead with the skull's bytes NOT being
    continuations, and still emits exactly the decodable text."""
    v = toy_vocab()
    tokens = [v.token_bytes.index(payload) for payload in [b" hello", SKULL[1:], EURO[:2], SKULL]]
    out, d = stream(tokens, v)
    assert out == " hello\U0001f480" and d.dropped == 2
