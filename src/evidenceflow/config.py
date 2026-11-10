import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(os.environ.get("EVIDENCEFLOW_ROOT", Path(__file__).resolve().parents[2]))


@dataclass
class Settings:
    root: Path = ROOT
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model_name: str = ""
    timeout: float = 60.0
    max_model_steps: int = 8
    max_tool_calls: int = 12
    strategy: str = "bm25"

    @classmethod
    def from_env(cls, root: Path = ROOT):
        load_dotenv(root / ".env", override=False)
        return cls(
            root=root,
            api_key=os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model_name=os.getenv("LLM_MODEL_NAME", ""),
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
            max_model_steps=int(os.getenv("MAX_MODEL_STEPS", "8")),
            max_tool_calls=int(os.getenv("MAX_TOOL_CALLS", "12")),
            strategy=os.getenv("RETRIEVAL_STRATEGY", "bm25"),
        )

    def live_blocker(self):
        missing = [
            k
            for k, v in {"LLM_API_KEY": self.api_key, "LLM_MODEL_NAME": self.model_name}.items()
            if not v
        ]
        return "Missing " + ", ".join(missing) if missing else None
