"""
查询重写器 - 使用LLM精炼行为链
将相关行为合并为自然语言描述，保持行为链结构
"""

import os
import sys
import math
import json
import asyncio
from .parser import CuckooParser
from .chain import BehaviorChain
from openai import OpenAI
from typing import List, Dict, Any  

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL


class QueryRewriter:
    """行为链重写器 - 合并相关行为，生成自然语言描述"""
    
    def __init__(self, llm_api_key: str, llm_base_url: str = None, model: str = "gpt-4"):
        """
        初始化重写器
        
        Args:
            llm_api_key: LLM API密钥
            llm_base_url: API基础URL（可选，用于自定义部署）
            model: 模型名称
        """
        self.client = OpenAI(
            api_key = llm_api_key,
            base_url = llm_base_url
        )
        self.model = model
        
    def rewrite_chain(self, behavior_chain: List[Dict], max_retries: int = 3) -> Dict[str, Any]:
        """
        重写行为链 - 合并相关行为为自然语言描述
        
        Args:
            behavior_chain: 从chain.py获取的行为链
            max_retries: 最大重试次数
            
        Returns:
            重写后的行为链
        """
        if not behavior_chain:
            return {"error": "行为链为空"}

        # 估算token数量（每行为约40 token）
        estimated_tokens = len(behavior_chain) * 40
        max_tokens_per_batch = 80000  # 预留安全阈值
        
        # 如果估算token数超限，分批处理
        if estimated_tokens > max_tokens_per_batch:
            print(f"The behavior chain is too long ({len(behavior_chain)} behaviors, about {estimated_tokens} tokens)")
            print(f"Enable batch processing mode...")
            return self._rewrite_chain_batched(behavior_chain, max_retries)

        return self._rewrite_chain_single(behavior_chain, max_retries)


    def _rewrite_chain_single(self, behavior_chain: List[Dict], max_retries: int = 3) -> Dict[str, Any]:   
        # 构建提示词
        prompt = self._build_rewrite_prompt(behavior_chain)
        
        # 调用LLM
        retry_count = 0
        while retry_count < max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个恶意软件行为分析专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                # 解析结果
                result = json.loads(response.choices[0].message.content)
                return self._format_result(result, behavior_chain)
                
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    # 所有重试都失败，返回原始链
                    return self._fallback_result(behavior_chain)
    

    def _rewrite_chain_batched(self, behavior_chain: List[Dict], max_retries: int = 3) -> Dict[str, Any]:
        """分批处理超长行为链"""
        batch_size = 200  # 每批200条行为
        total_behaviors = len(behavior_chain)
        num_batches = math.ceil(total_behaviors / batch_size)
        
        print(f"   Total number of batches: {num_batches}, about {batch_size} behaviors per batch")
        
        all_rewritten_items = []
        all_summaries = []
        
        # 分批处理
        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_behaviors)
            batch = behavior_chain[start_idx:end_idx]
            
            print(f"   batch {batch_idx + 1}/{num_batches} ({len(batch)} behaviors)...")
            
            # 处理单批
            batch_result = self._rewrite_chain_single(batch, max_retries)
        
            if "error" not in batch_result:
                # 成功：添加重写后的行为，并调整sequence编号
                for item in batch_result.get("rewritten_chain", []):
                    # 调整原始索引偏移
                    if "merged_from" in item:
                        original_indices = item["merged_from"]
                        adjusted_indices = [idx + start_idx for idx in original_indices]
                        item["merged_from"] = adjusted_indices
                    
                    # 设置全局sequence
                    item["sequence"] = len(all_rewritten_items) + 1
                    all_rewritten_items.append(item)
                
                # 收集该批次的摘要
                if "summary" in batch_result:
                    all_summaries.append(f"batch{batch_idx + 1}: {batch_result['summary']}")
            else:
                # 失败：使用原始行为
                print(f"     批次 {batch_idx + 1} 处理失败，使用原始行为")
                for j, item in enumerate(batch):
                    all_rewritten_items.append({
                        "sequence": len(all_rewritten_items) + 1,
                        "description": item.get("behavior", ""),
                        "original_behaviors": [item.get("behavior", "")],
                        "merged_from": [start_idx + j + 1],  # 1-based索引
                        "merged_count": 1,
                        "category": item.get("category", "unknown"),
                        "confidence": 0.5,
                        "time_info": {"start_time": item.get("timestamp")}
                    })
        
        # 生成整体摘要
        overall_summary = self._generate_batch_summary(all_summaries, behavior_chain[:10])
        
        return {
            "original_chain_length": total_behaviors,
            "rewritten_chain_length": len(all_rewritten_items),
            "compression_ratio": total_behaviors / len(all_rewritten_items) if all_rewritten_items else 0,
            "rewritten_chain": all_rewritten_items,
            "summary": overall_summary,
            "original_chain_preview": [item.get("behavior", "") for item in behavior_chain[:5]],
            "note": f"batch_processed_{num_batches}_batches"
        }


    def _generate_batch_summary(self, batch_summaries: List[str], preview_behaviors: List[Dict]) -> str:
        """从各批次摘要生成整体摘要"""
        if not batch_summaries:
            return "分批处理完成，无法生成整体摘要"
        
        # 如果批次太多，只取前5个
        if len(batch_summaries) > 5:
            summaries_text = "\n".join(batch_summaries[:3]) + f"\n... 等{len(batch_summaries)}个批次"
        else:
            summaries_text = "\n".join(batch_summaries)
        
        # 简单拼接各批次摘要
        return f"行为链分批处理完成。各批次摘要:\n{summaries_text}"

    def _estimate_tokens(self, behavior_chain: List[Dict]) -> int:
        """估算行为链的token数量"""
        # 简单估算：每条行为平均40 token
        return len(behavior_chain) * 40

    def _build_rewrite_prompt(self, behavior_chain: List[Dict]) -> str:
        """构建重写提示词"""
        chain_text = ""
        for i, item in enumerate(behavior_chain):
            behavior = item.get("behavior", "")
            timestamp = item.get("timestamp")
            time_str = f"[{timestamp:.2f}s]" if timestamp is not None else ""
            chain_text += f"{i+1}. {time_str} {behavior}\n"
        
        prompt = f"""
You are a cybersecurity expert. Review the following raw malware behavior chain extracted from a sandbox.
Please summarize these behaviors into a concise, chronological, and technical narrative.

### Raw Behavior Chain:
{chain_text}

### Instructions:
1. Identify logically related sequential actions (e.g., File Create -> File Write, Load DLL -> GetProcAddress).
2. **Merge** related actions into a single natural language description.
3. Keep isolated actions separate.
4. Maintain the chronological order.
5. Preserve technical details (filenames, IP addresses, API names).
6. **OUTPUT MUST BE STRICTLY IN ENGLISH.**

### Output Format (JSON):
The output must be a valid JSON object with the following structure:
{{
    "rewritten_chain": [
        {{
            "sequence": 1,
            "description": "Natural language description of the action (in English)",
            "merged_from": [1, 2],  // Indices of raw actions merged into this (1-based)
            "category": "Action Category (e.g., Process, Network, File)",
            "confidence": 0.95
        }}
    ],
    "summary": "High-level summary of the malware behavior (in English)"
}}

### Example:
Raw:
1. API: LoadLibrary(path="kernel32.dll")
2. API: GetProcAddress(function="CreateProcess")
3. API: CreateProcess(name="cmd.exe")

Output:
{{
    "rewritten_chain": [
        {{
            "sequence": 1,
            "description": "Loaded kernel32.dll and retrieved address for CreateProcess function.",
            "merged_from": [1, 2],
            "category": "API Resolution",
            "confidence": 0.98
        }},
        {{
            "sequence": 2,
            "description": "Spawned a new process 'cmd.exe'.",
            "merged_from": [3],
            "category": "Process Creation",
            "confidence": 0.95
        }}
    ],
    "summary": "The malware resolves system APIs to spawn a command shell."
}}
"""
        return prompt
    
    def _format_result(self, llm_result: Dict, original_chain: List[Dict]) -> Dict[str, Any]:
        """格式化LLM返回的结果"""
        if "rewritten_chain" not in llm_result:
            return self._fallback_result(original_chain)
        
        # 验证并补充原始链的信息
        formatted_chain = []
        for item in llm_result["rewritten_chain"]:
            # 提取合并的原始行为
            original_indices = item.get("merged_from", [])
            original_behaviors = []
            timestamps = []
            
            for idx in original_indices:
                if 0 <= idx-1 < len(original_chain):
                    original = original_chain[idx-1]
                    original_behaviors.append(original.get("behavior", ""))
                    
                    # 收集时间戳
                    ts = original.get("timestamp")
                    if ts is not None:
                        timestamps.append(ts)
            
            # 计算时间信息
            if timestamps:
                min_time = min(timestamps)
                max_time = max(timestamps)
                time_info = {
                    "start_time": min_time,
                    "end_time": max_time,
                    "duration": max_time - min_time if len(timestamps) > 1 else 0
                }
            else:
                time_info = {}
            
            formatted_chain.append({
                "sequence": item.get("sequence", 0),
                "description": item.get("description", ""),
                "original_behaviors": original_behaviors,
                "merged_count": len(original_indices),
                "category": item.get("category", "unknown"),
                "confidence": item.get("confidence", 0.5),
                "time_info": time_info
            })
        
        return {
            "original_chain_length": len(original_chain),
            "rewritten_chain_length": len(formatted_chain),
            "compression_ratio": len(original_chain) / len(formatted_chain) if formatted_chain else 0,
            "rewritten_chain": formatted_chain,
            "summary": llm_result.get("summary", ""),
            "original_chain_preview": [item.get("behavior", "") for item in original_chain[:5]]
        }
    
    def _fallback_result(self, original_chain: List[Dict]) -> Dict[str, Any]:
        """LLM失败时的回退结果"""
        fallback_chain = []
        for i, item in enumerate(original_chain):
            fallback_chain.append({
                "sequence": i + 1,
                "description": item.get("behavior", ""),
                "original_behaviors": [item.get("behavior", "")],
                "merged_count": 1,
                "category": item.get("category", "unknown"),
                "confidence": 0.5,
                "time_info": {"start_time": item.get("timestamp")}
            })
        
        return {
            "original_chain_length": len(original_chain),
            "rewritten_chain_length": len(fallback_chain),
            "compression_ratio": 1.0,
            "rewritten_chain": fallback_chain,
            "summary": "LLM处理失败，返回原始行为链",
            "note": "fallback_mode"
        }
    
    def generate_readable_output(self, rewrite_result: Dict) -> str:
        """生成可读性强的输出文本"""
        if "rewritten_chain" not in rewrite_result:
            return "重写结果无效"
        
        output_lines = []
        
        # 标题
        output_lines.append("=" * 60)
        output_lines.append("恶意软件行为链精炼结果")
        output_lines.append("=" * 60)
        
        # 统计信息
        output_lines.append(f"原始行为数: {rewrite_result.get('original_chain_length', 0)}")
        output_lines.append(f"精炼后行为数: {rewrite_result.get('rewritten_chain_length', 0)}")
        output_lines.append(f"压缩比例: {rewrite_result.get('compression_ratio', 0):.1f}倍")
        output_lines.append("")
        
        # 精炼后的行为链
        output_lines.append("【精炼行为链】")
        output_lines.append("-" * 40)
        
        for item in rewrite_result.get("rewritten_chain", []):
            seq = item.get("sequence", 0)
            desc = item.get("description", "")
            merged = item.get("merged_count", 0)
            category = item.get("category", "unknown")
            confidence = item.get("confidence", 0)
            
            time_info = item.get("time_info", {})
            time_str = ""
            if time_info.get("start_time") is not None:
                time_str = f"[{time_info['start_time']:.2f}s] "
                if time_info.get("duration", 0) > 0:
                    time_str += f"(持续{time_info['duration']:.2f}s) "
            
            confidence_str = f"[置信度: {confidence:.1%}]" if confidence > 0 else ""
            
            output_lines.append(f"{seq}. {time_str}{desc} {confidence_str}")
            output_lines.append(f"   类别: {category}, 合并了{merged}个原始行为")
            
            # 显示原始行为（如果合并了多个）
            if merged > 1 and item.get("original_behaviors"):
                output_lines.append("   原始行为:")
                for j, orig in enumerate(item["original_behaviors"]):
                    output_lines.append(f"     {j+1}. {orig}")
        
        # 总结
        output_lines.append("")
        output_lines.append("【行为总结】")
        output_lines.append("-" * 40)
        output_lines.append(rewrite_result.get("summary", "无总结信息"))
        
        return "\n".join(output_lines)


    def extract_chain_text(self, json_data: Any) -> str:
        """从重写后的JSON行为链中提取序列和描述"""
        try:
            data = json_data
            
            # 提取 rewritten_chain 数据
            if "rewritten_chain" in data:
                chain_data = data["rewritten_chain"]
            elif "chain" in data:  # 备用键名
                chain_data = data["chain"]
            else:
                raise ValueError("未找到 rewritten_chain 或 chain 字段")
            
            # 组合文本
            chain_txt = ""
            for item in chain_data:
                sequence = item.get("sequence", 0)
                description = item.get("description", "")
                
                # 确保描述不为空
                if not description:
                    # 尝试其他可能的字段
                    description = item.get("desc", item.get("behavior", "无描述"))
                
                # 添加到文本
                chain_txt += f"{sequence}. {description}\n"
            
            return chain_txt.strip()  # 移除末尾的换行符
        
        except Exception as e:
            return f"错误：{str(e)}"



def rewrite(report_path):
    parser = CuckooParser(report_path)
    parser.extract_all_behavior_units()   # 提取行为单元
    chain_data = parser.get_behavior_chain_data()   # 结构化
    builder = BehaviorChain(chain_data)
    behavior_chain = builder.build_greedy_chain()   # 构建json格式行为链，含更多信息
    rewriter = QueryRewriter(
        llm_api_key = LLM_API_KEY,
        llm_base_url = LLM_API_BASE,
        model = LLM_MODEL  
    )
    result = rewriter.rewrite_chain(behavior_chain)
    if "error" in result:
        print(f"错误: {result['error']}")
        return
    chain_txt = rewriter.extract_chain_text(result)    # 重写行为链

    return chain_txt
