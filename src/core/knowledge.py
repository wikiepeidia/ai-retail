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
        print("📚 [RAG] Initializing Knowledge Base 2.5 (Verbose Mode)...")
        
        self.doc_dir = doc_dir
        
        # Models
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu')
        
        # DB Setup
        os.makedirs(persist_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name="project_a_docs")
        
        # Run Ingestion
        self.ingest_folder()

    def ingest_folder(self):
        """Scans folder and ingests files with detailed logging."""
        files = glob.glob(os.path.join(self.doc_dir, "*.*"))
        
        print(f"📂 [RAG] Scanning {self.doc_dir}... Found {len(files)} files.")
        
        for file_path in files:
            filename = os.path.basename(file_path)
            
            # 1. Check DB for duplicates
            existing = self.collection.get(where={"source": filename})
            if existing['ids']:
                print(f"   ℹ️  [Cache] Already in DB: {filename}")
                continue 

            # 2. Extract Text based on Extension (Case Insensitive)
            text = ""
            ext = os.path.splitext(filename)[1].lower()
            
            try:
                if ext == ".pdf":
                    reader = PdfReader(file_path)
                    text = "\n".join([page.extract_text() or "" for page in reader.pages])
                    
                elif ext == ".docx":
                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    
                elif ext in [".txt", ".md", ".json", ".py"]:
                    with open(file_path, "r", encoding="utf-8", errors='ignore') as f:
                        text = f.read()
                
                else:
                    print(f"   ⚠️  Unsupported Format: {filename} ({ext})")
                    continue
                
                # 3. Save if text found
                if text.strip():
                    self.add_document(text, source=filename)
                    print(f"   ✅ Learned: {filename}")
                else:
                    print(f"   ⚠️  Empty File (No selectable text): {filename}")
                    
            except Exception as e:
                print(f"   ❌ Error reading {filename}: {e}")

    def add_document(self, text: str, source: str = "manual_entry"):
        chunk_size = 800 # Increased chunk size for better context
        overlap = 100
        
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
        query_vec = self.embedder.encode([query]).tolist()
        results = self.collection.query(query_embeddings=query_vec, n_results=10)
        
        candidates = results['documents'][0]
        if not candidates: return None
        
        # Re-Ranking
        pairs = [[query, doc] for doc in candidates]
        scores = self.reranker.predict(pairs)
        scored_docs = sorted(list(zip(candidates, scores)), key=lambda x: x[1], reverse=True)
        
        # Return top K with Score > 0
        final_docs = [doc for doc, score in scored_docs if score > 0][:top_k]
        return "\n---\n".join(final_docs) if final_docs else None