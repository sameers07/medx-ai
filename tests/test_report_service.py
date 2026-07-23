"""Tests ReportService with a fake OpenAI client — no real API key/network needed."""
from app.config.model_config import config
from app.services.report_service import ReportService

_REPORT_CONFIG = config["report_generation"]


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        return type("Response", (), {"choices": [_FakeChoice(self._content)]})()


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeOpenAIClient:
    def __init__(self, content="Findings are consistent with mild cardiomegaly."):
        self.chat = _FakeChat(content)


def test_generate_report_returns_llm_content():
    fake_client = _FakeOpenAIClient()
    service = ReportService(client=fake_client)

    report = service.generate_report({"Cardiomegaly": 0.92, "Pneumonia": 0.03})

    assert report == "Findings are consistent with mild cardiomegaly."


def test_generate_report_uses_configured_model_and_max_tokens():
    fake_client = _FakeOpenAIClient()
    service = ReportService(client=fake_client)

    service.generate_report({"Cardiomegaly": 0.92})

    call_kwargs = fake_client.chat.completions.last_call_kwargs
    assert call_kwargs["model"] == _REPORT_CONFIG["model"]
    assert call_kwargs["max_tokens"] == _REPORT_CONFIG["max_tokens"]


def test_generate_report_includes_findings_in_prompt():
    fake_client = _FakeOpenAIClient()
    service = ReportService(client=fake_client)

    service.generate_report({"Cardiomegaly": 0.92, "Pneumonia": 0.03})

    user_message = fake_client.chat.completions.last_call_kwargs["messages"][1]["content"]
    assert "Cardiomegaly: 0.92" in user_message
    assert "Pneumonia: 0.03" in user_message
