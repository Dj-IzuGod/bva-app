"""Stage 3 unit tests: python tests/test_embed.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np

from src.embed import cosine_similarity, embed_pair, euclidean_distance, get_embedding

def test_embedding_shape_and_norm():
 rng = np.random.default_rng(42)
 fake_face = rng.integers(0, 255, size=(160, 160, 3), dtype=np.uint8)
 emb = get_embedding(fake_face)
 assert emb.shape == (512,), f"expected (512,), got {emb.shape}"
 assert abs(np.linalg.norm(emb) - 1.0) < 1e-5, "embedding not L2-normalized"
 print("PASS: shape (512,) + unit norm")

def test_same_image_zero_distance():
 rng = np.random.default_rng(0)
 face = rng.integers(0, 255, size=(160, 160, 3), dtype=np.uint8)
 e1 = get_embedding(face)
 e2 = get_embedding(face)
 d = euclidean_distance(e1, e2)
 assert d < 1e-4, f"same image should give ~0 distance, got {d}"
 print(f"PASS: identical images -> distance {d:.2e}")

def test_embed_pair_missing_branch():
 result = embed_pair(None, None)
 assert result["status"] == "missing_embedding"
 assert result["euclidean_distance"] is None
 print("PASS: missing-embedding exclusion branch")

if __name__ == "__main__":
 test_embedding_shape_and_norm()
 test_same_image_zero_distance()
 test_embed_pair_missing_branch()
 print("\nAll Stage 3 tests passed.")