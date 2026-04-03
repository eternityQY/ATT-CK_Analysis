# src/kb_builder/cleaner.py
import re
import spacy
# 修改为新的导入路径
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DataCleaner:
    def __init__(self):
        # 加载 spaCy 模型
        try:
            print("[Info] Loading Spacy model for NLP cleaning...")
            self.nlp = spacy.load("en_core_web_sm")
            self.nlp.max_length = 2000000 
        except OSError:
            raise RuntimeError("请先运行: python -m spacy download en_core_web_sm")

    def clean_text(self, text):
        """正则清洗：去噪、脱敏"""
        # 1. 替换多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 2. IP 脱敏
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        text = re.sub(ip_pattern, '[IP_ADDRESS]', text)
        
        # 3. CVE 标准化 (转大写)
        cve_pattern = r'(?i)cve-\d{4}-\d{4,7}'
        text = re.sub(cve_pattern, lambda m: m.group(0).upper(), text)

        return text

    def advanced_normalization(self, text):
        """NLP 规范化：利用 spaCy 分句并过滤无效短句"""
        if not text:
            return ""
            
        doc = self.nlp(text)
        cleaned_sentences = []
        
        for sent in doc.sents:
            # 过滤少于 5 个单词的句子 (通常是噪音)
            if len(sent.text.split()) < 5:
                continue
            cleaned_sentences.append(sent.text)
            
        return " ".join(cleaned_sentences)

    def split_documents(self, documents):
        """分块处理"""
        print("[Info] Cleaning and splitting documents...")
        cleaned_docs = []
        
        for doc in documents:
            step1 = self.clean_text(doc.page_content)
            # 只有当文本长度适中时才进行昂贵的 NLP 处理，否则直接用正则清洗结果
            if len(step1) > 20: 
                final_text = self.advanced_normalization(step1)
            else:
                final_text = step1
            
            if final_text.strip():
                doc.page_content = final_text
                cleaned_docs.append(doc)

        # 分块参数配置
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_documents(cleaned_docs)
        print(f"[Info] Generated {len(chunks)} knowledge chunks from {len(documents)} raw files.")
        return chunks