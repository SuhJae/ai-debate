import asyncio

from app.api.routes import llm_providers


def test_llm_providers_exposes_default_models():
    response = asyncio.run(llm_providers())
    body = response.model_dump(mode="json")
    providers = body["providers"]

    assert providers["codex"]["default_model"] == "gpt-5.4"
    assert providers["gemini"]["default_model"] == "gemini-2.5-pro"
    assert providers["claude"]["default_model"] == "claude-sonnet-4-6"
    assert any(model["id"] == "gpt-5.4" and model["default"] for model in providers["codex"]["models"])
