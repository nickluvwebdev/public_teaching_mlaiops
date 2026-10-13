import math
from scripts.evaluation_gate import decision


def test_gate_rejects_missing_incumbent_and_nonfinite_scores():
    assert not decision(0.85, None)[0]
    assert not decision(math.nan, 0.80)[0]
    assert not decision(0.85, math.inf)[0]


def test_gate_blocks_noise_and_weaker_candidate():
    assert not decision(0.843, 0.8426)[0]
    assert not decision(0.83, 0.8426)[0]
    assert decision(0.85, 0.8426)[0]


def test_first_registration_requires_explicit_flag_and_floor():
    assert decision(0.85, None, True)[0]
    assert not decision(0.79, None, True)[0]
