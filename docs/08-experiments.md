# 检索消融本轮实测（2026-11-11）

| 策略 | 状态 | R@3 | R@5 | MRR@5 | 平均ms | P95ms | 模型/工具调用均值 |
|---|---|---:|---:|---:|---:|---:|---:|
| A_BM25 | PASS | 0.9250 | 0.9375 | 0.9175 | 0.200 | 0.240 | 0.0000 / 1.0000 |
| B_Dense | PASS | 0.9750 | 0.9750 | 0.9625 | 2.427 | 3.068 | 0.0000 / 1.0000 |
| C_Hybrid_RRF | PASS | 0.9875 | 1.0000 | 0.9833 | 2.335 | 2.829 | 0.0000 / 1.0000 |
| D_Hybrid_AgentRewrite | PASS | 0.9875 | 1.0000 | 0.9833 | 964.885 | 1596.829 | 1.4545 / 1.4545 |

同一固定语料32篇、44题、40个可回答。指标由176条原始记录重算，数据哈希一致；D是实际qwen-plus决策和补查，未改善R@3/MRR。初始化 9623.660ms单列，单轮CPU查询，不含初始化，无置信区间。

实际token、逐题排名、调用和延迟见 [本轮检索指标](../FINAL_ACCEPTANCE/F4_retrieval_metrics.json) 与 [原始数据](../FINAL_ACCEPTANCE/F4_retrieval_details.json)。4个资料外问题不进入Recall/MRR分母。无分级标签，nDCG=null；未知模型单价USD=null；检索实验不冒充问答引用正确率或自然拒答率。模型 revision/文件哈希见 ../reports/embedding_manifest.json，D每题Trace路径在逐题记录内。

上轮指标完整保存于 ../FINAL_ACCEPTANCE/before/reports/retrieval_metrics.json；历史FAIL和错例不删除。[本轮全报告](../FINAL_ACCEPTANCE/FINAL_REPORT.md)。
