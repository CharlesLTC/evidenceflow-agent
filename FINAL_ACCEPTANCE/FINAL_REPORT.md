# EvidenceFlow 最终交付验收

本轮状态：**DELIVERY_BLOCKED**。实际开始 2026-11-10T19:58:34.568952+00:00，报告生成 2026-11-10T20:06:55.345245+00:00。全部本轮结果来自新执行，不以历史通过代替复验。未修改业务源码、原75项测试、数据标签或验收标准。

## 1. 项目概况

题目3《企业知识问答 Agent》。LangGraph StateGraph、真实 Tool Calling、本地BM25/ONNX Dense/Hybrid RRF、强制EvidenceGuard、可选Evidence Critic、FastAPI、Streamlit和SQLite会话。
流程：CLI/API/UI → AgentService → 模型动作 → 实际工具 → Observation → 后续模型决策；提交必须通过原文引用和冲突校验。8次模型决策、12次业务工具上限；Critic共享预算。没有新增架构或框架依赖。

## 2. 最终功能清单

| 功能 | 实现 | 源码 |
|---|---|---|
| LangGraph 动态决策、预算及异常处理 | 已实现 | [src/evidenceflow/agent_graph.py](../src/evidenceflow/agent_graph.py) |
| 真实模型 Tool Calling | 已实现 | [src/evidenceflow/llm_client.py](../src/evidenceflow/llm_client.py) |
| BM25、Dense、Hybrid RRF | 已实现 | [src/evidenceflow/retriever.py](../src/evidenceflow/retriever.py) |
| 真实 ONNX 语义嵌入 | 已实现 | [src/evidenceflow/embeddings.py](../src/evidenceflow/embeddings.py) |
| Agent 动态检索 | 已实现 | [src/evidenceflow/query_rewrite.py](../src/evidenceflow/query_rewrite.py) |
| 文档原文和工具执行 | 已实现 | [src/evidenceflow/tools.py](../src/evidenceflow/tools.py) |
| 已读原文引用校验 | 已实现 | [src/evidenceflow/evidence_guard.py](../src/evidenceflow/evidence_guard.py) |
| 制度数值和范围冲突检测 | 已实现 | [src/evidenceflow/claim_conflicts.py](../src/evidenceflow/claim_conflicts.py) |
| 会话历史 | 已实现 | [src/evidenceflow/session_store.py](../src/evidenceflow/session_store.py) |
| 可选 Evidence Critic | 已实现 | [src/evidenceflow/evidence_critic.py](../src/evidenceflow/evidence_critic.py) |
| 可观察 Observation 决策摘要 | 已实现 | [src/evidenceflow/decision_basis.py](../src/evidenceflow/decision_basis.py) |
| FastAPI | 已实现 | [src/evidenceflow/api.py](../src/evidenceflow/api.py) |
| Streamlit | 已实现 | [ui/app.py](../ui/app.py) |

F1语法、JSON、依赖、导入和入口实测见 [F1](F1_project_integrity.json)。本轮新增脚本只负责验收，不改变业务行为。

## 3. 官方验收表

模型 qwen-plus，模式 live，策略 bm25，Critic关闭。**6/6**；精确已读原文引用 6/6，不同工具路径 5 条。[汇总](F3_live_acceptance.json)，[动态分支与步数校验](F3_dynamic_paths.json)。decision_basis是可观察事实摘要，不是隐藏推理。

| 编号 | 输入 | 预期 | 实际 | 结果 | 工件 |
|---|---|---|---|---|---|
| TC01 | 办公电脑申领审批需要多久？ | 完成，D03 原文、3个工作日 | COMPLETED：D03：办公电脑申领须在IT门户填写申请，经主管审批后3个工作日内完成。 | PASS | [输入](../examples/inputs/live-15cce898235f4d6c974d9e1c71e729d6.json) / [输出](../examples/outputs/live/15cce898235f4d6c974d9e1c71e729d6.json) / [Trace](../examples/traces/live/15cce898235f4d6c974d9e1c71e729d6.json) |
| TC02 | 差旅报销期限是多久？ | 双引用，30/15天冲突，待确认 | NEEDS_CLARIFICATION：D01：差旅报销应在30天内提交。报销须附发票和出差审批单。<br>D02：差旅报销应在15天内提交。报销须附发票和出差审批单。<br>适用范围及优先级尚待确认，当前无法确定唯一规则。 | PASS | [输入](../examples/inputs/live-023756ecf77e4a98807e656d11585745.json) / [输出](../examples/outputs/live/023756ecf77e4a98807e656d11585745.json) / [Trace](../examples/traces/live/023756ecf77e4a98807e656d11585745.json) |
| TC03 | 公司的年终奖金是多少？ | 资料不足，不编造、无引用 | INSUFFICIENT_EVIDENCE：当前资料不足，无法依据知识库回答。 | PASS | [输入](../examples/inputs/live-90ebac3d03074110ab256efcfdf67f69.json) / [输出](../examples/outputs/live/90ebac3d03074110ab256efcfdf67f69.json) / [Trace](../examples/traces/live/90ebac3d03074110ab256efcfdf67f69.json) |
| TC04 | 领电脑一般几天能批下来？ | 相似表述仍答3个工作日 | COMPLETED：D03：办公电脑申领须在IT门户填写申请，经主管审批后3个工作日内完成。 | PASS | [输入](../examples/inputs/live-3c449ec488c04d8fa5c284e85097b218.json) / [输出](../examples/outputs/live/3c449ec488c04d8fa5c284e85097b218.json) / [Trace](../examples/traces/live/3c449ec488c04d8fa5c284e85097b218.json) |
| TC05 | 那多久批下来？ | 继承电脑申领上下文，3个工作日 | COMPLETED：D03：办公电脑申领须在IT门户填写申请，经主管审批后3个工作日内完成。 | PASS | [输入](../examples/inputs/live-fe7df459449c4ad1a244427398468301.json) / [输出](../examples/outputs/live/fe7df459449c4ad1a244427398468301.json) / [Trace](../examples/traces/live/fe7df459449c4ad1a244427398468301.json) / [前轮Trace](../examples/traces/live/4c306532423840a1a492de503d3c757f.json) |
| TC06 | 办公电脑申领审批需要多久？ | 注入首搜超时后重新决策或如实终止 | COMPLETED：D03：办公电脑申领须在IT门户填写申请，经主管审批后3个工作日内完成。 | PASS | [输入](../examples/inputs/live-4e5385fea91f484697c9e1a5b12eca93.json) / [输出](../examples/outputs/live/4e5385fea91f484697c9e1a5b12eca93.json) / [Trace](../examples/traces/live/4e5385fea91f484697c9e1a5b12eca93.json) |

## 4. 增强功能实验

Hybrid实际Agent官方六项：**6/6，PASS**。全部用例尝试Hybrid；语义后端不可用为显式故障注入，模型选择BM25恢复；见 [执行覆盖](F4_hybrid_execution.json)、[故障回退](F4_hybrid_fallback_live.json)。超时后无程序自动重试。

检索：32篇合成文档、44个固定问题、40个有答案；同一原始数据哈希，176条策略×问题记录，逐题分母固定。CPU单轮，初始化单独计时 9623.660ms，不包含在查询时间内。无置信区间。

| 策略 | 状态 | R@3 | R@5 | MRR@5 | 平均ms | P95ms | 模型/工具调用均值 |
|---|---|---:|---:|---:|---:|---:|---:|
| A_BM25 | PASS | 0.9250 | 0.9375 | 0.9175 | 0.200 | 0.240 | 0.0000 / 1.0000 |
| B_Dense | PASS | 0.9750 | 0.9750 | 0.9625 | 2.427 | 3.068 | 0.0000 / 1.0000 |
| C_Hybrid_RRF | PASS | 0.9875 | 1.0000 | 0.9833 | 2.335 | 2.829 | 0.0000 / 1.0000 |
| D_Hybrid_AgentRewrite | PASS | 0.9875 | 1.0000 | 0.9833 | 964.885 | 1596.829 | 1.4545 / 1.4545 |

[指标](F4_retrieval_metrics.json)、[原始逐题数据](F4_retrieval_details.json)、[未命中R@3的全部错例](F4_retrieval_failures.json)。D的真实模型检索Trace路径在逐题数据中；模型与权重哈希在 ../reports/embedding_manifest.json。引用正确率来自Agent最终引用核验，不冒充排序指标或独立人工语义正确率。D本轮没有改善R@3/MRR；调用和延迟增加，USD未知保持null。

Critic：**PASS**，增强最终正确 6/6，基线 2/6；修正 4/4，新增最终错误 0，干净对照误修 0，无效最终引用 0。平均额外模型步数 2.3333，独立Critic调用 1.6667，额外耗时 4259.310ms，额外token 21951，USD=null。[本轮全部配对Trace与判据](F4_critic_evaluation.json)。4个候选遗漏为人工注入，2个干净对照；候选源于真实模型并保留注入标记，不能当作自然错误率。初轮历史FAIL仍保留在 ../reports/critic_eval_runs。

TC02：本轮连续 5/5，成功率 100%，Guard拒绝 0，未挑选或外部重试。[五次Trace](F4_tc02_stability.json)。历史五次及本轮TC03复核均见 [F4](F4_enhancement_validation.json)。TC03：bm25：0 次中间拒绝，最终 INSUFFICIENT_EVIDENCE（PASS）；hybrid：1 次中间拒绝，最终 INSUFFICIENT_EVIDENCE（PASS）。保留可恢复失败，不放松Guard。

异常注入、预算和安全性扩展见 [扩展live](F4_extended_live.json)；每项预期、真实结果和Trace在JSON中。

## 5. 自动化与前后端实测

pytest：**75/75**，失败0，错误0，跳过0，JUnit耗时 14.762s，退出码0。命令：`.\.venv\Scripts\python.exe -m pytest -q --junitxml=FINAL_ACCEPTANCE/F2_pytest_results.xml`。[JUnit](F2_pytest_results.xml)、[摘要和原始命令日志路径](F2_pytest_summary.json)。

API/UI：**PASS**。实际API `http://127.0.0.1:9551`，实际Streamlit `http://127.0.0.1:9552`，HTTP health/docs/openapi/首页/Streamlit health均200；UI经真实HTTP调用qwen-plus，展示状态、原文引用、实际Trace；mock用于额外冲突、资料不足和持续失败展示。空输入禁用、断开后端有错误提示、404/422受控。只关闭本次启动进程。[F5完整证据](F5_ui_api_check.json)、[系统排除端口](F5_port_exclusions.txt)。默认8000/18501已占用（bind 10048），因此选备用端口，未强行结束原服务。未做浏览器像素人工检查。

工件检查遍历全部JSON、输入/输出/Trace三件套、已读原文引用、P0–P6 Gate及模式分离；结果见 [工件核验](artifact_verification.json)。Ruff、pip、原始命令日志见 commands.jsonl 和 logs/。历史可变指标在 before/ 保存，失败文件保留，仅隐私路径脱敏有单独例外说明。

## 6. GitHub交付与SHA

仓库：[CharlesLTC/evidenceflow-agent](https://github.com/CharlesLTC/evidenceflow-agent)，现有private仓库，main。未创建重复仓库，未更改可见性，未在缺授权时重写历史或force push。[F8实际发布快照](F8_github_delivery.json)。

最终 SHA 以同一仓库 `git rev-parse HEAD`、`git ls-remote origin refs/heads/main` 和本机忽略的 `reports/delivery_verification.local.json` 为准；ZIP 的 Git archive 注释同样记录完整 SHA。提交不能在自己的文件中硬编码自身 SHA。本报告不把源代码基线 SHA 冒充最终 SHA。

本轮源代码基线：`b76dfe7f455fc937ad1ab94adc844baae445712b`。最终普通推送后的三方SHA、完整远程树和ZIP CRC/文件一致性证明保存在上述本机最终回执（不提交，避免自引用）。ZIP为最终Git提交的git archive，外部路径 `E:\秋招笔试\EvidenceFlow\evidenceflow-agent-delivery.zip`，不含.git、环境、缓存、模型权重或密钥。提交内F8标明已验证快照，不能把它当作最新SHA。

评审：**PENDING_REVIEWER_ACCESS**。实际协作者与邀请通过GitHub API查询；仅所有者、无邀请。未提供指定评审账号，不能声称评审已授权。待用户提供账号后才可实际授权。

## 7. 已知问题与限制

- 阻断：历史 P0 失败日志包含私人 Windows 路径。当前文件只脱敏4处路径，原始日志和 Git bundle 已在本机忽略目录保存，失败内容与非路径字节未改。远程历史尚未获得改写授权，F7 保持 BLOCKED。未发现已配置密钥值或已知凭证模式泄露。
- 授权待办：私有仓库仅核实到所有者访问、无待接受邀请；未提供评审账号，PENDING_REVIEWER_ACCESS。未添加虚构账号、未更改可见性。
- 非阻断：本轮 Hybrid TC03 自然出现一次 MISSING_INFO_REQUIRED 中间校验拒绝，真实模型随后修正并正确结束，Trace完整保留。
- 非阻断：Critic 是4个受控遗漏、2个干净对照的小样本，不是自然模型错误率；默认关闭，共享8次模型预算、最多1次修正。
- 非阻断：32篇合成制度、40个可回答检索问题；无独立人工事实支持率或分级相关性标注，USD单价未知保持null。D动态改写本轮未改善排序指标。
- 环境：8000、18501 本轮 bind 返回10048，未终止未知服务；实际独立服务使用备用端口。AppTest验证控件和真实HTTP，未声称浏览器像素人工验收。API用于本机合成演示，未实施多用户鉴权。

[F7原始安全审计](F7_security_audit.initial.json)、[最新审计](F7_security_audit.json)、[路径脱敏与保留证明](privacy_redaction.json)。新的提交内容没有匹配的密钥/.env/私人路径；历史问题不以当前文件删除或脱敏冒充清理成功。未经确认不强制改写历史。安全扫描不是对所有可能敏感信息的数学证明。

## 8. Windows可复现命令

```powershell
cd E:\秋招笔试\EvidenceFlow\evidenceflow-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install --no-build-isolation --no-deps -e ".[dev,embeddings]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# 本机编辑 .env；保留已有配置，不在聊天或 Git 中发送密钥
python -m pytest -q
python -m evidenceflow.cli ask --mode mock --question "电脑审批多久？"
python -m evidenceflow.cli ask --mode live --question "差旅报销期限是多久？"
python -m scripts.run_acceptance --mode live
python -m scripts.validate_live_evidence
python -m scripts.evaluate_retrieval
python -m scripts.verify_retrieval_results
python -m scripts.evaluate_critic
python -m scripts.verify_artifacts
python -m scripts.final_security_audit
# 分别在两个激活环境的终端启动；先检查端口占用
python -m uvicorn evidenceflow.api:app --host 127.0.0.1 --port 8000
$evidenceflowUiPort = if ($env:STREAMLIT_SERVER_PORT) { [int]$env:STREAMLIT_SERVER_PORT } else { 18501 }
python -m streamlit run ui/app.py --server.address 127.0.0.1 --server.port $evidenceflowUiPort
# 端口占用时可选空闲端口，并在前端终端设置对应后端URL：
# $env:EVIDENCEFLOW_API_URL="http://127.0.0.1:18000"
# $env:STREAMLIT_SERVER_PORT="19001"
# 后端命令同时将 --port 设为18000；不占用未知进程
python -m scripts.verify_delivery
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

README、五份考核文档、当前证据索引见 [F6](F6_documentation_check.json)。文档中的历史表格明确标注历史，不合并为本轮通过次数。最终总判定遵循当前证据，历史FAIL不删除、不改写为PASS。

文档初次检查为 FAIL：README 缺少明确的局限说明。补充栏目后按同一判据通过；首次结果见 F6_documentation_check.initial_FAIL.json。
