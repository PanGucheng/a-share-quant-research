# Corrected Selection Mutation Contract

- Status: `pass`
- Outer-test mutation cases: `12`
- Sources: test IC, factor exposure, labels, raw OHLCVA; each also covers row order and extreme missing values.
- Proof mode: effective source mutation, exact allowed-date projection identity, verified selection parent chain, and committed split-scoped business payload hashes.
- Selection stages are not re-run because their content-addressed inputs are byte-identical after mutation; this contract proves the release boundary rather than fabricating alternate outputs.
