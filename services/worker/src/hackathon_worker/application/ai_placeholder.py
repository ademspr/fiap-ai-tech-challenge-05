from hackathon_contracts import (
    ArchitecturalRisk,
    BasicRecommendation,
    IdentifiedComponent,
    TechnicalReportV1,
)


def run_placeholder_analysis(
    diagram_bytes: bytes, content_hint: str
) -> tuple[TechnicalReportV1, int]:
    """Placeholder until real IA integration. Returns (report, tokens_used)."""
    report = TechnicalReportV1(
        schema_version=1,
        identified_components=[
            IdentifiedComponent(
                id="cmp-1",
                name="Placeholder component",
                description="Detected during MVP placeholder analysis.",
            )
        ],
        architectural_risks=[
            ArchitecturalRisk(
                id="risk-1",
                title="Single point of processing",
                description="Worker is a single consumer; scale-out not yet modeled.",
                severity="medium",
            )
        ],
        basic_recommendations=[
            BasicRecommendation(
                id="rec-1",
                title="Add redundancy",
                description="Introduce multiple worker replicas and idempotent completion.",
            )
        ],
        tokens_used=42,
        model_metadata={
            "engine": "placeholder-v0",
            "input_byte_length": str(len(diagram_bytes)),
            "content_hint": content_hint,
        },
    )
    return report, report.tokens_used
