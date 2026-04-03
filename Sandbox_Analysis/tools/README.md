# 开发者工具

本目录包含 MalGTA 项目的开发者工具，仅供系统管理员和开发人员使用。

## 工具列表

### 1. build_kb.py - 知识库构建工具

用于构建和更新 RAG 知识库。

#### 使用方法

```bash
# 构建知识库（使用默认配置）
python tools/build_kb.py --build

# 指定自定义路径
python tools/build_kb.py --build --source /path/to/docs --output /path/to/db

# 验证知识库
python tools/build_kb.py --verify
```

#### 准备工作

1. 将知识源文档放入 `data/knowledge_source/` 目录：
   - ATT&CK 框架文档（PDF/HTML）
   - Windows API 文档（PDF/HTML）
   - 威胁情报（CTI）文档（PDF/HTML）

2. 确保已安装所有依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量（如需要）：
   ```bash
   export LLM_API_KEY="your-api-key"
   export LLM_API_BASE="https://api.openai.com/v1"
   ```

#### 构建流程

工具会自动完成以下步骤：

1. **加载文档** - 从 `knowledge_source` 目录读取所有 PDF 和 HTML 文件
2. **文本清洗** - 清洗并分块处理文本内容
3. **向量化** - 使用嵌入模型生成文本向量
4. **构建索引** - 创建 FAISS 向量索引
5. **保存** - 将索引保存到 `data/vector_db/` 目录

#### 输出

成功构建后，`data/vector_db/` 目录将包含：
- 向量索引文件
- 文档元数据
- 索引配置信息

## 注意事项

⚠️ **重要提醒**：

1. 这些工具仅供开发人员使用
2. 最终用户不需要运行这些工具
3. 知识库应该预先构建好，随系统一起分发
4. 如需更新知识库，重新运行构建工具即可覆盖旧版本

## 用户工具

最终用户应该使用项目根目录下的 `main.py`：

```bash
# 用户使用方式（在项目根目录）
python main.py data/raw_reports/sample.json
```

用户无需关心知识库的构建过程，只需使用预先构建好的知识库进行分析。
