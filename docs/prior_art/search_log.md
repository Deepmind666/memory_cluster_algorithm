# Prior-Art Search Log

检索日期：2026-02-09

## 检索策略
- 主题 A：语义聚类 + 对话/语料主题归并
- 主题 B：可控摘要 + 偏好驱动摘要
- 主题 C：多 Agent 共享记忆与跨代理访问
- 主题 D：分层记忆与记忆管理工作流

## 关键词记录
1. `semantic clustering conversational agent patent`
2. `controllable summarization user preference patent`
3. `shared memory vectors conversational agents patent`
4. `multi-agent memory management framework`
5. `ConversationSummaryBufferMemory`
6. `agent memory conflict resolution`
7. `CNIPA AI algorithm technical effect`

## 结果条目（节选）
- US20110238408A1: https://patents.google.com/patent/US20110238408A1/en
- US12008332B1: https://patents.google.com/patent/US12008332B1/en
- US20240289863A1: https://patents.google.com/patent/US20240289863A1/en
- US11941378B1: https://patents.google.com/patent/US11941378B1/en
- US20250130778A1: https://patents.google.com/patent/US20250130778A1/en
- US11941373B2: https://patents.google.com/patent/US11941373B2
- US20250165890A1: https://patents.google.com/patent/US20250165890A1/en
- CN119917107A: https://patents.google.com/patent/CN119917107A/en
- PerfCodeGen: https://arxiv.org/abs/2412.03578
- POLO (IJCAI 2025): https://www.ijcai.org/proceedings/2025/814
- ECO: https://openreview.net/forum?id=KhwOuB0fs9
- EffiLearner: https://openreview.net/forum?id=R5L1TD1Z58
- SWE-Perf: https://openreview.net/forum?id=KxFaKvtBiG
- LangChain ConversationSummaryBufferMemory: https://api.python.langchain.com/en/latest/langchain/memory/langchain.memory.summary_buffer.ConversationSummaryBufferMemory.html
- Google ADK Context: https://google.github.io/adk-docs/context/
- SEDM: https://arxiv.org/abs/2509.09498
- LatentMem: https://arxiv.org/abs/2602.03036

## 初步结论
- “语义聚类”“可控摘要”“共享记忆”均已有公开，单点写法风险高。
- 可绕开空间应落在“多 Agent 异构碎片 + 冲突显式化 + 偏好策略向量 + 可逆 backrefs”的组合闭环。
