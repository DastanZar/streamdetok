# Measurement protocol

Run `python benchmarks/run.py` from this checkout after installing `.[viz]`.
The standard-library benchmark itself has no runtime dependencies; plotting is
separate: `python demos/make_figures.py`.

`receipts/receipt.json` is overwritten on every run. It includes UTC, Python,
platform and a SHA-256 of the sorted library source files, plus all seven timing
samples after two untimed warmups. Units are microseconds from perf_counter_ns.
The range is run-to-run variation, not a confidence interval. CPU frequency,
background processes and interpreter build are uncontrolled. No GPU was used.

The project README defines workloads, reference paths and exclusions. Figures
and the GIF consume receipt rows/real execution traces, not hand-authored values.
The synthetic examples do not establish production speedups or universal safety.

`receipts/verification.json` records the separately executed local Ruff, formatting,
mypy, pytest and sdist/wheel build gates. Visual files were decoded successfully
and SVG parsed as XML. Auxiliary visual-model review failed (provider error / timeout),
so no successful model-based visual review is claimed.
