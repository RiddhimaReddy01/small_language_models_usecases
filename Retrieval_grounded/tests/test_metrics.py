from src.metrics import compute_em, compute_f1


def test_compute_em_exact_matches():
    score = compute_em(["Paris", "Blue"], ["Paris", "Green"])
    assert score == 50.0


def test_compute_f1_non_zero_overlap():
    score = compute_f1(["the big apple"], ["big apple"])
    assert score > 0.0
