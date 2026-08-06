# RAG 接口 — 检索增强生成抽象

> 属于 [确定性工作流框架 — 高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖：RAG 能力的框架级接口。采用主流方案的接口设计；不做实现讨论。

---

## 更新日志

| 日期 | 版本 | 变更 |
|------|---------|---------|
| 2026-06-18 | 0.1.0 | 初始 RAG 接口规范 — Document、DocumentStore、Embedder、Retriever、RAGPipeline |

---

## 1. 角色

RAG 是框架中的横向基础设施服务：

```
Layer 1 (NLU/Extract)  ──→  实体解析、知识查询
Layer 3 (Response)      ──→  LLM 生成的上下文增强
                                │
                    ┌───────────┴───────────┐
                    │     RAG 接口           │
                    │  （本规范）             │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
         Haystack          LlamaIndex         LangChain
        （参考设计）        （适配器）          （适配器）
```

框架仅定义**接口**。后端实现来自现有开源方案。本规范不设计新的 RAG 引擎——它采用生态系统中经过验证的接口。

### 设计原则

1. **采纳，不发明。** 接口以 Haystack 的协议设计为参考（关注点分离最清晰），结合 LangChain 的 Runnable 组合模式。
2. **可插拔后端。** 同一接口可由 Haystack、LlamaIndex、LangChain 或自定义实现支撑。
3. **基于 Protocol 的类型定义。** 所有接口使用 `Protocol` 类——任何符合方法签名的对象都是有效实现。
4. **查询与文档嵌入分离。** `TextEmbedder`（查询端）和 `DocumentEmbedder`（文档端）是不同的接口，防止常见的不对称查询/文档处理陷阱。

---

## 2. 接口契约

### 2.1 Document

通用数据单元。以 Haystack 的 `Document` 为参考，支持稀疏嵌入。

```python
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class Document:
    """RAG 系统中的单个文档。"""
    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None          # 稠密向量
    sparse_embedding: Optional[dict[int, float]] = None  # 稀疏（BM25）向量
    score: Optional[float] = None                     # 由检索器/重排器赋值

@dataclass
class RetrievedDocument:
    """检索器返回的文档，带相关性分数。"""
    document: Document
    score: float
```

### 2.2 DocumentStore

文档的持久存储和管理。以 Haystack 的 `DocumentStore` 协议为参考。

```python
from typing import Protocol, Optional

class DocumentStore(Protocol):
    """文档存储后端的协议。

    后端示例：
        - Haystack：InMemoryDocumentStore、ElasticsearchDocumentStore、WeaviateDocumentStore
        - LlamaIndex：VectorStoreIndex（封装向量数据库）
        - LangChain：VectorStore 实现（FAISS、Chroma、Pinecone 等）
    """

    def count_documents(self) -> int:
        """返回存储中的文档总数。"""
        ...

    def write_documents(self, documents: list[Document], policy: str = "replace") -> int:
        """将文档写入存储。返回写入的文档数。

        policy："replace"（覆盖重复）| "skip"（忽略重复）| "fail"（重复时抛出异常）
        """
        ...

    def delete_documents(self, document_ids: list[str]) -> None:
        """按 ID 删除文档。"""
        ...

    def filter_documents(self, filters: Optional[dict[str, Any]] = None) -> list[Document]:
        """返回匹配元数据过滤条件的文档。

        filters：例如 {"field": "product", "operator": "==", "value": "home_insurance"}
        """
        ...

    def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """按 ID 检索单个文档。"""
        ...
```

### 2.3 Embedder

**显式分离**查询端和文档端嵌入——以 Haystack 的 `TextEmbedder` / `DocumentEmbedder` 区分设计为参考。

```python
from typing import Protocol

class TextEmbedder(Protocol):
    """将单个查询字符串嵌入为向量。

    后端示例：
        - Haystack：SentenceTransformersTextEmbedder、OpenAITextEmbedder
        - LlamaIndex：HuggingFaceEmbedding、OpenAIEmbedding
        - LangChain：OpenAIEmbeddings、HuggingFaceEmbeddings
    """

    def embed(self, text: str) -> list[float]:
        """嵌入查询字符串。返回稠密向量。"""
        ...


class DocumentEmbedder(Protocol):
    """将一批文档嵌入为向量。嵌入存储在 Document.embedding 中。

    后端示例：
        - Haystack：SentenceTransformersDocumentEmbedder、OpenAIDocumentEmbedder
        - LlamaIndex：HuggingFaceEmbedding（通过 _get_text_embeddings）
        - LangChain：OpenAIEmbeddings（通过 embed_documents）
    """

    def embed(self, documents: list[Document]) -> list[Document]:
        """原地嵌入文档。返回已填充 .embedding 的文档。"""
        ...
```

> **为什么要分离？** 某些模型对短查询和长文档使用不同的编码策略（例如非对称双编码器、指令微调嵌入）。单一的 `Embeddings` 类通过 `embed_query`/`embed_documents` 隐藏了这种不对称性。显式分离在类型层面使这种区分不可忽视。

### 2.4 Retriever

查询 → 相关文档。以 Haystack 的检索器组件 + LangChain 的 `BaseRetriever` 为参考。

```python
from typing import Protocol, Optional

class Retriever(Protocol):
    """为查询检索相关文档。

    后端示例：
        - Haystack：InMemoryEmbeddingRetriever、InMemoryBM25Retriever
        - LlamaIndex：VectorIndexRetriever、BM25Retriever
        - LangChain：VectorStoreRetriever、MultiQueryRetriever
    """

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[RetrievedDocument]:
        """检索查询的前 k 个相关文档。

        query：   自然语言查询字符串
        top_k：   返回的文档数
        filters： 可选的元数据过滤条件
        """
        ...


class Reranker(Protocol):
    """对检索到的文档进行重排以提升相关性。

    后端示例：
        - Cohere Rerank API、Jina Reranker API
        - HuggingFace cross-encoder 模型（BGE-reranker 等）
        - rerankers 库（多提供商的统一接口）
    """

    def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        """重排文档并返回前 k 个。文档返回时带有更新后的分数。"""
        ...
```

### 2.5 RAG Pipeline

检索 → 增强 → 生成的组合。以 LangChain 的 `Runnable` 协议（函数式管道组合）为参考。

```python
from typing import Protocol, Any

class RAGPipeline(Protocol):
    """一次性 RAG 执行：检索 + 增强 + 生成。

    这是 Layer 3（Response Generation）消费的主要接口。
    管道组合 Retriever（可选 Reranker）+ LLM Generator 以生成上下文感知的回复。

    后端示例：
        - Haystack：RAG Pipeline（自定义组件 DAG）
        - LlamaIndex：QueryEngine（retriever + response_synthesizer）
        - LangChain：create_retrieval_chain（retriever | prompt | llm）
    """

    def query(
        self,
        prompt: str,
        top_k: int = 5,
        filters: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> RAGResult:
        """执行 RAG：检索上下文、增强提示词、生成回复。

        prompt：  用户查询或提示词模板
        top_k：   检索的文档数
        filters： 检索的元数据过滤条件
        kwargs：  后端特定参数（temperature、model override 等）
        """
        ...


@dataclass
class RAGResult:
    """RAG 管道执行结果。"""
    response: str                              # 生成的文本
    sources: list[RetrievedDocument]            # 用作上下文的文档
    metadata: dict[str, Any] = field(default_factory=dict)  # 后端特定元数据
```

---

## 3. 集成点

### 3.1 与 Layer 3（Response Generation）集成

```
ResponseGenerator
    │
    ├─ intent == "ask_question"  ──→  RAGPipeline.query(prompt)
    │                                    │
    │                                    ├─ Retriever.retrieve(query)
    │                                    ├─ [可选] Reranker.rerank(query, docs)
    │                                    └─ LLM.generate(augmented_prompt)
    │
    └─ 其他意图  ──→  非 RAG 响应路径
```

### 3.2 配置

```yaml
# framework.yaml — RAG 后端选择
rag:
  backend: "haystack"          # haystack | llamaindex | langchain | custom
  document_store:
    type: "elasticsearch"      # elasticsearch | weaviate | chroma | etc.
  embedder:
    model: "text-embedding-3-small"
    provider: "openai"         # openai | huggingface | cohere
  retriever:
    type: "embedding"          # embedding | bm25 | hybrid
    top_k_default: 10
  reranker:
    enabled: true
    provider: "cohere"         # cohere | jina | huggingface | none
  pipeline:
    max_context_length: 4000   # 检索上下文的最大 token 数
```

---

## 5. 本规范不涵盖的内容

- **任何 RAG 后端的实现。** 本规范定义接口。后端由采纳团队选择和配置。
- **嵌入模型选择或基准测试。** 团队根据其准确率/成本/延迟需求选择模型。
- **向量数据库操作。** 分块策略、索引和存储优化是后端关注的问题。
- **高级 RAG 模式**（HyDE、self-query、parent-document retrieval 等）。这些通过后端的原生 API 暴露，而非框架接口。
- **RAG 评估或质量指标。** 由可观察性/监控规范和 CI/CD 评估管道覆盖。

---

## 参考资料

- [Haystack 文档](https://docs.haystack.deepset.ai/) — `DocumentStore`、`TextEmbedder`/`DocumentEmbedder` 分离的参考设计
- [LangChain RAG 教程](https://python.langchain.com/docs/tutorials/rag/) — `Runnable` 组合模式
- [LlamaIndex RAG 指南](https://docs.llamaindex.ai/en/stable/understanding/rag/) — 丰富的数据模型（`Node` / `QueryBundle`）
- [rerankers 库](https://github.com/AnswerDotAI/rerankers) — 统一重排接口
- [高层设计](./01-deterministic-workflow-framework-design.md) — 父文档
- [LLM 网关](./14-llm-gateway.md) — LLM 调用（RAG 管道用于生成）
- [响应生成层](./08-response-generation-layer-design.md) — RAG 的主要消费者
