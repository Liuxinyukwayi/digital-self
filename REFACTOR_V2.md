# Digital Self V2 重构方案

基于 LightRAG + 分层记忆架构的数字分身系统升级

---

## 一、现状问题诊断

### 当前数据流

```
聊天记录 → 5分钟聚合 → episodic memory → Hash Embedding → Qdrant → 向量检索 → LLM
```

### 8个核心问题

| # | 问题 | 影响 |
|---|------|------|
| 1 | 所有内容都是 `episodic` | 偏好/事实/目标混在一起，检索精度低 |
| 2 | 5分钟聚合策略 | "我决定去宁波" 和表情包被合并，Embedding 质量差 |
| 3 | 固定 `importance=4` | 人生规划 = 发表情包 |
| 4 | Hash Embedding | 非语义向量，召回质量极差 |
| 5 | Memory 无上限控制 | 导入 2 万条后系统变慢 |
| 6 | 无去重机制 | "喜欢宁波" 重复 100 次 = 100 条记忆 |
| 7 | 同步导入阻塞 | 大文件 OOM/超时 |
| 8 | 无人格层 | 无法形成价值观/兴趣/风格 |

---

## 二、V2 总体架构

```
                     User Query
                           │
                           ▼
                ┌─ Retrieval Orchestrator ─┐
                │                         │
     ┌──────────┼──────────┬──────────────┼─────────────┐
     ▼          ▼          ▼              ▼             ▼
 Identity   Preference  Timeline     LightRAG      Episodic
  Layer       Layer       Layer    (Knowledge)      Layer
     │          │          │              │             │
     └──────────┴──────────┴──────┬───────┴─────────────┘
                                  │
                                  ▼
                              LLM Response
```

### 核心分离原则

| 层 | 存储内容 | 检索方式 |
|---|---------|---------|
| LightRAG | 公众号/文档/PDF/技术资料 | 知识图谱 + 向量检索 |
| Memory Layer | 偏好/事实/目标/关系/经历 | 分类检索 + 评分排序 |
| Persona Layer | 价值观/兴趣/风格 | 直接加载，不走检索 |

---

## 三、记忆类型重构

### 新 MemoryType 枚举

```python
class MemoryType(str, enum.Enum):
    EPISODIC = "episodic"        # 原始经历：参加银行面试
    FACT = "fact"                # 客观事实：工作地点是宁波
    PREFERENCE = "preference"    # 偏好：喜欢宁波、喜欢AI
    OPINION = "opinion"          # 观点：低空经济潜力巨大
    GOAL = "goal"                # 目标：进入低空经济行业
    RELATIONSHIP = "relationship" # 关系：张三是大学室友
    KNOWLEDGE = "knowledge"      # 知识（文档来源）
    SEMANTIC = "semantic"        # 蒸馏后的长期记忆
    PERSONA = "persona"          # 人格画像
```

---

## 四、分阶段实施计划

### Phase 1: 记忆类型 + Embedding 升级（核心基础）

**目标**：解决最根本的存储质量问题

#### 1.1 升级 Embedding

废弃 `hashed_embedding`，接入真实 Embedding API。

**修改文件**：
- `backend/app/core/config.py` — 添加 Embedding 配置
- `backend/app/services/rag/text_index.py` — 替换 embedding 实现
- `backend/app/services/memory/memory_service.py` — 使用新 embedding
- `backend/app/services/knowledge/knowledge_service.py` — 使用新 embedding

**新依赖**（`requirements.txt`）：
```
sentence-transformers>=2.2.0   # 本地 bge-m3
# 或
openai>=1.0.0                  # API 方案
```

**Embedding 策略**（可配置）：
```python
# config.py 新增
EMBEDDING_PROVIDER: str = "local"  # local | openai | jina
EMBEDDING_MODEL: str = "BAAI/bge-m3"
EMBEDDING_DIMENSION: int = 1024    # bge-m3 输出维度
JINA_API_KEY: Optional[str] = None
```

**新 text_index.py 核心改动**：
```python
# 替换 hashed_embedding
async def get_embedding(text: str) -> List[float]:
    if settings.EMBEDDING_PROVIDER == "local":
        return await _local_embedding(text)
    elif settings.EMBEDDING_PROVIDER == "openai":
        return await _openai_embedding(text)
    elif settings.EMBEDDING_PROVIDER == "jina":
        return await _jina_embedding(text)
```

#### 1.2 扩展 MemoryType

**修改文件**：
- `backend/app/models/models.py` — 更新枚举
- `backend/alembic/versions/` — 数据库迁移脚本

**迁移策略**：
```sql
-- 现有 episodic 记忆保持不变
-- 新导入的记忆使用 LLM 分类
```

#### 1.3 导入时 LLM 分类

**修改文件**：
- `backend/app/services/sync/sync_service.py` — 添加分类步骤

**新导入流程**：
```python
async def import_messages(self, payload, user_id, source):
    messages = self._parse_messages(payload)
    chunks = self._group_into_chunks(messages)  # 保留分组，但窗口改为 3 分钟
    
    for chunk in chunks:
        content = "\n".join(chunk["lines"])
        
        # 新增：LLM 分类
        memory_type = await self._classify_content(content)
        
        # 新增：LLM 评分
        importance = await self._score_importance(content)
        
        await self.memory_service.create_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            ...
        )
```

**分类 Prompt**：
```python
CLASSIFY_PROMPT = """分析以下聊天内容，判断其类型，只返回类型名称：

fact - 客观事实陈述（工作、地点、时间等）
preference - 个人偏好（喜欢、讨厌、偏好）
opinion - 观点看法（认为、觉得、判断）
goal - 目标计划（想要、计划、目标）
relationship - 人物关系（提到某人及其关系）
episodic - 一般经历/日常对话

内容：
{content}

类型："""
```

**评分 Prompt**：
```python
SCORE_PROMPT = """评估以下内容的重要性（1-10分）：
1-2 = 闲聊/表情
3-4 = 日常对话
5-6 = 有价值信息
7-8 = 重要事实/决策
9-10 = 人生转折点

内容：
{content}

分数（只返回数字）："""
```

**预计工期**：3-4 天

---

### Phase 2: 去重 + 评分系统

**目标**：解决重复记忆和评分问题

#### 2.1 记忆去重

**新增文件**：
- `backend/app/services/memory/memory_dedup.py`

**去重逻辑**：
```python
class MemoryDedupService:
    async def check_and_merge(self, new_memory: Memory, user_id: int) -> Memory:
        # 1. 向量检索相似记忆（阈值 0.92）
        similar = await self._find_similar(new_memory, threshold=0.92)
        
        if similar and similar.memory_type == new_memory.memory_type:
            # 2. 类型相同 → 合并（更新 evidence_count）
            similar.evidence_count += 1
            similar.confidence = min(1.0, similar.evidence_count * 0.1)
            similar.last_evidence_at = datetime.utcnow()
            return similar
        else:
            # 3. 无重复 → 存为新记忆
            return await self._create_new(new_memory)
```

**新增字段**（models.py + 迁移）：
```python
class Memory(Base):
    # 现有字段...
    evidence_count = Column(Integer, default=1)    # 证据计数
    confidence = Column(Float, default=0.5)         # 置信度
    last_evidence_at = Column(DateTime)             # 最后证据时间
```

#### 2.2 综合评分公式

```python
def calculate_memory_score(memory: Memory) -> float:
    # 重要性（0-1）
    importance = memory.importance / 10.0
    
    # 置信度（基于 evidence_count）
    confidence = memory.confidence or 0.5
    
    # 新鲜度（时间衰减）
    days_old = (datetime.utcnow() - memory.created_at).days
    freshness = math.exp(-days_old / 365)
    
    return importance * confidence * freshness
```

**修改文件**：
- `backend/app/services/memory/memory_service.py` — search 使用新评分
- `backend/app/services/rag/text_index.py` — rank_documents 集成评分

**预计工期**：2 天

---

### Phase 3: LightRAG 知识层集成

**目标**：知识检索升级为知识图谱 + 向量混合检索

#### 3.1 安装 LightRAG

```bash
pip install lightrag-hku
# 或从源码
pip install -e ".[api]"
```

#### 3.2 新增知识服务

**新增文件**：
- `backend/app/services/lightrag/lightrag_service.py`

**核心实现**：
```python
from lightrag import LightRAG, QueryParam

class LightRAGService:
    def __init__(self):
        self.rag = LightRAG(
            working_dir="./data/lightrag",
            llm_model_func=self._llm_call,
            embedding_func=self._embedding_call,
        )
    
    async def insert_document(self, content: str, metadata: dict):
        """导入文档到知识图谱"""
        await self.rig.ainsert(content)
    
    async def query(self, question: str, mode: str = "hybrid") -> str:
        """混合检索：naive | local | global | hybrid"""
        return await self.rag.aquery(
            question,
            QueryParam(mode=mode)
        )
    
    async def _llm_call(self, prompt: str, **kwargs) -> str:
        """复用现有 MIMO API"""
        return await mimo_client.simple_chat(prompt)
    
    async def _embedding_call(self, texts: List[str]) -> List[List[float]]:
        """复用 Phase 1 的 embedding"""
        return [await get_embedding(t) for t in texts]
```

#### 3.3 知识导入分离

**修改文件**：
- `backend/app/services/sync/sync_service.py` — 文档类导入走 LightRAG
- `backend/app/api/v1/endpoints/knowledge.py` — 上传走 LightRAG

**导入分流**：
```python
# 聊天记录 → Memory Layer（分类存储）
# 文档/文章 → LightRAG（知识图谱）
async def import_document(content, user_id, source):
    if source in [DataSource.WECHAT, DataSource.QQ]:
        # 聊天记录 → 记忆层
        await sync_service.import_messages(content, user_id, source)
    else:
        # 文档 → LightRAG
        await lightrag_service.insert_document(content, {"source": source.value})
```

#### 3.4 检索改造

**修改文件**：
- `backend/app/services/rag/rag_service.py` — 双路检索

**新检索流程**：
```python
class RAGService:
    async def retrieve_context(self, query, user_id) -> dict:
        # 并行检索记忆层和知识层
        memories_task = self.memory_service.search_memories(query, user_id)
        knowledge_task = self.lightrag_service.query(query, mode="hybrid")
        
        memories, knowledge_context = await asyncio.gather(
            memories_task, knowledge_task
        )
        
        return {
            "memories": memories,
            "knowledge_context": knowledge_context,
            "context_text": self._build_context(memories, knowledge_context),
        }
```

**预计工期**：3-4 天

---

### Phase 4: 异步导入 + 记忆蒸馏

**目标**：解决大文件阻塞和记忆提炼问题

#### 4.1 异步导入队列

**新增文件**：
- `backend/app/services/queue/task_queue.py`
- `backend/app/services/queue/import_worker.py`

**方案选择**：

| 方案 | 复杂度 | 推荐度 |
|------|--------|--------|
| FastAPI BackgroundTasks | 低 | 小规模推荐 |
| Celery + Redis | 高 | 大规模推荐 |
| asyncio.Queue | 中 | 中等规模推荐 |

**推荐**：`asyncio.Queue`（最小改动，适合当前规模）

```python
# task_queue.py
import asyncio
from typing import Callable, Any

class TaskQueue:
    def __init__(self, max_workers: int = 3):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers = []
        self.max_workers = max_workers
    
    async def start(self):
        for _ in range(self.max_workers):
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)
    
    async def enqueue(self, func: Callable, *args, **kwargs):
        await self.queue.put((func, args, kwargs))
    
    async def _worker(self):
        while True:
            func, args, kwargs = await self.queue.get()
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"Task error: {e}")
            finally:
                self.queue.task_done()

# 全局实例
task_queue = TaskQueue()
```

#### 4.2 记忆蒸馏升级

**修改文件**：
- `backend/app/services/memory/memory_service.py` — 升级 distill

**三层蒸馏**：

```
Layer 1: Message → Memory（导入时已完成）
Layer 2: Episodic → Semantic（周度蒸馏）
Layer 3: Semantic → Persona（月度构建）
```

**Layer 2 蒸馏 Prompt**：
```python
DISTILL_PROMPT = """将以下零散经历提炼为长期记忆。
提取：关键事实、偏好、目标、重要事件。
每条记忆用一行概括，保持简洁。

经历：
{memories}

长期记忆："""
```

**Layer 3 Persona 构建**：
```python
PERSONA_PROMPT = """基于以下长期记忆，构建用户人格画像。
输出 JSON 格式：
{
  "interests": ["兴趣1", "兴趣2"],
  "values": ["价值观1", "价值观2"],
  "goals": ["目标1", "目标2"],
  "speech_style": ["口头禅1", "口头禅2"],
  "thinking_style": "思维风格"
}

长期记忆：
{semantic_memories}

人格画像："""
```

**预计工期**：2-3 天

---

### Phase 5: Retrieval Orchestrator

**目标**：智能路由检索，根据问题类型动态分配权重

**新增文件**：
- `backend/app/services/rag/retrieval_orchestrator.py`

```python
class RetrievalOrchestrator:
    async def retrieve(self, query: str, user_id: int) -> dict:
        # 1. 分析查询意图
        intent = await self._classify_intent(query)
        
        # 2. 根据意图分配检索权重
        weights = self._get_weights(intent)
        
        # 3. 并行检索各层
        results = await self._parallel_retrieve(query, user_id, weights)
        
        # 4. 合并排序
        return self._merge_and_rank(results, weights)
    
    def _get_weights(self, intent: str) -> dict:
        configs = {
            "personal": {"memory": 0.6, "knowledge": 0.2, "timeline": 0.2},
            "knowledge": {"memory": 0.2, "knowledge": 0.7, "timeline": 0.1},
            "history": {"memory": 0.3, "knowledge": 0.1, "timeline": 0.6},
            "general": {"memory": 0.4, "knowledge": 0.4, "timeline": 0.2},
        }
        return configs.get(intent, configs["general"])
```

**预计工期**：2 天

---

## 五、数据库变更汇总

### 新增/修改字段

```sql
-- Memory 表新增
ALTER TABLE memories ADD COLUMN evidence_count INTEGER DEFAULT 1;
ALTER TABLE memories ADD COLUMN confidence FLOAT DEFAULT 0.5;
ALTER TABLE memories ADD COLUMN last_evidence_at TIMESTAMP;

-- MemoryType 枚举扩展
ALTER TYPE memorytype ADD VALUE 'fact';
ALTER TYPE memorytype ADD VALUE 'preference';
ALTER TYPE memorytype ADD VALUE 'opinion';
ALTER TYPE memorytype ADD VALUE 'goal';
ALTER TYPE memorytype ADD VALUE 'relationship';

-- 新增 raw_messages 表（可选，保留原始消息）
CREATE TABLE raw_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    source VARCHAR(50),
    sender VARCHAR(100),
    content TEXT,
    message_time TIMESTAMP,
    chunk_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 新增 persona_profiles 表
CREATE TABLE persona_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    version INTEGER DEFAULT 1,
    interests JSONB,
    values JSONB,
    goals JSONB,
    speech_style JSONB,
    thinking_style VARCHAR(100),
    summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 六、新增依赖

```txt
# requirements.txt 新增
lightrag-hku>=0.1.0          # LightRAG 知识图谱
sentence-transformers>=2.2.0  # 本地 Embedding (bge-m3)
openai>=1.0.0                 # API Embedding (可选)
tiktoken                      # token 计算
neo4j>=5.0.0                  # 知识图谱存储（LightRAG 可选后端）
```

---

## 七、实施时间线

```
Phase 1: 记忆类型 + Embedding 升级    [3-4 天]  ← 最关键
Phase 2: 去重 + 评分系统              [2 天]
Phase 3: LightRAG 知识层集成          [3-4 天]
Phase 4: 异步导入 + 蒸馏升级          [2-3 天]
Phase 5: Retrieval Orchestrator       [2 天]
─────────────────────────────────────────────
总计                                  12-15 天
```

---

## 八、验证标准

### Phase 1 验证
- [ ] 导入聊天记录后，记忆有正确的 memory_type（非全部 episodic）
- [ ] Embedding 从 hash 升级为真实语义向量
- [ ] 语义搜索结果质量明显提升

### Phase 2 验证
- [ ] "喜欢宁波" 出现 10 次只保留 1 条，evidence_count=10
- [ ] 搜索结果按 importance * confidence * freshness 排序

### Phase 3 验证
- [ ] 文档导入走 LightRAG，聊天记录走 Memory
- [ ] 检索时两路结果正确合并

### Phase 4 验证
- [ ] 大文件导入不阻塞主进程
- [ ] 蒸馏正确生成 semantic 记忆和 persona

### Phase 5 验证
- [ ] 问"为什么喜欢宁波"→ 偏好层权重高
- [ ] 问"什么是低空经济"→ 知识层权重高
