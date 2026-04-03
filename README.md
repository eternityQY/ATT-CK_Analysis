# ATT-CK_Analysis
本项目设计实现了一个基于LLM的恶意软件技战术生成工具，执行逻辑如下：  
恶意软件 - Cuckoo沙箱运行 - json行为报告 - 预处理提取行为单元 - 按照时间戳、相关性还原行为链 - LLM精练行为链 - RAG匹配 - LLM生成分析报告  
GroundTruth/         # 恶意软件数据集（json行为报告）  
Sandbox_Analysis/    # ttp分析工具源代码
