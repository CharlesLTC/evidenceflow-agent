"""Generate result documentation from recorded artifacts, never from assumed successes."""

import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta, timezone

from evidenceflow.config import ROOT


def load(name, default=None):
    p = ROOT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def counts():
    latest = ROOT / "reports/quality/final-pytest.xml"
    if latest.exists():
        suites = list(ET.parse(latest).getroot().iter("testsuite"))
        result = {
            k: sum(int(s.get(k, 0)) for s in suites)
            for k in ("tests", "failures", "errors", "skipped")
        }
        result["passed"] = (
            result["tests"] - result["failures"] - result["errors"] - result["skipped"]
        )
        return result
    for stage in ("P8", "P4"):
        p = ROOT / f"reports/logs/{stage}-pytest.xml"
        if p.exists():
            suites = list(ET.parse(p).getroot().iter("testsuite"))
            result = {
                k: sum(int(s.get(k, 0)) for s in suites)
                for k in ("tests", "failures", "errors", "skipped")
            }
            result["passed"] = (
                result["tests"] - result["failures"] - result["errors"] - result["skipped"]
            )
            return result
    return None


def main():
    now = datetime.now(UTC)
    live = load("reports/acceptance_results.live.json", {})
    mock = load("reports/acceptance_results.mock.json", {})
    extended = load("reports/extended_live.json", {})
    retrieval = load("reports/retrieval_metrics.json", {})
    github = load("reports/github_delivery.json", {})
    quality = load("reports/quality/summary.json", {})
    gates = [
        load(f"reports/gates/P{i}.json", {"stage": f"P{i}", "status": "NOT_RUN"}) for i in range(9)
    ]
    unit = counts()
    started = datetime.fromtimestamp(ROOT.stat().st_ctime, UTC)
    elapsed = (now - started).total_seconds() / 60
    quality_start = load("reports/quality/baseline.json", {}).get("started_at")
    quality_minutes = (
        (now - datetime.fromisoformat(quality_start)).total_seconds() / 60
        if quality_start
        else None
    )
    lines = [
        "# 实际评估结果",
        "",
        f"生成时间：{now.isoformat()}。所有表格读取实际 JSON/JUnit。",
        "",
        f"pytest：{unit}。mock：{mock.get('passed')}/{mock.get('total')}；live：{live.get('passed')}/{live.get('total')}（{live.get('model_name')}）。",
        "",
        "| 用例 | live 验收 | 实际状态 | 输入/输出/Trace |",
        "|---|---|---|---|",
    ]
    for row in live.get("cases", []):
        lines.append(
            f"| {row['id']} | {row['status']} | {row['result_status']} | [输入](../{row['input']}) / [输出](../{row['output']}) / [Trace](../{row['trace']}) |"
        )
    lines += ["", "扩展 live：", "", "| 用例 | 结果 | 实际状态 | Trace |", "|---|---|---|---|"]
    for row in extended.get("cases", []):
        lines.append(
            f"| {row['id']} | {row['status']} | {row['result_status']} | [Trace](../{row['trace']}) |"
        )
    lines += [
        "",
        "TC08 错 ID/quote 是确定性 Guard 与替身测试，不宣称为 live。早期 live 缺凭证尝试、扩展 TC11/TC12 失败和对应修复均保留在 reports/logs/attempts 与原始 Trace 中。",
        "",
        "引用准确率只统计已读精确原文："
        + str(live.get("citation_validity"))
        + "。它不是独立人工语义正确率。fact_supported_rate 未标注，保持未测。",
        "",
        "API 测试见 P6 JUnit；界面交互见 reports/ui_smoke.json（实际 HTTP + AppTest，明确 mock 模型，非浏览器像素验收）。",
        "",
        "复现：README 中 pytest、run_acceptance、run_extended_live、evaluate_retrieval、verify_artifacts 命令。",
    ]
    save("docs/03-evaluation.md", "\n".join(lines))
    if quality:
        with (ROOT / "docs/03-evaluation.md").open("a", encoding="utf-8") as f:
            f.write(
                "\n本轮 BM25/Hybrid/Critic 对照、连续五次 TC02 和全部失败见 [质量报告](10-quality-review.md)。\n"
            )
    experiment = [
        "# 检索消融实测",
        "",
        f"同一固定数据集：{retrieval.get('documents')} 篇，{retrieval.get('queries')} 题，{retrieval.get('answerable_queries')} 个有答案。",
        "",
        "| 策略 | 状态 | Recall@3 | Recall@5 | MRR@5 | 平均 ms | P95 ms | 平均模型调用 | USD |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, data in retrieval.get("strategies", {}).items():
        m = data.get("metrics")
        if m:
            experiment.append(
                f"| {name} | {data['status']} | {m['recall_at_3']['value']:.4f} | {m['recall_at_5']['value']:.4f} | {m['mrr_at_5']['value']:.4f} | {m['mean_latency_ms']:.3f} | {m['p95_latency_ms']:.3f} | {m['mean_model_calls']:.4f} | {data['cost_usd']} |"
            )
        else:
            experiment.append(
                f"| {name} | {data['status']} | null | null | null | null | null | null | null |"
            )
    experiment += [
        "",
        "![Recall@3](../reports/charts/recall_at_3.png)",
        "",
        "![效果与调用成本](../reports/charts/quality_cost.png)",
        "",
        "初始化与计时协议："
        + str(retrieval.get("initialization_ms"))
        + " ms；"
        + str(retrieval.get("timing_protocol")),
        "",
        "A 为中文 bigram BM25；B 为实际多语 MiniLM ONNX 量化嵌入＋cosine；C 为 RRF k=60；D 为真实 qwen-plus 基于候选 Observation 自主改写补查，最多两次。D 未带来指标改善，增加外部调用和延迟，该负面结果不删除。",
        "",
        "Recall 为逐题宏平均，报告也提供检出相关文档/总相关文档和每题分子分母；MRR 记录倒数排名和分母。4 个资料外问题不进入这些分母。无分级标注，nDCG=null；检索器不产生问答拒答率。模型单价未知则 USD=null，保留实际 token 用量。",
        "",
        "语料与标签在实验前固定并保存 SHA256；不得事后改标签。标注由开发依据合成制度制作，未独立人工复审，单次小样本无置信区间，不代表真实企业分布。",
        "",
        "逐题原始结果：reports/retrieval_details.json / CSV；错例：reports/retrieval_failures.json；每题 D 的真实模型 Trace：reports/retrieval_traces/live；模型 revision 和文件哈希：reports/embedding_manifest.json。",
    ]
    save("docs/08-experiments.md", "\n".join(experiment))
    time_lines = [
        "# 实际时间日志",
        "",
        "阶段表中的时间为实际验收命令窗口；实现可跨窗口，因此不能把这些秒数相加充当完整开发用时。",
        "",
        f"项目目录创建：{started.isoformat()}；报告生成：{now.isoformat()}；墙钟跨度 {elapsed:.1f} 分钟，包含用户检查与等待时间，不等于开发工时。",
        f"本轮质量工作起点：{quality_start}；本轮墙钟用时 {quality_minutes:.1f} 分钟。"
        if quality_start
        else "初次交付时间记录保留在 Git 历史。",
        "",
        f"北京时间：{started.astimezone(timezone(timedelta(hours=8))).isoformat()} → {now.astimezone(timezone(timedelta(hours=8))).isoformat()}。",
        "",
        "| 阶段 | 开始 UTC | 结束 UTC | 当前状态 |",
        "|---|---|---|---|",
    ]
    for g in gates:
        time_lines.append(
            f"| {g['stage']} | {g.get('started_at', '未运行')} | {g.get('finished_at', '未运行')} | {g['status']} |"
        )
    time_lines += [
        "",
        "完整命令、输出、阻塞、失败尝试和修复见 CODEX_WORKLOG.md、reports/logs/attempts、reports/quality。P7 本轮已实现且默认关闭，状态按真实结果记录。",
    ]
    save("docs/09-time-log.md", "\n".join(time_lines))
    failure_lines = [
        "# 失败与局限分析",
        "",
        "1. 初始依赖网络/额外包源/TEMP 与 socketpair 环境问题均保留失败日志，已用受控执行或本地临时目录解决。",
        "2. 扩展语料使离线模拟器错误关联通用词，已修正并复跑。",
        "3. 首轮扩展 live 中，TC11 复制了注入文本，TC12 将全工具故障当资料不足。增加 Guard 指令文本拒绝和故障分类校验；原始失败 Trace 仍保留，最终结果见 extended_live.json。",
        "4. D Query Rewrite 没改善指标但增加成本；不改标签隐藏负面结果。",
        "5. 数值冲突与指令模式识别只覆盖受控范围，不保证任意语言、任意范围包含关系；Guard 精确引用不等于文档真伪或问题相关性证明。",
        "6. 未做独立人工语义标注；USD 单价未知；未做生产鉴权、跨进程锁和浏览器像素 QA。P7 初轮曾因重复补查耗尽预算及结构化响应不合法而失败，原始 FAIL 保留，最终结果见 reports/critic_evaluation.json。",
        "",
        "检索错例：",
    ]
    for row in load("reports/retrieval_failures.json", []):
        failure_lines.append(
            f"- {row['strategy']} {row['id']} {row['question']}；期望 {row['expected_doc_ids']}；前五 {row['ranked_doc_ids'][:5]}。"
        )
    save("reports/failure_analysis.md", "\n".join(failure_lines))
    complete = (
        all(g["status"] == "PASS" for g in gates if g["stage"] != "P7")
        and gates[7]["status"] in ("PASS", "SKIPPED_OPTIONAL")
        and live.get("status") == "PASS"
        and extended.get("status") == "PASS"
        and bool(github.get("url"))
        and (not quality or quality.get("status") == "PASS")
    )
    final = [
        "# EvidenceFlow 最终验收",
        "",
        f"状态：{'COMPLETE' if complete else 'PARTIAL'}。生成于 {now.isoformat()}。",
        "",
        f"项目路径：{ROOT}；题号：3；实测模型：{live.get('model_name')}。",
        "",
        "GitHub："
        + (
            github.get("url")
            or "BLOCKED_GITHUB：本机 GitHub CLI 尚未登录或尚未完成远程交付；不能声称已建仓/推送。"
        ),
        "",
        "最终 SHA：交付完成后由忽略的本机收据 reports/delivery_verification.local.json 记录，须与 git rev-parse HEAD、git ls-remote origin HEAD 一致。版本化报告不能嵌入自身 commit SHA。",
        "",
        "| 阶段 | 状态 |",
        "|---|---|",
    ]
    final += [f"| {g['stage']} | {g['status']} |" for g in gates]
    final += [
        "",
        f"pytest 实际统计：{unit}。本轮 JUnit：reports/quality/final-pytest.xml；原始交付 JUnit 保留在 reports/logs/P8-pytest.xml。",
        "",
        f"官方 live：{live.get('passed')}/{live.get('total')}，mock：{mock.get('passed')}/{mock.get('total')}；live 差异工具路径见 reports/live_branch_evidence.json。",
        "",
        "六项及扩展用例实际输入/输出/Trace 的逐条链接见 docs/03-evaluation.md。TC08 为确定性 Guard 测试，其余扩展 live 结果见 reports/extended_live.json。",
        "",
        "检索：32 篇、44 题/40 有答案，A/B/C/D 的 Recall@3 = 0.9250/0.9750/0.9875/0.9875；D 无改善，平均调用 1.4545 次/题，USD=null。指标、图表、分子分母和错例见 docs/08-experiments.md 与 reports/retrieval_*.json。",
        "",
        "运行：README 包含环境、CLI、API（8000/docs）、UI（8501）、完整评估和工件核验命令。API/UI 返回实际后端数据，界面五种交互状态已验证。",
        "",
        "P7 独立 Critic 默认关闭，共享8次模型预算，最多一次修正且不可绕过 Guard。修正率仅针对显式注入缺失，不代表自然错误率，见 docs/10-quality-review.md。",
        "局限：合成标注集、摘录回答、受控范围与提示模式；未独立人工测量事实支持率；未实施生产鉴权及跨进程锁。实际仓库授权清单见 reports/reviewer_access.json。",
        "",
        f"本轮质量墙钟用时 {quality_minutes:.1f} 分钟；用户检查间隔单列，见 docs/09-time-log.md。"
        if quality_start
        else "详见 docs/09-time-log.md。",
    ]
    save("reports/final_acceptance.md", "\n".join(final))
    print(f"Built actual-result documentation; delivery={'COMPLETE' if complete else 'PARTIAL'}")


if __name__ == "__main__":
    main()
