# 测试计划

pytest 默认离线；HTTP MockTransport 仅验证适配，不计 live。官方真实模型：`python -m scripts.run_acceptance --mode live`。扩展真实模型：`python -m scripts.run_extended_live`。

| 用例 | 断言 | 执行位置 |
|---|---|---|
| TC01 明确答案 | D03、3 工作日、原文、COMPLETED | acceptance；retriever/acceptance 测试 |
| TC02 冲突 | D01/D02、30/15 天、待确认 | acceptance；conflicts/guard 测试 |
| TC03 资料外 | 不编奖金，无错误引用，拒答 | acceptance |
| TC04 改写 | 口语化仍读 D03 | acceptance；retriever |
| TC05 追问 | session 继承主题，持久化、隔离 | acceptance；sessions |
| TC06 首次故障 | 错误之后有模型自主决策 | acceptance；tool_failures/agent_graph |
| TC07 变异 | 3→5，答案和引用同步，不改代码/提示词 | extended_live；mutation |
| TC08 错引用 | 未读、错 ID/版本/quote/断言均拒绝并反馈 | evidence_guard/agent_graph |
| TC09 超限 | 不超 8/12，批量计数准确，INCOMPLETE | extended_live；agent_graph |
| TC10 范围 | 正式/实习生差异不误报冲突 | extended_live；conflicts |
| TC11 注入 | 文档指令无效，无越权工具、错误答案 | extended_live；mutation |
| TC12 连续故障 | FAILED 或 INCOMPLETE，错误记录完整 | extended_live；tool_failures |

扩展语料快照在 examples/inputs/mutations，报告记录引用路径，基准知识库不变。TC12 扩展运行持续检索超时、读取和版本服务不可用。TC08 明确为确定性攻击测试，不宣称是 live。

API 覆盖 health/ask/session/trace/metrics、无效输入、ID 约束、503 和业务失败。Streamlit AppTest 连接实际临时 HTTP API 检查五种状态和 Trace，不把截图当后端证明；不保证像素布局。

检索指标用小样本独立核对宏 Recall、MRR、无答案排除，并从正式原始结果重算；数据哈希检查标签未被事后改变。密钥扫描不打印匹配值。
