import os
import sys
sys.path.insert(0, os.getcwd())
from vectorstore.chroma_store import ChromaStore

c = ChromaStore()
r = c.collection.get(where={'document_id': 'bsa_2023'}, include=['documents', 'metadatas'])
print('Total BSA chunks:', len(r['ids']))
for i, (text, meta) in enumerate(zip(r['documents'], r['metadatas'])):
    c_idx = meta.get('chunk_index')
    if c_idx is not None and 87 <= c_idx <= 92:
        print(f"=== Chunk Index {c_idx} (ID: {r['ids'][i]}) ===")
        print(f"Text:\n{text}\n")
