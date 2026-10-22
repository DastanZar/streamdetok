"""Generate offline visuals from measured receipt traces, never invented data."""

import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)
r = json.loads((ROOT / "receipts" / "receipt.json").read_text())
plt.rcParams.update({"font.family": "DejaVu Sans", "figure.dpi": 150, "font.size": 10})


def save(name):
    plt.tight_layout()
    plt.savefig(OUT / name)
    plt.close()


def frames_gif(rows, lines, name, accent):
    frames = []
    for index, row in enumerate(rows):
        image = Image.new("RGB", (850, 280), "#0f172a")
        draw = ImageDraw.Draw(image)
        draw.text(
            (28, 22),
            f"{ROOT.name} | live-code trace | step {index + 1}/{len(rows)}",
            fill=accent,
            font_size=23,
        )
        for j, line in enumerate(lines(row)):
            draw.text((28, 80 + j * 38), line, fill="#e2e8f0", font_size=20)
        draw.rectangle((28, 250, 28 + int(780 * (index + 1) / len(rows)), 258), fill=accent)
        frames.append(image)
    frames[0].save(OUT / name, save_all=True, append_images=frames[1:], duration=500, loop=0)


rows = r["chunk_sweep"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for key, label in [("custom", "Python scanner"), ("codecs", "CPython incremental codec")]:
    axes[0].plot(
        [x["chunk_bytes"] for x in rows], [x[key]["median_us"] for x in rows], "o-", label=label
    )
axes[0].set_xscale("log", base=2)
axes[0].set_yscale("log")
axes[0].set_xlabel("Bytes per payload token")
axes[0].set_ylabel("Median whole-stream time (microseconds)")
axes[0].legend(fontsize=8)
for key, label in [
    ("naive_replacements", "Naive per-token replace"),
    ("custom_replacements", "Incremental scanner"),
]:
    axes[1].plot([x["chunk_bytes"] for x in rows], [x[key] for x in rows], "o-", label=label)
axes[1].set_xscale("log", base=2)
axes[1].set_xlabel("Bytes per payload token")
axes[1].set_ylabel("Replacement characters introduced")
axes[1].legend(fontsize=8)
fig.suptitle("Byte-boundary correctness has overhead: compare with codecs, too")
save("garbage_curve.png")

plt.figure(figsize=(9, 3))
plt.step(
    [x["step"] for x in r["trace"]],
    [x["held_bytes"] for x in r["trace"]],
    where="post",
    color="#d97706",
)
plt.xticks([x["step"] for x in r["trace"]], [x["input_hex"] for x in r["trace"]])
plt.xlabel("One-byte payload tokens (hex)")
plt.ylabel("Retained bytes")
plt.title("Actual stream state: complete codepoints emit; at most 3 bytes remain")
save("buffer_timeline.png")
frames_gif(
    r["trace"],
    lambda row: [
        "Input byte: " + row["input_hex"],
        "Emit: " + (" ".join(row["emitted_codepoints"]) or "nothing"),
        "Retain: " + (row["held_hex"] or "empty"),
    ],
    "utf8_trace.gif",
    "#fbbf24",
)
