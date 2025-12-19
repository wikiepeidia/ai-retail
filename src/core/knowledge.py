import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
import os
import glob
import logging
import uuid
from pypdf import PdfReader
import docx

class KnowledgeBase:
    def __init__(self, persist_dir="./data/vector_db", doc_dir="./src/data/docs"):
        print("📚 [RAG] Initializing Knowledge Base 2.0 (Re-Ranker Enabled)...")
        
        self.doc_dir = doc_dir
        
        # 1. Bi-Encoder (The Librarian) - Fast Retrieval
        # Runs on CPU to save VRAM for Qwen
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        
        # 2. Cross-Encoder (The Professor) - Deep Re-ranking
        # This is a small model, safe to run on CPU or GPU
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu')
        
        # 3. Vector DB
        os.makedirs(persist_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name="project_a_docs")
        
        # Auto-ingest on startup
        self.ingest_folder()

    def ingest_folder(self):
        """Scans src/data/docs and ingests new files."""
        files = glob.glob(os.path.join(self.doc_dir, "*.*"))
        
        print(f"📂 [RAG] Scanning {self.doc_dir}... Found {len(files)} files.")
        
        for file_path in files:
            filename = os.path.basename(file_path)
            
            # Simple deduplication check by source name
            existing = self.collection.get(where={"source": filename})
            if existing['ids']:
                continue # Skip if already ingested

            text = ""
            try:
                if filename.endswith(".pdf"):
                    reader = PdfReader(file_path)
                    text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                elif filename.endswith(".docx"):
                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                elif filename.endswith(".txt") or filename.endswith(".md"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                
                if text:
                    self.add_document(text, source=filename)
                    print(f"   ✅ Learned: {filename}")
            except Exception as e:
                print(f"   ❌ Error reading {filename}: {e}")

    def add_document(self, text: str, source: str = "manual_entry"):
        # Chunking strategy: Overlapping windows for better context
        chunk_size = 500
        overlap = 50
        
        raw_chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            raw_chunks.append(text[start:end])
            start += (chunk_size - overlap)
        
        if not raw_chunks: return

        ids = [f"{source}_{i}" for i in range(len(raw_chunks))]
        embeddings = self.embedder.encode(raw_chunks).tolist()
        metadatas = [{"source": source} for _ in raw_chunks]
        
        self.collection.add(
            documents=raw_chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, top_k=3):
        """
        2-Stage Retrieval:
        1. Vector Search: Get top 10 candidates.
        2. Re-Ranking: Score candidates against query.
        3. Return top_k best matches.
        """
        # Stage 1: Retrieval (Recall)
        query_vec = self.embedder.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_vec,
            n_results=10 # Fetch more than we need
        )
        
        candidates = results['documents'][0]
        if not candidates: return None
        
        # Stage 2: Re-Ranking (Precision)
        # Prepare pairs: [ [query, doc1], [query, doc2] ... ]
        pairs = [[query, doc] for doc in candidates]
        scores = self.reranker.predict(pairs)
        
        # Combine docs with scores
        scored_docs = list(zip(candidates, scores))
        
        # Sort by score descending (Highest relevance first)
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Filter: Keep only high confidence (Score > 0)
        # And take top K
        final_docs = [doc for doc, score in scored_docs if score > 0][:top_k]
        
        if not final_docs: return None
        
        return "\n---\n".join(final_docs)