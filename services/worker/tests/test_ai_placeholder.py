from hackathon_worker.application.ai_placeholder import run_placeholder_analysis


def test_run_placeholder_analysis_tokens_and_structure():
    payload = b"\x89PNG"
    report, tokens = run_placeholder_analysis(payload, "image/png")
    assert tokens == 42
    assert report.tokens_used == 42
    assert report.model_metadata is not None
    assert report.model_metadata.get("input_byte_length") == str(len(payload))
    assert report.model_metadata.get("content_hint") == "image/png"
    assert len(report.identified_components) >= 1
    assert len(report.architectural_risks) >= 1
    assert len(report.basic_recommendations) >= 1
