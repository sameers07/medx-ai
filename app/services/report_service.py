"""ReportService — turns model findings into a narrative radiology report via an LLM."""
from openai import OpenAI

from app.config.model_config import config
from app.config.settings import settings

_REPORT_CONFIG = config["report_generation"]

_SYSTEM_PROMPT = (
    "You are a radiologist writing a concise chest X-ray report from a model's predicted "
    "disease probabilities. Note higher-probability findings as more likely present and "
    "lower-probability ones as not significant. A few sentences, plain clinical language, "
    "no disclaimers about being an AI."
)


class ReportService:
    def __init__(self, client: OpenAI | None = None):
        self.client = client or OpenAI(api_key=settings.llm_api_key)

    def generate_report(self, findings: dict[str, float]) -> str:
        findings_text = "\n".join(
            f"{label}: {prob:.2f}" for label, prob in sorted(findings.items(), key=lambda kv: -kv[1])
        )
        response = self.client.chat.completions.create(
            model=_REPORT_CONFIG["model"],
            max_tokens=_REPORT_CONFIG["max_tokens"],
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": findings_text},
            ],
        )
        return response.choices[0].message.content
