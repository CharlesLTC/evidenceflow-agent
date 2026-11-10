# EvidenceFlow 最终验收

状态：PARTIAL。生成于 2026-11-10T05:08:39.060246+00:00。

项目路径：E:\秋招笔试\EvidenceFlow\evidenceflow-agent；题号：3；实测模型：qwen-plus。

GitHub：BLOCKED_GITHUB：本机 GitHub CLI 尚未登录或尚未完成远程交付；不能声称已建仓/推送。

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
| P7 | SKIPPED_OPTIONAL |
| P8 | BLOCKED |

pytest 实际统计：{'tests': 63, 'failures': 0, 'errors': 0, 'skipped': 0, 'passed': 63}。命令：python -m pytest -q；最新 JUnit 为 reports/logs/P8-pytest.xml（未产生前引用 P4）。

官方 live：6/6，mock：6/6；live 差异工具路径见 reports/live_branch_evidence.json。

六项及扩展用例实际输入/输出/Trace 的逐条链接见 docs/03-evaluation.md。TC08 为确定性 Guard 测试，其余扩展 live 结果见 reports/extended_live.json。

检索：32 篇、44 题/40 有答案，A/B/C/D 的 Recall@3 = 0.9250/0.9750/0.9875/0.9875；D 无改善，平均调用 1.4545 次/题，USD=null。指标、图表、分子分母和错例见 docs/08-experiments.md 与 reports/retrieval_*.json。

运行：README 包含环境、CLI、API（8000/docs）、UI（8501）、完整评估和工件核验命令。API/UI 返回实际后端数据，界面五种交互状态已验证。

局限：小型合成标注集；摘录式回答；受控数值/范围/提示模式；未独立人工测量事实支持率；未实现 P7 Critic、生产鉴权与跨进程锁；私有仓库需另授评审访问权。

可核验开发区间：目录创建后至本报告 35.2 分钟；详见 docs/09-time-log.md。
