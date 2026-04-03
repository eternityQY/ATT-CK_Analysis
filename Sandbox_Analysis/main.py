import argparse
import sys
import os
from pathlib import Path

# Ensure src is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL, VECTOR_DB_DIR
from src.query_opt import CuckooParser, BehaviorChain, QueryRewriter
from src.rag_engine.retriever import KnowledgeRetriever
from src.rag_engine.generator import ReportGenerator
from src.utils.llm_client import LLMClient

def main():
    # 1. Argument Parsing
    parser = argparse.ArgumentParser(description="MalGTA: LLM-based Guided Malware Tactical Analysis System")
    parser.add_argument("report_path", type=str, help="Path to Cuckoo Sandbox JSON report")
    parser.add_argument("--query", type=str, default="", help="Optional: Specific analysis question (e.g., 'How does it achieve persistence?')")
    args = parser.parse_args()

    report_path = Path(args.report_path)
    if not report_path.exists():
        print(f"❌ Error: Report file not found at {report_path}")
        return

    print("="*60)
    print("   MalGTA: Malware General Threat Analysis System")
    print("="*60)

    try:
        # --- Step 1: Parse Cuckoo Report ---
        print("\n📊 [Step 1/5] Parsing Cuckoo Report...")
        cuckoo_parser = CuckooParser(report_path)
        cuckoo_parser.load_report()
        cuckoo_parser.extract_all_behavior_units()
        chain_data = cuckoo_parser.get_behavior_chain_data()

        print(f"   ✓ Extracted {len(chain_data)} raw behavior units.")

        if not chain_data:
            print("   ⚠️ No behavior data found in report. Analysis might be limited.")

        # --- Step 2: Build Behavior Chain ---
        print("\n🔗 [Step 2/5] Building Behavior Chain...")
        chain_builder = BehaviorChain(chain_data)
        behavior_chain = chain_builder.build_greedy_chain()
        a = chain_builder.generate_paper_output()
        output_file = "Behavior_chain.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(a)

        print(f"   ✓ Constructed behavior chain with {len(behavior_chain)} nodes.")

        # --- Step 3: Query Rewriting (LLM) ---
        print("\n🤖 [Step 3/5] Rewriting Chain to Natural Language...")
        
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY not found in config.py or environment variables.")
            
        llm_client = LLMClient(LLM_API_KEY, LLM_API_BASE, LLM_MODEL)
        
        # Use Rewriter
        rewriter = QueryRewriter(LLM_API_KEY, LLM_API_BASE, LLM_MODEL)
        rewrite_result = rewriter.rewrite_chain(behavior_chain)
        
        # Extract Natural Language Description
        behavior_description = rewriter.extract_chain_text(rewrite_result)
        file_name = "Rewriter_chain.txt"
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(behavior_description)
        print(f"   ✓ Behavior Description (Preview): {behavior_description[:100]}...")

        # --- Step 4: Knowledge Retrieval (RAG) ---
        print("\n📚 [Step 4/5] Retrieving Knowledge Context...")
        retriever = KnowledgeRetriever(str(VECTOR_DB_DIR))
        
        # Use user query OR behavior description (first 300 chars) as search query
        # Adding "search_query: " prefix is good practice for Nomic model but optional here
        search_query = args.query if args.query else behavior_description[:300]
        print(f"   Using query: {search_query[:50]}...")
        
        retrieved_docs = retriever.retrieve(search_query, top_k=5)
        print(f"   ✓ Retrieved {len(retrieved_docs)} relevant documents.")

        # --- Step 5: Generate Report ---
        print("\n📝 [Step 5/5] Generating Final Analysis Report...")
        generator = ReportGenerator(llm_client)
        
        # Pass English query intent
        final_report = generator.generate_report(
            query=args.query if args.query else "Comprehensive analysis of malware behavior and tactical intent",
            behavior_description=behavior_description,
            retrieved_docs=retrieved_docs
        )

        file_name = "Report.txt"
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(final_report)
        print("\n" + "="*60)
        print("FINAL ANALYSIS REPORT")
        print("="*60 + "\n")
        print(final_report)
        print("\n" + "="*60)
        print("✅ Analysis Complete.")

    except Exception as e:
        print(f"\n❌ Critical Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()