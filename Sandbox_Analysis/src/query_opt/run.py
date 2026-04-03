import json
from parser import CuckooParser
from chain import BehaviorChain
from rewriter import QueryRewriter


def main():
    """
    单行为链模块测试脚本
    python run.py
    """

    # 1. 解析报告
    print("正在构建行为链...")
    report_path = "../../../GroundTruth/standard/LZ_raw_reports/dec173444481ca304f478b9f656e2d34e822b250e594f1e07c889824e183826b.json"   # 要查询的Cuckoo报告路径
    parser = CuckooParser(report_path)
    parser.extract_all_behavior_units()   # 提取行为单元
    chain_data = parser.get_behavior_chain_data()   # 结构化
    
    # 构建行为链
    builder = BehaviorChain(chain_data)

    # 生成可读行为链（简洁版本）
    paper_chain = builder.generate_paper_output()
    with open("chain.txt", 'w', encoding='utf-8') as f:
        f.write(paper_chain)   

    behavior_chain = builder.build_greedy_chain()   # 构建json格式行为链，含更多信息
    print("\n行为链构建成功")
    
    # 2. 初始化重写器
    rewriter = QueryRewriter(
        llm_api_key = "sk-b0381fddbe8a409ab1d3d13c89dc85c4",
        llm_base_url = "https://api.deepseek.com",
        model = "deepseek-chat"  
    )
    
    # 3. 重写行为链
    print("\n正在重写行为链...")
    result = rewriter.rewrite_chain(behavior_chain)
    
    if "error" in result:
        print(f"错误: {result['error']}")
        return
    print("\n行为链重写完成...")

    # 5. 保存详细合并结果(json)
    with open("rewritten_chain.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # 标准格式输出
    chain_txt = rewriter.extract_chain_text(result)
    output_file = "rewritten_chain.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(chain_txt)
    print("重写结果见当前目录下 rewritten_chain.txt & rewritten_chain.json")

if __name__ == "__main__":
    main()