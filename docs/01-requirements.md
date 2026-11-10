# 需求与成功标准

选择题目 3，面向员工、制度维护人员和评审。员工需要获得电脑申领、报销、请假等可靠答案；维护人员需要检查冲突、缺口和引用；评审需要更换原文、注入故障后核对模型动作。

范围为合成企业制度、本地检索读取、真实模型 Tool Calling、会话追问、证据核验、故障恢复、Trace、CLI、API、Streamlit 和检索消融。未接真实企业系统，不解释真实法律或劳动政策，不做生产部署和多用户权限系统。

硬约束：TC01 明确答案、TC02 冲突、TC03 资料外、TC04 相似改写、TC05 上下文追问、TC06 工具失败，均有实际输入/输出/Trace，至少两条 live 差异路径。引用必须来自已读原文；D01 30 天/D02 15 天的效力未知时不能擅自裁定。最多 8 次模型决策、12 次工具执行；故障和超限须明确状态。

P0—P4 是核心；P5 检索实验、P6 API/UI 为增强；P7 独立 Critic 可选。P8 要求实际全量测试、密钥检查、文档、GitHub URL 和远程核验 SHA。缺凭证或远程失败必须报告 BLOCKED，不能用 mock 充当 live。

质量目标 Hybrid Recall@3>=0.85 不是结果承诺。模型用量可报告，缺单价则 USD 成本=null。未独立标注的事实支持率不填推测值。

## 2026-11-11 最终复验

本轮重新执行，未扩展业务架构或修改验收标准。pytest 75/75（0跳过），BM25官方live 6/6，Hybrid官方live 6/6；TC02五次 5/5，Critic PASS。上文旧日期及表格均为历史观察；当前每项结果、失败、路径及权限限制见 [最终报告](../FINAL_ACCEPTANCE/FINAL_REPORT.md) 和 [F4增强实测](../FINAL_ACCEPTANCE/F4_enhancement_validation.json)。

本轮TC03：bm25：0 次中间拒绝，最终 INSUFFICIENT_EVIDENCE（PASS）；hybrid：1 次中间拒绝，最终 INSUFFICIENT_EVIDENCE（PASS）。F7历史路径问题未获改写授权，保持BLOCKED；未发现配置密钥泄露；当前日志只作路径隐私脱敏，原失败事实、非路径字节、原始本机备份和全部历史失败记录保留。评审账号未提供，PENDING_REVIEWER_ACCESS。新模型调用、UI真实HTTP检查和实验均有工件，未声称独立人工语义标注或浏览器人工检查。
