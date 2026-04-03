# Sandbox_Analysis
Cuckoo Sandbox Analysis

## 项目结构

```
Project/
│
├── data/                  # 存放数据
│   ├── raw_reports/       # Cuckoo 原始 JSON 报告（用户输入）
│   ├── knowledge_source/  # ATT&CK, MS-API, CTI 的原始文档 (PDF/HTML)（开发者维护）
│   └── vector_db/         # FAISS 向量数据库（预构建，随系统分发）
│
├── src/                   # 源代码目录
│   ├── __init__.py
│   ├── config.py          # 配置文件 (API Key, 路径设置)
│   ├── kb_builder/        # 【模块1】知识库构建（开发者使用）
│   │   ├── __init__.py
│   │   ├── data_loader.py # 读取 PDF/HTML
│   │   ├── cleaner.py     # 数据清洗 (NLP处理)
│   │   └── indexer.py     # 向量化存储 (FAISS)
│   │
│   ├── query_opt/         # 【模块2】查询优化 (处理 Cuckoo 报告)
│   │   ├── __init__.py
│   │   ├── parser.py      # 提取 JSON 关键信息
│   │   ├── chain.py       # 构建行为链
│   │   └── rewriter.py    # LLM 重写查询
│   │
│   ├── rag_engine/        # 【模块3】检索增强与生成
│   │   ├── __init__.py
│   │   ├── retriever.py   # 检索 Top-K
│   │   └── generator.py   # 最终生成分析报告
│   │
│   └── utils/             # 通用工具
│       ├── __init__.py
│       └── llm_client.py  # 封装 LLM 调用接口
│
├── tools/                 # 开发者工具（仅供开发人员使用）
│   ├── __init__.py
│   ├── build_kb.py        # 知识库构建脚本
│   └── README.md          # 开发者工具使用说明
│
├── tests/                 # 测试代码
│   └── __init__.py
│
├── main.py                # 用户入口（恶意软件分析工具）
├── requirements.txt       # 依赖库列表
├── README.md              # 项目说明书
└── .gitignore             # Git 忽略配置
```