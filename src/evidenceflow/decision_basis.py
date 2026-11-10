"""Factual action captions derived from recorded events, never inferred hidden reasoning."""


def observation_caption(name, args, observation):
    if "error" in observation:
        return f"{name} 返回 {observation['error'].get('code', 'ERROR')}，失败 Observation 已交给模型。"
    if name == "search_documents":
        ids = list(dict.fromkeys(h["doc_id"] for h in observation.get("hits", [])))
        strategy = observation.get("strategy", args.get("strategy", "default"))
        return f"{strategy} 检索返回 {len(ids)} 篇候选（{', '.join(ids[:6]) or '无结果'}），尚不具备引用资格。"
    if name == "read_document":
        context = observation.get("evidence_context", {})
        conflicts = context.get("conflicts", [])
        if conflicts:
            values = "/".join(str(v) for c in conflicts for v in c["values"])
            return f"已读取 {observation['doc_id']} 原文，当前已读资料存在 {values} 的未解决冲突。"
        return f"已读取 {observation.get('doc_id', args.get('doc_id'))} 的 {len(observation.get('chunks', []))} 个原文片段。"
    if name == "inspect_versions":
        scopes_missing = sum(v.get("scope") is None for v in observation.get("versions", []))
        return f"版本查询返回 {len(observation.get('versions', []))} 个版本，{scopes_missing} 个适用范围未知；优先级为 {observation.get('precedence')}。"
    if name == "submit_answer":
        if observation.get("critic", {}).get("verdict") == "REVISE":
            return "Guard 已通过，独立 Critic 请求修正：" + ", ".join(
                observation["critic"]["issue_codes"]
            )
        if observation.get("valid"):
            return "候选已通过原文、已读资格、版本、冲突及摘录格式校验。"
        return "Guard 拒绝候选：" + "; ".join(observation.get("errors", [])[:3])
    return f"{name} 的结构化结果已返回。"


def decision_caption(events, calls):
    previous = next((e for e in reversed(events) if e["kind"] == "tool_observation"), None)
    action = "、".join(c["name"] for c in calls)
    if previous is None:
        return f"当前轮尚无工具 Observation；模型选择 {action}。", []
    obs = previous["observation"]
    source = previous["tool_name"]
    prefix = observation_caption(source, previous["arguments"], obs)
    context = obs.get("evidence_context", {})
    if context.get("conflicts") and any(c["name"] == "inspect_versions" for c in calls):
        outcome = "本轮选择补查版本的适用范围和效力。"
    elif "error" in obs and any(c["name"] == "search_documents" for c in calls):
        strategies = [
            c["arguments"].get("strategy", "configured default")
            for c in calls
            if c["name"] == "search_documents"
        ]
        outcome = f"本轮重新检索，所选策略为 {', '.join(strategies)}。"
    else:
        outcome = f"本轮模型选择 {action}。"
    return prefix + outcome, [previous["step"]]
