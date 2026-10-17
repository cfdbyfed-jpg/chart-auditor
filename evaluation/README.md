# Synthetic audit benchmark

## Purpose

This benchmark asks whether Uncharted's rule-based checks return their
predefined statuses for controlled chart configurations. It is a reproducible
sanity check for implementation behavior, not a study of how often misleading
charts occur in practice.

## Method

The scenarios in `benchmark.py` specify chart settings, values, and expected
statuses before running the auditor. They cover all five supported chart types,
including clear settings, detected range clipping, a truncated bar baseline,
missing values, line-order cases, crowded and repeated bar categories, constant
values, and a scale-dominating extreme observation. The runner compares each
expected status with the result returned by `audit_chart`.

Threshold-based checks are documented in `auditor.py`: bar charts with more
than 20 categories are flagged for review; extreme values are screened with
3×IQR fences and a full-range-to-IQR ratio of at least 10. These are transparent
review heuristics, not universal definitions of a poor chart or erroneous data.

True-positive, false-positive, false-negative, and true-negative counts are
reported only for binary expected statuses (`detected` and `clear`).
`not_applicable` checks are counted separately. A status mismatch involving a
missing or `not_applicable` result is reported as an exact-status mismatch and
is not forced into a binary confusion category.

## Run

From the project root:

```powershell
python -m evaluation.benchmark
```

The command exits with a nonzero status if any expected scenario does not
match. The same scenarios are covered by `tests/test_benchmark.py`.

## Recorded run

Run date: 2026-10-17. All 21 scenarios matched all 87 expected check statuses.
The binary counts below exclude `not_applicable` checks:

| Check | Exact status matches | TP | FP | FN | TN | N/A |
|---|---:|---:|---:|---:|---:|---:|
| Chart and data suitability | 7/7 | 2 | 0 | 0 | 5 | 0 |
| Axis data visibility | 10/10 | 4 | 0 | 0 | 6 | 0 |
| Bar-axis integrity | 14/14 | 2 | 0 | 0 | 2 | 10 |
| Difference amplification | 14/14 | 1 | 0 | 0 | 1 | 12 |
| Extreme-value context | 7/7 | 1 | 0 | 0 | 3 | 3 |
| Incomplete rows | 14/14 | 1 | 0 | 0 | 13 | 0 |
| Line X order | 14/14 | 1 | 0 | 0 | 1 | 12 |
| Repeated bar categories | 7/7 | 1 | 0 | 0 | 2 | 4 |

## Interpreting results and limitations

The cases are hand-authored synthetic examples, not independently annotated
real-world charts. Matching every case demonstrates that these specified
behaviors work as expected; it does not establish general precision, recall,
F1-score, or resistance to false alarms on unseen data. The reported confusion
counts describe only these designed cases. Broader claims would require a
representative, independently labeled chart set and a documented evaluation
procedure.
