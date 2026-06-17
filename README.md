# Digital Self - 数字分身

基于分层记忆架构 + LightRAG 知识图谱的个人数字分身系统。

## 核心特性

### 双模式检索

| | Lite 模式（默认） | Full 模式 |
|---|---|---|
| **依赖** | 无额外依赖 | 需安装 [Ollama](https://ollama.com) |
| **Embedding** | 不生成向量 | Ollama 本地运行 bge-m3（1024 维） |
| **记忆检索** | TF-IDF 文本排序 | Qdrant 向量余弦相似度 |
| **去重** | TF-IDF cosine | 向量 cosine ≥ 0.92 |
| **LightRAG** | hashed embedding 兜底 | bge-m3 语义向量 |

Lite 模式开箱即用，无需任何额外配置。在设置页面可随时切换到 Full 模式。

### 分层记忆系统

- **11 种记忆类型**：episodic / fact / preference / opinion / goal / relationship / knowledge / semantic / persona / short_term / long_term
- **LLM 自动分类**：导入时自动判断内容类型
- **LLM 自动评分**：导入时评估重要性（1-10 分）
- **记忆去重**：相似记忆自动合并，evidence_count 递增
- **综合评分**：importance x confidence x freshness 排序

### 知识图谱（LightRAG）

- 自动从文档提取实体和关系，构建知识图谱
- 支持 local / global / hybrid 三种查询模式
- 三路并行检索：Memory + LightRAG + Knowledge

### 三层蒸馏

| 层级 | 输入 | 输出 | 触发方式 |
|------|------|------|---------|
| Layer 1 | 聊天消息 | Memory（分类存储） | 导入时自动 |
| Layer 2 | Episodic Memory | Semantic Memory（按类型分组蒸馏） | 手动触发 |
| Layer 3 | Semantic Memory | PersonaProfile（人格画像） | 手动触发 |

### 其他

- **异步导入**：后台队列处理大文件，支持任务状态查询
- **时间线**：Event + Memory 合并按时间排序，分页浏览
- **多 LLM 支持**：MiMo / DeepSeek / ChatGPT / 自定义（兼容 OpenAI 格式）
- **单 API Key**：只需配置一个 LLM 提供商，Embedding 由本地 Ollama 处理（Full 模式）

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd digital-self
```

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env，至少配置一个 LLM 提供商的 API Key
```

最简配置（仅需一个 API Key）：

```env
ACTIVE_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxx
EMBEDDING_MODE=lite
```

### 3. 安装依赖并启动

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端（新终端）
cd frontend
npm install
npm run dev
```

### 4. 访问应用

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 5. 启用 Full 模式（可选）

1. 安装 [Ollama](https://ollama.com)
2. 在设置页面将检索模式切换为 "Full"
3. 点击"检查 Ollama 并下载模型"
4. 系统自动下载 bge-m3 模型（约 2GB，仅首次）

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Next.js 14 + TypeScript + Tailwind CSS |
| 后端 | FastAPI + SQLAlchemy + Alembic |
| 数据库 | SQLite（本地）/ PostgreSQL（部署） |
| 向量检索 | Qdrant + Ollama bge-m3（Full 模式） |
| 文本检索 | TF-IDF（Lite 模式，内置） |
| 知识图谱 | LightRAG（lightrag-hku） |
| LLM | MiMo / DeepSeek / OpenAI / 自定义 |
| 部署 | Docker Compose |

## API 端点

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/` | 对话（三路检索 + LLM） |
| POST | `/api/v1/chat/rag/search` | 仅检索不回答 |

### 记忆

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/memory/?skip=0&limit=50` | 分页获取 |
| POST | `/api/v1/memory/` | 创建记忆 |
| POST | `/api/v1/memory/search` | 语义搜索 |
| POST | `/api/v1/memory/distill` | Layer 2 分类蒸馏 |
| POST | `/api/v1/memory/distill/persona` | Layer 3 人格构建 |
| GET | `/api/v1/memory/distill/persona` | 查询人格画像 |
| POST | `/api/v1/memory/dedup` | 批量去重 |

### 数据导入

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/sync/import/{source}` | 同步导入 |
| POST | `/api/v1/sync/import/{source}/async` | 异步导入 |
| GET | `/api/v1/sync/tasks` | 所有任务状态 |
| GET | `/api/v1/sync/tasks/{task_id}` | 单个任务状态 |

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/knowledge/?skip=0&limit=50` | 分页获取 |
| POST | `/api/v1/knowledge/upload` | 上传文档（写入 LightRAG） |
| POST | `/api/v1/knowledge/search` | 语义搜索 |

### 设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/settings/` | 获取配置 |
| POST | `/api/v1/settings/` | 更新配置 |
| GET | `/api/v1/settings/providers` | 可用 LLM 提供商 |
| POST | `/api/v1/settings/check-ollama` | 检查 Ollama 状态 |

## 配置项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ACTIVE_PROVIDER` | `mimo` | LLM 提供商：mimo / deepseek / openai / custom |
| `MIMO_API_KEY` | - | MiMo API 密钥 |
| `DEEPSEEK_API_KEY` | - | DeepSeek API 密钥 |
| `OPENAI_API_KEY` | - | OpenAI API 密钥 |
| `CUSTOM_API_BASE` | - | 自定义 API 地址（兼容 OpenAI 格式） |
| `CUSTOM_API_KEY` | - | 自定义 API 密钥 |
| `CUSTOM_MODEL` | - | 自定义模型名称 |
| `EMBEDDING_MODE` | `lite` | 检索模式：lite（TF-IDF）/ full（Ollama 向量） |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `QDRANT_ENABLED` | `false` | 是否启用 Qdrant 向量库 |
| `LIGHTRAG_ENABLED` | `true` | 是否启用 LightRAG 知识图谱 |

## 项目结构

```
digital-self/
├── frontend/                    # Next.js 前端
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py        # 全局配置
│   │   │   └── database.py      # 数据库连接
│   │   ├── models/
│   │   │   └── models.py        # ORM 模型（11 种 MemoryType）
│   │   ├── services/
│   │   │   ├── embedding/       # EmbeddingService（Lite/Full 双模式）
│   │   │   ├── memory/          # 记忆管理 + 去重
│   │   │   ├── lightrag/        # LightRAG 知识图谱
│   │   │   ├── rag/             # 三路检索 + TF-IDF
│   │   │   ├── queue/           # 异步任务队列
│   │   │   ├── distill/         # 三层蒸馏
│   │   │   ├── sync/            # 导入分流 + LLM 分类
│   │   │   └── llm/             # 多 Provider LLM 客户端
│   │   └── api/v1/endpoints/    # REST API
│   ├── alembic/                 # 数据库迁移
│   └── requirements.txt
├── data/                        # 数据目录
│   └── lightrag/                # LightRAG 知识图谱数据
└── docker-compose.yml
```

## License

MIT
