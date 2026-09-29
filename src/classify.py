"""Stage 4: Vulnerability classification for the BVA pipeline.

Consumes the 512-D L2-normalized ArcFace embeddings produced by Stage 3 and
assesses how vulnerable the face verification system is to *related impostors*
(monozygotic twins, biological siblings) compared with a general impostor
population.

Methodology definitions
-----------------------
- Genuine pair     : two images of the same subject (pair_type='genuine')
- Related impostor : twin or sibling pair (different identities, high similarity)
- t@FAR=a          : the a-quantile of the general impostor distance
                     distribution; a fraction `a` of random impostor pairs
                     fall below it (and would be falsely accepted).
- Vulnerability level (non-genuine pairs, distance d):
    HIGH   : d <= t@FAR=0.01 -> pair accepted even at a strict 1% FAR point
    MEDIUM : t@FAR=0.01 < d <= t@FAR=0.10
    LOW    : d >  t@FAR=0.10
  Genuine pairs are not vulnerabilities (the system working as intended):
  they get level 'NONE' plus a false-reject flag instead.

For L2-normalized embeddings, Euclidean distance and cosine similarity are
monotonically equivalent (d^2 = 2 - 2*cos), so the grading is identical under
either metric; distances are used throughout for readability.
"""

import argparse
import csv
import os
from collections import defaultdict

import numpy as np

# FAR operating points that define the vulnerability buckets.
VULNERABILITY_HIGH_FAR = 0.01
VULNERABILITY_MEDIUM_FAR = 0.10
DEFAULT_FAR_TARGETS = (VULNERABILITY_HIGH_FAR, VULNERABILITY_MEDIUM_FAR)

VALID_PAIR_TYPES = ("genuine", "twin", "sibling", "impostor")


# ---------------------------------------------------------------- embeddings I/O

def save_embeddings(path, embeddings):
    """Save {subject_id: 512-D vector} to a compressed .npz file."""
    ids = list(embeddings.keys())
    if not ids:
        raise ValueError("embeddings dict is empty; nothing to save.")
    vectors = np.stack([np.asarray(embeddings[sid], dtype=np.float32) for sid in ids])
    np.savez_compressed(path, ids=np.array(ids, dtype=str), vectors=vectors)


def load_embeddings(path):
    """Load embeddings saved by save_embeddings -> {subject_id: np.ndarray}."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Embeddings file not found: '{path}'. Produce it with the Stage 3/5 embedding runner."
        )
    with np.load(path) as data:
        return {str(sid): vec for sid, vec in zip(data["ids"], data["vectors"])}


# ---------------------------------------------------------------- scoring
# These mirror src.embed so classify.py stays decoupled from the ML stack.

def euclidean_distance(emb_a, emb_b):
    """Euclidean distance between two L2-normalized embeddings (lower = more similar)."""
    return float(np.linalg.norm(emb_a - emb_b))


def cosine_similarity(emb_a, emb_b):
    """Cosine similarity between two embeddings (higher = more similar)."""
    return float(np.dot(emb_a, emb_b) / ((np.linalg.norm(emb_a) * np.linalg.norm(emb_b)) + 1e-10))


# ---------------------------------------------------------------- thresholds

def determine_thresholds(impostor_distances, genuine_distances=None, far_targets=DEFAULT_FAR_TARGETS):
    """Distance thresholds at chosen FAR operating points, plus the EER.

    t@FAR=a is the a-quantile of the impostor distance distribution: a
    fraction `a` of random impostor pairs score below it and would be
    falsely accepted.
    """
    impostor = np.asarray(impostor_distances, dtype=np.float64)
    report = {
        "thresholds": {f"far_{a:g}": float(np.quantile(impostor, a)) for a in far_targets}
    }
    if genuine_distances is not None and len(genuine_distances) > 0:
        eer, eer_threshold = _equal_error_rate(np.asarray(genuine_distances, dtype=np.float64), impostor)
        report["eer"] = eer
        report["eer_threshold"] = eer_threshold
    return report


def _equal_error_rate(genuine, impostor):
    """EER via a vectorized sweep over candidate thresholds (no external deps)."""
    gen = np.sort(genuine)
    imp = np.sort(impostor)
    candidates = np.unique(np.concatenate([gen, imp]))
    far = np.searchsorted(imp, candidates, side="right") / len(imp)
    frr = 1.0 - np.searchsorted(gen, candidates, side="right") / len(gen)
    gaps = np.abs(far - frr)
    i = int(np.argmin(gaps))
    return float((far[i] + frr[i]) / 2.0), float(candidates[i])


def compute_verification_metrics(distances, is_genuine, threshold):
    """TAR / FAR / FRR / accuracy + confusion counts at one operating threshold."""
    distances = np.asarray(distances, dtype=np.float64)
    is_genuine = np.asarray(is_genuine, dtype=bool)
    accept = distances <= threshold
    tp = int(np.sum(accept & is_genuine))
    fn = int(np.sum(~accept & is_genuine))
    fp = int(np.sum(accept & ~is_genuine))
    tn = int(np.sum(~accept & ~is_genuine))
    return {
        "threshold": float(threshold),
        "true_positives": tp, "false_accepts": fp, "false_rejects": fn, "true_negatives": tn,
        "tar": tp / (tp + fn) if (tp + fn) else None,
        "far": fp / (fp + tn) if (fp + tn) else None,
        "frr": fn / (tp + fn) if (tp + fn) else None,
        "accuracy": (tp + tn) / len(distances) if len(distances) else None,
    }


# ---------------------------------------------------------------- classification

def classify_pair(distance, pair_type, threshold_report):
    """Assess one pair. Returns vulnerability level + false accept/reject flags."""
    if pair_type not in VALID_PAIR_TYPES:
        raise ValueError(f"Invalid pair_type {pair_type!r}; expected one of {VALID_PAIR_TYPES}")
    if distance is None:
        return {"vulnerability": None, "is_false_accept": None, "is_false_reject": None}

    thresholds = threshold_report["thresholds"]
    try:
        t_high = thresholds[f"far_{VULNERABILITY_HIGH_FAR:g}"]
        t_medium = thresholds[f"far_{VULNERABILITY_MEDIUM_FAR:g}"]
    except KeyError as e:
        raise KeyError(
            f"threshold_report is missing {e}; recompute with far_targets including "
            f"{VULNERABILITY_HIGH_FAR} and {VULNERABILITY_MEDIUM_FAR}."
        ) from e

    if pair_type == "genuine":
        return {
            "vulnerability": "NONE",
            "is_false_accept": None,
            "is_false_reject": bool(distance > t_high),
        }

    if distance <= t_high:
        level = "HIGH"
    elif distance <= t_medium:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {"vulnerability": level, "is_false_accept": bool(distance <= t_high), "is_false_reject": None}


# ---------------------------------------------------------------- batch driver

def evaluate_pairs(pairs, embeddings, far_targets=DEFAULT_FAR_TARGETS, threshold_report=None):
    """Score + classify every pair and produce a summary.

    pairs      : iterable of dicts {pair_id, id_a, id_b, pair_type}
    embeddings : {subject_id: vector} (as produced by load_embeddings)
    If threshold_report is None it is derived from the data: quantiles of the
    general-impostor ('impostor' rows) distances when present, else of all
    non-genuine rows. Related impostors (twin/sibling) are then graded
    against those general operating points.
    """
    results = []
    for p in pairs:
        row = {
            "pair_id": p.get("pair_id"),
            "id_a": p["id_a"],
            "id_b": p["id_b"],
            "pair_type": p.get("pair_type", "impostor"),
        }
        va, vb = embeddings.get(row["id_a"]), embeddings.get(row["id_b"])
        if va is None or vb is None:
            row.update(status="missing_embedding", distance=None, cosine_similarity=None)
        else:
            row.update(
                status="success",
                distance=euclidean_distance(va, vb),
                cosine_similarity=cosine_similarity(va, vb),
            )
        results.append(row)

    if threshold_report is None:
        genuine = [r["distance"] for r in results if r["pair_type"] == "genuine" and r["status"] == "success"]
        impostor = [r["distance"] for r in results if r["pair_type"] == "impostor" and r["status"] == "success"]
        if not impostor:
            impostor = [r["distance"] for r in results if r["pair_type"] != "genuine" and r["status"] == "success"]
        if not genuine or not impostor:
            raise ValueError(
                "Cannot derive thresholds: need scored 'genuine' and 'impostor' pairs "
                "(or pass threshold_report explicitly)."
            )
        threshold_report = determine_thresholds(impostor, genuine, far_targets=far_targets)

    for row in results:
        row.update(classify_pair(row["distance"], row["pair_type"], threshold_report))

    return {
        "threshold_report": threshold_report,
        "results": results,
        "summary": _summarize(results, threshold_report),
    }


def _summarize(results, threshold_report):
    buckets = defaultdict(lambda: {
        "count": 0, "scored": 0, "false_accepts": 0, "false_rejects": 0,
        "distances": [], "vuln": defaultdict(int),
    })
    for r in results:
        b = buckets[r["pair_type"]]
        b["count"] += 1
        if r["status"] != "success":
            continue
        b["scored"] += 1
        b["distances"].append(r["distance"])
        if r["pair_type"] != "genuine" and r["is_false_accept"]:
            b["false_accepts"] += 1
            b["vuln"][r["vulnerability"]] += 1
        if r["pair_type"] == "genuine" and r["is_false_reject"]:
            b["false_rejects"] += 1

    summary = {}
    for ptype, b in buckets.items():
        entry = {"pairs": b["count"], "scored": b["scored"], "excluded": b["count"] - b["scored"]}
        if b["distances"]:
            entry["mean_distance"] = float(np.mean(b["distances"]))
            entry["min_distance"] = float(np.min(b["distances"]))
            entry["max_distance"] = float(np.max(b["distances"]))
        if ptype == "genuine":
            frr = b["false_rejects"] / b["scored"] if b["scored"] else None
            entry["false_reject_rate"] = frr
            entry["true_accept_rate"] = (1.0 - frr) if frr is not None else None
        else:
            entry["false_accept_rate"] = b["false_accepts"] / b["scored"] if b["scored"] else None
            entry["vulnerability_counts"] = dict(b["vuln"])
        summary[ptype] = entry

    # Standard verification metrics at the strict operating point, computed on
    # genuine + general impostors only (related impostors are the attackers,
    # not the calibration population).
    t_strict = threshold_report["thresholds"][f"far_{VULNERABILITY_HIGH_FAR:g}"]
    gen_rows = [r for r in results if r["pair_type"] == "genuine" and r["status"] == "success"]
    imp_rows = [r for r in results if r["pair_type"] == "impostor" and r["status"] == "success"]
    if gen_rows and imp_rows:
        d = [r["distance"] for r in gen_rows] + [r["distance"] for r in imp_rows]
        g = [True] * len(gen_rows) + [False] * len(imp_rows)
        summary["verification_at_far_1pct"] = compute_verification_metrics(d, g, t_strict)
    return summary


# ---------------------------------------------------------------- I/O helpers

def load_pairs_csv(path):
    """Load a pair manifest CSV with columns pair_id,id_a,id_b,pair_type."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Pairs manifest not found: '{path}'")
    with open(path, newline="") as f:
        rows = [dict(r) for r in csv.DictReader(f)]
    for r in rows:
        if r.get("pair_type") not in VALID_PAIR_TYPES:
            raise ValueError(
                f"Invalid pair_type {r.get('pair_type')!r} for pair {r.get('pair_id')}; "
                f"expected one of {VALID_PAIR_TYPES}"
            )
    return rows


def write_report_csv(assessment, path):
    """Write the per-pair assessment to CSV."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fields = ["pair_id", "id_a", "id_b", "pair_type", "status", "distance",
              "cosine_similarity", "is_false_accept", "is_false_reject", "vulnerability"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(assessment["results"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage 4: vulnerability assessment over scored pairs.")
    parser.add_argument("--embeddings", required=True, help="Path to embeddings .npz (from Stage 3)")
    parser.add_argument("--pairs", required=True, help="CSV with columns pair_id,id_a,id_b,pair_type")
    parser.add_argument("--output", default=None, help="Optional CSV path for the per-pair report")
    args = parser.parse_args(argv)

    embeddings = load_embeddings(args.embeddings)
    pairs = load_pairs_csv(args.pairs)
    assessment = evaluate_pairs(pairs, embeddings)

    print("=== Threshold report (general impostors) ===")
    for k, v in assessment["threshold_report"]["thresholds"].items():
        print(f"  {k}: {v:.4f}")
    if "eer" in assessment["threshold_report"]:
        print(f"  EER: {assessment['threshold_report']['eer']:.4f} "
              f"(threshold {assessment['threshold_report']['eer_threshold']:.4f})")
    print("\n=== Summary by pair type ===")
    for ptype, entry in assessment["summary"].items():
        print(f"  {ptype}: {entry}")
    if args.output:
        write_report_csv(assessment, args.output)
        print(f"\nPer-pair report written to {args.output}")
    return assessment


if __name__ == "__main__":
    main()
