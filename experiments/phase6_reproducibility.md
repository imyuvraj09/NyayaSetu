# Phase 6 Reproducibility Specification

## Experimental Runtime Environment

- **Operating System**: Windows 11 64-bit Architecture
- **Hardware**: Multi-core x86_64 CPU (PyTorch CPU Execution)
- **Python Version**: 3.14.3 (`.\rag-service\venv\Scripts\python.exe`)
- **Virtual Environment**: `.\rag-service\venv`
- **Core Dependencies**:
  - `numpy==2.5.2`
  - `scipy==1.18.1`
  - `scikit-learn==1.9.0`
  - `pyyaml==6.0.3`
  - `pydantic==2.13.5`
- **Corpus Version**: 14 Statutory Enactments (6,545 indexed chunks in `rag-service/data/processed/legal_chunks.jsonl`)
- **Benchmark Version**: `phase6-v1` (N = 250 records across `benchmark_train.json`, `benchmark_validation.json`, `benchmark_test.json`)
- **Deterministic Random Seed**: `42` (applied to all bootstrap resampling and split operations)
- **Bootstrap Iterations**: $B = 10,000$ (95% Confidence Level)
- **Significance Alpha**: $\alpha = 0.05$ (Holm-Bonferroni & Benjamini-Hochberg FDR adjustments)

## Reproduction Commands

To reproduce the complete benchmark validation, data integrity checks, comparative evaluation, inferential significance testing, and results compilation:

```powershell
# 1. Run unit test suites
.\rag-service\venv\Scripts\python.exe -m unittest discover -s tests
.\rag-service\venv\Scripts\python.exe -m unittest discover -s rag-service/tests

# 2. Run data integrity & schema validation
.\rag-service\venv\Scripts\python.exe evaluation/phase6/benchmark_validator.py
.\rag-service\venv\Scripts\python.exe evaluation/phase6/data_integrity.py

# 3. Execute end-to-end evaluation & statistical testing suite
.\rag-service\venv\Scripts\python.exe scripts/run_phase6_evaluation.py --config configs/phase6_evaluation_config.yaml

# 4. Compile and verify results tables
.\rag-service\venv\Scripts\python.exe scripts/compile_phase6_results.py
```
