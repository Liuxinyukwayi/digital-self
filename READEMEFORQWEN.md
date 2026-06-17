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