"""Build latest quality documentation from retained measurements, including all failed trials."""

import json
import xml.etree.ElementTree as ET

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import utc_now, write_json


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def xml_counts(path):
    suites = list(ET.parse(ROOT / path).getroot().iter("testsuite"))
    data = {
        k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")
    }
    data["passed"] = data["tests"] - data["failures"] - data["errors"] - data["skipped"]
    return data


def main():
    validation = read("reports/quality/final_validation.json")
    stability = read("reports/quality/tc02_stability.json")
    critic = read("reports/critic_evaluation.json")
    bm25 = read("reports/quality/bm25_official.json")
    hybrid = read("reports/quality/hybrid_official.json")
    enabled = read("reports/quality/bm25_critic_official.json")
    previous = [
        read(p.relative_to(ROOT))
        for p in sorted((ROOT / "reports/critic_eval_runs").glob("*.json"))
    ]
    all_official = [
        (p, read(p.relative_to(ROOT)))
        for p in sorted((ROOT / "reports/quality/runs").glob("*.json"))
    ]
    failed_official = [
        {
            "path": p.relative_to(ROOT).as_posix(),
            "passed": r["passed"],
            "total": r["total"],
            "status": r["status"],
        }
        for p, r in all_official
        if r["critic_enabled"] and r["status"] != "PASS"
    ]
    summary = {
        "timestamp": utc_now(),
        "status": "PASS"
        if validation["status"] == "PASS"
        and critic["status"] == "PASS"
        and enabled["status"] == "PASS"
        else "FAIL",
        "original_baseline_tests": xml_counts("reports/quality/baseline-pytest.xml"),
        "current_tests": xml_counts("reports/quality/final-pytest.xml"),
        "isolated_tests": xml_counts("reports/quality/isolated-pytest.xml"),
        "bm25_official": {
            "passed": bm25["passed"],
            "total": bm25["total"],
            "status": bm25["status"],
        },
        "hybrid_official": {
            "passed": hybrid["passed"],
            "total": hybrid["total"],
            "status": hybrid["status"],
        },
        "critic_official": {
            "passed": enabled["passed"],
            "total": enabled["total"],
            "status": enabled["status"],
        },
        "tc02": {
            "passed": stability["passed"],
            "total": stability["total"],
            "success_rate": stability["success_rate"],
            "mean_guard_rejections": stability["mean_guard_rejections"],
            "baseline_guard_rejections": stability["baseline_guard_rejections"],
        },
        "critic": {
            "correction_success": critic["correction_success"],
            "new_final_errors": critic["new_final_errors"],
            "clean_control_false_revisions": critic["clean_control_false_revisions"],
            "mean_api_calls": critic["mean_critic_api_calls"],
            "mean_extra_model_steps": critic["mean_extra_model_steps"],
            "mean_extra_latency_ms": critic["mean_extra_latency_ms"],
            "extra_tokens": critic["extra_tokens"],
            "cost_usd": critic["cost_usd"],
        },
        "critic_trials": [
            {
                "run_id": r["run_id"],
                "status": r["status"],
                "correction_success": r["correction_success"],
            }
            for r in previous
        ],
        "failed_critic_official_attempts": failed_official,
        "reviewer_access": read("reports/reviewer_access.json"),
        "references": [
            "reports/quality/final_validation.json",
            "reports/quality/hybrid_execution.json",
            "reports/quality/hybrid_fallback_live.json",
            "reports/quality/verification_all.json",
        ],
    }
    write_json(ROOT / "reports/quality/summary.json", summary)
    lines = [
        "# 最后一轮质量优化与实际验证",
        "",
        f"生成于 {summary['timestamp']}；结果：{summary['status']}。",
        "",
        "在既有项目上增量修改，原有63项测试及官方六项断言保持不变。历史Trace和FAIL不改写；新Trace版本2提供事件来源。",
        "",
        "## Trace 与提交契约",
        "",
        "decision_basis 由实际工具名、错误码、命中文档、已读冲突、版本范围和本轮工具选择生成，basis_event_steps 指向先前实际Observation；不声称披露内部因果推理。",
        "",
        "基线 TC02 三次拒绝均为 ANSWER_NOT_EXTRACTIVE：两次遗漏固定状态后缀，一次后缀前少换行。现在模型可省略answer，仅提交status/citations/missing_info，由服务端统一排版。显式传answer仍执行原Guard，未放宽原文、已读、版本或冲突条件。",
        "",
        f"连续五次TC02：{stability['passed']}/{stability['total']}，成功率 {stability['success_rate']:.1%}，平均Guard拒绝 {stability['mean_guard_rejections']}（基线 {stability['baseline_guard_rejections']}）。没有丢弃、外部重试或改分母。",
        "",
        "| 连续运行 | 状态 | Guard拒绝 | 首次提交有效 | Trace |",
        "|---|---|---:|---|---|",
    ]
    for row in stability["runs"]:
        lines.append(
            f"| {row['run']} | {row['status']} | {row['guard_rejections']} | {row['first_submission_valid']} | [Trace](../{row['trace']}) |"
        )
    lines += [
        "",
        "## 实际 Hybrid 与回退",
        "",
        f"BM25官方六项 {bm25['passed']}/{bm25['total']}；Hybrid官方六项 {hybrid['passed']}/{hybrid['total']}。策略进入提示词、Schema及执行默认值；仅看到环境变量不算执行证据。",
        "",
        "| 用例 | 原样官方断言 | 实际策略顺序（TC05含前置轮） | 成功Hybrid次数 | Trace |",
        "|---|---|---|---:|---|",
    ]
    for row in read("reports/quality/hybrid_execution.json")["cases"]:
        lines.append(
            f"| {row['id']} | {row['official_status']} | {row['search_strategies']} | {row['successful_hybrid_searches']} | [Trace](../{row['traces'][0]}) |"
        )
    fallback = read("reports/quality/hybrid_fallback_live.json")
    lines += [
        "",
        f"单独注入语义后端不可用：{fallback['status']}，[Trace](../{fallback['trace']})。模型收到RETRIEVAL_UNAVAILABLE后自主选择BM25；没有程序自动重试或把回退冒充Hybrid成功。",
        "",
        "## P7 独立 Critic",
        "",
        "默认关闭；Guard先强制核验，随后独立上下文审查覆盖与范围，只输出枚举问题代码；反馈仍由主模型决定重交或补查。最多一次修正，Critic和主模型共享原8次上限。API/CLI不能安装评测候选变换钩子。",
        "",
        "固定独立集6例：4个显式候选覆盖缺失、2个干净对照。只变换首个真实模型候选，Trace保留原候选与candidate_injection事件；后续Critic和Agent均为真实LLM。此实验不估计自然错误率，也不以模型自评分代替固定事实断言。",
        "",
        f"最新修正 {critic['correction_success']['numerator']}/{critic['correction_success']['denominator']}，整体 {critic['critic_correct']}/{critic['total']}；新增最终错误 {critic['new_final_errors']}；干净对照误修正 {critic['clean_control_false_revisions']}；无效最终引用 {critic['invalid_final_citations']}。",
        "",
        f"平均Critic API调用 {critic['mean_critic_api_calls']:.4f}/题；总模型步骤增量 {critic['mean_extra_model_steps']:.4f}/题；平均整体延迟增量 {critic['mean_extra_latency_ms']:.1f}ms；总token增量 {critic['extra_tokens']}。单价未知，USD={critic['cost_usd']}。单次小样本时延受服务波动影响。",
        "",
        "| 例 | 显式注入 | 关闭Critic正确 | 开启Critic正确 | 开启后的状态 | Trace |",
        "|---|---|---|---|---|---|",
    ]
    for row in critic["cases"]:
        lines.append(
            f"| {row['id']} | {row['fault']} | {row['baseline']['correct']} | {row['critic']['correct']} | {row['critic']['result_status']} | [Trace](../{row['critic']['trace']}) |"
        )
    lines += [
        "",
        f"开启Critic的原样官方六项：{enabled['passed']}/{enabled['total']}。",
        "",
        "历史运行全部保留：",
        "",
        "| 评测运行 | 原状态 | 修正分子/分母 | 文件 |",
        "|---|---|---|---|",
    ]
    for row in previous:
        lines.append(
            f"| {row['run_id']} | {row['status']} | {row['correction_success']['numerator']}/{row['correction_success']['denominator']} | [原始结果](../reports/critic_eval_runs/{row['run_id']}.json) |"
        )
    lines += [
        "",
        "首次受控评测失败是冲突修正时重复补查耗尽预算，增强反馈后用原用例、指标和上限复测。另一次开启Critic的官方TC02出现ValidationError；原实现未存字段级诊断，因此不反推具体违规字段。已加强一致性提示、补充无输入/无隐藏推理的诊断并保留可得用量，复测原六项。",
        "",
    ]
    for row in failed_official:
        lines.append(
            f"- 官方Critic历史 {row['status']} {row['passed']}/{row['total']}：[记录](../{row['path']})。"
        )
    lines += [
        "",
        "## 最终回归与授权",
        "",
        f"本轮pytest：{summary['current_tests']}；原锁定隔离环境复测：{summary['isolated_tests']}。这次隔离环境是之前建立的环境复测，不伪称再次全新安装。",
        "",
        "异常注入、读取后引用核验、安全扫描、原检索指标重算与实际HTTP UI均见 final_validation.json 的真实命令、退出码和日志。原44题检索消融保持数据与标签哈希，不为本轮改指标。",
        "",
        "实际授权快照：",
        "",
        "```json",
        json.dumps(summary["reviewer_access"], ensure_ascii=False, indent=2),
        "```",
        "",
        "当前未提供目标评审账号，不自动邀请或修改仓库可见性。最终本地/远程/GitHub API SHA在发布后再次核对，见本机忽略收据 reports/delivery_verification.local.json。",
    ]
    (ROOT / "docs/10-quality-review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k not in ("reviewer_access", "critic_trials")},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
