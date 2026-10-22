import codecs
import itertools
import random

from streamdetok import Detok, Vocab
from streamdetok.core import UTF8, scan


def compare(chunks):
    decoder = codecs.getincrementaldecoder("utf-8")("ignore")
    detok = Detok(Vocab(chunks))
    output = []
    for index, chunk in enumerate(chunks):
        emitted = detok.push(index)
        assert emitted == decoder.decode(chunk, final=False)
        codec_tail = decoder.getstate()[0]
        # CPython defers ED A0..BF rejection until a third byte. Our scanner
        # rejects that already-impossible surrogate prefix eagerly.
        if bytes(detok.buf) != codec_tail:
            assert codec_tail[:1] == b"\xed" and len(codec_tail) == 2 and codec_tail[1] >= 0xA0
            assert not detok.buf
        assert len(detok.buf) <= 3
        output.append(emitted)
    assert detok.flush() == decoder.decode(b"", final=True)
    raw = b"".join(chunks)
    assert "".join(output) == raw.decode("utf-8", "ignore")
    assert detok.dropped_bytes == len(raw) - len("".join(output).encode())


def test_all_one_and_two_byte_scanner_inputs_against_codec():
    for length in (1, 2):
        for values in itertools.product(range(256), repeat=length):
            raw = bytes(values)
            decoder = codecs.getincrementaldecoder("utf-8")("ignore")
            text = decoder.decode(raw, final=False)
            good, tail = UTF8.pending(raw)
            count, pending, dead = scan(raw)
            assert good.decode() == text
            codec_tail = decoder.getstate()[0]
            if tail != codec_tail:
                assert codec_tail[:1] == b"\xed" and len(codec_tail) == 2 and codec_tail[1] >= 0xA0
                assert tail == b""
            assert count == len(good) and pending == len(tail)
            assert len(raw) == count + pending + len(dead)


def test_all_partitions_of_small_valid_text():
    raw = "A€💀".encode()
    for mask in range(1 << (len(raw) - 1)):
        cuts = [0] + [i for i in range(1, len(raw)) if mask & (1 << (i - 1))] + [len(raw)]
        compare([raw[a:b] for a, b in zip(cuts, cuts[1:])])


def test_random_invalid_streams_and_valid_unicode():
    rng = random.Random(123)
    for _ in range(1500):
        raw = rng.randbytes(rng.randrange(1, 80))
        compare([raw[i : i + 3] for i in range(0, len(raw), 3)])
    for _ in range(300):
        points = [rng.randrange(0x110000) for _ in range(30)]
        raw = "".join(chr(p) for p in points if not 0xD800 <= p <= 0xDFFF).encode()
        compare([bytes([byte]) for byte in raw])
