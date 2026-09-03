# Data

`processed/` is the complete analysis-ready dataset for all 142 accepted runs.
`example-run/` is representative raw and normalized evidence for one
narrow-spike/oracle execution; request-level JSONL is omitted from this compact
repository. Definitions, exclusions, and raw-archive requirements are in
`docs/DATA.md` and `processing/DATA-DICTIONARY.md`.

Do not treat aligned seconds or annotated events as independent inferential
replicates. The run is the inferential unit.
