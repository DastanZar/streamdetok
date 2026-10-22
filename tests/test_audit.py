import codecs

import pytest

from streamdetok import Detok, Vocab
from streamdetok.core import UTF8


@pytest.mark.parametrize(
    "raw", [b"\xc0\x80", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe0\x80", b"\xffA"]
)
def test_invalid_utf8_recovery_matches_ignore(raw):
    detok = Detok(Vocab([raw]))
    assert detok.push(0) + detok.flush() == raw.decode("utf-8", "ignore")
    assert not UTF8.complete(raw)


def test_nonfinal_flush_preserves_valid_pending_tail():
    detok = Detok(Vocab([b"\xe2", b"\x82\xac"]))
    assert detok.push(0) == ""
    assert detok.flush(eos=False) == ""
    assert detok.push(1) == "€"


def test_per_push_matches_incremental_codec():
    raw = "A€💀é".encode()
    decoder = codecs.getincrementaldecoder("utf-8")()
    detok = Detok(Vocab([bytes([b]) for b in raw]))
    for index, byte in enumerate(raw):
        assert detok.push(index) == decoder.decode(bytes([byte]), final=False)
        assert bytes(detok.buf) == decoder.getstate()[0]
