"""
Live endpoint verification script for NyayaSetu LLM Resilience and Fallback Delivery.
"""

import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"

def get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post(path, body):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("=== 1. Checking GET /api/v1/health ===")
health = get("/api/v1/health")
print(json.dumps(health, indent=2))

print("\n=== 2. Checking GET /api/v1/health/llm ===")
llm_health = get("/api/v1/health/llm")
print(json.dumps(llm_health, indent=2))

print("\n=== 3. Testing Case-Law Consent Query ===")
consent_query = (
    "A woman alleges that she was sexually assaulted by a person with whom she was previously in a "
    "consensual relationship. The accused claims that their prior relationship automatically establishes consent. "
    "Does a previous consensual relationship constitute consent for a subsequent sexual act under Indian law? "
    "Explain the relevant legal provisions and important judicial principles."
)
consent_resp = post("/api/v1/query", {"query": consent_query})
print(f"Status: {consent_resp.get('status')}")
print(f"Generation Status: {consent_resp.get('generation_status')}")
print(f"Retrieval Status: {consent_resp.get('retrieval_status')}")
print(f"Validation Status: {consent_resp.get('validation_status')}")
print(f"Sources Count: {len(consent_resp.get('sources', []))}")
print(f"Warnings: {consent_resp.get('warnings')}")
print("\n--- Answer Payload ---")
try:
    parsed_ans = json.loads(consent_resp['answer'])
    print("Legal Domain:", parsed_ans.get("legalDomain"))
    print("\nMain Answer:\n", parsed_ans.get("mainAnswer")[:400], "...\n")
    print("\nLegal Basis:\n", parsed_ans.get("legalBasis")[:400], "...\n")
except Exception:
    print(consent_resp['answer'][:600])

print("\n=== 4. Testing Murder Regression Query ===")
murder_query = "What constitutes murder under BNS and what is the punishment?"
murder_resp = post("/api/v1/query", {"query": murder_query})
print(f"Status: {murder_resp.get('status')}")
print(f"Generation Status: {murder_resp.get('generation_status')}")
print(f"Retrieval Status: {murder_resp.get('retrieval_status')}")
print(f"Validation Status: {murder_resp.get('validation_status')}")
print(f"Sources Count: {len(murder_resp.get('sources', []))}")
print(f"Warnings: {murder_resp.get('warnings')}")
print("\n--- Answer Payload ---")
try:
    parsed_ans = json.loads(murder_resp['answer'])
    print("Legal Domain:", parsed_ans.get("legalDomain"))
    print("\nMain Answer:\n", parsed_ans.get("mainAnswer")[:400], "...\n")
    print("\nLegal Basis:\n", parsed_ans.get("legalBasis")[:400], "...\n")
except Exception:
    print(murder_resp['answer'][:600])

print("\n=== VERIFICATION COMPLETE ===")
