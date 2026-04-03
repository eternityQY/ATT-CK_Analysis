import argparse
import sys
import os
from pathlib import Path
import re
import csv

# Ensure src is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL, VECTOR_DB_DIR
from src.query_opt import CuckooParser, BehaviorChain, QueryRewriter
from src.rag_engine.retriever import KnowledgeRetriever
from src.rag_engine.generator import ReportGenerator
from src.utils.llm_client import LLMClient


# ===============================
# TTP提取
# ===============================
def extract_ttps(report_text):
    """
    从分析报告中提取 MITRE ATT&CK TTP
    例如:
    T1055
    T1055.012
    """
    pattern = r"T\d{4}(?:\.\d{3})?"
    ttps = re.findall(pattern, report_text)

    # 去重
    ttps = sorted(list(set(ttps)))

    return ttps


# ===============================
# 保存结果
# ===============================
def save_analysis_results(report_path, report_text):
    output_dir = Path("analysis_results")
    output_dir.mkdir(exist_ok=True)

    hash_name = report_path.stem

    # 保存完整报告
    report_file = output_dir / f"{hash_name}.txt"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    # 提取TTP
    ttps = extract_ttps(report_text)

    # 保存TTP列表
    ttp_file = output_dir / f"{hash_name}_ttps.txt"

    with open(ttp_file, "w", encoding="utf-8") as f:
        for t in ttps:
            f.write(t + "\n")

    return hash_name, ttps


# ===============================
# 保存跳过样本记录
# ===============================
def save_skipped_sample(report_path, reason):
    """保存被跳过的样本信息"""
    output_dir = Path("analysis_results")
    output_dir.mkdir(exist_ok=True)
    
    skipped_file = output_dir / "skipped_samples.csv"
    file_exists = skipped_file.exists()
    
    hash_name = report_path.stem
    
    with open(skipped_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        if not file_exists:
            writer.writerow(["hash", "reason", "filename"])
        
        writer.writerow([hash_name, reason, report_path.name])


# ===============================
# 读取已分析样本
# ===============================
def load_existing_results():
    csv_file = Path("analysis_results") / "all_results.csv"

    if not csv_file.exists():
        return set()

    analyzed_hashes = set()

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            analyzed_hashes.add(row["hash"])

    return analyzed_hashes


# ===============================
# 追加写入CSV
# ===============================
def append_to_csv(hash_name, ttps):
    output_dir = Path("analysis_results")
    csv_file = output_dir / "all_results.csv"

    file_exists = csv_file.exists()

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["hash", "predicted_ttps"])

        writer.writerow([
            hash_name,
            ";".join(ttps)
        ])


# ===============================
# 单样本分析函数
# ===============================
def analyze_single_report(report_path, user_query="", max_behavior_units=5000):
    print("="*60)
    print(f"Analyzing: {report_path.name}")
    print("="*60)

    # --- Step 1: Parse Cuckoo Report ---
    print("\n📊 [1/5] Parsing Cuckoo Report...")
    cuckoo_parser = CuckooParser(report_path)
    cuckoo_parser.load_report()
    cuckoo_parser.extract_all_behavior_units()
    chain_data = cuckoo_parser.get_behavior_chain_data()
    
    behavior_unit_count = len(chain_data)
    print(f"   ✓ Extracted {behavior_unit_count} behavior units.")
    
    # --- 检查行为单元数量，超过阈值则跳过 ---
    if behavior_unit_count > max_behavior_units:
        print(f"\n⚠️  Skipping {report_path.name}: Too many behavior units ({behavior_unit_count} > {max_behavior_units})")
        print(f"   This report is too large and may cause performance issues.")
        
        # 保存跳过记录
        save_skipped_sample(report_path, f"Too many behavior units: {behavior_unit_count}")
        
        return

    # --- Step 2: Build Behavior Chain ---
    print("\n🔗 [2/5] Building Behavior Chain...")
    chain_builder = BehaviorChain(chain_data)
    behavior_chain = chain_builder.build_greedy_chain()

    print(f"   ✓ Chain nodes: {len(behavior_chain)}")

    # --- Step 3: Query Rewriting (LLM) ---
    print("\n🤖 [3/5] Rewriting Chain to Natural Language...")
    
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY not found in config.py or environment variables.")
    
    llm_client = LLMClient(LLM_API_KEY, LLM_API_BASE, LLM_MODEL)
    
    # Use Rewriter
    rewriter = QueryRewriter(LLM_API_KEY, LLM_API_BASE, LLM_MODEL)
    rewrite_result = rewriter.rewrite_chain(behavior_chain)
    
    # Extract Natural Language Description
    behavior_description = rewriter.extract_chain_text(rewrite_result)
    
    print(f"   ✓ Behavior Description generated.")

    # --- Step 4: Knowledge Retrieval (RAG) ---
    print("\n📚 [4/5] Retrieving Knowledge Context...")
    retriever = KnowledgeRetriever(str(VECTOR_DB_DIR))
    
    # Use user query OR behavior description (first 300 chars) as search query
    search_query = user_query if user_query else behavior_description[:300]
    print(f"   Using query: {search_query[:50]}...")
    
    retrieved_docs = retriever.retrieve(search_query, top_k=5)
    print(f"   ✓ Retrieved {len(retrieved_docs)} relevant documents.")

    # --- Step 5: Generate Report ---
    print("\n📝 [5/5] Generating Final Analysis Report...")
    generator = ReportGenerator(llm_client)
    
    # Pass English query intent (与 main.py 保持一致)
    final_report = generator.generate_report(
        query=user_query if user_query else "Comprehensive analysis of malware behavior and tactical intent",
        behavior_description=behavior_description,
        retrieved_docs=retrieved_docs
    )
    
    print("   ✓ Report generated.")

    # 保存结果
    hash_name, ttps = save_analysis_results(report_path, final_report)

    append_to_csv(hash_name, ttps)

    print(f"\n💾 Saved results for {hash_name}")
    print(f"   Extracted {len(ttps)} TTPs: {', '.join(ttps) if ttps else 'None'}")

    return


# ===============================
# 主函数
# ===============================
def main():
    parser = argparse.ArgumentParser(
        description="MalGTA Malware Tactical Analysis System (Batch Mode)"
    )

    parser.add_argument(
        "report_path",
        type=str,
        help="Single Cuckoo report OR directory containing reports"
    )

    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Optional analysis question"
    )
    
    parser.add_argument(
        "--max-units",
        type=int,
        default=5000,
        help="Maximum number of behavior units to process (default: 5000)"
    )

    args = parser.parse_args()

    path = Path(args.report_path)

    if not path.exists():
        print("❌ Path not found")
        return

    try:
        # ===============================
        # 单文件模式
        # ===============================
        if path.is_file():
            analyze_single_report(path, args.query, args.max_units)

        # ===============================
        # 批量模式
        # ===============================
        elif path.is_dir():
            reports = list(path.glob("*.json"))
            analyzed_hashes = load_existing_results()
            
            # 读取已跳过的样本
            skipped_file = Path("analysis_results") / "skipped_samples.csv"
            skipped_hashes = set()
            if skipped_file.exists():
                with open(skipped_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        skipped_hashes.add(row["hash"])
            
            print(f"\n📁 Detected {len(reports)} reports")
            print(f"   Already analyzed: {len(analyzed_hashes)}")
            print(f"   Previously skipped: {len(skipped_hashes)}")
            print(f"   Max behavior units: {args.max_units}")
            print()

            processed = 0
            skipped_count = 0
            
            for report in reports:
                hash_name = report.stem
                
                if hash_name in analyzed_hashes:
                    print(f"⏭️  Skip (already analyzed): {hash_name}")
                    continue
                    
                if hash_name in skipped_hashes:
                    print(f"⏭️  Skip (previously skipped): {hash_name}")
                    continue

                try:
                    analyze_single_report(report, args.query, args.max_units)
                    processed += 1
                    
                except Exception as e:
                    print(f"❌ Failed: {report.name}")
                    print(f"   Error: {e}")
                    skipped_count += 1
            
            print(f"\n✅ Analysis finished!")
            print(f"   Successfully analyzed: {processed}")
            print(f"   Failed/Skipped: {skipped_count}")
            print(f"   Total processed this run: {processed + skipped_count}")

    except Exception as e:
        print("\n❌ Critical Error:", str(e))

        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
