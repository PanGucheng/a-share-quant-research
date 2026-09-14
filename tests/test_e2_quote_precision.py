import math

from scripts.adjudicate_e2_quote_precision import precision_only


def test_only_amount_precision_is_accepted():
    left = dict(open=10.0, high=11.0, low=9.0, close=10.0, volume=100.0, amount=1000.0)
    assert precision_only(left, dict(left, amount=1000.99))
    assert not precision_only(left, dict(left, amount=1001.01))
    assert not precision_only(left, dict(left, close=10.01))
    assert not precision_only(left, dict(left, volume=101.0))
    assert not precision_only(left, dict(left, amount=math.nan))
    assert not precision_only(left, dict(left, volume=0.0))
