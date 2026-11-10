import os
import sys
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui.backend import Backend

st.set_page_config(page_title="EvidenceFlow · 制度证据问答", page_icon="◈", layout="wide")
st.title("EvidenceFlow")
st.caption("企业制度问答 · 每条事实都有原文 · 合成制度演示库")

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.turns = []

with st.sidebar:
    st.subheader("会话")
    mode = st.selectbox(
        "运行模式",
        ["live", "mock"],
        key="mode",
        help="live 调用真实模型；mock 为离线模拟，不能证明模型决策效果。",
    )
    if mode == "mock":
        st.warning("离线模拟模式")
    base_url = st.text_input(
        "后端地址", os.getenv("EVIDENCEFLOW_API_URL", "http://127.0.0.1:8000"), key="backend_url"
    )
    failures = st.selectbox(
        "检索故障注入", [0, 1, 2], key="failures", help="0 为正常；1 为首次超时；2 为连续两次超时。"
    )
    if st.button("新会话", key="new_session"):
        st.session_state.session_id = uuid.uuid4().hex
        st.session_state.turns = []
        st.session_state.pop("last_result", None)
        st.rerun()
    st.caption("Session: " + st.session_state.session_id[:12])
    for turn in st.session_state.turns[-8:]:
        st.markdown("**" + turn["question"] + "**")
        st.caption(turn["status"] + " · " + turn["mode"])

backend = Backend(base_url)
left, right = st.columns([1.35, 1], gap="large")
with left:
    question = st.text_area(
        "你的问题", key="question", placeholder="例如：差旅报销期限是多久？", height=90
    )
    if st.button("核查制度", key="ask", type="primary", disabled=not question.strip()):
        try:
            with st.spinner("正在检索原文并核验证据…"):
                result = backend.ask(question.strip(), mode, st.session_state.session_id, failures)
            st.session_state.last_result = result
            st.session_state.turns.append(result)
            st.session_state.pop("last_trace", None)
        except Exception:
            st.error("后端连接或请求失败。请检查后端服务和地址后重试。")
            st.session_state.pop("last_result", None)
    result = st.session_state.get("last_result")
    if result:
        st.subheader("核查结果")
        status = result["status"]
        st.caption(result["mode"] + " · " + result["model_name"] + " · " + status)
        if status == "COMPLETED":
            st.success("已依据原文完成核查")
        elif status in ("FAILED", "INCOMPLETE"):
            st.error("核查失败" if status == "FAILED" else "核查未完成")
        else:
            st.warning("需要补充确认" if status == "NEEDS_CLARIFICATION" else "资料不足")
        st.text(result["answer"])
        for c in result["citations"]:
            with st.expander(f"{c['doc_id']} · {c['version_date']} · 原文", expanded=True):
                st.text(c["quote"])
                st.caption(c["chunk_id"])
        if result["conflicts"]:
            st.warning("存在未解决的制度冲突")
            st.json(result["conflicts"])
        if result["missing_info"]:
            st.write("待确认：" + "；".join(result["missing_info"]))
        st.caption(
            f"模型决策 {result['steps_used']} 次 · 工具执行 {result['tool_calls_used']} 次 · {result['latency_ms'] / 1000:.2f}s"
        )

with right:
    st.subheader("决策时间线")
    result = st.session_state.get("last_result")
    if result:
        try:
            trace = backend.request("GET", f"/traces/{result['trace_id']}?mode={result['mode']}")
            st.caption("Trace: " + trace["trace_id"])
            for event in trace["events"]:
                label = event.get("tool_name", event["kind"])
                if isinstance(event.get("next_action"), list):
                    label = ", ".join(event["next_action"])
                with st.expander(f"{event['step']:02} · {event['kind']} · {label}"):
                    st.json(event)
                if event.get("tool_name") == "search_documents" and event.get(
                    "observation", {}
                ).get("hits"):
                    st.dataframe(event["observation"]["hits"], hide_index=True)
        except Exception:
            st.error("读取 Trace 失败；回答结果已保留。")
    else:
        st.info("提交问题后，这里显示实际模型动作与工具结果。")

with st.expander("检索实验与验收指标"):
    try:
        data = backend.request("GET", "/metrics")
        retrieval = data.get("retrieval")
        if retrieval:
            rows = []
            for name, info in retrieval["strategies"].items():
                m = info.get("metrics")
                rows.append(
                    {
                        "策略": name,
                        "状态": info["status"],
                        "Recall@3": m["recall_at_3"]["value"] if m else None,
                        "MRR@5": m["mrr_at_5"]["value"] if m else None,
                        "平均耗时 ms": m["mean_latency_ms"] if m else None,
                    }
                )
            st.dataframe(rows, hide_index=True)
        else:
            st.caption("尚未生成检索实验报告。")
        st.json(data.get("acceptance"))
    except Exception:
        st.caption("指标服务暂不可用。")
