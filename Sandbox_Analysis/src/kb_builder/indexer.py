# src/kb_builder/indexer.py
import os
from tqdm import tqdm  # 导入进度条
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from src.config import VECTOR_DB_DIR, EMBEDDING_MODEL_NAME

class Indexer:
    def __init__(self):
        print(f"[Info] Loading embedding model: {EMBEDDING_MODEL_NAME}...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={
                'device': 'cpu',
                'trust_remote_code': True
            }
        )
        self.vector_store = None

    def build_and_save(self, chunks):
        """构建索引并保存（带进度条版）"""
        if not chunks:
            print("[Warning] No chunks to index.")
            return

        total_chunks = len(chunks)
        print(f"[Info] Vectorizing {total_chunks} chunks using Nomic (Batch processing)...")

        # === 修改开始：分批处理 ===
        batch_size = 32  # 每次处理32个，防止内存溢出且能看进度
        
        # 1. 先初始化第一个 batch 以创建 vector_store
        first_batch = chunks[:batch_size]
        self.vector_store = FAISS.from_documents(first_batch, self.embeddings)
        
        # 2. 剩下的 batch 逐个添加
        # 使用 tqdm 显示进度条
        if total_chunks > batch_size:
            for i in tqdm(range(batch_size, total_chunks, batch_size), desc="Embedding"):
                batch = chunks[i : i + batch_size]
                self.vector_store.add_documents(batch)
        # === 修改结束 ===

        if not os.path.exists(VECTOR_DB_DIR):
            os.makedirs(VECTOR_DB_DIR)
            
        self.vector_store.save_local(VECTOR_DB_DIR)
        print(f"\n[Success] Knowledge Base saved to: {VECTOR_DB_DIR}")
        print(f"          Files generated: index.faiss, index.pkl")

    def load_local(self):
        """加载已存在的索引"""
        if not os.path.exists(VECTOR_DB_DIR):
            raise FileNotFoundError(f"Vector DB not found at {VECTOR_DB_DIR}. Please run build_kb.py first.")
            
        print(f"[Info] Loading Knowledge Base from {VECTOR_DB_DIR}...")
        self.vector_store = FAISS.load_local(
            VECTOR_DB_DIR, 
            self.embeddings,
            allow_dangerous_deserialization=True 
        )
        return self.vector_store