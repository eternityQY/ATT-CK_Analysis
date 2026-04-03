from rewriter import rewrite

def main():
    report_path = "../../data/raw_reports/report5.json"   # Cuckoo报告路径
    chain = rewrite(report_path)    # 生成自然语言行为链
    

    # 保存输出供调试
    output_file = "rewritten_chain.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(chain)

if __name__ == "__main__":
    main()