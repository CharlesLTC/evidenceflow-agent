# 发给 Codex 的总控执行 Prompt

请先将同目录 `01_EvidenceFlow_完整开发规格.md` 作为**唯一开发主规格**完整读取；按照其中的架构、工具契约、阶段P0～P8、数据定义、TC01～TC12、验收指标和GitHub交付要求，直接在当前工作空间创建完整可运行项目 `evidenceflow-agent`。

## 你的角色与总体目标

你是负责自主实施、调试、验证和交付的资深 Python / Agent 工程师。此次任务不是帮我写一份开发建议，而是**真正创建项目文件、运行程序、执行测试、修复错误、留下真实证据、最终创建GitHub仓库并推送**。

业务目标：做一个企业知识问答Agent，真实LLM驱动ReAct工具决策，支持多轮证据检索、原文读取、冲突检测、证据核验、资料缺失时拒答、工具故障恢复；在核心验收通过后，继续实现Hybrid RAG消融评估、FastAPI和Streamlit，时间充裕再增加自检修正。

## 强制执行规则

1. **不要停在方案或伪代码**，立刻创建文件并运行命令。原则上不反复询问非关键细节。模型、库版本、UI布局可在规格范围内自主选型。
2. **严格按 P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7(可选) → P8 执行**。每阶段先定义验收，再实现、跑测试、修复、复跑、记录 `reports/gates/Px.json` 和 `CODEX_WORKLOG.md`，通过才能推进；增强项失败可回滚，不得影响 P0～P4。
3. **真实ReAct是最高优先级**：LangGraph StateGraph里由实际LLM依据Observation选择下一个工具/调整query/结束；不得用基于问题字符串的if/else或固定重试冒充模型决策。工具返回、版本数据、提示词必须能被替换后改变模型的后续动作。
4. 强制回答证据边界：已读取文档的真实原文quote才可引用，引用不存在则拦截；D01 30天、D02 15天且适用范围不明时，输出冲突和待确认，禁止擅自挑一个。无依据问题拒绝编造。
5. 每次真实工具调用记录step、工具名、参数、Observation摘要、下一动作、可观察的简要决策依据、Trace ID、mode、模型名、时间戳及用量（可得时）。不要请求或记录隐藏思维链。live/mock/fake_model分目录存档。达到8次模型决策或12次工具调用时返回INCOMPLETE。
6. 不能伪造运行结果。没API密钥则先做确定性单测与mock，再把live验证标BLOCKED并告知如何补齐；不能将mock说成真实LLM。也不允许以「代码看起来没问题」代替运行。
7. 按测试计划实现官方六项TC01～TC06，再做TC07～TC12；至少保存3组真实输入/输出/Trace覆盖正常、资料不足、工具失败，真实live至少两条不同Observation下的不同决策路径（模型可用时）。
8. 检索扩展对比 BM25、Dense、Hybrid(RRF)、Hybrid+Agent Query Rewrite；同一标注集，输出真实 Recall@3/5、MRR@5、成本、耗时、失败案例。无数据不可填假指标；性能目标没达到也要保留负面结果。
9. CLI始终为稳态运行入口，FastAPI和Streamlit是增强；不能只做网页空壳。所有API/UI返回真实后端数据，不写死结果。
10. 所有依赖版本与Windows PowerShell命令必须实际可运行，优先Python 3.11/3.12，支持本机环境允许的兼容版本。API和Embedding依赖失败时采用规格中的合法回退策略并记录。
11. GitHub最终阶段：先自测、依赖检查、真实secret扫描，才运行 `gh auth status` 和 `gh repo create evidenceflow-agent --private --source=. --remote=origin --push`。注意不要重复创建已有仓库。确认推送后返回可访问URL、最终commit SHA、远程HEAD校验。如果认证或权限不足，必须报告BLOCKED_GITHUB，不要编造URL。私有仓库是否能供评审访问也须说明。
12. 不提交 `.env`、API Key、cache、嵌入模型权重或真实内部信息。合成数据可以提交。
13. 必须在最终回答中给出项目完成程度及复现命令：项目路径、GitHub URL、SHA、测试通过数/总数、live六项结果、主要Trace、算法对比、演示入口、失败限制。不得只回答「完成了」。

## 开工后执行节奏

- 先检查工作目录、Python版本、Git、GitHub CLI与API环境变量是否可用，但禁止打印密钥值。
- 阅读主规格和原考核题目（如已存在），新建 `evidenceflow-agent`，先完成 P0～P4 **完整核心闭环**。不要在核心六项没通过时转去美化界面。
- 每阶段运行实际测试命令，修复失败并写Gate JSON；不等待我的逐阶段确认，继续推进可执行阶段。
- 核心完成后实现 P5、P6；剩余资源允许再做P7，必须证明实验和验证有效。
- 最后运行全量命令，生成 `reports/final_acceptance.md`，完成 P8 和GitHub推送。

## Codex最终回答格式

```
项目名称：EvidenceFlow
项目路径：...
GitHub URL：...（或者 BLOCKED_GITHUB + 具体原因）
最终 commit SHA：...（或未生成）
完成阶段：P0 ... P8，各阶段 PASS/FAIL/BLOCKED/SKIPPED
pytest：通过 n/n，失败 x；实际命令...
六项硬验：TC01 ... TC06 每项状态 + 实际输出/Trace路径
真实ReAct验证：至少两条差异路径（使用的工具与Observation）
检索实验：样本数、A/B/C/D指标、失败案例路径
如何运行：CLI、API、UI、完整评估命令
实际用时与局限：...
```

**现在直接开始实施。对缺密钥、缺GitHub登录等真实外部阻碍提供明确提示，但不要借此跳过可在本地完成的实现与测试。**
