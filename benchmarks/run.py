"""Reproducible CPU measurement; run from any directory."""

import codecs
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def metadata():
    files = sorted((ROOT / ROOT.name).glob("*.py"))
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()
    return {
        "utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "source_sha256": digest,
        "clock": "perf_counter_ns",
        "warmup": 2,
        "repeats": 7,
    }


def timed(fn):
    for _ in range(2):
        fn()
    samples = []
    for _ in range(7):
        start = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - start) / 1000)
    return {
        "samples_us": samples,
        "median_us": median(samples),
        "min_us": min(samples),
        "max_us": max(samples),
    }


def save(receipt):
    (ROOT / "receipts").mkdir(exist_ok=True)
    (ROOT / "receipts" / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    print("BENCHMARK_OK")


from streamdetok import Detok, Vocab  # noqa: E402


def custom(chunks):
    detok = Detok(Vocab(chunks))
    return "".join(detok.push(i) for i in range(len(chunks))) + detok.flush()


def reference(chunks):
    decoder = codecs.getincrementaldecoder("utf-8")("ignore")
    return "".join(decoder.decode(chunk, final=False) for chunk in chunks) + decoder.decode(
        b"", final=True
    )


def main():
    text = "café € emoji \U0001f480 — हिंदी e\u0301 " * 64
    raw = text.encode()
    rows = []
    for chunk_size in [1, 2, 3, 4, 8, 32, 128]:
        chunks = [raw[i : i + chunk_size] for i in range(0, len(raw), chunk_size)]
        assert custom(chunks) == reference(chunks) == text
        naive = "".join(chunk.decode("utf-8", "replace") for chunk in chunks)
        rows.append(
            {
                "chunk_bytes": chunk_size,
                "input_bytes": len(raw),
                "pushes": len(chunks),
                "naive_replacements": naive.count("\ufffd"),
                "custom_replacements": custom(chunks).count("\ufffd"),
                "custom": timed(lambda: custom(chunks)),
                "codecs": timed(lambda: reference(chunks)),
            }
        )
    raw = "A€💀é".encode()
    detok = Detok(Vocab([bytes([byte]) for byte in raw]))
    trace = []
    for i, byte in enumerate(raw):
        emitted = detok.push(i)
        trace.append(
            {
                "step": i + 1,
                "input_hex": f"{byte:02x}",
                "emitted": emitted,
                "emitted_codepoints": [f"U+{ord(char):04X}" for char in emitted],
                "held_hex": bytes(detok.buf).hex(),
                "held_bytes": len(detok.buf),
            }
        )
    invalid = [b"A\xc0\x80B", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe2\x82"]
    recovery = []
    for raw in invalid:
        decoder = Detok(Vocab([raw]))
        output = decoder.push(0) + decoder.flush()
        assert output == raw.decode("utf-8", "ignore")
        recovery.append(
            {
                "input_hex": raw.hex(),
                "output": output,
                "dropped_bytes": decoder.dropped_bytes,
                "reports": decoder.reported,
            }
        )
    save(
        {
            "metadata": metadata(),
            "scope": "byte payload vocab only; no tokenizer context transformations",
            "chunk_sweep": rows,
            "trace": trace,
            "invalid_recovery": recovery,
        }
    )


if __name__ == "__main__":
    main()
