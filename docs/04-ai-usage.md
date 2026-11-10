# AI 使用记录

当前 Codex 会话根据用户提供的主规格、执行提示词、验收 JSON 和原始 Word 题目，实际完成架构、合成数据、代码、测试、调试、报告、文档及终端执行。未使用子 Agent 或另一个规划服务替代执行。

用户提供规格并在本机配置模型凭证，随后确认文件路径；Codex 将项目旁 env 文件复制到项目内部被 Git 忽略的 .env。没有在 Git 或报告中保存密钥。除规格和凭证配置外，未观察到用户对实现代码的人工修改；不宣称独立人工代码审核已经完成。

运行时 live 决策由 qwen-plus 完成；真实工具调用、Usage 和 Guard 修订见 Trace。Dense 为实际多语 MiniLM。MockModel/ScriptedModel 的离线结果不计为 live。

验证使用实际 pip、pytest、HTTP、Streamlit AppTest、真实模型场景、检索消融和独立 Critic 对照；保留退出码、JUnit、JSON、数据哈希及全部失败。Critic 对照显式注入 4 个候选覆盖缺失并保留 2 个干净对照，不能当作模型自然错误率。未标注事实支持率、未知 USD 单价仍不填猜测值。

## 2026-11-11 最终复验

本轮重新执行，未扩展业务架构或修改验收标准。pytest 75/75（0跳过），BM25官方live 6/6，Hybrid官方live 6/6；TC02五次 5/5，Critic PASS。上文旧日期及表格均为历史观察；当前每项结果、失败、路径及权限限制见 [最终报告](../FINAL_ACCEPTANCE/FINAL_REPORT.md) 和 [F4增强实测](../FINAL_ACCEPTANCE/F4_enhancement_validation.json)。

本轮TC03：bm25：0 次中间拒绝，最终 INSUFFICIENT_EVIDENCE（PASS）；hybrid：1 次中间拒绝，最终 INSUFFICIENT_EVIDENCE（PASS）。F7历史路径问题未获改写授权，保持BLOCKED；未发现配置密钥泄露；当前日志只作路径隐私脱敏，原失败事实、非路径字节、原始本机备份和全部历史失败记录保留。评审账号未提供，PENDING_REVIEWER_ACCESS。新模型调用、UI真实HTTP检查和实验均有工件，未声称独立人工语义标注或浏览器人工检查。
