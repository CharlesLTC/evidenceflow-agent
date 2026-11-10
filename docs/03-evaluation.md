# 实际评估结果

生成时间：2026-11-10T05:08:39.060246+00:00。所有表格读取实际 JSON/JUnit。

pytest：{'tests': 63, 'failures': 0, 'errors': 0, 'skipped': 0, 'passed': 63}。mock：6/6；live：6/6（qwen-plus）。

| 用例 | live 验收 | 实际状态 | 输入/输出/Trace |
|---|---|---|---|
| TC01 | PASS | COMPLETED | [输入](../examples/inputs/live-950eaa1d6aed49659f1c4d35dd41c55b.json) / [输出](../examples/outputs/live/950eaa1d6aed49659f1c4d35dd41c55b.json) / [Trace](../examples/traces/live/950eaa1d6aed49659f1c4d35dd41c55b.json) |
| TC02 | PASS | NEEDS_CLARIFICATION | [输入](../examples/inputs/live-3408645f3b73421896b3fe948b941ce5.json) / [输出](../examples/outputs/live/3408645f3b73421896b3fe948b941ce5.json) / [Trace](../examples/traces/live/3408645f3b73421896b3fe948b941ce5.json) |
| TC03 | PASS | INSUFFICIENT_EVIDENCE | [输入](../examples/inputs/live-27a4c53118f343f18c220173e655d1ba.json) / [输出](../examples/outputs/live/27a4c53118f343f18c220173e655d1ba.json) / [Trace](../examples/traces/live/27a4c53118f343f18c220173e655d1ba.json) |
| TC04 | PASS | COMPLETED | [输入](../examples/inputs/live-56fc1f4308c9442a961359238a1fca26.json) / [输出](../examples/outputs/live/56fc1f4308c9442a961359238a1fca26.json) / [Trace](../examples/traces/live/56fc1f4308c9442a961359238a1fca26.json) |
| TC05 | PASS | COMPLETED | [输入](../examples/inputs/live-03ec06c28887493ebe7a23b775ada0c4.json) / [输出](../examples/outputs/live/03ec06c28887493ebe7a23b775ada0c4.json) / [Trace](../examples/traces/live/03ec06c28887493ebe7a23b775ada0c4.json) |
| TC06 | PASS | COMPLETED | [输入](../examples/inputs/live-921123a8ab1d4908992a7c46134f0069.json) / [输出](../examples/outputs/live/921123a8ab1d4908992a7c46134f0069.json) / [Trace](../examples/traces/live/921123a8ab1d4908992a7c46134f0069.json) |

扩展 live：

| 用例 | 结果 | 实际状态 | Trace |
|---|---|---|---|
| TC07 | PASS | COMPLETED | [Trace](../examples/traces/live/8467a5f1139a4f56b004dc463479589b.json) |
| TC09 | PASS | INCOMPLETE | [Trace](../examples/traces/live/a94b88372f1a42d896c906bd72259959.json) |
| TC10 | PASS | COMPLETED | [Trace](../examples/traces/live/1c4d62bc485443c887fab981d2b41b55.json) |
| TC11 | PASS | COMPLETED | [Trace](../examples/traces/live/e9a631d4584f45f88039bd84023eebd8.json) |
| TC12 | PASS | INCOMPLETE | [Trace](../examples/traces/live/187a20a3d2e84db8a4af5333bcfe8069.json) |

TC08 错 ID/quote 是确定性 Guard 与替身测试，不宣称为 live。早期 live 缺凭证尝试、扩展 TC11/TC12 失败和对应修复均保留在 reports/logs/attempts 与原始 Trace 中。

引用准确率只统计已读精确原文：{'numerator': 6, 'denominator': 6, 'rate': 1.0}。它不是独立人工语义正确率。fact_supported_rate 未标注，保持未测。

API 测试见 P6 JUnit；界面交互见 reports/ui_smoke.json（实际 HTTP + AppTest，明确 mock 模型，非浏览器像素验收）。

复现：README 中 pytest、run_acceptance、run_extended_live、evaluate_retrieval、verify_artifacts 命令。
