from calculator import divide


def test_zero_divisor_returns_none() -> None:
    assert divide(10, 0) is None
