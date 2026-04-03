# src/kb_builder/data_loader.py
import os
import json
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from src.config import KNOWLEDGE_SOURCE_DIR

class DataLoader:
    def __init__(self, source_dir=KNOWLEDGE_SOURCE_DIR):
        self.source_dir = source_dir

    def load_pdf(self, file_path):
        """解析 PDF 文件 (针对 CTI 报告)"""
        docs = []
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": os.path.basename(file_path), "type": "pdf"}
                ))
            doc.close()
        except Exception as e:
            print(f"[Error] Failed to load PDF {file_path}: {e}")
        return docs

    def load_html(self, file_path):
        """解析 HTML 文件 (针对 MS-API)"""
        docs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                
                # 简单清洗：去除 script 和 style 标签
                for script in soup(["script", "style"]):
                    script.extract()
                
                text = soup.get_text(separator="\n")
                if text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={"source": os.path.basename(file_path), "type": "html"}
                    ))
        except Exception as e:
            print(f"[Error] Failed to load HTML {file_path}: {e}")
        return docs

    def load_attack_json(self, file_path):
        """
        【新增】解析 ATT&CK JSON 文件
        将结构化的 TTPs 转换为文本描述
        """
        docs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 假设数据是 download_data.py 生成的列表格式
                if isinstance(data, list):
                    for item in data:
                        # 组合成语义文本，方便向量检索
                        name = item.get('name', 'Unknown')
                        desc = item.get('description', '')
                        tid = item.get('id', '')
                        
                        content = f"ATT&CK Technique: {name} (ID: {tid})\nDescription: {desc}"
                        
                        docs.append(Document(
                            page_content=content,
                            metadata={"source": name, "type": "attack_technique"}
                        ))
        except Exception as e:
            print(f"[Error] Failed to load JSON {file_path}: {e}")
        return docs

    def load_all(self):
        """遍历目录加载所有支持的文件 (PDF, HTML, JSON)"""
        documents = []
        if not os.path.exists(self.source_dir):
            print(f"[Warning] Source directory {self.source_dir} does not exist.")
            return []

        print(f"[Info] Scanning {self.source_dir} for knowledge files...")
        
        # os.walk 会自动进入子目录 (如 attack/, cti/, ms_api/)
        for root, dirs, files in os.walk(self.source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                ext = file.lower().split('.')[-1]
                
                if ext == "pdf":
                    documents.extend(self.load_pdf(file_path))
                elif ext == "html":
                    documents.extend(self.load_html(file_path))
                elif ext == "json":
                    # 仅处理 ATT&CK 的 json，防止处理其他无关 json
                    documents.extend(self.load_attack_json(file_path))
        
        print(f"[Info] Successfully loaded {len(documents)} documents.")
        return documents