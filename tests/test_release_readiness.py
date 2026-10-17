from dataclasses import replace
from backend.release_readiness import Evidence, REQUIREMENTS, evaluate, default_report


def test_unknown_evidence_blocks_production():
    result = default_report()
    assert result['production_ready'] is False
    assert result['verified'] == 0
    assert len(result['pending']) == len(REQUIREMENTS)


def test_every_requirement_is_mandatory():
    all_passed = Evidence(**{key: True for key in REQUIREMENTS})
    assert evaluate(all_passed)['production_ready'] is True
    for key in REQUIREMENTS:
        result = evaluate(replace(all_passed, **{key: False}))
        assert result['production_ready'] is False
        assert result['pending'] == [REQUIREMENTS[key]]


def test_truthy_non_boolean_does_not_pass():
    result = evaluate(Evidence(postgres_integration_passed='yes'))
    assert result['verified'] == 0
