"""Tests for the prompt builder module."""

from hackathon_worker.application.prompt_builder import build_system_prompt, build_user_prompt


def test_build_system_prompt_contains_key_instructions():
    prompt = build_system_prompt()
    assert "analysis_summary" in prompt
    assert "identified_components" in prompt
    assert "architectural_risks" in prompt
    assert "basic_recommendations" in prompt
    assert "JSON" in prompt


def test_build_system_prompt_contains_guardrails():
    prompt = build_system_prompt()
    # Guardrail: only return JSON, no extra text
    assert "ONLY the JSON" in prompt
    # Guardrail: don't invent things
    assert "invent" in prompt.lower() or "not visible" in prompt.lower()


def test_build_user_prompt_includes_content_hint():
    prompt = build_user_prompt(content_hint="image/png")
    assert "image/png" in prompt


def test_build_user_prompt_includes_content_hint_pdf():
    prompt = build_user_prompt(content_hint="application/pdf")
    assert "application/pdf" in prompt


def test_build_system_prompt_is_string():
    assert isinstance(build_system_prompt(), str)
    assert len(build_system_prompt()) > 100


def test_build_user_prompt_is_string():
    assert isinstance(build_user_prompt("image/png"), str)
    assert len(build_user_prompt("image/png")) > 10
