from scripts.run_acceptance import run


def test_official_six_offline_scenarios_with_real_tool_execution(service_factory):
    report = run("mock", service_factory())
    assert report["passed"] == report["total"] == 6
    assert report["live_branch_count"] == 0
    assert report["citation_validity"]["rate"] == 1.0
