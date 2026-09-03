# Step 18 — Statistical Analysis

This package performs the prespecified paired statistical analysis of the Step 17 run-level dataset.

Primary files:

- `ANALYSIS-PROTOCOL.md`: frozen estimands, tests, multiplicity, interactions, and limitations;
- `STATISTICAL-ANALYSIS-REPORT.md`: complete interpretation;
- `output/paired-comparisons.csv`: effects, confidence intervals, tests, adjusted p-values, and sensitivity;
- `output/condition-descriptives.csv`: means, medians, IQRs, and standard deviations;
- `output/individual-run-points.csv`: every analyzed run value;
- `output/interaction-contrasts.csv`: identified difference-in-differences;
- `output/ranking-agreement.csv` and `condition-rankings.csv`: supplementary ranking analysis;
- `figures/`: six publication-quality vector charts with accessible titles and descriptions;
- `tools/`: deterministic analysis and validation programs.

The run, not the second or event, is the inferential unit. No accepted run is excluded.
