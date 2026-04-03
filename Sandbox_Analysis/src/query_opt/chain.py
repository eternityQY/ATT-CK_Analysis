"""
行为链构建器
算法：从当前节点开始，按相关性连接，没有可连接节点时取最小时间节点到链尾，重复上述过程
"""
import re
import heapq
from typing import List, Dict, Any, Tuple, Set, Optional


class BehaviorChain:
    """行为链构建器"""
    
    def __init__(self, behavior_data: List[Dict[str, Any]]):
        """
        初始化
        
        Args:
            behavior_data: 从parser.py获取的行为链数据，包含timestamp
        """
        self.behavior_data = behavior_data
        self.all_nodes = behavior_data  # 所有节点
        self.chain: List[int] = []  # 链的节点索引
        self.used_indices: Set[int] = set()  # 已使用的节点索引
        
    def build_greedy_chain(self) -> List[Dict]:
        """
        行为链构建主函数

        算法步骤：
        1. 找到起始节点（最小时间戳）
        2. 从当前节点出发，寻找相关性最强的未使用节点
        3. 如果找到，连接到链尾
        4. 如果找不到，从剩余节点中取时间最小的连接到链尾
        5. 重复2-4，直到所有节点都使用
        """
        if not self.all_nodes:
            return []
        
        # 步骤1：初始化，找到起始节点（时间最小的节点）
        start_index = self._find_start_node()
        if start_index is None:
            return []
        
        # 初始化链
        self.chain = [start_index]
        self.used_indices = {start_index}
        
        # 步骤2：逐步构建链
        while len(self.used_indices) < len(self.all_nodes):
            # 从链尾开始
            current_index = self.chain[-1]
            
            # 尝试找到相关性最强的未使用节点
            best_related = self._find_best_related_node(current_index)
            
            if best_related is not None:
                # 找到相关节点，连接到链尾
                self.chain.append(best_related)
                self.used_indices.add(best_related)
            else:
                # 没有相关节点，找时间最小的未使用节点
                next_node = self._find_earliest_unused_node()
                if next_node is not None:
                    self.chain.append(next_node)
                    self.used_indices.add(next_node)
                else:
                    # 没有更多节点了
                    break
        
        # 步骤3：格式化输出
        return self._format_chain()
    
    def _find_start_node(self) -> Optional[int]:
        """找到起始节点（时间戳最小的节点）"""
        if not self.all_nodes:
            return None
        
        # 找到所有有时间戳的节点
        nodes_with_time = []
        for idx, node in enumerate(self.all_nodes):
            timestamp = node.get("timestamp")
            if timestamp is not None:
                nodes_with_time.append((idx, timestamp))
        
        if not nodes_with_time:
            # 如果没有时间戳，返回第一个节点
            return 0
        
        # 返回时间最小的节点
        nodes_with_time.sort(key=lambda x: x[1])
        return nodes_with_time[0][0]
    
    def _find_best_related_node(self, current_index: int) -> Optional[int]:
        """
        找到与当前节点相关性最强的未使用节点
        
        Returns:
            相关性最强的节点索引，如果没有返回None
        """
        current_node = self.all_nodes[current_index]
        best_index = None
        best_score = 0.0
        
        for idx, node in enumerate(self.all_nodes):
            if idx in self.used_indices:
                continue
                
            # 计算相关性得分
            score = self._calculate_relation_score(current_node, node)
            
            if score > best_score:
                best_score = score
                best_index = idx
        
        # 只返回相关性足够强的节点
        return best_index if best_score > 0.3 else None
    
    def _calculate_relation_score(self, node_a: Dict, node_b: Dict) -> float:
        """
        计算两个节点的相关性得分 (0-1)
        
        考虑因素：
        1. 语义关联（共同语义键）
        2. 时间接近性
        3. 进程上下文
        4. 行为类型的逻辑关系
        """
        score = 0.0
        
        # 1. 语义关联（权重：0.5）
        semantic_score = self._calculate_semantic_score(node_a, node_b)
        score += 0.5 * semantic_score
        
        # 2. 时间接近性（权重：0.2）
        time_score = self._calculate_time_proximity_score(node_a, node_b)
        score += 0.2 * time_score
        
        # 3. 进程上下文（权重：0.2）
        process_score = self._calculate_process_context_score(node_a, node_b)
        score += 0.2 * process_score
        
        # 4. 逻辑关系（权重：0.1）
        logic_score = self._calculate_logic_relation_score(node_a, node_b)
        score += 0.1 * logic_score
        
        return min(score, 1.0)  # 确保不超过1.0
    
    def _calculate_semantic_score(self, node_a: Dict, node_b: Dict) -> float:
        """计算语义关联得分"""
        keys_a = set(node_a.get("semantic_keys", []))
        keys_b = set(node_b.get("semantic_keys", []))
        
        if not keys_a or not keys_b:
            return 0.0
        
        # 计算Jaccard相似度
        intersection = len(keys_a.intersection(keys_b))
        union = len(keys_a.union(keys_b))
        
        if union == 0:
            return 0.0
        
        # 加强某些关键语义键的权重
        base_score = intersection / union
        
        # 检查是否有强关联键
        strong_keys = {"process:", "memory:", "inject", "payload"}
        for key in keys_a.intersection(keys_b):
            if any(sk in key for sk in strong_keys):
                base_score = min(base_score * 1.5, 1.0)  # 加强权重
        
        return base_score
    
    def _calculate_time_proximity_score(self, node_a: Dict, node_b: Dict) -> float:
        """计算时间接近性得分"""
        time_a = node_a.get("timestamp")
        time_b = node_b.get("timestamp")
        
        if time_a is None or time_b is None:
            return 0.0
        
        time_diff = abs(time_b - time_a)
        
        # 时间差越小，得分越高
        if time_diff < 0.1:  # 0.1秒内
            return 1.0
        elif time_diff < 1.0:  # 1秒内
            return 0.8
        elif time_diff < 5.0:  # 5秒内
            return 0.5
        elif time_diff < 10.0:  # 10秒内
            return 0.2
        else:
            return 0.0
    
    def _calculate_process_context_score(self, node_a: Dict, node_b: Dict) -> float:
        """计算进程上下文得分"""
        ctx_a = node_a.get("process_context", {})
        ctx_b = node_b.get("process_context", {})
        
        if not ctx_a or not ctx_b:
            return 0.0
        
        # 检查PID是否相同
        if ctx_a.get("pid") == ctx_b.get("pid") and ctx_a.get("pid") is not None:
            return 1.0
        
        # 检查进程名是否相同
        if ctx_a.get("name") == ctx_b.get("name") and ctx_a.get("name"):
            return 0.7
        
        return 0.0
    
    def _calculate_logic_relation_score(self, node_a: Dict, node_b: Dict) -> float:
        """计算逻辑关系得分"""
        std_a = node_a.get("standardized", "").lower()
        std_b = node_b.get("standardized", "").lower()
        cat_a = node_a.get("category", "")
        cat_b = node_b.get("category", "")
        
        # 常见逻辑关系模式
        patterns = [
            # (条件函数, 得分)
            (lambda: "createprocess" in std_a and cat_b == "process", 1.0),
            (lambda: "loadlibrary" in std_a and "getprocaddress" in std_b, 0.9),
            (lambda: "createfile" in std_a and "writefile" in std_b, 0.8),
            (lambda: "writeprocessmemory" in std_a and "createremotethread" in std_b, 1.0),
            (lambda: cat_a == "file_op" and "write" in std_a and 
                     cat_b == "file_op" and "read" in std_b and 
                     self._same_file_path(node_a, node_b), 0.7),
            (lambda: "internetopenurl" in std_a and cat_b == "network", 0.8),
        ]
        
        for condition_func, score in patterns:
            if condition_func():
                return score
        
        return 0.0
    
    def _same_file_path(self, node_a: Dict, node_b: Dict) -> bool:
        """检查两个文件操作是否针对同一文件"""
        # 从标准化字符串提取文件路径
        std_a = node_a.get("standardized", "")
        std_b = node_b.get("standardized", "")
        
        # 提取path参数
        pattern = r'path="([^"]+)"'
        path_a = re.search(pattern, std_a)
        path_b = re.search(pattern, std_b)
        
        if path_a and path_b:
            return path_a.group(1) == path_b.group(1)
        
        return False
    
    def _find_earliest_unused_node(self) -> Optional[int]:
        """找到时间最早的未使用节点"""
        earliest_node = None
        earliest_time = float('inf')
        
        for idx, node in enumerate(self.all_nodes):
            if idx in self.used_indices:
                continue
                
            timestamp = node.get("timestamp")
            if timestamp is not None and timestamp < earliest_time:
                earliest_time = timestamp
                earliest_node = idx
        
        # 如果所有节点都没有时间戳，返回第一个未使用的
        if earliest_node is None:
            for idx in range(len(self.all_nodes)):
                if idx not in self.used_indices:
                    return idx
        
        return earliest_node
    
    def _format_chain(self) -> List[Dict]:
        """格式化行为链输出"""
        formatted_chain = []
        
        for i, idx in enumerate(self.chain):
            node = self.all_nodes[idx]
            
            # 确定显示格式
            display_format = self._determine_display_format(i, idx)
            
            formatted_chain.append({
                "index": idx,
                "behavior": node.get("standardized", ""),
                "timestamp": node.get("timestamp"),
                "category": node.get("category", ""),
                "display_format": display_format,
                "semantic_keys": node.get("semantic_keys", [])
            })
        
        return formatted_chain
    
    def _determine_display_format(self, position: int, current_idx: int) -> str:
        """确定节点显示格式"""
        if position == 0:
            return "start"
        
        prev_idx = self.chain[position - 1]
        prev_node = self.all_nodes[prev_idx]
        current_node = self.all_nodes[current_idx]
        
        # 计算相关性
        relation_score = self._calculate_relation_score(prev_node, current_node)
        
        if relation_score > 0.5:
            return "bullet"  # 强相关
        elif relation_score > 0.3:
            return "dash"    # 中等相关
        else:
            return "newline" # 弱相关
    
    def generate_paper_output(self) -> str:
        """生成标准格式输出"""
        if not self.chain:
            self.build_greedy_chain()
        
        chain_data = self._format_chain()
        
        output_lines = ["Operate: Link behavioral units sequentially to construct behavioral chains.\n"]
        output_lines.append("Output:\n")
        
        for i, item in enumerate(chain_data):
            behavior = item["behavior"]
            display_format = item["display_format"]
            
            if i == 0:
                output_lines.append(f"• {behavior}")    # 这里可根据不同的相关程度使用不同的标识符号
            elif display_format == "bullet":
                output_lines.append(f"• {behavior}")
            elif display_format == "dash":
                output_lines.append(f"• {behavior}")
            else:
                output_lines.append(f"• {behavior}")
        
        return "\n".join(output_lines)
    
    def generate_detailed_report(self) -> str:
        """生成详细报告"""
        chain_data = self._format_chain()
        
        output_lines = ["=== 行为链构建详细报告 ==="]
        output_lines.append(f"总节点数: {len(self.all_nodes)}")
        output_lines.append(f"链长度: {len(chain_data)}")
        output_lines.append("")
        
        # 显示构建过程
        output_lines.append("【构建过程】")
        for i, idx in enumerate(self.chain):
            node = self.all_nodes[idx]
            timestamp = node.get("timestamp")
            time_str = f"[{timestamp:.2f}]" if timestamp is not None else "[----]"
            
            # 显示相关性（如果是链尾选择）
            if i > 0:
                prev_idx = self.chain[i - 1]
                prev_node = self.all_nodes[prev_idx]
                relation_score = self._calculate_relation_score(prev_node, node)
                
                if relation_score > 0.3:
                    output_lines.append(f"{i+1:2d}. {time_str} ← 相关(score={relation_score:.2f}) {node.get('standardized', '')}")
                else:
                    output_lines.append(f"{i+1:2d}. {time_str} ← 时间顺序 {node.get('standardized', '')}")
            else:
                output_lines.append(f"{i+1:2d}. {time_str} 起始节点 {node.get('standardized', '')}")
        
        # 统计信息
        output_lines.append("\n【统计信息】")
        
        # 计算相关连接的比例
        strong_links = 0
        weak_links = 0
        time_links = 0
        
        for i in range(1, len(self.chain)):
            prev_idx = self.chain[i - 1]
            curr_idx = self.chain[i]
            prev_node = self.all_nodes[prev_idx]
            curr_node = self.all_nodes[curr_idx]
            
            score = self._calculate_relation_score(prev_node, curr_node)
            if score > 0.5:
                strong_links += 1
            elif score > 0.3:
                weak_links += 1
            else:
                time_links += 1
        
        total_links = len(self.chain) - 1
        if total_links > 0:
            output_lines.append(f"强相关连接: {strong_links} ({strong_links/total_links*100:.1f}%)")
            output_lines.append(f"弱相关连接: {weak_links} ({weak_links/total_links*100:.1f}%)")
            output_lines.append(f"时间顺序连接: {time_links} ({time_links/total_links*100:.1f}%)")
        
        return "\n".join(output_lines)