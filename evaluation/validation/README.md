# Validation Benchmark Partition

This directory contains the independent **validation benchmark** for tuning retrieval parameters, compatibility weights, and reranker thresholds.

## Requirements for Validation Datasets
1. **Separation**: Must not contain queries present in `evaluation/development/existing_questions.json` or `evaluation/test/`.
2. **Schema Adherence**: All entries must validate against [evaluation/benchmark_schema.json](../benchmark_schema.json).
3. **No Fabrication**: Validation annotations must be collected via manual expert annotation using the templates in [evaluation/annotation_templates/](../annotation_templates/).
4. **Review Status**: Must indicate `draft`, `unreviewed`, or `peer_reviewed`.
