"""Independent dense Bartlett covariance oracle, including a missing session."""
import numpy as np
from scripts.review_lightgbm_completed import hac20


def test_hac20_preserves_missing_session_and_matches_dense_kernel():
    x = np.sin(np.arange(80)/5) + .15
    x[23:29] = np.nan
    valid = np.isfinite(x)
    residual = np.where(valid, x - np.nanmean(x), 0.)
    distance = np.abs(np.arange(len(x))[:, None] - np.arange(len(x))[None, :])
    kernel = np.maximum(1-distance/21, 0.)
    expected = np.sqrt(residual @ kernel @ residual)/valid.sum()
    result = hac20(x)
    assert np.isclose(result['se'], expected, rtol=0, atol=1e-14)
    assert result['n'] == 74
    assert not np.isclose(result['se'], hac20(x[valid])['se'])
