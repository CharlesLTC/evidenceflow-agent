# 架构与职责

| 组件 | 职责 |
|---|---|
| schemas / config | 请求、文档、引用、响应契约和本机配置 |
| agent_graph / llm_client | 模型工具选择、Observation 回路、预算和真实 HTTP 适配 |
| document_store / tools | 精确原文区间、版本字段、受控错误、故障注入 |
| retriever / embeddings / query_rewrite | BM25、实际 Dense、RRF、真实模型补查 |
| claim_conflicts / evidence_guard | 数值制度冲突、已读/原文核验、摘录输出 |
| session_store / trace_writer | SQLite 隔离会话、真实步骤、脱敏与用量 |
| api / ui | 同一后端与 HTTP 客户端，无硬编码成功数据 |
| scripts | 验收、变异、消融、图表、扫描、阶段报告 |

状态保存 session_id、messages、question、loaded_evidence、search_history、observations、conflicts、validation_errors、调用计数、status、result、trace_id。只有 Guard 通过候选或明确受控失败/未完成结果返回。历史不继承本轮引用资格。

原文和工具结果是不可信数据；模型没有 shell、文件写入、发布工具，文档要求也不能获得这些能力。Trace 不保存 Authorization、供应商错误正文和隐藏推理。交付扫描对照本机已配置密钥值。

默认本机回环，未实现鉴权、限流、跨进程会话锁和生产持久审计。只使用合成材料，不应直接加入真实内部文件。
