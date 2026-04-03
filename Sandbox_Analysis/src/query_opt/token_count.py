#!/usr/bin/env python3
# count_tokens.py - 使用OpenAI tiktoken计算token数

import tiktoken
import sys

def count_tokens(filename, encoding_name="cl100k_base"):
    """计算文本文件的token数量"""
    try:
        # 读取文件
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # 获取编码器
        encoding = tiktoken.get_encoding(encoding_name)
        
        # 编码并计算token数
        tokens = encoding.encode(text)
        token_count = len(tokens)
        
        print(f"文件: {filename}")
        print(f"字符数: {len(text)}")
        print(f"Token数: {token_count}")
        print(f"编码器: {encoding_name}")
        
        return token_count
        
    except FileNotFoundError:
        print(f"错误: 文件 '{filename}' 未找到")
        return 0
    except Exception as e:
        print(f"错误: {e}")
        return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python count_tokens.py <文件名>")
        sys.exit(1)
    
    count_tokens(sys.argv[1])