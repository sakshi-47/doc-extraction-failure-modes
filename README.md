# Document Extraction Failure Modes

Measuring how document field extraction fails under real-world image degradation — and specifically how often it fails *silently*, returning a confident, well-formed, wrong value that passes every format check downstream.

> **Status: milestone 1 of 4 — scoring layer only.** The metric is implemented and tested. There are no experimental results in this repository yet, and this README will not claim any until there are. See [Roadmap](#roadmap).

---

## The question

A verification pipeline that returns `null` for a date of birth has failed usefully: validation catches it, the case routes to a human, it costs money. A pipeline that returns `1991-02-01` when the document says `1990-02-01` has failed dangerously: it satisfies every format check and reaches a decision carrying a value nobody verified.

Standard extraction benchmarks report field accuracy, which counts both as one error. This project treats them as different failure classes and measures the second one directly.

**Central hypothesis:** as input images degrade, the ratio of silent failures to loud failures rises. Models do not become uncertain in proportion to how wrong they are.

## The metric

Two numbers, both defined in [`src/docfail/metrics/cfer.py`](src/docfail/metrics/cfer.py).

**Critical Field Error Rate (CFER)** weights each field error along two axes:

- *Criticality* — a wrong date of birth is a compliance failure; a mangled street suffix is noise.
- *Severity* — `WRONG` and `SPURIOUS` reach a decision; `MISSING` fails loudly and routes to review. Weighting them equally, as flat accuracy does, hides the mode that matters.

```
CFER = Σ (criticality_weight × severity_weight) / Σ criticality_weight
```

**Silent Failure Rate (SFR)** isolates the dangerous quadrant on its own: fields that are wrong, well-formed, and confidently asserted. A value the canonicaliser cannot parse as its field kind is *excluded* — it fails validation loudly, which is the safe outcome.

Every headline number in this project ships with a bootstrap confidence interval. A difference reported without one is not a finding.

## Quickstart

```bash
git clone https://github.com/sakshi-47/doc-extraction-failure-modes
cd doc-extraction-failure-modes
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Optional, for the extraction backends in milestone 3:

```bash
cp .env.example .env   # then fill in a provider key
docfail config         # shows resolved settings; holds no credentials
```

Datasets are never committed. Fetch one with `python scripts/download_data.py cord --extract`.

## Layout

```
src/docfail/
  settings.py        typed settings; no import-time side effects, no credentials
  types.py           Criticality, FieldKind, MatchStatus, FieldOutcome
  metrics/
    normalize.py     field-kind-aware canonicalisation
    fields.py        predicted field vs. ground truth  →  MatchStatus
    cfer.py          CFER, Silent Failure Rate, bootstrap intervals
  datasets/base.py   corpus adapter interface       (milestone 2)
  degrade/           degradation conditions          (milestone 2)
  extract/base.py    extraction backend interface    (milestone 3)
tests/               47 tests over the scoring layer
scripts/             dataset download with checksum + safe extraction
```

## Roadmap

| # | Milestone | State |
|---|---|---|
| 1 | Scoring layer: CFER, SFR, canonicalisation, bootstrap CIs, CI | **done** |
| 2 | CORD adapter + degradation grid (blur, glare, skew, low light, occlusion, JPEG, screen-replay) | next |
| 3 | Extraction backends: a VLM baseline and a local OCR baseline, cached and rate-limited | |
| 4 | Experiments, results, confidence intervals, and a deployed results service | |

## Prior work

The framing owes a debt to [svpathak/rag-failure-modes](https://github.com/svpathak/rag-failure-modes), which asks the analogous question of retrieval-augmented generation: it introduces an Evidence Coverage Score to catch answers that look faithful but were generated from the wrong retrieved context. The silent-failure quadrant here is the same idea moved from retrieval to extraction, and its Caveats section is a model worth copying.

Two things in that repository shaped decisions here rather than being inherited from it:

- Its scorer takes a sequence of accepted answers, and every call site passes a single string. Iterating a string yields characters, so `"Yes"` is scored against `'Y'`, `'e'`, `'s'`. Nothing raises. All nine rows of its published F1 table are token overlap against single characters. [`metrics/fields.py`](src/docfail/metrics/fields.py) rejects a bare `str` at runtime for exactly this reason — a `str` satisfies `Sequence[str]`, so no type checker catches it — and `TestBareStringGuard` is the regression test.
- Its four experiment scripts all raise `ImportError` on a clean checkout, because a constant was removed from its config during cleanup and nothing re-imported them. CI here runs an import smoke test on every push.

Neither observation diminishes the original idea, which is a good one. They are the reason this is an independent implementation rather than a fork.

## Caveats

Kept deliberately, in the spirit of the prior work, and updated as the project grows:

- No experimental results exist yet. The metric is tested against constructed cases, not validated against human judgement on real extractions.
- Severity and criticality weights (`1.0 / 0.3 / 0.05`) are reasoned, not calibrated. They encode a claim about verification economics that a cost model should eventually replace. Results should be reported as sensitive to them.
- Date canonicalisation assumes day-first ordering. That suits the target corpora but silently mis-parses US-format dates, which is itself one of the silent failures this project is about.
- Name canonicalisation sorts tokens, so it cannot distinguish a genuine given-name/surname swap from a formatting difference. For corpora where field ordering is semantically load-bearing this is wrong.
- Treating absent confidence as confident is a choice, not a fact. It is the conservative reading — no confidence signal means nothing routes the case to review — but it inflates SFR for backends that simply do not report confidence.

## Licence

MIT. See [LICENSE](LICENSE).
