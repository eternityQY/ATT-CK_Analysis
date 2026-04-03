# tools/build_kb.py
import sys
import os

# 1. 动态添加项目根目录到 Python 路径，确保能导入 src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.kb_builder.data_loader import DataLoader
from src.kb_builder.cleaner import DataCleaner
from src.kb_builder.indexer import Indexer

def main():
    print("="*50)
    print("   MalGTA Knowledge Base Builder v1.0")
    print("="*50)
    
    # 1. 加载 (支持 PDF, HTML, JSON)
    loader = DataLoader()
    raw_docs = loader.load_all()
    
    if not raw_docs:
        print("[Error] No documents found! Run tools/download_data.py first.")
        return

    # 2. 清洗 (NLP 处理)
    cleaner = DataCleaner()
    chunks = cleaner.split_documents(raw_docs)

    # 3. 索引 (Vector DB)
    indexer = Indexer()
    indexer.build_and_save(chunks)
    
    print("\n[Done] Knowledge Base is ready for retrieval.")

if __name__ == "__main__":
    main()