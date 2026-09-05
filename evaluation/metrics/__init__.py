"""NyayaSetu Information Retrieval & Evaluation Metrics Package.

Provides mathematically correct implementations of:
- Hit@K (Binary target discovery within top K)
- Precision@K (Proportion of evaluated retrieved positions that are relevant)
- Recall@K (True multi-target recall over unique relevant items)
- Reciprocal Rank (RR) & Mean Reciprocal Rank (MRR)
- DCG, IDCG & Normalized Discounted Cumulative Gain (nDCG@K) with graded relevance
- Keyword Coverage (Fraction of expected legal keywords present)
"""

from evaluation.metrics.hit_at_k import (
    calculate_hit_at_k,
    calculate_mean_hit_at_k,
)
from evaluation.metrics.keyword_coverage import (
    calculate_keyword_coverage,
)
from evaluation.metrics.mrr import (
    calculate_mrr,
    calculate_reciprocal_rank,
)
from evaluation.metrics.ndcg import (
    calculate_dcg_at_k,
    calculate_idcg_at_k,
    calculate_mean_ndcg_at_k,
    calculate_ndcg_at_k,
)
from evaluation.metrics.precision_at_k import (
    calculate_mean_precision_at_k,
    calculate_precision_at_k,
)
from evaluation.metrics.recall_at_k import (
    calculate_mean_recall_at_k,
    calculate_recall_at_k,
)

__all__ = [
    "calculate_hit_at_k",
    "calculate_mean_hit_at_k",
    "calculate_precision_at_k",
    "calculate_mean_precision_at_k",
    "calculate_recall_at_k",
    "calculate_mean_recall_at_k",
    "calculate_reciprocal_rank",
    "calculate_mrr",
    "calculate_dcg_at_k",
    "calculate_idcg_at_k",
    "calculate_ndcg_at_k",
    "calculate_mean_ndcg_at_k",
    "calculate_keyword_coverage",
]
