"""Stage 4 unit tests: python tests/test_classify.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np

from src.classify import (classify_pair, compute_verification_metrics, determine_thresholds,
                          evaluate_pairs, load_embeddings, save_embeddings)


def _unit(v):
    return v / np.linalg.norm(v)


def _offset_vector(v, lam, rng):
    """Unit vector at a fixed angular offset from v (orthogonal perturbation)."""
    w = rng.normal(size=v.shape[0])
    w -= np.dot(w, v) * v
    w = _unit(w)
    return _unit((1.0 - lam) * v + lam * w)


def test_threshold_ordering_and_eer():
    rng = np.random.default_rng(7)
    genuine = 0.05 + rng.uniform(0, 0.05, size=400)
    impostor = 1.2 + rng.uniform(0, 0.5, size=400)
    report = determine_thresholds(impostor, genuine)
    t01 = report["thresholds"]["far_0.01"]
    t10 = report["thresholds"]["far_0.1"]
    assert t01 <= t10
    assert 1.2 <= t01 <= 1.25, t01
    assert 1.25 <= t10 <= 1.3, t10
    assert report["eer"] < 0.01, report["eer"]
    print("PASS: threshold ordering + separated EER ~ 0")


def test_classify_levels():
    impostor = np.linspace(1.0, 2.0, 1000)
    genuine = np.full(200, 0.1)
    report = determine_thresholds(impostor, genuine)
    assert classify_pair(0.5, "twin", report)["vulnerability"] == "HIGH"
    assert classify_pair(1.05, "sibling", report)["vulnerability"] == "MEDIUM"
    assert classify_pair(1.5, "impostor", report)["vulnerability"] == "LOW"
    g = classify_pair(0.05, "genuine", report)
    assert g["vulnerability"] == "NONE" and g["is_false_reject"] is False
    assert classify_pair(None, "twin", report)["vulnerability"] is None
    print("PASS: HIGH / MEDIUM / LOW / NONE grading + missing branch")


def test_verification_metrics():
    distances = np.array([0.1, 0.2, 0.9, 1.1])
    is_genuine = np.array([True, True, False, False])
    m = compute_verification_metrics(distances, is_genuine, threshold=0.5)
    assert m["true_positives"] == 2 and m["false_rejects"] == 0
    assert m["false_accepts"] == 0 and m["true_negatives"] == 2
    assert m["tar"] == 1.0 and m["far"] == 0.0 and m["accuracy"] == 1.0
    print("PASS: verification metrics on hand-checked case")


def test_save_load_roundtrip():
    rng = np.random.default_rng(1)
    emb = {"s1": _unit(rng.normal(size=512)), "s2": _unit(rng.normal(size=512))}
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "emb.npz")
        save_embeddings(p, emb)
        loaded = load_embeddings(p)
        assert set(loaded) == {"s1", "s2"}
        assert np.allclose(loaded["s1"], emb["s1"], atol=1e-6)
    print("PASS: embeddings npz round-trip")


def test_evaluate_pairs_end_to_end():
    rng = np.random.default_rng(3)
    a = _unit(rng.normal(size=512))
    a2 = _offset_vector(a, 0.05, rng)      # genuine partner (d ~ 0.05)
    twin = _offset_vector(a, 0.30, rng)    # related impostor (d ~ 0.40)
    other = _unit(rng.normal(size=512))    # unrelated impostor (d ~ 1.4)

    embeddings = {"A": a, "A2": a2, "T": twin,
                  "R1": other, "R2": _unit(rng.normal(size=512)),
                  "R3": _unit(rng.normal(size=512))}
    pairs = [
        {"pair_id": "g1", "id_a": "A", "id_b": "A2", "pair_type": "genuine"},
        {"pair_id": "t1", "id_a": "A", "id_b": "T", "pair_type": "twin"},
        {"pair_id": "i1", "id_a": "A", "id_b": "R1", "pair_type": "impostor"},
        {"pair_id": "i2", "id_a": "A", "id_b": "R2", "pair_type": "impostor"},
        {"pair_id": "i3", "id_a": "A", "id_b": "R3", "pair_type": "impostor"},
        {"pair_id": "x1", "id_a": "A", "id_b": "GHOST", "pair_type": "twin"},
    ]
    assessment = evaluate_pairs(pairs, embeddings)

    by_id = {r["pair_id"]: r for r in assessment["results"]}
    assert by_id["x1"]["status"] == "missing_embedding"
    assert by_id["t1"]["vulnerability"] == "HIGH"
    assert by_id["t1"]["distance"] < by_id["i1"]["distance"]
    s = assessment["summary"]
    assert s["twin"]["false_accept_rate"] == 1.0        # twin accepted at 1% FAR point
    assert s["impostor"]["false_accept_rate"] <= 0.34   # general impostors mostly rejected
    assert s["genuine"]["true_accept_rate"] == 1.0
    assert "verification_at_far_1pct" in s
    print("PASS: end-to-end evaluation, twin FAR=1.0 vs impostors, exclusion branch")


if __name__ == "__main__":
    test_threshold_ordering_and_eer()
    test_classify_levels()
    test_verification_metrics()
    test_save_load_roundtrip()
    test_evaluate_pairs_end_to_end()
    print("\nAll Stage 4 tests passed.")
