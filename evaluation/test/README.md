# Test Benchmark Partition

This directory holds the holdout **test benchmark** reserved exclusively for final evaluation and ablation experiments.

## Integrity Protocols
1. **Blind Evaluation**: No model, weight, or prompt parameter may be tuned using queries in this directory.
2. **Leakage Verification**: Must pass [evaluation/detect_leakage.py](../detect_leakage.py) with 0 exact or near-duplicate overlaps with development or validation splits.
3. **Expert Ground Truth**: Every query and relevant provision must be reviewed by qualified legal experts and marked with `review_status: expert_verified`.
4. **Schema**: Validated against [evaluation/benchmark_schema.json](../benchmark_schema.json).
