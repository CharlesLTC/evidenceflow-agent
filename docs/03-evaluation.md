# 实际评估结果

生成时间：2026-11-10T07:35:06.592579+00:00。所有表格读取实际 JSON/JUnit。

pytest：{'tests': 75, 'failures': 0, 'errors': 0, 'skipped': 0, 'passed': 75}。mock：6/6；live：6/6（qwen-plus）。

| 用例 | live 验收 | 实际状态 | 输入/输出/Trace |
|---|---|---|---|
| TC01 | PASS | COMPLETED | [输入](../examples/inputs/live-6827fe9166a64952b5e134a47f461ecf.json) / [输出](../examples/outputs/live/6827fe9166a64952b5e134a47f461ecf.json) / [Trace](../examples/traces/live/6827fe9166a64952b5e134a47f461ecf.json) |
| TC02 | PASS | NEEDS_CLARIFICATION | [输入](../examples/inputs/live-32d20c70b4f74b40b31bccafbe528f5c.json) / [输出](../examples/outputs/live/32d20c70b4f74b40b31bccafbe528f5c.json) / [Trace](../examples/traces/live/32d20c70b4f74b40b31bccafbe528f5c.json) |
| TC03 | PASS | INSUFFICIENT_EVIDENCE | [输入](../examples/inputs/live-0d4286e7a8e34ec0b5caa38d466f5938.json) / [输出](../examples/outputs/live/0d4286e7a8e34ec0b5caa38d466f5938.json) / [Trace](../examples/traces/live/0d4286e7a8e34ec0b5caa38d466f5938.json) |
| TC04 | PASS | COMPLETED | [输入](../examples/inputs/live-00e27fb491fb4b2daa0fe36590c2a9cb.json) / [输出](../examples/outputs/live/00e27fb491fb4b2daa0fe36590c2a9cb.json) / [Trace](../examples/traces/live/00e27fb491fb4b2daa0fe36590c2a9cb.json) |
| TC05 | PASS | COMPLETED | [输入](../examples/inputs/live-a9cd3ce8db644043abdece9f4eeedb11.json) / [输出](../examples/outputs/live/a9cd3ce8db644043abdece9f4eeedb11.json) / [Trace](../examples/traces/live/a9cd3ce8db644043abdece9f4eeedb11.json) |
| TC06 | PASS | COMPLETED | [输入](../examples/inputs/live-df05242ac584406f81e9fac6fcae0262.json) / [输出](../examples/outputs/live/df05242ac584406f81e9fac6fcae0262.json) / [Trace](../examples/traces/live/df05242ac584406f81e9fac6fcae0262.json) |

扩展 live：

| 用例 | 结果 | 实际状态 | Trace |
|---|---|---|---|
| TC07 | PASS | COMPLETED | [Trace](../examples/traces/live/db19a94df2564a4c9bc0fc3654e4d72a.json) |
| TC09 | PASS | INCOMPLETE | [Trace](../examples/traces/live/b54700f707ae42439b116aeda32dec4c.json) |
| TC10 | PASS | COMPLETED | [Trace](../examples/traces/live/b6128822e7694c30bdbcbc37c5c5100c.json) |
| TC11 | PASS | COMPLETED | [Trace](../examples/traces/live/841090c1596f4d9089390391832fa2c0.json) |
| TC12 | PASS | FAILED | [Trace](../examples/traces/live/c0d50eb66e5a4bf5bc261c637c284a93.json) |

TC08 错 ID/quote 是确定性 Guard 与替身测试，不宣称为 live。早期 live 缺凭证尝试、扩展 TC11/TC12 失败和对应修复均保留在 reports/logs/attempts 与原始 Trace 中。

引用准确率只统计已读精确原文：{'numerator': 6, 'denominator': 6, 'rate': 1.0}。它不是独立人工语义正确率。fact_supported_rate 未标注，保持未测。

API 测试见 P6 JUnit；界面交互见 reports/ui_smoke.json（实际 HTTP + AppTest，明确 mock 模型，非浏览器像素验收）。

复现：README 中 pytest、run_acceptance、run_extended_live、evaluate_retrieval、verify_artifacts 命令。

本轮 BM25/Hybrid/Critic 对照、连续五次 TC02 和全部失败见 [质量报告](10-quality-review.md)。
