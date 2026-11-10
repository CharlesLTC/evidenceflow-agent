# EvidenceFlow 最终验收

状态：COMPLETE。生成于 2026-11-10T07:35:06.592579+00:00。

项目路径：E:\秋招笔试\EvidenceFlow\evidenceflow-agent；题号：3；实测模型：qwen-plus。

GitHub：https://github.com/CharlesLTC/evidenceflow-agent

最终 SHA：交付完成后由忽略的本机收据 reports/delivery_verification.local.json 记录，须与 git rev-parse HEAD、git ls-remote origin HEAD 一致。版本化报告不能嵌入自身 commit SHA。

| 阶段 | 状态 |
|---|---|
| P0 | PASS |
| P1 | PASS |
| P2 | PASS |
| P3 | PASS |
| P4 | PASS |
| P5 | PASS |
| P6 | PASS |
| P7 | PASS |
| P8 | PASS |

pytest 实际统计：{'tests': 75, 'failures': 0, 'errors': 0, 'skipped': 0, 'passed': 75}。本轮 JUnit：reports/quality/final-pytest.xml；原始交付 JUnit 保留在 reports/logs/P8-pytest.xml。

官方 live：6/6，mock：6/6；live 差异工具路径见 reports/live_branch_evidence.json。

六项及扩展用例实际输入/输出/Trace 的逐条链接见 docs/03-evaluation.md。TC08 为确定性 Guard 测试，其余扩展 live 结果见 reports/extended_live.json。

检索：32 篇、44 题/40 有答案，A/B/C/D 的 Recall@3 = 0.9250/0.9750/0.9875/0.9875；D 无改善，平均调用 1.4545 次/题，USD=null。指标、图表、分子分母和错例见 docs/08-experiments.md 与 reports/retrieval_*.json。

运行：README 包含环境、CLI、API（8000/docs）、UI（默认18501，端口可配置）、完整评估和工件核验命令。API/UI 返回实际后端数据，界面五种交互状态已验证。

P7 独立 Critic 默认关闭，共享8次模型预算，最多一次修正且不可绕过 Guard。修正率仅针对显式注入缺失，不代表自然错误率，见 docs/10-quality-review.md。
局限：合成标注集、摘录回答、受控范围与提示模式；未独立人工测量事实支持率；未实施生产鉴权及跨进程锁。实际仓库授权清单见 reports/reviewer_access.json。

本轮质量墙钟用时 24.8 分钟；用户检查间隔单列，见 docs/09-time-log.md。

## 最终交付复验

2026-11-10T07:51:34.867458+00:00：pytest 75/75，官方真实live 6/6，工件和安全检查PASS，611个历史文件未变化。Streamlit默认18501，可通过环境变量或CLI覆盖。详见 [交付复验](handoff/20261110T074943Z/delivery.md)。私有仓库评审访问仍待授权，目标账号未提供。
