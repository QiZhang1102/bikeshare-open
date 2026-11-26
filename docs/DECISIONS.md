# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-25: Added `cnt_roll_3` (3-day rolling mean of prior ride counts; when forecasting Jan 12, the Jan 9-11 ride counts are already known). Validation R^2 changed ridge 0.6475 -> 0.6439 (delta -0.0036) and hgb hgb 0.2185 -> 0.1983 (delta -0.0202); both fell short of the +0.01 guideline. We kept cnt_roll_3 in the default training pipeline to reproduce the 15-feature experiment. Based on the validation results, we recommend using the original 14 features for forecasting.
