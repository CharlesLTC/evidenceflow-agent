import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="EvidenceFlow enterprise policy agent")
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="Ask with evidence; live requires configured credentials")
    ask.add_argument("--question", required=True)
    ask.add_argument("--mode", choices=["live", "mock"], default="live")
    ask.add_argument("--session-id")
    ask.add_argument("--fail-search-count", type=int, default=0)
    ask.add_argument("--max-model-steps", type=int, default=8)
    ask.add_argument("--max-tool-calls", type=int, default=12)
    group = ask.add_mutually_exclusive_group()
    group.add_argument("--critic", dest="enable_critic", action="store_true", default=None)
    group.add_argument("--no-critic", dest="enable_critic", action="store_false")
    args = parser.parse_args()
    from evidenceflow.agent_graph import AgentService
    from evidenceflow.schemas import AskRequest

    result = AgentService().ask(
        AskRequest(**{k: v for k, v in vars(args).items() if k != "command"})
    )
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    return 2 if result.status in ("FAILED", "INCOMPLETE") else 0


if __name__ == "__main__":
    raise SystemExit(main())
