# tools/download_model_local.py
import os
# 需要先 pip install huggingface_hub
from huggingface_hub import snapshot_download

# 定义模型 ID 和本地保存路径
REPO_ID = "nomic-ai/nomic-embed-text-v1.5"
LOCAL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "models", "nomic-embed-text-v1.5")

print(f"正在将模型 {REPO_ID} 下载到 {LOCAL_DIR} ...")
print("这可能需要几分钟 (约 0.5 GB)...")

try:
    snapshot_download(
        repo_id=REPO_ID,
        local_dir=LOCAL_DIR,
        local_dir_use_symlinks=False, # 关键：确保下载的是真实文件，不是链接
        resume_download=True
    )
    print("✅ 模型下载完成！现在项目是离线可用的了。")
except Exception as e:
    print(f"❌ 下载失败: {e}")
    print("请检查网络连接（是否开启了 HF_ENDPOINT 镜像加速？）")