# 实现方案与取舍

LangGraph 1.2.20 StateGraph 负责状态编排：agent_decide 调用真实模型并获得工具及参数，execute_tools 执行并把完整 Observation 放入 tool 消息；有终止结果进入 END，否则回到模型。程序没有按问题字符串选择 live 工具，也没有自动重试。MockModel 是独立标注的启发式模拟器，ScriptedModel 仅供异常测试。

四个工具是 search_documents、read_document、inspect_versions、submit_answer。参数经 Pydantic 校验；空结果、未知 ID、超时、无效参数均返回结构化 Observation。模型选择换 query、扩大范围、读原文、补查或停止；Guard 拒绝也交回模型。

BM25 使用中文 bigram；Dense 使用固定 revision 的实际多语 MiniLM 量化 ONNX、attention-mask mean pooling、L2 和 NumPy cosine；Hybrid RRF k=60。算法 D 从 Hybrid 候选出发，真实模型选择最多两次补查。小语料不引入向量数据库或 FAISS。

DocumentStore 每个最多 500 字符的 chunk 保留 start/end。Guard 校验 ID、chunk、版本、read-before-cite 和精确 quote；候选答案必须是引用摘录及固定状态后缀，避免真实引用伴随编造断言，facts 也须是 quote 子串。格式约束可能增加修订次数，真实 Trace 保留该代价。

冲突抽取比较数值、单位、字段、主题和 scope，日期不能证明取代。不同明确适用范围的合成员工类别不强行报冲突。复杂范围包含关系和任意自然语言冲突仍是局限。

显式 sqlite3 WAL 存储最近历史，按 mode 隔离、会话串行锁；当前轮仍须重读原文。未启用 LangGraph checkpointer，以免把上轮完整图状态和已读证据混入本轮预算。该进程内锁不解决多进程并发。

API/CLI/UI 共用 AgentService，UI 仅经真实 HTTP 取数。模型 API 不重试，HTTP 错误只记录安全错误码，不写供应商错误正文。Trace 不请求或保存隐藏思维链。达到 8/12 预算后明确返回 INCOMPLETE。
