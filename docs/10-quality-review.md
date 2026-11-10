# 最后一轮质量优化与实际验证

生成于 2026-11-10T07:35:06.409745+00:00；结果：PASS。

在既有项目上增量修改，原有63项测试及官方六项断言保持不变。历史Trace和FAIL不改写；新Trace版本2提供事件来源。

## Trace 与提交契约

decision_basis 由实际工具名、错误码、命中文档、已读冲突、版本范围和本轮工具选择生成，basis_event_steps 指向先前实际Observation；不声称披露内部因果推理。

基线 TC02 三次拒绝均为 ANSWER_NOT_EXTRACTIVE：两次遗漏固定状态后缀，一次后缀前少换行。现在模型可省略answer，仅提交status/citations/missing_info，由服务端统一排版。显式传answer仍执行原Guard，未放宽原文、已读、版本或冲突条件。

连续五次TC02：5/5，成功率 100.0%，平均Guard拒绝 0.0（基线 3）。没有丢弃、外部重试或改分母。

| 连续运行 | 状态 | Guard拒绝 | 首次提交有效 | Trace |
|---|---|---:|---|---|
| 1 | PASS | 0 | True | [Trace](../examples/traces/live/d4cb406a81fa4e4f8f4db9dc03d6d813.json) |
| 2 | PASS | 0 | True | [Trace](../examples/traces/live/7815dd28e7f74c2eb09d6b2636e6e162.json) |
| 3 | PASS | 0 | True | [Trace](../examples/traces/live/a6900ec3faca4826b5a9e53a114469ff.json) |
| 4 | PASS | 0 | True | [Trace](../examples/traces/live/491237b6c58d4a3a9ef8798cf4db6ea9.json) |
| 5 | PASS | 0 | True | [Trace](../examples/traces/live/a4a0a53303834359aa0ee4df02522ed0.json) |

## 实际 Hybrid 与回退

BM25官方六项 6/6；Hybrid官方六项 6/6。策略进入提示词、Schema及执行默认值；仅看到环境变量不算执行证据。

| 用例 | 原样官方断言 | 实际策略顺序（TC05含前置轮） | 成功Hybrid次数 | Trace |
|---|---|---|---:|---|
| TC01 | PASS | ['hybrid'] | 1 | [Trace](../examples/traces/live/6827fe9166a64952b5e134a47f461ecf.json) |
| TC02 | PASS | ['hybrid'] | 1 | [Trace](../examples/traces/live/32d20c70b4f74b40b31bccafbe528f5c.json) |
| TC03 | PASS | ['hybrid', 'bm25'] | 1 | [Trace](../examples/traces/live/0d4286e7a8e34ec0b5caa38d466f5938.json) |
| TC04 | PASS | ['hybrid'] | 1 | [Trace](../examples/traces/live/00e27fb491fb4b2daa0fe36590c2a9cb.json) |
| TC05 | PASS | ['hybrid', 'hybrid'] | 2 | [Trace](../examples/traces/live/a9cd3ce8db644043abdece9f4eeedb11.json) |
| TC06 | PASS | ['hybrid', 'bm25'] | 0 | [Trace](../examples/traces/live/df05242ac584406f81e9fac6fcae0262.json) |

单独注入语义后端不可用：PASS，[Trace](../examples/traces/live/a61034fdd1f24cfe9a307fdb41c8fb73.json)。模型收到RETRIEVAL_UNAVAILABLE后自主选择BM25；没有程序自动重试或把回退冒充Hybrid成功。

## P7 独立 Critic

默认关闭；Guard先强制核验，随后独立上下文审查覆盖与范围，只输出枚举问题代码；反馈仍由主模型决定重交或补查。最多一次修正，Critic和主模型共享原8次上限。API/CLI不能安装评测候选变换钩子。

固定独立集6例：4个显式候选覆盖缺失、2个干净对照。只变换首个真实模型候选，Trace保留原候选与candidate_injection事件；后续Critic和Agent均为真实LLM。此实验不估计自然错误率，也不以模型自评分代替固定事实断言。

最新修正 4/4，整体 6/6；新增最终错误 0；干净对照误修正 0；无效最终引用 0。

平均Critic API调用 1.6667/题；总模型步骤增量 2.3333/题；平均整体延迟增量 4222.6ms；总token增量 21994。单价未知，USD=None。单次小样本时延受服务波动影响。

| 例 | 显式注入 | 关闭Critic正确 | 开启Critic正确 | 开启后的状态 | Trace |
|---|---|---|---|---|---|
| CE01 | omit_duration | False | True | COMPLETED | [Trace](../examples/traces/live/a5689e71d2a74d36848307ef83979d95.json) |
| CE02 | omit_training_deadline | False | True | COMPLETED | [Trace](../examples/traces/live/2444e4210f5c4dc4a3ddd3328ad14f3a.json) |
| CE03 | omit_conflicting_values | False | True | NEEDS_CLARIFICATION | [Trace](../examples/traces/live/784a8a67a7814fb8b635ce0f8ae035d8.json) |
| CE04 | omit_one_scope | False | True | COMPLETED | [Trace](../examples/traces/live/cd96f366cb89452baa6ed4bee17cb091.json) |
| CE05 | None | True | True | COMPLETED | [Trace](../examples/traces/live/c4ae04217332468e9329787150043bbf.json) |
| CE06 | None | True | True | COMPLETED | [Trace](../examples/traces/live/9d14b5c6d33c49a48747cb92c1cdaf4a.json) |

开启Critic的原样官方六项：6/6。

历史运行全部保留：

| 评测运行 | 原状态 | 修正分子/分母 | 文件 |
|---|---|---|---|
| 1858d99745e542f2b793126cdbf27947 | FAIL | 3/4 | [原始结果](../reports/critic_eval_runs/1858d99745e542f2b793126cdbf27947.json) |
| f113b999cc7b496395f24e41464343b9 | PASS | 4/4 | [原始结果](../reports/critic_eval_runs/f113b999cc7b496395f24e41464343b9.json) |

首次受控评测失败是冲突修正时重复补查耗尽预算，增强反馈后用原用例、指标和上限复测。另一次开启Critic的官方TC02出现ValidationError；原实现未存字段级诊断，因此不反推具体违规字段。已加强一致性提示、补充无输入/无隐藏推理的诊断并保留可得用量，复测原六项。

- 官方Critic历史 FAIL 5/6：[记录](../reports/quality/runs/48cfa25cfad845909579cb223bb7d4b4-bm25_critic_official.json)。

## 最终回归与授权

本轮pytest：{'tests': 75, 'failures': 0, 'errors': 0, 'skipped': 0, 'passed': 75}；原锁定隔离环境复测：{'tests': 75, 'failures': 0, 'errors': 0, 'skipped': 0, 'passed': 75}。这次隔离环境是之前建立的环境复测，不伪称再次全新安装。

异常注入、读取后引用核验、安全扫描、原检索指标重算与实际HTTP UI均见 final_validation.json 的真实命令、退出码和日志。原44题检索消融保持数据与标签哈希，不为本轮改指标。

实际授权快照：

```json
{
  "verified_at": "2026-11-10T07:34:38.162488+00:00",
  "status": "CHECKED",
  "private": true,
  "collaborators": [
    {
      "login": "CharlesLTC",
      "role": "admin",
      "read": true
    }
  ],
  "pending_invitations": [],
  "intended_reviewer": null,
  "conclusion": "No intended reviewer account supplied; do not infer their access from repository visibility."
}
```

当前未提供目标评审账号，不自动邀请或修改仓库可见性。最终本地/远程/GitHub API SHA在发布后再次核对，见本机忽略收据 reports/delivery_verification.local.json。
