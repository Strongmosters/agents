# Data Agent

基于 LangGraph 的智能数据查询 Agent，通过自然语言自动生成并执行 SQL，实现对数据仓库的智能问答。

## 架构概览

```
用户自然语言查询 → FastAPI → LangGraph Agent Pipeline → SQL → MySQL(DW) → 结果
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
                 Qdrant           Qdrant           ES
              (字段语义检索)    (指标语义检索)    (取值全文检索)
```

## Agent 工作流

1. **extract_keywords** — 从用户查询中提取关键词
2. **recall_column** — 通过 Qdrant 向量检索召回相关字段
3. **recall_metric** — 通过 Qdrant 向量检索召回相关指标
4. **recall_value** — 通过 Elasticsearch 全文检索召回字段取值
5. **merge_retrieved_info** — 合并上述三种检索结果
6. **filter_table / filter_metric** — LLM 过滤出真正相关的表和指标
7. **add_extra_context** — 补充日期、数据库版本等上下文信息
8. **generate_sql** — LLM 根据上下文生成 SQL 语句
9. **validate_sql** — 验证 SQL 正确性
10. **correct_sql** — 如有错误则修正 SQL
11. **run_sql** — 在数据仓库中执行 SQL 并返回结果

## 技术栈

| 组件 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI |
| Agent 编排 | LangGraph + LangChain |
| 向量数据库 | Qdrant |
| 全文检索 | Elasticsearch |
| 元数据存储 | MySQL (meta) |
| 数据仓库 | MySQL (dw) |
| Embedding | BAAI/bge-large-zh-v1.5 (HuggingFace TEI) |
| LLM | OpenAI 兼容 API |
| 配置管理 | OmegaConf |
| 日志 | Loguru |

## 项目结构

```
├── main.py                  # FastAPI 应用入口
├── pyproject.toml           # 项目依赖配置
├── conf/
│   ├── app_config.yaml      # 应用配置（数据库、Qdrant、ES、LLM）
│   └── meta_config.yaml     # 元数据配置（表、字段定义）
├── docker/
│   ├── docker-compose.yaml  # 基础设施编排（MySQL、ES、Qdrant、TEI）
│   ├── elasticsearch/       # ES 自定义镜像
│   ├── embedding/           # Embedding 模型文件
│   └── mysql/               # MySQL 初始化脚本
├── prompts/                 # LLM Prompt 模板
├── app/
│   ├── api/                 # API 路由、依赖注入、请求模型
│   ├── agent/               # LangGraph 状态图、节点、状态定义
│   ├── clients/             # 外部服务客户端（MySQL、ES、Qdrant、Embedding）
│   ├── conf/                # 配置加载模块
│   ├── core/                # 日志、上下文变量
│   ├── entities/            # 领域实体
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── prompt/              # Prompt 加载器
│   ├── repositories/        # 数据访问层（MySQL、ES、Qdrant）
│   ├── scripts/             # 知识库构建脚本
│   └── services/            # 业务服务层
```

## 快速开始

### 1. 启动基础设施

```bash
cd docker
docker compose up -d
```

启动的服务：
- **MySQL** — 端口 3307，包含 meta（元数据）和 dw（数据仓库）两个库
- **Elasticsearch** — 端口 9200
- **Kibana** — 端口 5601
- **Qdrant** — HTTP 端口 6333，gRPC 端口 6334
- **Embedding** — 端口 8081，BGE-large-zh-v1.5 模型

### 2. 配置

编辑 `conf/app_config.yaml`，填入 LLM API Key 等信息：

```yaml
llm:
  model_name: gpt-5.2-codex
  api_key: <your-api-key>
  base_url: https://api.openai-proxy.org/v1
```

### 3. 构建元数据知识库

```bash
python -m app.scripts.build_meta_knowledge
```

该脚本读取 `conf/meta_config.yaml` 中定义的表和字段信息，将其向量化后写入 Qdrant 和 Elasticsearch，供后续检索使用。

### 4. 启动应用

```bash
uv run main.py
```

### 5. 调用 API

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "请统计华北地区的销售总额"}'
```

响应为 SSE (Server-Sent Events) 流式输出，可实时看到 Agent 各节点的处理进度和最终结果。
