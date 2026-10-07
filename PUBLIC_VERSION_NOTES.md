# Public version notes

- Original RawData and CleanData files removed.
- Original training datasets and serialized model removed.
- Dataset generator replaced with a fictional example.com demo.
- Classifier training changed to synthetic-only, with example.com email templates.
- Original guideline screenshot and stale test report removed.
- Source code attribution retained; no Git history is included in this ZIP.
- This package does not clean or alter the original GitHub repository or its history.
- Use a new repository for this snapshot, rather than uploading it into a fork with old sensitive history.

## Validation

- Synthetic CLI demo: 13 rows, 12 valid, 1 quarantined, 12 unique entities.
- Focused normalization/contract tests: 31 passed, 3 original-data integration tests deselected.
- Full original suite: 62 passed, 12 failed (original datasets, hard-coded local paths, Windows/compiled installer artifacts or original CLI fixtures unavailable). These are not claimed as passing.
- Windows installer build and browser dashboard interaction were not verified.
- Synthetic classifier validation is template-based and is not evidence of real-world accuracy.
