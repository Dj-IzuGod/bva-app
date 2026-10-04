"""
Decisive test: what does the batch report say about the pair I live-scored?

Edit PAIR_A / PAIR_B to the exact two filenames you uploaded to the
live scorer, then run from the repo root:  python check_pair.py

Matches pairs by BASENAME (e.g. "000000.jpg") so it works whether the
report stores full paths or bare filenames.
"""
import json
from pathlib import Path

PAIR_A = "000000.jpg"   # <-- replace with your 1st uploaded filename
PAIR_B = "000001.jpg"   # <-- replace with your 2nd uploaded filename


def basename(p):
    """Normalise a stored path (Windows or POSIX separators) to its filename."""
    return Path(str(p).replace("\\", "/")).name.lower()


def same_pair(result, filename_a, filename_b):
    """True if this report row references exactly the two given basenames."""
    result_a = basename(result.get("image_a", ""))
    result_b = basename(result.get("image_b", ""))
    return {result_a, result_b} == {basename(filename_a), basename(filename_b)}


r = json.load(open("results/pipeline_report.json", encoding="utf-8"))
results = r.get("results", [])

# --- 1. Does the report contain this exact pair, and what does it say? ---
hit = [x for x in results if same_pair(x, PAIR_A, PAIR_B)]

print("=" * 60)
if hit:
    for x in hit:
        print(f"REPORT SAYS  pair_id={x.get('pair_id')}  "
              f"pair_type={x.get('pair_type')}  "
              f"distance={x.get('distance')}  "
              f"cosine={x.get('cosine_similarity')}")
else:
    print(f"REPORT SAYS  {PAIR_A} + {PAIR_B} is NOT in the report at all")

# --- 2. The best genuine pair to test the live scorer with ---------------
genuine = sorted(
    (x for x in results
     if x.get("pair_type") == "genuine"
     and isinstance(x.get("distance"), (int, float))),
    key=lambda x: x["distance"],
)
print("=" * 60)
if genuine:
    x = genuine[0]
    print("LIVE-TEST WITH THESE TWO FILES (most-similar genuine pair):")
    print(f"  {x.get('image_a')}")
    print(f"  {x.get('image_b')}")
    print(f"  expected live distance ~ {x['distance']:.4f}")
else:
    print("No genuine pairs with numeric distances found in the report.")
print("=" * 60)
