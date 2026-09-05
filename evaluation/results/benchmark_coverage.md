# Benchmark Coverage Analysis: `existing_questions.json`

**Total Queries Evaluated:** 43
- **Single-Target Queries:** 39 (90.7%)
- **Multi-Target Queries:** 0 (0.0%)
- **Zero-Target / Out-of-Scope Queries:** 4 (9.3%)

## 1. Statute Distribution
| Statute / Enactment | Count | Percentage |
|---|---|---|
| Constitution of India | 6 | 14.0% |
| Bharatiya Nyaya Sanhita, 2023 | 6 | 14.0% |
| Bharatiya Nagarik Suraksha Sanhita, 2023 | 6 | 14.0% |
| Bharatiya Sakshya Adhiniyam, 2023 | 6 | 14.0% |
| Consumer Protection Act | 5 | 11.6% |
| Information Technology Act | 5 | 11.6% |
| Motor Vehicles Act | 5 | 11.6% |
| None / Out of Scope | 4 | 9.3% |

## 2. Query Type Taxonomy
| Query Type | Count | Percentage |
|---|---|---|
| `direct_statutory` | 33 | 76.7% |
| `section_identification` | 4 | 9.3% |
| `fact_pattern` | 2 | 4.7% |
| `negative_or_out_of_scope` | 2 | 4.7% |
| `ambiguous` | 2 | 4.7% |

## 3. Difficulty Distribution
| Difficulty | Count | Percentage |
|---|---|---|
| Medium | 17 | 39.5% |
| Hard | 13 | 30.2% |
| Easy | 13 | 30.2% |

## 4. Imbalance Assessment & Research Limitations
> [!IMPORTANT]
> **Taxonomy Imbalance:** CRITICAL IMBALANCE: Direct statutory queries dominate (>70%); fact-pattern queries are under-represented (<5%).
>
> **Target Complexity Imbalance:** CRITICAL IMBALANCE: 100% of answerable queries are annotated with only a single target document.
>
> **Research Implication:** The current development benchmark cannot be used alone to justify general multi-target legal discovery claims. It serves as a reliable development baseline for regression and single-statute discovery.