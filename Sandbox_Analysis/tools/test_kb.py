# tools/test_kb.py
import sys
import os

# 将项目根目录加入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kb_builder.indexer import Indexer

def test_retrieval():
    print("=== Testing Knowledge Base Retrieval ===")
    
    # 1. 加载刚才构建好的索引
    try:
        indexer = Indexer()
        vector_store = indexer.load_local()
        print("✅ Successfully loaded Vector DB.")
    except Exception as e:
        print(f"❌ Failed to load DB: {e}")
        return

    # 2. 定义几个测试问题 (涵盖 API, ATT&CK, 威胁情报)
    test_queries = [
        "What is the VirtualAlloc function used for?",    # 测试 MS-API
        "How do attackers use PowerShell for persistence?", # 测试 ATT&CK/CTI
        "DLL injection techniques"                        # 混合概念
    ]

    # 3. 执行检索
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 30)
        
        # 搜索最相关的 2 个片段
        results = vector_store.similarity_search(query, k=2)
        
        if not results:
            print("   (No results found)")
        
        for i, doc in enumerate(results):
            source = doc.metadata.get('source', 'Unknown')
            # 打印前 200 个字符预览
            preview = doc.page_content[:200].replace('\n', ' ')
            print(f"   Result {i+1} [Source: {source}]:\n   Content: {preview}...")
            print("")

if __name__ == "__main__":
    test_retrieval()