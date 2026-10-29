# Input/output v1

Contract fields: `schema_version:1`, `task:"regression"|"binary"`, unique `features:[strings]`, `target:string`, `feature_availability:{feature:"known_at_prediction"}`, `split:"group"|"time"|"group_time"`, and corresponding `group_field`/`time_field` strings. Time values must be ISO 8601 including timezone. Group and row IDs must be nonempty strings. Features are finite JSON numbers or null, with every key present. Labels are finite numeric, and binary labels exactly 0/1. Numeric strings/booleans/NaN/infinity/duplicate JSON keys are refused.

Training and development files contain JSON arrays of labelled row objects. Test is a separate sealed labelled array. Prediction rows have the same numeric features and unique `id`; split metadata is optional for prediction. Additional fields are ignored, so the declared feature list is the only model input. Keep the source feature contract when converting CSV and preserve identifiers rather than making labels from them.

CLI: `python scripts/model.py seal-test examples/test.json SEAL.json`; `python scripts/model.py fit examples/contract.json examples/train.json examples/dev.json SEAL.json MODEL.json`; `python scripts/model.py predict MODEL.json examples/inference.json PRED.json`; `python scripts/model.py audit-test MODEL.json examples/test.json SEAL.json AUDIT.json`.

Outputs never overwrite. Model stores exact feature/preprocessing/weight contract, selection scores, split IDs/group/time boundary, input hashes and seal hash. A successful audit records model/test SHA256 and metrics. The seal-adjacent `.audit-lock` remains on success or failure and forbids a second audit through that seal. Keep it with the seal/model receipt. These are source files/data, not platform hooks or background services.
