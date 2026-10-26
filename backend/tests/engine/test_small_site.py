"""A small site (parameter sets v25+, OPEN_QUESTIONS 165): one small server runs the application
and its database, so no managed database and, on AWS, no monitoring fee are priced."""

from collections.abc import Callable

from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak


def small(
    golden: Callable[[str], EstimateInput], reference: ReferenceData, params: str
) -> EstimateInput:
    """The small golden project (one server at 99.0%, 100 users online at once) on AWS."""
    inp = tweak(
        golden("small"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog_version("v5"),
        rate_card=reference.rate_card("v9"),
        parameters=reference.parameter_set(params),
    )
    return answer(inp, "hosting_provider", "aws")


def hosting(inp: EstimateInput) -> set[str]:
    return {ln.label.split(" (")[0] for ln in calculate(inp).lines if ln.bucket == "run.hosting"}


def test_small_site_runs_the_database_on_its_server(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    before = hosting(small(golden, reference, "v24"))
    after = hosting(small(golden, reference, "v25"))
    assert {"Managed database", "Monitoring and logging"} <= before
    assert "Managed database" not in after and "Monitoring and logging" not in after
    assert "Application servers" in after


def test_more_than_one_server_keeps_its_database(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    inp = answer(small(golden, reference, "v25"), "uptime_sla", "99.5")  # two servers (ha)
    assert {"Managed database", "Monitoring and logging", "Load balancer"} <= hosting(inp)


def test_a_bigger_load_keeps_its_database(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    inp = answer(small(golden, reference, "v25"), "peak_concurrent_users", 1000)  # 10 vCPUs
    assert "Managed database" in hosting(inp)


def test_a_small_site_at_99_5_runs_on_one_server(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    """v26 (OPEN_QUESTIONS 171): a single cloud server is itself covered at 99.5%."""
    inp = answer(small(golden, reference, "v26"), "uptime_sla", "99.5")
    parts = hosting(inp)
    assert "Application servers" in parts
    assert not {"Load balancer", "Managed database"} & parts


def test_99_5_with_a_bigger_load_keeps_two_servers(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    inp = answer(small(golden, reference, "v26"), "uptime_sla", "99.5")
    inp = answer(inp, "peak_concurrent_users", 500)  # 5 vCPUs: more than one small server
    assert {"Managed database", "Load balancer"} <= hosting(inp)


def test_servers_follow_the_load_not_the_features(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    """Many features with a small load: one server; the feature points do not decide it."""
    inp = answer(small(golden, reference, "v26"), "uptime_sla", "99.5")
    assert "Load balancer" not in hosting(answer(inp, "size_points", 30))


def test_99_9_keeps_two_servers_on_a_small_site(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    inp = answer(small(golden, reference, "v26"), "uptime_sla", "99.9")
    assert {"Managed database", "Load balancer"} <= hosting(inp)
