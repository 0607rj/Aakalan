"""Scenarios (brief 7.6): re-price the same snapshot with questionnaire overrides
(cloud vs on-prem, AWS vs Indian cloud, LLM API vs self-hosted GPU, open source vs licensed,
deadline variants) and return side-by-side summaries."""

from pydantic import BaseModel, ConfigDict

from app.services.engine.core import calculate
from app.services.engine.inputs import AnswerIn, EstimateInput
from app.services.engine.outputs import ConfidenceOut, GroupTotal, Timeline, Totals


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    overrides: dict[str, object]


class ScenarioResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    overrides: dict[str, object]
    feasible: bool
    message: str | None
    totals: Totals | None
    by_stage: list[GroupTotal]
    timeline: Timeline
    confidence: ConfidenceOut


def with_overrides(inp: EstimateInput, overrides: dict[str, object]) -> EstimateInput:
    """Replace (or add) answers for the overridden keys; their cited requirements are kept."""
    answers = {a.key: a for a in inp.answers}
    for key, value in overrides.items():
        prior = answers.get(key)
        answers[key] = AnswerIn(
            key=key, value=value, requirement_ids=prior.requirement_ids if prior else []
        )
    return inp.model_copy(update={"answers": list(answers.values())})


def run_scenarios(inp: EstimateInput, scenarios: list[Scenario]) -> list[ScenarioResult]:
    out = []
    for sc in [Scenario(name="Baseline", overrides={}), *scenarios]:
        result = calculate(
            EstimateInput.model_validate(with_overrides(inp, sc.overrides).model_dump())
        )
        out.append(
            ScenarioResult(
                name=sc.name,
                overrides=sc.overrides,
                feasible=result.feasible,
                message=result.infeasibility.message if result.infeasibility else None,
                totals=result.totals,
                by_stage=result.by_stage,
                timeline=result.timeline,
                confidence=result.confidence,
            )
        )
    return out
