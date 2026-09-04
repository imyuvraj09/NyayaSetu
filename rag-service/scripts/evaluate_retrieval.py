"""
Comprehensive Retrieval Benchmark and Corpus Validation Suite for NyayaSetu.

Tests and reports:
1. Corpus Validation across all 14 legal Acts (document count, chunk count, section metadata)
2. Substantive, Procedural, Evidentiary, Multi-part, and Cross-domain queries
3. Metrics: Hit@1, Hit@3, Hit@5, MRR, Top-1 Statute Accuracy, Top-K Statute Purity, Evidence Completeness
"""

import json
import time
from typing import Any, Dict, List

from retrieval.advanced_retriever import AdvancedRetriever
from retrieval.section_indexer import get_section_indexer
from utils.logger import get_logger
from vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)

# Test Query Dataset representing diverse legal inquiry types
BENCHMARK_QUERIES = [
    # Substantive Criminal Law (BNS)
    {
        "id": "SUB-01",
        "category": "Substantive",
        "query": "What constitutes murder under BNS?",
        "expected_act": "Bharatiya Nyaya Sanhita, 2023",
        "expected_act_id": "bns_2023",
        "expected_sections": ["101"],
    },
    {
        "id": "SUB-02",
        "category": "Substantive",
        "query": "What is the punishment for murder?",
        "expected_act": "Bharatiya Nyaya Sanhita, 2023",
        "expected_act_id": "bns_2023",
        "expected_sections": ["103", "104"],
    },
    {
        "id": "SUB-03",
        "category": "Substantive",
        "query": "What are the exceptions to murder?",
        "expected_act": "Bharatiya Nyaya Sanhita, 2023",
        "expected_act_id": "bns_2023",
        "expected_sections": ["101"],
    },
    {
        "id": "SUB-04",
        "category": "Substantive",
        "query": "What is culpable homicide?",
        "expected_act": "Bharatiya Nyaya Sanhita, 2023",
        "expected_act_id": "bns_2023",
        "expected_sections": ["100", "101", "105"],
    },
    {
        "id": "SUB-05",
        "category": "Substantive",
        "query": "What is the difference between murder and culpable homicide?",
        "expected_act": "Bharatiya Nyaya Sanhita, 2023",
        "expected_act_id": "bns_2023",
        "expected_sections": ["100", "101"],
    },
    # Procedural Criminal Law (BNSS)
    {
        "id": "PROC-01",
        "category": "Procedural",
        "query": "How is a murder case investigated?",
        "expected_act": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "expected_act_id": "bnss_2023",
        "expected_sections": ["175", "176", "179", "180", "193"],
    },
    {
        "id": "PROC-02",
        "category": "Procedural",
        "query": "What happens after an FIR for murder?",
        "expected_act": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "expected_act_id": "bnss_2023",
        "expected_sections": ["173", "175", "176", "193"],
    },
    {
        "id": "PROC-03",
        "category": "Procedural",
        "query": "What is the procedure for investigation?",
        "expected_act": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "expected_act_id": "bnss_2023",
        "expected_sections": ["175", "176", "180"],
    },
    # Evidence Law (BSA)
    {
        "id": "EVID-01",
        "category": "Evidence",
        "query": "What evidence is relevant in a murder trial?",
        "expected_act": "Bharatiya Sakshya Adhiniyam, 2023",
        "expected_act_id": "bsa_2023",
        "expected_sections": ["4", "5", "6", "26", "45", "104"],
    },
    {
        "id": "EVID-02",
        "category": "Evidence",
        "query": "What is the evidentiary value of electronic records?",
        "expected_act": "Bharatiya Sakshya Adhiniyam, 2023",
        "expected_act_id": "bsa_2023",
        "expected_sections": ["61", "62", "63"],
    },
    # Multi-Part Substantive
    {
        "id": "MULTI-01",
        "category": "Multi-Part",
        "query": "What constitutes murder under the Bharatiya Nyaya Sanhita, 2023, and what is the punishment prescribed for it?",
        "expected_act": "Bharatiya Nyaya Sanhita, 2023",
        "expected_act_id": "bns_2023",
        "expected_sections": ["101", "103"],
        "requires_both": True,
    },
    # Cross-Domain Inquiry
    {
        "id": "CROSS-01",
        "category": "Cross-Domain",
        "query": "What is murder, how is it investigated, and what evidence can prove it?",
        "expected_act": "Bharatiya Nyaya Sanhita, 2023",
        "expected_act_id": "bns_2023",
        "expected_sections": ["101", "175", "176", "61"],
        "is_cross_domain": True,
    },
    # Specialized Acts
    {
        "id": "SPEC-01",
        "category": "Child Protection",
        "query": "What is penetrative sexual assault under POCSO Act and what is the punishment?",
        "expected_act": "The Protection of Children from Sexual Offences Act, 2012",
        "expected_act_id": "pocso_act_2012",
        "expected_sections": ["3", "4", "5", "6"],
    },
    {
        "id": "SPEC-02",
        "category": "Labour / POSH",
        "query": "How is an Internal Complaints Committee constituted under POSH Act?",
        "expected_act": "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
        "expected_act_id": "sexual_harassment_workplace_act_2013",
        "expected_sections": ["4"],
    },
    {
        "id": "SPEC-03",
        "category": "Constitutional Law",
        "query": "What is the right to personal liberty under Article 21 of the Constitution?",
        "expected_act": "Constitution of India",
        "expected_act_id": "constitution_of_india",
        "expected_sections": ["21"],
    },
]


def validate_corpus(chroma_store: ChromaStore) -> Dict[str, Any]:
    """Validate all 14 legal Acts in the index."""
    print("=" * 80)
    print("1. NYAYASETU CORPUS VALIDATION")
    print("=" * 80)

    total_count = chroma_store.count()
    data = chroma_store.collection.get(include=["metadatas"])
    metadatas = data.get("metadatas", [])

    doc_counts: Dict[str, int] = {}
    for m in metadatas:
        doc_id = m.get("document_id", "unknown")
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

    print(f"Total Chunks in ChromaDB: {total_count}")
    print(f"Total Unique Acts Detected: {len(doc_counts)} / 14")
    print("-" * 80)
    print(f"{'Act Document ID':<38} | {'Chunk Count':<12}")
    print("-" * 80)
    for doc_id, count in sorted(doc_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{doc_id:<38} | {count:<12}")
    print("-" * 80)

    section_indexer = get_section_indexer()
    section_indexer.build_index()

    chunks_with_sections = sum(1 for c in section_indexer.all_chunks if c.section_numbers)
    sec_pct = (chunks_with_sections / total_count * 100) if total_count > 0 else 0

    print(f"Chunks with Resolved Section Numbers: {chunks_with_sections} / {total_count} ({sec_pct:.1f}%)")
    print(f"Unique Section Keys in Index: {len(section_indexer.chunks_by_doc_sec)}")
    print("=" * 80)

    return {
        "total_chunks": total_count,
        "unique_acts": len(doc_counts),
        "doc_counts": doc_counts,
        "chunks_with_sections": chunks_with_sections,
        "section_coverage_pct": sec_pct,
    }


def run_benchmark() -> Dict[str, Any]:
    """Run retrieval benchmark suite."""
    print("\n" + "=" * 80)
    print("2. LEGAL RETRIEVAL EVALUATION BENCHMARK")
    print("=" * 80)

    retriever = AdvancedRetriever()
    results = []

    hit_1 = 0
    hit_3 = 0
    hit_5 = 0
    reciprocal_ranks = []
    statute_accuracies = []
    statute_purities = []
    completeness_scores = []

    for test in BENCHMARK_QUERIES:
        qid = test["id"]
        qtext = test["query"]
        expected_act_id = test["expected_act_id"]
        expected_secs = test["expected_sections"]
        requires_both = test.get("requires_both", False)
        is_cross = test.get("is_cross_domain", False)

        start = time.time()
        ret_res = retriever.retrieve(qtext, initial_k=20, final_k=5)
        latency = time.time() - start

        top_chunks = ret_res.results
        chunk_doc_ids = [c.metadata.get("document_id") or c.chunk_id.split("_c")[0] for c in top_chunks]

        # Top-1 Statute Accuracy
        top1_statute_match = (chunk_doc_ids[0] == expected_act_id) if chunk_doc_ids else False
        statute_accuracies.append(1.0 if top1_statute_match else 0.0)

        # Statute Purity (percentage of top-5 belonging to expected act)
        if not is_cross:
            purity = sum(1 for d in chunk_doc_ids if d == expected_act_id) / len(chunk_doc_ids) if chunk_doc_ids else 0.0
            statute_purities.append(purity)

        # Section coverage for each retrieved chunk
        section_indexer = get_section_indexer()
        chunk_sections_covered = []
        for c in top_chunks:
            sec_set = set()
            if c.section_number:
                sec_set.add(c.section_number)
            idx_chunk = section_indexer.chunks_by_id.get(c.chunk_id)
            if idx_chunk:
                sec_set.update(idx_chunk.section_numbers)
            chunk_sections_covered.append(sec_set)

        # Section Hits
        found_expected_at = None
        for rank, sec_set in enumerate(chunk_sections_covered, start=1):
            if any(s in expected_secs for s in sec_set):
                if found_expected_at is None:
                    found_expected_at = rank
                break

        h1 = (found_expected_at == 1)
        h3 = (found_expected_at is not None and found_expected_at <= 3)
        h5 = (found_expected_at is not None and found_expected_at <= 5)

        if h1: hit_1 += 1
        if h3: hit_3 += 1
        if h5: hit_5 += 1

        rr = 1.0 / found_expected_at if found_expected_at else 0.0
        reciprocal_ranks.append(rr)

        # Multi-provision completeness check
        all_retrieved_secs = set().union(*chunk_sections_covered) if chunk_sections_covered else set()
        if requires_both:
            has_all = all(exp in all_retrieved_secs for exp in expected_secs)
            completeness_scores.append(1.0 if has_all else 0.0)
            comp_str = f"Completeness: {'PASS' if has_all else 'FAIL'}"
        else:
            has_all = True
            comp_str = ""

        status_symbol = "[OK]" if h5 and (not requires_both or has_all) else "[WARN]"

        print(f"\n{status_symbol} [{qid}] ({test['category']}) \"{qtext}\"")
        print(f"    Expected Act: {expected_act_id} | Expected Sections: {expected_secs}")
        print(f"    Retrieved Top-5:")
        for c in top_chunks:
            sec_display = f"Sec {c.section_number}" if c.section_number else "Sec -"
            title_display = f"({c.section_title})" if c.section_title else ""
            print(f"      Rank {c.rank}: {c.act_short_name} {sec_display} {title_display} | Score: {c.reranker_score:.4f} | Chunk: {c.chunk_id}")
        print(f"    Hit@1: {h1} | Hit@3: {h3} | Hit@5: {h5} | RR: {rr:.3f} | Latency: {latency:.2f}s {comp_str}")

        results.append({
            "id": qid,
            "query": qtext,
            "top1_statute": chunk_doc_ids[0] if chunk_doc_ids else "",
            "top_sections": [c.section_number for c in top_chunks],
            "hit_at_1": h1,
            "hit_at_3": h3,
            "hit_at_5": h5,
            "reciprocal_rank": rr,
        })

    num_queries = len(BENCHMARK_QUERIES)
    mrr = sum(reciprocal_ranks) / num_queries
    avg_statute_acc = sum(statute_accuracies) / len(statute_accuracies)
    avg_purity = sum(statute_purities) / len(statute_purities) if statute_purities else 1.0

    print("\n" + "=" * 80)
    print("3. BENCHMARK SUMMARY METRICS")
    print("=" * 80)
    print(f"Total Benchmark Queries : {num_queries}")
    print(f"Hit@1 Accuracy          : {hit_1} / {num_queries} ({hit_1 / num_queries * 100:.1f}%)")
    print(f"Hit@3 Accuracy          : {hit_3} / {num_queries} ({hit_3 / num_queries * 100:.1f}%)")
    print(f"Hit@5 Accuracy          : {hit_5} / {num_queries} ({hit_5 / num_queries * 100:.1f}%)")
    print(f"Mean Reciprocal Rank    : {mrr:.4f}")
    print(f"Top-1 Statute Accuracy  : {avg_statute_acc * 100:.1f}%")
    print(f"Top-K Statute Purity    : {avg_purity * 100:.1f}%")
    if completeness_scores:
        print(f"Multi-Part Completeness : {sum(completeness_scores) / len(completeness_scores) * 100:.1f}%")
    print("=" * 80)

    return {
        "hit_at_1": hit_1 / num_queries,
        "hit_at_3": hit_3 / num_queries,
        "hit_at_5": hit_5 / num_queries,
        "mrr": mrr,
        "top1_statute_accuracy": avg_statute_acc,
        "top_k_statute_purity": avg_purity,
    }


def main():
    store = ChromaStore()
    corpus_stats = validate_corpus(store)
    benchmark_metrics = run_benchmark()


if __name__ == "__main__":
    main()
