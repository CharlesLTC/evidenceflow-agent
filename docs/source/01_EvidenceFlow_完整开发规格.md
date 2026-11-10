# EvidenceFlow — 企业制度知识问答 Agent｜完整开发规格与逐阶段验收方案

> 项目类型：Agent 项目考核，选择「题目 3：企业知识问答 Agent」。
> 目标：构建一个真实模型驱动、可观察、可证据追溯、可测试复现的企业制度问答系统；在基础合规后增加检索优化、冲突推理、自动评估、API 与可视化。
> 交付策略：**先做满足考核的 MVP，再逐层增强；每阶段自动验收，不通过修复；最终才创建 GitHub 仓库并推送。**
> 说明：本文是 Codex 的执行规格，不是声称已经完成实现。所有运行结果、通过率、性能数字必须由实际执行产生。

---

## 0. 项目原则与考核硬约束

原题通用要求：建议投入约 3 小时，重点是可运行项目与测试证据；界面、线上部署、多 Agent、生产级 Runtime 均非必要。CLI / HTTP API / Notebook 至少一种必须可运行；GitHub 仓库提交题号、URL 与最终 commit SHA。原题题目 3 的必验项目：①明确答案；②文档冲突；③资料外问题；④改写后的相似问题；⑤上下文追问；⑥工具失败。

**否决性缺陷（必须避免）**
1. 只做条件分支、预设流程或自动重试，冒充模型自主决定下一动作。
2. 输出无证据支持的制度内容、伪造引用，或出现冲突时未经证据证明就选定一个版本。
3. Mock 记录伪装成真实模型调用记录；未运行测试却报告「PASS」。
4. 达到循环/工具调用上限时没有明确未完成状态。
5. 真实 API 密钥、用户隐私、内部资料进入 GitHub 仓库。
6. UI 成功图示与实际后端结果不一致，工具失败时显示成功。

**开发优先级**：P0 核心 ReAct → P0 六项验收 → P1 检索/冲突增强 → P1 自动评估 → P2 UI/API → P2 进阶优化 → GitHub 最终交付。不要为了追求丰富功能牺牲硬性验收。

## 1. 背景、业务对象和价值

### 1.1 业务背景

企业内的差旅、请假、设备申领、IT 支持等知识通常分散在 FAQ、制度文件和不同版本的通知中。传统关键词搜索难以回答员工口语化提问；普通 RAG 容易只返回检索到的第一个片段、忽视冲突规则和适用范围；出现文档更新、工具报错或资料缺失时，模型可能仍生成确定性回答。考核要求实现具备「工具观察→重新选择动作」的 Agent，以给出有依据且可靠的答复。

### 1.2 用户和典型情形

- 员工：询问「电脑申领多久批准」「差旅费多久报销」；希望快速获得明确答案或知道该向谁确认。
- 运营/人事/IT 管理员（仅模拟身份）：检查引用来源、文档版本、冲突和知识缺口。
- 评审人员：修改合成文档、注入一次工具异常、改写问题后，观察 Agent 是否调整工具选择与最终答复。

### 1.3 可交付的业务价值

1. **准确性**：每个确定性制度事实都能回溯到文档 ID 和真实原文片段。
2. **稳健性**：证据不足/互相冲突/工具失败时，不造答案，不虚报成功。
3. **自主性**：模型根据工具 Observation 自主选择重新检索、读取、补查、终止。
4. **可解释性**：Trace 留存可观察步骤、工具输入输出和简短决策依据，不公开内部思维链。
5. **可复现性**：提供全套用例、自动化脚本、原始结果和分析，评审可以复跑。

## 2. 最终产品形态与成功标准

**产品形态**：命令行是稳定评审入口；FastAPI 提供 `/health`、`/ask`、`/sessions/{id}`、`/traces/{id}`、`/metrics`；Streamlit 是可选的演示面板。不要将 API/UI 作为核心 Agent 能运行的前提。

**主界面建议分为**：左侧对话历史与问题输入；中间结构化回答、制度引用和冲突警告；右侧「决策时间线」与工具调用详情；底部检索排名/测试指标。UI 的所有内容来自后端真实数据。

**输出 JSON 契约**（字段可扩展，含义不得变更）：

```json
{
  "question": "差旅报销期限是多久？",
  "answer": "D01记载30天，D02记载15天。由于适用范围和效力关系尚未明确，当前无法确认唯一有效期限。",
  "status": "NEEDS_CLARIFICATION",
  "citations": [
    {"doc_id": "D01", "version_date": "2025-01-01", "quote": "差旅报销应在30天内提交。", "chunk_id": "D01-C01"},
    {"doc_id": "D02", "version_date": "2025-07-01", "quote": "差旅报销应在15天内提交。", "chunk_id": "D02-C01"}
  ],
  "missing_info": ["两份制度的适用范围及优先级"],
  "conflicts": [{"field": "差旅报销期限", "documents": ["D01", "D02"], "values": ["30天", "15天"], "resolution": "UNRESOLVED"}],
  "steps_used": 5,
  "tool_calls_used": 5,
  "trace_id": "...",
  "mode": "live"
}
```

以上为**目标结构示例**，不是实际执行输出。`status` 枚举为 `COMPLETED`、`NEEDS_CLARIFICATION`、`INSUFFICIENT_EVIDENCE`、`FAILED`、`INCOMPLETE`；离线模式必须有 `mode=mock` 标记。

**完成定义**：原题六项验收全部有真实输出和 Trace；至少两条真实 live 路径体现因工具返回不同而改变决策；自动化单测/集成测试均通过；README 一键复现；GitHub URL、最终 SHA 可核验。模型服务不可用时，必须明确列出 live 阻断项，不能宣布完整达标。

## 3. 总体技术架构

```text
                 CLI                  FastAPI                Streamlit
                  |                      |                       |
                  +----------------------+-----------------------+
                                         |
                               Request / Session Service
                                         |
                          LangGraph StateGraph Orchestrator
                                         |
                           [LLM DECIDE] <-------------------+
                              |    ^                         |
                  model ToolCalls   Tool Observation         |
                              v    |                         |
                           [Tool Executor]                   |
                           /       |       \                |
             search_documents  read_document  inspect_versions
                   |             |              |
            BM25 + Dense       原文/元数据      版本与适用范围
                   \             |              /
                    +----- Evidence Store ------+
                              |
                    Conflict / Claim Analyzer
                              |
                  Answer Draft -> Evidence Guard
                              |      | (校验失败)
                         通过 |      +-----------------------+
                              v
                  Structured Output + Trace + Metrics
```

**架构边界**：LLM决定下一步调用哪个工具、参数和何时结束；检索器执行排名，文档读取器返回原文；程序化 Guard 强制检查引用是否真实、是否读过、是否存在未解决冲突，且不能被提示词跳过。Guard 失败作为可观察结果返回给模型，让它修订或补查。框架只负责编排与状态，不将所有规则硬编码成固定调用序列。

### 3.1 技术选型

| 层 | 默认选型 | 理由 / 退路 |
|---|---|---|
| 开发环境 | Python 3.11 / 3.12，Windows PowerShell | 优先选择依赖兼容较成熟的环境；如本机 3.13 可运行则无需降级 |
| 模型 | OpenAI-compatible Tool Calling 模型，基于环境变量配置 | 允许替换模型；live 必须真调用；无密钥可测 mock |
| 工作流 | LangGraph 1.x `StateGraph` + ToolNode/自定义工具执行 | 可检查状态、工具结果、循环边界；不使用已弃用 `langgraph.prebuilt.create_react_agent` |
| 检索 | BM25 + 多语/中文 Embedding + RRF | 有明确消融实验对象；小规模数据可用 NumPy 余弦，不强制部署向量数据库 |
| 证据 | JSON/JSONL + 文档 ID、版本、原文 span | 文件可读、可重现、易变异测试 |
| 会话 | LangGraph checkpointer（优先 SQLite，可退回内存） | 支持上下文追问，持久化是增强项 |
| 服务 | FastAPI + Pydantic | API 契约与自动 OpenAPI 文档 |
| 界面 | Streamlit | Python 快速可视化 |
| 测试 | pytest，httpx/TestClient，故障注入 | 单测/集成/端到端分层，避免依赖网络 |
| 工程 | pyproject.toml、.env.example、ruff（可选） | 安装与运行清楚，减少环境歧义 |

依赖选择原则：允许调整具体包，但必须固定兼容版本并写入 lock/requirements；必须记录改变原因。若 FAISS 在 Windows 环境安装困难，改用 NumPy dense cosine，**不能因此删除语义检索评估**。

## 4. 从输入到输出：完整业务执行链路

1. **读取请求**：接收问题、session_id、可选历史、模式、执行上限；检查空问题和非法参数；产生唯一 trace_id。目的：所有入口一致和可审计。
2. **理解问题与选择动作**：LLM观察历史与当前上下文，调用 `search_documents`、`read_document`、`inspect_versions` 或 `submit_answer`。目的：真实自主决策，而非写死调用顺序。
3. **检索候选制度**：对 query 归一化与分词；BM25 计算字面相关性，Embedding 计算语义相似度，RRF 合并候选，返回文档 ID、片段、版本、分数。目的：适配口语改写并发现可能冲突的多个版本。
4. **读取可信证据**：模型按需要读取原文段落；记录已读取的 doc_id/chunk_id、版本和引用字符串。目的：防止只基于摘要生成答案。
5. **识别冲突和缺口**：抽取候选 Claim（主题、属性、值、单位、适用范围、生效日期、文档 ID），比较同一事实域下不兼容的值；不明确优先级时标记 `UNRESOLVED`。目的：不武断选新版本。
6. **动态补查**：当结果不充分、存在冲突、工具错误或证据校验失败时，将 Observation 提交给 LLM，模型决定更换查询、扩大 top_k、读取其他文档、询问用户或停止。目的：满足 ReAct 验收。
7. **生成候选答复**：模型调用 `submit_answer`，包含结构化状态、事实性陈述、每条引用及缺失信息。目的：结构化接口统一。
8. **证据安全门**：程序核验引用 ID存在、引用过的文档被读过、quote为对应版本原文真子串、断言可对应证据；未解决的冲突不能给出单一确定答案。失败作为 Observation 回到 Agent，仍受上限保护。目的：将可靠性约束放在模型之外。
9. **落盘并返回**：写入 `examples/traces/live/` 或 `.../mock/` 和输出 JSON；前端/API展示同一个返回结构。目的：实际结果可复核。

### 4.1 工具契约

- `search_documents(query: str, top_k: int=5, strategy: str='hybrid')`：返回 `query, strategy, hits[{doc_id, chunk_id, title, version_date, score, preview}], error?`；允许空结果；首次失败由故障注入开关控制。
- `read_document(doc_id: str, chunk_ids: list[str]|None=None)`：返回真实原文、版本、适用范围、引用区间；不允许模型使用不存在的文档编号。
- `inspect_versions(topic: str)`：返回同一主题已知版本、效力和适用范围字段，缺失保留 null；不可假设较新必然有效。
- `submit_answer(answer, status, citations, missing_info)`：终止候选动作，经 Guard 通过才结束；引用校验不通过、冲突未解决却给确定结论时拒绝并返回结构化错误。

注意：`detect_conflicts`/`validate_evidence` 可以是确定性内部服务，也可以作为模型可选择的附加工具。但**至少模型需要真的自主选择检索、读取、补查与结束**，不能仅让规则引擎自动选择工具。

### 4.2 LangGraph 状态及执行限制

最低 State 字段：`session_id`、`messages`、`question`、`loaded_evidence`、`search_history`、`observations`、`conflicts`、`validation_errors`、`tool_calls_used`、`model_steps_used`、`status`、`result`、`trace_id`。每次工具执行后回到模型决策节点。默认最多 `8` 次模型决策、`12` 次工具调用，达到任一上限立即返回 `INCOMPLETE` 与原因；不允许无限自检或重试。需确保并行多个 tool_calls 计数准确。

### 4.3 可靠性与安全边界

- 文档、搜索结果、工具返回均视为不可信数据：即使片段出现「忽略以上指令」也不能改变 System/Developer 的规则。
- 冲突处理需区分**不同适用范围**与**同一适用范围的不一致**，不要把所有不同数值都当成冲突。
- 不应仅靠 LLM 的自报置信度决定“已验证”；必须有可追溯引用和确定性 Guard。
- 失败注入（空结果、超时、异常、无效 doc_id）要作为真实的工具 Observation；模型的下一步由其自主决定，不能按用例编号选择重试。
- 记录可观察决策依据摘要，**不要求、不输出模型隐藏推理链**。
- API key、请求 token、完整私有输入不能出现在公开 Trace/日志里；本项目只用合成材料。

## 5. 数据集设计与评估基准

### 5.1 首批最小知识库（MVP 5～8 篇）

D01：差旅报销制度 A，提交期限 30 天；D02：差旅报销制度 B，提交期限 15 天；两者未明确适用范围/优先级。D03：办公电脑申领，主管审批后 3 个工作日内完成；D04：IT 设备维修，IT 工单处理；D05：请假制度；D06：新员工培训；D07：访客管理；D08：采购申请。

每条必须包含 `doc_id, title, version_date, effective_date|null, scope|null, status, content`；较长内容用 chunk ID 保留原文 offset。**D01/D02 不可在数据里暗藏“最新自动覆盖旧版”的规则**，避免破坏冲突验收。

### 5.2 扩展数据（增强阶段）

合成 25～40 篇合理制度/FAQ，其中加入同义改写、不同适用范围、历史版本、矛盾值、缺失规定、带恶意提示的无害测试文本。每篇文档保持事实自洽；建立 `data/eval_questions.jsonl`，每条包含 `id, question, category, expected_doc_ids, expected_status, expected_facts, answerability, optional_history`。扩展题目 30～50 问，其中覆盖六个官方场景。

### 5.3 官方六项必验及附加用例

| ID | 场景/输入 | 期望状态 | 强制断言 |
|---|---|---|---|
| TC01 | 「办公电脑申领审批需要多久？」 | COMPLETED | 包含3个工作日、D03、正确原文 quote |
| TC02 | 「差旅报销期限是多久？」 | NEEDS_CLARIFICATION | D01/D02 两种期限均呈现，不擅自选一 |
| TC03 | 「公司的年终奖金是多少？」 | INSUFFICIENT_EVIDENCE | 不编造金额，不使用错误引用 |
| TC04 | 「领电脑一般几天能批下来？」 | COMPLETED | 相似改写仍命中 D03，准确答复 |
| TC05 | 先问「电脑怎么申领？」再问「那多久批下来？」 | COMPLETED | 同一session正确继承「电脑申领」上下文 |
| TC06 | 首次检索工具注入超时/错误 | COMPLETED或FAILED | Trace必须有错误Observation及模型之后的真实决策，不能虚报成功 |
| TC07 | D03文档变异：3工作日→5工作日 | COMPLETED | 不改模型提示词/代码，答案与引用同步变化 |
| TC08 | 注入错误 doc_id 或伪造 quote | 校验拒绝 | Guard必须阻断并返回可解释错误 |
| TC09 | 超过执行上限 | INCOMPLETE | 不再执行额外工具，明确原因 |
| TC10 | 同一主题不同员工类别 | 按证据 | 不把合法差异误报为制度冲突 |
| TC11 | 知识片段包含提示注入文本 | 按证据 | 系统指令、工具访问、引用规则不被覆盖 |
| TC12 | 第二次调用工具仍失败 | FAILED或INCOMPLETE | 明确故障与已知状态，追踪日志无假成功 |

**TC06** 不要求一定成功恢复：允许明确停止，但必须出现“模型读到失败结果并自主决定下一动作”，且已成功步骤不可伪装为失败。强制对比 TC01 正常检索与 TC06 故障注入后的动作。

## 6. 实验设计和测量指标

### 6.1 检索算法对比

- A：BM25（必要时 jieba 中文分词）
- B：Dense（中文/多语 Embedding + cosine）
- C：BM25 + Dense，RRF 融合，默认 `k=60`
- D：C + 模型驱动的 Query Rewrite/补查（计入模型调用成本）

**检索指标**：Recall@3、Recall@5、MRR@5、nDCG@5（有分级标注时）、平均/95分位检索耗时、平均工具调用次数。固定同一文档集合和问答集合；输出每道题的命中文档和失败案例。对于无答案问题，单独计算正确拒答率，不用它们伪造检索 Recall。

**目标值（设计目标，不是现有实测）**：
- 在不少于 30 个有证据的评估查询上，Hybrid Recall@3 争取 ≥ 0.85；若未达成，保留实测并分析失败。
- 对比 A/B/C/D 时必须输出原始值与差异。模型动态补查的收益不能只展示成功例子，也应展示平均调用次数、成本和时延。
- 不允许通过修改评测标签或删去困难用例追求指标。检索扩展阶段的硬性 Gate 是「对比可执行、结果真实、失败案例可查」，性能目标是质量目标，不得填假数字。

### 6.2 可靠问答指标

- `citation_validity_rate` = 引用字符串为已读取原文真实子串的引用数 / 总引用数；**硬指标 100%（由 Guard 保障）**。
- `mandatory_scenario_coverage` = 已有至少一条可复现验收证据的官方场景数 / 6；**硬指标 6/6**。
- `fact_supported_rate` = 有证据明确支持的事实断言数 / 所有事实断言数；质量目标 ≥ 95%，必须人工或独立评审集标注，不能仅模型自评。
- `conflict_handling_success` = 正确识别未解决冲突且不擅自择一的测试数 / 冲突测试总数；目标 100%（核心 TC02 必须通过）。
- `abstention_accuracy` = 资料外问题正确拒答占比；目标 ≥ 90%，核心 TC03 必须通过。
- `tool_failure_behavior` = 失败注入时状态和 Trace 一致、能返回受控结果；硬指标全部注入用例不抛未处理异常。
- `live_branch_evidence`：至少两条**真正调用模型**的 Trace，能观察到模型因结果差异采取不同后续动作；硬指标 ≥ 2 条。
- 记录 `latency_ms`、`tokens_in/out`（模型返回用量可得时）、`steps`、`tool_calls`、错误类型；不将用量缺失填为 0。

### 6.3 评估分层

**确定性单元测试**：检索、原文切片、引用 Guard、冲突比较、预算、工具故障、序列化。要求 100% 通过。
**模型替身集成测试**：使用可控 Fake LLM 模拟工具调用，验证编排、状态、边界和失败恢复。要求全部通过；单独标 `fake_model`，不充当 live 证据。
**Live E2E**：真实模型连接，按六个官方场景运行、保存 Trace；每个核心场景的强制断言都应通过。不通过则修复 prompt、工具返回或检索，最多两轮系统性迭代；仍不通过则显式标 FAIL，不能隐瞒。
**变异/对抗测试**：在不修改答案逻辑的前提下改变原文或注入错误，检验答案与路径是否变化。

## 7. 代码目录规范

```text
evidenceflow-agent/
├── README.md
├── pyproject.toml
├── requirements.txt              # 可生成并固定版本
├── .env.example
├── .gitignore
├── LICENSE                       # 根据仓库发布策略决定
├── CODEX_WORKLOG.md
├── src/evidenceflow/
│   ├── __init__.py
│   ├── config.py
│   ├── schemas.py
│   ├── cli.py
│   ├── api.py
│   ├── agent_graph.py
│   ├── llm_client.py
│   ├── tools.py
│   ├── retriever.py
│   ├── claim_conflicts.py
│   ├── evidence_guard.py
│   ├── session_store.py
│   └── trace_writer.py
├── ui/
│   └── app.py
├── data/
│   ├── documents.json
│   ├── eval_questions.jsonl
│   ├── gold_labels.json
│   └── README.md
├── scripts/
│   ├── run_acceptance.py
│   ├── evaluate_retrieval.py
│   ├── verify_artifacts.py
│   ├── check_gate.py
│   └── smoke_api.py
├── tests/
│   ├── test_retriever.py
│   ├── test_evidence_guard.py
│   ├── test_conflicts.py
│   ├── test_agent_graph.py
│   ├── test_tool_failures.py
│   ├── test_sessions.py
│   ├── test_api.py
│   └── test_mutation.py
├── examples/
│   ├── inputs/
│   ├── outputs/live/
│   ├── outputs/mock/
│   ├── traces/live/
│   └── traces/mock/
├── reports/
│   ├── gates/
│   ├── retrieval_metrics.json
│   ├── acceptance_results.json
│   ├── failure_analysis.md
│   ├── final_acceptance.md
│   └── charts/
└── docs/
    ├── 01-requirements.md
    ├── 02-solution.md
    ├── 03-evaluation.md
    ├── 04-ai-usage.md
    ├── 05-retrospective.md
    ├── 06-architecture.md
    ├── 07-test-plan.md
    ├── 08-experiments.md
    └── 09-time-log.md
```

必须优先保留原题指定的 README、src、tests、examples、data、docs 五份规定文档、依赖和 `.env.example`。上表中的 P1/P2 增强文件可以在后续阶段按需补齐，但最终必须与实际实现一致，禁止空壳文件冒充功能。

## 8. 分阶段开发与自动验收（Codex 的核心工作流）

每一阶段都按以下闭环运行：**Implement → Run tests → Inspect real outputs → Fix → Re-run → Write gate report → Commit checkpoint → Move on**。本地 commit 可在阶段通过后进行；只有最终阶段才需要创建远程仓库。每个 `reports/gates/Px.json` 至少包含 `stage, started_at, finished_at, status(PASS/FAIL/BLOCKED), commands, test_counts, metrics, evidence_paths, errors, changes_made`。不能在未实际执行命令时标 PASS。

### P0. 初始化与输入契约（约10–15分钟）

**目的**：建立可复制环境、数据契约和项目骨架，避免后续功能虽多却不可安装。

**实施**：初始化 Python 包、环境变量、配置类、状态/输出 Pydantic Schema；编写最小 `.env.example`、`.gitignore`、README；写入 5～8 篇合成文档；增加 smoke test。

**验收**：`python -m pip install -e ".[dev]"` 成功；`python -m pytest -q` 可执行；`python -m evidenceflow.cli --help` 退出码0；真实密钥不存在于仓库；生成 `P0.json=PASS`。失败则停在 P0 修复。

### P1. 可复核的知识读取/检索工具（约20–25分钟）

**目的**：确保后续所有 Agent 输出基于可追溯、能查原文的数据，不先把精力用于花哨界面。

**实施**：构建 `documents.json` loader、唯一 ID/版本字段检查、chunk id/offset、BM25基础搜索、read_document、inspect_versions；工具返回统一结构（包括错误与空结果）；编写错误注入器。

**验收**：TC01 可检索/读取 D03，TC02 可分别读 D01/D02；不存在的文档返回可预期错误结构；所有原文quote来源真实；工具单测全部通过；`P1.json=PASS`。

### P2. 真实LLM驱动的LangGraph ReAct（约35–45分钟）

**目的**：解决评分最关键的动态决策要求，保证不是预设分支。

**实施**：用 StateGraph 定义 `agent_decide`、`execute_tools`、`validate_and_finalize`（或等价状态图）；将工具结果写回模型上下文；允许模型自主搜索、换query、读取原文、补查、提交答案；计数与上限强制执行；每步记录 Trace；增加离线 Fake LLM 测试与真实 live 模式。

**验收**：fake模型下不同 Observation 导致不同 tool selection 路径且状态正确；live模式在密钥可用时展示至少两条真实路径（如正常回答和报销冲突），Trace 含真实模型动作、工具参数与返回摘要；超上限返回 INCOMPLETE；若无模型凭证，标 `P2=BLOCKED_LIVE`，mock pass 不可代替完整 PASS。

### P3. 证据核验与冲突处理（约25–35分钟）

**目的**：确保可靠答案和资料不足时适当拒答，解决题目3最大失分风险。

**实施**：记录已读取证据；`submit_answer` 强制校验 quote 精确子串、文档ID、版本和未解决冲突；冲突 Claim 对比兼顾 scope；补查失败时返回 NEEDS_CLARIFICATION 或 INSUFFICIENT_EVIDENCE；对 invalid quote / hallucinated reference 注入测试。

**验收**：TC01、TC02、TC03、TC07、TC08、TC10、TC11 通过适用断言；引用准确率100%；未解决冲突不返回单一确定性期限；`P3.json=PASS`。

### P4. 会话追问、故障恢复和六项验收（约25–35分钟）

**目的**：打通评审必验所有边界条件，留存真实运行证据。

**实施**：session_id、最近历史、对话隔离、必要时SQLite checkpoint；故障注入、超限、失败回传、批量runner；完成 TC01~TC06 实际输入输出 Trace，测试脚本自动判断 JSON 契约并报告分数。

**验收**：官方六项 6/6 留存证据，单测/集成全通过；至少3组“输入+实际输出+Trace”覆盖正常/资料不足/工具失败；至少2条 live 不同决策路径；所有错误场景都有明确状态；`P4.json=PASS`。这一关通过即形成**符合考核的核心版本**。

### P5. 检索增强与实验（约25–40分钟，可增量）

**目的**：用可量化的算法改进体现技术深度，而非仅堆框架。

**实施**：增至25～40篇合成文档；实现中文BM25、dense语义检索（可用 NumPy 向量余弦）、RRF、Query Rewrite；构造30～50个带正确答案标签的查询；运行消融，生成 JSON/CSV和至少两张图（Recall@3对比，效果-调用成本对比）。记录错例。

**验收**：A/B/C/D 使用同一数据集；指标文件含样本数、真实分子分母、Recall@3/5、MRR@5、查询耗时与工具调用统计；可通过 `python -m scripts.evaluate_retrieval` 复现；任何没有跑出的数字写 null/未执行；`P5.json=PASS`。质量目标见第6节，不强行制造提升。

### P6. API与可视化面板（约25–35分钟，可增量）

**目的**：让评审能够在1分钟内观察答案、引用和真实工具轨迹，同时保持核心不依赖UI。

**实施**：FastAPI接口与异常处理、Streamlit前端；左侧对话，中间引用与冲突，右侧 Trace，底部实验图；运行 smoke API 测试、界面加载/交互测试；禁止界面硬编码“示例成功”冒充实时结果。

**验收**：`GET /health` 200、`POST /ask` 返回 Schema 正确、异常映射成受控HTTP响应；Streamlit 通过实际API返回数据可查一次完整问答；API测试全通过；`P6.json=PASS`。

### P7. 可选进阶：自我核验 / 评审模式（30～60分钟，仅剩余时间充足时）

**目的**：增加真实 Agent 迭代质量，且不破坏核心稳定性。

**实施**：候选答案 → 独立 Evidence Critic（规则+可选LLM判断）→ 有条件重新检索/修正；不允许自检无限循环；增加 baseline vs critic 对比，记录答案修正成功率、额外Token与延迟、误拒答数量。

**验收**：关闭 critic 时 P0～P4 测试仍全通过；开启后在独立评测集产生真实结果，无新增无依据确定性回答；能统计修正前后差异与成本；`P7.json=PASS` 或明确 `SKIPPED_OPTIONAL`。若增加 critic 反而导致核心失败则回滚增强。

### P8. 文档、最终自动验收、GitHub建仓并推送（约15～25分钟）

**目的**：将项目变成评审可直接运行、审计和复现的最终成品。

**实施**：完善 README 和原题五份 docs；核对时间日志与 AI 使用记录（区分Codex生成、用户修改、实际验证）；运行全量测试与live验收；`scripts/verify_artifacts.py` 检查路径、数量、json格式与非法密钥模式；生成 `reports/final_acceptance.md` 和本地最终摘要。接着检查 `gh auth status`、`git status`；**确认通过核心验收后才使用 GitHub CLI 创建仓库**，默认 `--private` 避免意外公开，按评审要求将仓库设为公开或授权指定账号。提交并推送，验证 `git ls-remote origin HEAD`、仓库文件可读、获取最终 SHA。

**验收**：README所有命令在干净环境有复现说明；必需目录齐全；基础 P0～P4 PASS；P5～P7已实施的模块各有真实 Gate；没有密钥/个人隐私；最终报告引用实际 Trace；GitHub URL 存在、`git rev-parse HEAD` 是40字符SHA且可与远程核对；`P8.json=PASS`。若 GitHub 登录或权限缺失，报告 `BLOCKED_GITHUB` 和具体步骤，不能编造URL或SHA。

**重要**：如果官方仅建议3小时，可优先完成 P0～P4 + P8；P5/P6/P7按剩余时间增量。避免超过核心要求仍无有效成果。

## 9. Codex的阶段自治与失败处理机制

1. 每次开始某阶段读取上一阶段 `reports/gates/P*.json` 和 `CODEX_WORKLOG.md`。
2. 先写该阶段需要的最小测试，再实现，避免空壳模块。
3. 按实际退出码和 JSON 断言计算结果；测试失败→定位原因→最小幅度修复→复跑。
4. 可针对同一问题尝试合理修复，但不得陷入无限修复；若受密钥、网络或外部依赖限制，标 BLOCKED，继续完成不依赖外部资源的部分。
5. 不因某增强功能失败而损坏核心功能；可选增强允许回滚并标 SKIPPED/FAILED，必须留报告。
6. 每个阶段完成后写 `CODEX_WORKLOG.md`：时间、变更、命令、真实输出位置、未解决问题、是否进入下一阶段。
7. 阶段结束创建本地 git commit，消息 `feat(Px): ...`、`test(Px): ...`；重要：`P8` 之前不创建远程仓库。
8. 最终交付说明必须包含真实完成程度，分 `COMPLETE`, `PARTIAL`, `BLOCKED`，不要仅显示「全绿」视觉效果。

## 10. 必备验收命令（Windows PowerShell）

项目从仓库根目录执行，实际命令选项需与实现保持一致：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# 在本机 .env 填写真实 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME，不提交 .env
python -m pytest -q
python -m evidenceflow.cli ask --mode live --question "办公电脑申领审批需要多久？"
python -m evidenceflow.cli ask --mode live --question "差旅报销期限是多久？"
python -m scripts.run_acceptance --mode live
python -m scripts.evaluate_retrieval
python -m scripts.verify_artifacts
python -m scripts.check_gate --stage P4
uvicorn evidenceflow.api:app --reload
streamlit run ui/app.py
```

命令需要真能执行；如果实际不安装 `py -3.11`，README同时提供通用 `python -m venv .venv` 入口。不能仅因为某个依赖不兼容就直接宣称全部功能完成。

### 10.1 GitHub最终交付命令

```powershell
gh auth status
# 已创建本地git仓库、已提交且完成本地核心验收之后执行
# 若仓库名占用，应检查是否存在已有同名仓库，避免覆写他人项目
gh repo create evidenceflow-agent --private --source=. --remote=origin --push
git status --short
git rev-parse HEAD
git remote -v
git ls-remote origin HEAD
```

`gh repo create` 语法以 GitHub CLI 官方手册为准。后续如公开分享，请再次检查合成资料与密钥扫描，并在得到用户要求后调整 visibility；私有仓库需保证评审账号有读权限。

## 11. README 和文档具体写什么

- `README.md`：项目简介、题号3、架构图、特性、快速开始（PowerShell为主）、环境变量、live/mock区别、CLI/API/UI示例、测试命令、结果路径、局限、GitHub提交信息。
- `docs/01-requirements.md`：用户、业务场景、范围、六个硬性验收、成功标准与非目标。
- `docs/02-solution.md`：状态图、真实模型工具调用回路、工具契约、检索策略、冲突策略、版本处理、上限与错误边界、框架版本及职责。
- `docs/03-evaluation.md`：测试输入/预期/实际/Trace文件、通过状态、失败原因、消融指标、可复现步骤；不可写未执行测试的「结果」。
- `docs/04-ai-usage.md`：Codex/LLM参与的设计与编码工作、人工审核与修改（只有实际发生才记录）、真实测试核验方式。
- `docs/05-retrospective.md`：真实最难问题、解决方案、失败案例、下一步改进与实际用时。
- `docs/06-architecture.md`：组件职责、状态流与数据流、关键取舍。
- `docs/07-test-plan.md`：TC01～TC12、注入开关与断言、测试分层。
- `docs/08-experiments.md`：基线、样本、检索指标、成本评估、统计局限与图表。
- `docs/09-time-log.md`：记录真实阶段用时、遇到的阻塞与未完成事项。

## 12. 最终评审演示脚本（建议2～4分钟）

1. 展示 README 快速开始和真实运行入口（15秒）。
2. 跑 TC01：口语化问题→真实检索→文档引用→确定性答案（30秒）。
3. 跑 TC02：两份矛盾制度→补查→两份引用→待确认，展示差异决策 Trace（45秒）。
4. 跑 TC06：注入检索失败→Observation→模型重新选择动作/受控终止（35秒）。
5. 跑 TC07：修改 D03 原文→再次问答→答案随证据变化（30秒）。
6. 展示检索实验对比和失败分析，并说明真实指标不是伪造数据（30秒）。
7. 展示GitHub远程仓库URL与commit SHA，确保评审可直接复跑（15秒）。

## 13. 最终交付清单

Codex最后必须给出：①本地项目路径；②GitHub仓库 URL；③最终 commit SHA；④完整运行命令；⑤六项硬性验收逐条 PASS/FAIL/BLOCKED；⑥live工具决策路径和Trace；⑦pytest统计；⑧检索实验真实指标与图；⑨已知限制；⑩README/报告定位。没有的内容写“未实现/未验证”，不得用 Mock 冒充。

## 14. 技术细节与兼容性提醒

- 2026年较新 LangGraph 文档中，旧 `langgraph.prebuilt.create_react_agent` 已弃用，可用 `StateGraph` 或新版 `langchain.agents.create_agent`。本项目由于自定义Guard/Trace/State，选择 `StateGraph`；不要生成大量过时接口。
- Checkpointer 的 `thread_id` 用于会话状态恢复；InMemorySaver 不能跨重启持久化，若启用SQLite需测试安装、并发访问、锁处理。
- GitHub CLI `gh repo create` 支持 `--private --source=. --remote=origin --push`。需先完成 `gh auth status`；若没权限应返回 BLOCKED。
- 真实模型调用成本和时长受到第三方服务影响，不保证硬编码数值；必须保存实际运行结果。

**结束条件**：核心达标 + 真实Trace + 完整文档 + 自动验收报告 + 可读GitHub仓库及SHA。增强项按真实结果报告，宁可如实不达标，也不编造优秀指标。
