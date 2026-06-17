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

### 1. 克隆并启动

```bash
git clone https://github.com/Liuxinyukwayi/digital-self.git
cd digital-self
启动start.bat
```

### 2. 访问应用

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000

### 3. 启用 Full 模式（可选）

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
