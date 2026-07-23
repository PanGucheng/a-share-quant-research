# Corrected Outer-Split FDR Gate

- Status: `pass`
- Families / hypotheses per family: `3` / `25`
- Input folds: `outer train only`; outer validation and test are absent.
- Inner-window semantics: full outer-train eligibility gate, not nested pseudo-OOS FDR replay.
- Frozen bootstrap method: `gap_aware_moving_block`; policy artifact is bound by hash.
