"""
Cuckoo 报告解析器 - 完整行为链数据提取
为行为链构建提供时间戳、语义关联键等完整信息
"""

import re
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional, Set


@dataclass
class BehaviorUnit:
    """行为单元基类"""
    timestamp: Optional[float]  # 时间戳，用于排序
    category: str              # 行为类别：api_call, file_op, network, registry, process
    standardized: str          # 标准化格式字符串
    semantic_keys: List[str]   # 语义关联键列表
    process_context: Dict[str, Any]  # 进程上下文
    raw_data: Any              # 原始数据引用
    operation_type: str        # 操作类型：create, write, read, delete等


class CuckooParser:
    """完整的行为数据提取器，为行为链构建准备"""
    
    def __init__(self, report_path: Path):
        self.report_path = report_path
        self.report_data = None
        self.behavior_units: List[BehaviorUnit] = []  # 所有行为单元
        
    def load_report(self) -> Dict:
        """加载Cuckoo报告"""
        with open(self.report_path, 'r', encoding='utf-8') as f:
            self.report_data = json.load(f)
        return self.report_data
    
    def extract_all_behavior_units(self) -> List[BehaviorUnit]:
        """提取所有行为单元"""
        if not self.report_data:
            self.load_report()
        
        # 清空现有数据
        self.behavior_units = []
        
        # 提取各种行为
        self._extract_process_behavior()
        self._extract_api_calls()
        self._extract_file_operations()
        self._extract_network_activity()
        self._extract_registry_operations()
        
        # 按时间戳排序
        self.behavior_units.sort(key=lambda x: x.timestamp if x.timestamp is not None else float('inf'))
        
        return self.behavior_units
    
    def _extract_process_behavior(self) -> None:
        """提取进程行为"""
        if "behavior" not in self.report_data:
            return
            
        behavior = self.report_data["behavior"]
        
        if "processes" in behavior:
            for process in behavior["processes"]:
                # 提取进程信息
                pid = process.get("pid")
                process_name = process.get("process_name", "unknown")
                cmd_line = process.get("command_line", "")
                first_seen = process.get("first_seen")
                
                # 清理命令行
                if cmd_line.startswith('"') and cmd_line.endswith('"'):
                    cmd_line = cmd_line[1:-1]
                
                # 进程创建行为
                semantic_keys = [
                    f"pid:{pid}",
                    f"process:{process_name}",
                    f"cmd:{self._hash_string(cmd_line)}"
                ]
                
                unit = BehaviorUnit(
                    timestamp=first_seen,
                    category="process",
                    standardized=f'Process: Create(name="{process_name}", command_line="{cmd_line}")',
                    semantic_keys=semantic_keys,
                    process_context={"pid": pid, "name": process_name},
                    raw_data=process,
                    operation_type="create"
                )
                self.behavior_units.append(unit)
                
                # 检查是否有注入行为
                if "calls" in process:
                    for call in process["calls"]:
                        api_name = call.get("api", "")
                        if "WriteProcessMemory" in api_name or "CreateRemoteThread" in api_name:
                            # 检测到进程注入
                            target_pid = call.get("arguments", {}).get("process_identifier", "unknown")
                            data = call.get("arguments", {}).get("buffer", "")
                            
                            # 简化数据
                            if isinstance(data, str) and len(data) > 20:
                                data = data[:17] + "..."
                            
                            semantic_keys = [
                                f"pid:{pid}",
                                f"process:{process_name}",
                                f"target:{target_pid}"
                            ]
                            
                            inject_unit = BehaviorUnit(
                                timestamp=call.get("time"),
                                category="process",
                                standardized=f'Process: Inject(process="{process_name}", payload="malicious code")',
                                semantic_keys=semantic_keys,
                                process_context={"pid": pid, "name": process_name},
                                raw_data=call,
                                operation_type="inject"
                            )
                            self.behavior_units.append(inject_unit)
                            break
    
    def _extract_api_calls(self) -> None:
        """提取API调用"""
        if "behavior" not in self.report_data:
            return
            
        behavior = self.report_data["behavior"]
        
        # API格式化映射
        api_formatters = {
            "LoadLibrary": self._format_loadlibrary_api,
            "CreateProcess": self._format_createprocess_api,
            "WriteProcessMemory": self._format_writeprocessmemory_api,
            "CreateService": self._format_createservice_api,
            "InternetOpenUrl": self._format_internetopenurl_api,
            "NtAllocateVirtualMemory": self._format_allocatevirtualmemory_api,
            "LdrGetDllHandle": self._format_getdllhandle_api,
            "LdrGetProcedureAddress": self._format_getprocaddress_api
        }
        
        if "processes" in behavior:
            for process in behavior["processes"]:
                pid = process.get("pid")
                process_name = process.get("process_name", "unknown")
                
                if "calls" in process:
                    for call in process["calls"]:
                        try:
                            api_name = call.get("api", "")
                            arguments = call.get("arguments", {})
                            return_value = call.get("return", 0)
                            timestamp = call.get("time")
                            
                            # 使用特定格式化函数或通用函数
                            if api_name in api_formatters:
                                standardized, semantic_keys, op_type = api_formatters[api_name](
                                    arguments, return_value
                                )
                            else:
                                standardized, semantic_keys, op_type = self._format_generic_api(
                                    api_name, arguments, return_value
                                )
                            
                            if standardized:
                                # 添加进程相关的语义键
                                semantic_keys.extend([
                                    f"pid:{pid}",
                                    f"process:{process_name}"
                                ])
                                
                                unit = BehaviorUnit(
                                    timestamp=timestamp,
                                    category="api_call",
                                    standardized=standardized,
                                    semantic_keys=semantic_keys,
                                    process_context={"pid": pid, "name": process_name},
                                    raw_data=call,
                                    operation_type=op_type
                                )
                                self.behavior_units.append(unit)
                                
                        except Exception:
                            continue
    
    def _extract_file_operations(self) -> None:
        """提取文件操作"""
        # 从dropped文件提取
        if "dropped" in self.report_data:
            for dropped in self.report_data["dropped"]:
                path = dropped.get("path", "unknown")
                sha256 = dropped.get("sha256", "")
                md5 = dropped.get("md5", "")
                
                # 确定哈希值
                content_hash = sha256 if sha256 else (md5 if md5 else "N/A")
                if content_hash != "N/A":
                    content_hash = f"0x{content_hash[:8].upper()}"
                
                # 语义关联键
                semantic_keys = [
                    f"file:{path}",
                    f"hash:{content_hash}"
                ]
                
                standardized = f'File: Write(path="{path}", content_hash="{content_hash}")'
                
                unit = BehaviorUnit(
                    timestamp=None,  # dropped文件通常没有时间戳
                    category="file_op",
                    standardized=standardized,
                    semantic_keys=semantic_keys,
                    process_context={},
                    raw_data=dropped,
                    operation_type="write"
                )
                self.behavior_units.append(unit)
        
        # 从行为摘要提取
        if "behavior" in self.report_data:
            behavior = self.report_data["behavior"]
            if "summary" in behavior and "file" in behavior["summary"]:
                for file_op in behavior["summary"]["file"]:
                    op_type, path = self._parse_file_summary(file_op)
                    
                    if path != "unknown":
                        path = path.replace("\\\\", "\\")
                        semantic_keys = [f"file:{path}"]
                        
                        standardized = f'File: {op_type}(path="{path}", content_hash="N/A")'
                        
                        unit = BehaviorUnit(
                            timestamp=None,
                            category="file_op",
                            standardized=standardized,
                            semantic_keys=semantic_keys,
                            process_context={},
                            raw_data=file_op,
                            operation_type=op_type.lower()
                        )
                        self.behavior_units.append(unit)
    
    def _extract_network_activity(self) -> None:
        """提取网络活动"""
        if "network" in self.report_data:
            network = self.report_data["network"]
            
            # TCP连接
            if "tcp" in network:
                for tcp in network["tcp"]:
                    dest_ip = tcp.get("dst", "unknown")
                    dport = tcp.get("dport", "")
                    offset = tcp.get("offset", 0)
                    
                    dest = f"{dest_ip}:{dport}" if dport else dest_ip
                    data_size = f"{offset//1024}KB" if offset >= 1024 else f"{offset}B"
                    
                    semantic_keys = [f"network:{dest}"]
                    
                    standardized = f'Network: TCP(dest_ip="{dest}", data_size="{data_size}")'
                    
                    unit = BehaviorUnit(
                        timestamp=None,
                        category="network",
                        standardized=standardized,
                        semantic_keys=semantic_keys,
                        process_context={},
                        raw_data=tcp,
                        operation_type="connect"
                    )
                    self.behavior_units.append(unit)
            
            # HTTP请求
            if "http" in network:
                for http in network["http"]:
                    host = http.get("host", "unknown")
                    port = http.get("port", "80")
                    body = http.get("body", "")
                    
                    dest = f"{host}:{port}"
                    data_size = f"{len(body)}B"
                    
                    semantic_keys = [f"network:{dest}", f"url:{host}"]
                    
                    standardized = f'Network: HTTP(dest_ip="{dest}", data_size="{data_size}")'
                    
                    unit = BehaviorUnit(
                        timestamp=None,
                        category="network",
                        standardized=standardized,
                        semantic_keys=semantic_keys,
                        process_context={},
                        raw_data=http,
                        operation_type="http_request"
                    )
                    self.behavior_units.append(unit)
    
    def _extract_registry_operations(self) -> None:
        """提取注册表操作"""
        if "behavior" not in self.report_data:
            return
            
        behavior = self.report_data["behavior"]
        
        if "summary" in behavior and "registry" in behavior["summary"]:
            for reg_op in behavior["summary"]["registry"]:
                op_type, path, value = self._parse_registry_summary(reg_op)
                
                if path != "unknown":
                    path = path.replace("\\\\", "\\")
                    if len(value) > 50:
                        value = value[:47] + "..."
                    
                    semantic_keys = [f"registry:{path}"]
                    
                    standardized = f'Registry: {op_type}(path="{path}", value="{value}")'
                    
                    unit = BehaviorUnit(
                        timestamp=None,
                        category="registry",
                        standardized=standardized,
                        semantic_keys=semantic_keys,
                        process_context={},
                        raw_data=reg_op,
                        operation_type=op_type.lower()
                    )
                    self.behavior_units.append(unit)
    
    # API格式化函数
    def _format_loadlibrary_api(self, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        path = args.get("module_name", args.get("lpLibFileName", "unknown"))
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        standardized = f'API: LoadLibrary(path="{path}") -> {return_value} ({status})'
        semantic_keys = [f"dll:{path}"]
        return standardized, semantic_keys, "load_library"
    
    def _format_createprocess_api(self, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        name = args.get("application_name", args.get("lpCommandLine", "unknown"))
        cmd = args.get("command_line", args.get("lpCommandLine", "unknown"))
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        standardized = f'API: CreateProcess(name="{name}", command_line="{cmd}") -> {return_value} ({status})'
        semantic_keys = [f"process:{name}"]
        return standardized, semantic_keys, "create_process"
    
    def _format_writeprocessmemory_api(self, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        process = args.get("process_identifier", "unknown")
        address = args.get("base_address", "unknown")
        data = args.get("buffer", "")
        size = args.get("buffer_length", 0)
        
        if isinstance(data, str) and len(data) > 20:
            data = data[:17] + "..."
        
        size_str = f"{size//1024}KB" if size >= 1024 else f"{size}B"
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        
        standardized = f'API: WriteProcessMemory(process="{process}", address="{address}", data="{data}", size="{size_str}") -> {return_value} ({status})'
        semantic_keys = [f"process:{process}", f"memory:{address}"]
        return standardized, semantic_keys, "write_memory"
    
    def _format_createservice_api(self, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        name = args.get("service_name", "unknown")
        path = args.get("binary_path_name", args.get("lpBinaryPathName", "unknown"))
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        standardized = f'API: CreateService(name="{name}", path="{path}") -> {return_value} ({status})'
        semantic_keys = [f"service:{name}", f"file:{path}"]
        return standardized, semantic_keys, "create_service"
    
    def _format_internetopenurl_api(self, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        url = args.get("url", args.get("lpszUrl", "unknown"))
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        standardized = f'API: InternetOpenUrl(url="{url}") -> {return_value} ({status})'
        semantic_keys = [f"url:{url}"]
        return standardized, semantic_keys, "open_url"
    
    def _format_allocatevirtualmemory_api(self, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        size = args.get("region_size", 0)
        prot = args.get("protection", 0)
        size_str = f"{size//1024}KB" if size >= 1024 else f"{size}B"
        prot_map = {4: "PAGE_READWRITE", 0x20: "PAGE_EXECUTE_READ", 0x40: "PAGE_EXECUTE_READWRITE"}
        prot_str = prot_map.get(prot, f"0x{prot:X}")
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        standardized = f'API: NtAllocateVirtualMemory(size="{size_str}", protection="{prot_str}") -> {return_value} ({status})'
        semantic_keys = []
        return standardized, semantic_keys, "allocate_memory"
    
    def _format_getdllhandle_api(self, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        module = args.get("module_name", "unknown")
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        standardized = f'API: LdrGetDllHandle(module="{module}") -> {return_value} ({status})'
        semantic_keys = [f"dll:{module}"]
        return standardized, semantic_keys, "get_dll"
    
    def _format_getprocaddress_api(self, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        func = args.get("function_name", args.get("api_name", "unknown"))
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        standardized = f'API: LdrGetProcedureAddress(function="{func}") -> {return_value} ({status})'
        semantic_keys = [f"function:{func}"]
        return standardized, semantic_keys, "get_proc"
    
    def _format_generic_api(self, api_name: str, args: Dict, return_value: Any) -> Tuple[str, List[str], str]:
        if not args:
            status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
            return f'API: {api_name}() -> {return_value} ({status})', [], "generic"
        
        param_parts = []
        semantic_keys = []
        for key, value in args.items():
            if isinstance(value, str):
                if len(value) > 30:
                    value = value[:27] + "..."
                param_parts.append(f'{key}="{value}"')
                
                # 提取可能的语义键
                if key in ["filepath", "path", "filename"]:
                    semantic_keys.append(f"file:{value}")
                elif key in ["regkey", "subkey"]:
                    semantic_keys.append(f"registry:{value}")
                elif key in ["host", "url", "domain"]:
                    semantic_keys.append(f"network:{value}")
            else:
                param_parts.append(f'{key}={value}')
        
        params = ", ".join(param_parts)
        status = "SUCCESS" if return_value == 0 else f"ERROR({return_value})"
        return f'API: {api_name}({params}) -> {return_value} ({status})', semantic_keys, "generic"
    
    # 辅助函数
    def _parse_file_summary(self, file_op: str) -> Tuple[str, str]:
        file_op_lower = file_op.lower()
        
        if "created" in file_op_lower:
            op_type = "Create"
        elif "deleted" in file_op_lower:
            op_type = "Delete"
        elif "written" in file_op_lower:
            op_type = "Write"
        elif "read" in file_op_lower:
            op_type = "Read"
        elif "copied" in file_op_lower:
            op_type = "Copy"
        elif "moved" in file_op_lower:
            op_type = "Move"
        else:
            op_type = "Operation"
        
        path = "unknown"
        patterns = [r'file\s+"([^"]+)"', r'to\s+"([^"]+)"', r'from\s+"([^"]+)"', r'at\s+"([^"]+)"']
        for pattern in patterns:
            match = re.search(pattern, file_op)
            if match:
                path = match.group(1)
                break
        
        return op_type, path
    
    def _parse_registry_summary(self, reg_op: str) -> Tuple[str, str, str]:
        reg_op_lower = reg_op.lower()
        
        if "set" in reg_op_lower or "created" in reg_op_lower:
            op_type = "Create"
        elif "deleted" in reg_op_lower:
            op_type = "Delete"
        elif "queried" in reg_op_lower:
            op_type = "Query"
        else:
            op_type = "Operation"
        
        path = "unknown"
        value = "N/A"
        
        path_match = re.search(r'key\s+"([^"]+)"', reg_op)
        if path_match:
            path = path_match.group(1)
        
        value_match = re.search(r'value\s+"([^"]+)"', reg_op)
        if value_match:
            value = value_match.group(1)
        
        return op_type, path, value
    
    def _hash_string(self, s: str) -> str:
        """简单字符串哈希（用于语义键）"""
        import hashlib
        return hashlib.md5(s.encode()).hexdigest()[:8]
    
    def get_paper_format_output(self) -> str:
        """生成标准格式输出（无时间戳等额外信息）"""
        output_lines = ["Extract and formalize the following key behavioral information from the Cuckoo report.\n"]
        output_lines.append("Output:\n")
        output_lines.append("–")
        
        # 按类别分组
        categories = {
            "api_call": "API Call",
            "file_op": "File Operation",
            "network": "Network Activity",
            "registry": "Registry Operation",
            "process": "Process Behavior"
        }
        
        grouped = {}
        for unit in self.behavior_units:
            if unit.category not in grouped:
                grouped[unit.category] = []
            grouped[unit.category].append(unit.standardized)
        
        for cat_key, cat_name in categories.items():
            if cat_key in grouped and grouped[cat_key]:
                output_lines.append(f"• {cat_name}:")
                for item in grouped[cat_key]:
                    output_lines.append(f"  – {item}")
        
        return "\n".join(output_lines)
    
    def get_behavior_chain_data(self) -> List[Dict]:
        """获取行为链构建所需数据"""
        chain_data = []
        for unit in self.behavior_units:
            chain_data.append({
                "timestamp": unit.timestamp,
                "category": unit.category,
                "standardized": unit.standardized,
                "semantic_keys": unit.semantic_keys,
                "process_context": unit.process_context,
                "operation_type": unit.operation_type
            })
        return chain_data