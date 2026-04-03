"""
配置文件 - API Key, 路径设置
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据路径
DATA_DIR = PROJECT_ROOT / "data"
RAW_REPORTS_DIR = DATA_DIR / "raw_reports"
KNOWLEDGE_SOURCE_DIR = DATA_DIR / "knowledge_source"
VECTOR_DB_DIR = DATA_DIR / "vector_db"
MODELS_DIR = DATA_DIR / "models"  # 新增：模型存放目录

# LLM API 配置
# 建议：虽然这里写了默认 Key，但在 Git 提交时最好把真实 Key 删掉，或者使用环境变量
#LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-b0381fddbe8a409ab1d3d13c89dc85c4")
#LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.deepseek.com")
#LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-15fe099ebe734d7aadfc655a5a338824")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

# 向量数据库配置
# === 自动切换离线/在线模型逻辑 ===
LOCAL_NOMIC_PATH = MODELS_DIR / "nomic-embed-text-v1.5"

# 检查本地是否有模型文件
if LOCAL_NOMIC_PATH.exists() and any(LOCAL_NOMIC_PATH.iterdir()):
    print(f"[Config] Detected local embedding model at: {LOCAL_NOMIC_PATH}")
    print("[Config] Running in OFFLINE mode.")
    EMBEDDING_MODEL_NAME = str(LOCAL_NOMIC_PATH)
else:
    print(f"[Config] Local model not found at {LOCAL_NOMIC_PATH}")
    print("[Config] Falling back to HuggingFace Hub (Internet Connection Required).")
    EMBEDDING_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"

VECTOR_DB_NAME = "malware_knowledge_base"
TOP_K = 5  # 检索返回的文档数量

# 知识库配置
CHUNK_SIZE = 512  # 文本块大小
CHUNK_OVERLAP = 50  # 文本块重叠大小
