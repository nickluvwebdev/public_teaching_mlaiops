import numpy as np
import pytest
from monitoring.drift import psi, ks_statistic


def test_identical_distribution_has_zero_drift():
    a = np.arange(100, dtype=float)
    assert psi(a, a) == 0
    assert ks_statistic(a, a) == 0


def test_shift_is_detected_even_for_constant_reference():
    assert psi(np.ones(500), np.ones(500) * 10) > .1
    assert ks_statistic(np.ones(500), np.ones(500) * 10) == 1


@pytest.mark.parametrize("bad", [[], [np.nan], [np.inf]])
def test_bad_windows_fail_instead_of_silent_stability(bad):
    with pytest.raises(ValueError):
        psi(np.arange(10), bad)
    with pytest.raises(ValueError):
        ks_statistic(np.arange(10), bad)
