import argparse
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL
from src.query_opt import CuckooParser, BehaviorChain, QueryRewriter

from src.ai_engine.ttp_analyzer import TTPAnalyzer
from src.ai_engine.report_generator import AIReportGenerator

from src.utils.llm_client import LLMClient


def main():

    parser = argparse.ArgumentParser(
        description="AI-based Malware Tactical Analysis System"
    )

    parser.add_argument(
        "report_path",
        type=str,
        help="Path to Cuckoo JSON report"
    )

    args = parser.parse_args()

    report_path = Path(args.report_path)

    if not report_path.exists():
        print("Report file not found")
        return

    print("=" * 60)
    print("Malware Tactical Analysis System")
    print("=" * 60)

    # ---------------------------
    # Step 1 Parse Report
    # ---------------------------

    print("\n[1/5] Parsing Cuckoo Report")

    parser = CuckooParser(report_path)

    parser.load_report()

    parser.extract_all_behavior_units()

    chain_data = parser.get_behavior_chain_data()

    print("Behavior units:", len(chain_data))

    # ---------------------------
    # Step 2 Behavior Chain
    # ---------------------------

    print("\n[2/5] Building Behavior Chain")

    chain_builder = BehaviorChain(chain_data)

    behavior_chain = chain_builder.build_greedy_chain()

    print("Chain nodes:", len(behavior_chain))

    # ---------------------------
    # Step 3 Rewrite Chain
    # ---------------------------

    print("\n[3/5] Converting to Natural Language")

    llm_client = LLMClient(
        LLM_API_KEY,
        LLM_API_BASE,
        LLM_MODEL
    )

    rewriter = QueryRewriter(
        LLM_API_KEY,
        LLM_API_BASE,
        LLM_MODEL
    )

    rewrite_result = rewriter.rewrite_chain(behavior_chain)

    behavior_text = rewriter.extract_chain_text(
        rewrite_result
    )

    print("Behavior description generated")

    # ---------------------------
    # Step 4 TTP Analysis
    # ---------------------------

    print("\n[4/5] Identifying ATT&CK Techniques")

    analyzer = TTPAnalyzer(llm_client)

    ttp_result = analyzer.analyze(
        behavior_text
    )

    print("TTP identification completed")

    # ---------------------------
    # Step 5 Report Generation
    # ---------------------------

    print("\n[5/5] Generating Final Report")

    generator = AIReportGenerator(llm_client)

    final_report = generator.generate(
        behavior_text,
        ttp_result
    )

    print("\n" + "=" * 60)
    print("FINAL MALWARE ANALYSIS REPORT")
    print("=" * 60)

    print(final_report)

    print("\nAnalysis Complete")


if __name__ == "__main__":
    main()
