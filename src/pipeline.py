"""Stage 5: End-to-end BVA pipeline.

Pipeline flow:

    image pair CSV
        -> face detection and alignment (Stage 2 loads the images itself)
        -> ArcFace embedding and distance scoring
        -> vulnerability classification
        -> CSV and JSON reports

The pair manifest is accepted in either of two schemas:

    BVA schema:       pair_id,id_a,id_b,pair_type,image_a,image_b
    ND-TWINS schema:  pair_id,image1,image2,label

In the ND-TWINS schema, label 1 maps to 'genuine' and label 0 to 'impostor'
(see ND_TWINS_LABEL_MAP). Bare image filenames are resolved against the
--image-dir directory when one is provided.

Input modes (--input-mode):

    scene       Full Stage 1+2 preprocessing/detection/alignment. Use for
                general scene images (default).
    prealigned  Images are already aligned ArcFace face crops (e.g. the
                ND-TWINS 112x112 dataset). Stages 1-2 are skipped by design:
                re-running detection/alignment on tight crops degrades the
                embeddings and invalidates the distance distributions.

Integration contract (must match the real Stage 2/3 modules):

    detect_align.load_dlib_models(model_dir)     -> (detector, predictor)
    detect_align.process_image_pair(path_a, path_b, detector, predictor)
        -> dict with status 'success' or 'no_face_detected'
    detect_align.load_prealigned_pair(path_a, path_b)
        -> dict with status 'success' or 'load_failed'   (prealigned mode)
    embed.load_arcface_model()                   -> ONNX session
    embed.embed_pair(aligned_a, aligned_b)
        -> dict with status 'success' (or 'missing_embedding'),
           'euclidean_distance' and 'cosine_similarity'

The dlib detector/predictor (scene mode only) and the ArcFace session are
created ONCE per run and reused for every pair.
"""

import argparse
import csv
import json
import os
from collections import Counter

from src import detect_align
from src import embed
from src.classify import classify_pair, determine_thresholds

ND_TWINS_LABEL_MAP = {1: "genuine", 0: "impostor"}

CSV_FIELDNAMES = [
    "pair_id", "id_a", "id_b", "pair_type", "image_a", "image_b",
    "status", "distance", "cosine_similarity",
    "vulnerability", "is_false_accept", "is_false_reject", "error",
]

THRESHOLD_WARNING = (
    "WARNING: vulnerability thresholds could not be derived - the run needs "
    "at least one scored genuine pair AND one scored non-genuine "
    "(impostor/twin) pair. Vulnerability labels are left blank; the per-pair "
    "distances and errors are still written to the reports."
)


# --------------------------------------------------------------------------- #
# Pair manifest loading
# --------------------------------------------------------------------------- #
def _resolve_image_path(name, image_dir):
    """Join bare filenames with --image-dir; leave absolute paths untouched."""
    if image_dir and not os.path.isabs(name):
        return os.path.join(image_dir, name)
    return name


def _derive_id(image_name):
    """Derive a subject id from an image filename (reporting only)."""
    return os.path.splitext(os.path.basename(image_name))[0]


def _load_nd_twins_rows(rows, image_dir):
    """Normalize ND-TWINS schema rows (pair_id,image1,image2,label) to BVA rows."""
    normalized = []
    for row_number, row in enumerate(rows, start=2):  # line 1 is the header
        image_a = (row.get("image1") or "").strip()
        image_b = (row.get("image2") or "").strip()
        label_raw = (row.get("label") or "").strip()
        if not image_a or not image_b or not label_raw:
            raise ValueError(
                f"pairs CSV row {row_number}: incomplete ND-TWINS row "
                f"(pair_id={row.get('pair_id')!r})."
            )
        label = int(label_raw)
        if label not in ND_TWINS_LABEL_MAP:
            raise ValueError(
                f"pairs CSV row {row_number}: unexpected label {label!r}; "
                f"expected one of {sorted(ND_TWINS_LABEL_MAP)}."
            )
        image_a = _resolve_image_path(image_a, image_dir)
        image_b = _resolve_image_path(image_b, image_dir)
        normalized.append({
            "pair_id": (row.get("pair_id") or "").strip() or str(row_number - 2),
            "id_a": _derive_id(image_a),
            "id_b": _derive_id(image_b),
            "pair_type": ND_TWINS_LABEL_MAP[label],
            "image_a": image_a,
            "image_b": image_b,
        })
    return normalized


def _load_bva_rows(rows, image_dir):
    """Pass BVA schema rows through, resolving image paths against --image-dir."""
    normalized = []
    for row_number, row in enumerate(rows, start=2):
        image_a = (row.get("image_a") or "").strip()
        image_b = (row.get("image_b") or "").strip()
        pair_type = (row.get("pair_type") or "").strip()
        if not image_a or not image_b or not pair_type:
            raise ValueError(
                f"pairs CSV row {row_number}: incomplete BVA row "
                f"(pair_id={row.get('pair_id')!r})."
            )
        normalized.append({
            "pair_id": (row.get("pair_id") or "").strip(),
            "id_a": (row.get("id_a") or "").strip() or _derive_id(image_a),
            "id_b": (row.get("id_b") or "").strip() or _derive_id(image_b),
            "pair_type": pair_type,
            "image_a": _resolve_image_path(image_a, image_dir),
            "image_b": _resolve_image_path(image_b, image_dir),
        })
    return normalized


def load_pairs(pairs_path, image_dir=None):
    """Load the pair manifest, auto-detecting the schema.

    Returns a list of row dicts in the BVA schema:
        pair_id, id_a, id_b, pair_type, image_a, image_b
    """
    with open(pairs_path, "r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = set(reader.fieldnames or [])
        rows = list(reader)

    nd_twins_fields = {"pair_id", "image1", "image2", "label"}
    bva_fields = {"pair_id", "id_a", "id_b", "pair_type", "image_a", "image_b"}

    if nd_twins_fields.issubset(fieldnames):
        return _load_nd_twins_rows(rows, image_dir)
    if bva_fields.issubset(fieldnames):
        return _load_bva_rows(rows, image_dir)

    raise ValueError(
        "Unrecognized pairs CSV schema. Expected either the ND-TWINS schema "
        "(pair_id,image1,image2,label) or the BVA schema "
        "(pair_id,id_a,id_b,pair_type,image_a,image_b). "
        f"Found columns: {sorted(fieldnames)}."
    )


# --------------------------------------------------------------------------- #
# Shared model state -- dlib objects are expensive to create, so they are
# built once per run and reused for every pair.
# --------------------------------------------------------------------------- #
_DLIB_MODELS = None


def _get_models():
    """Load the dlib detector/predictor (and warm the ArcFace session) once."""
    global _DLIB_MODELS
    if _DLIB_MODELS is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_dir = os.path.join(repo_root, "models")
        _DLIB_MODELS = detect_align.load_dlib_models(model_dir)
        embed.load_arcface_model()
    return _DLIB_MODELS


def score_pair(row, input_mode="scene"):
    """Process, embed, and score one image pair."""
    result = {
        "pair_id": row["pair_id"],
        "id_a": row["id_a"],
        "id_b": row["id_b"],
        "pair_type": row["pair_type"],
        "image_a": row["image_a"],
        "image_b": row["image_b"],
        "status": "success",
        "distance": None,
        "cosine_similarity": None,
        "error": None,
    }

    try:
        # Stage 1 + 2: preprocess, detect, align. Both Stage 2 entry points
        # take image PATHS and load the images themselves; both own the
        # "Flag & Exclude" branch when a usable face cannot be produced.
        if input_mode == "prealigned":
            # Images are already aligned crops: skip detection/alignment
            # entirely (dlib models are intentionally not loaded in this
            # mode -- see the module docstring).
            stage2 = detect_align.load_prealigned_pair(
                row["image_a"], row["image_b"]
            )
        else:
            detector, predictor = _get_models()
            stage2 = detect_align.process_image_pair(
                row["image_a"], row["image_b"], detector, predictor
            )

        if stage2["status"] != "success":
            # 'no_face_detected' (scene mode) or 'load_failed' (prealigned).
            result["status"] = stage2["status"]
            result["error"] = stage2.get(
                "message", "A face could not be detected, aligned, or loaded."
            )
            return result

        # Stage 3: embed the aligned crops and score the pair.
        embedding_result = embed.embed_pair(
            stage2["aligned_a"], stage2["aligned_b"]
        )

        if embedding_result.get("status") != "success":
            result["status"] = embedding_result.get("status", "embedding_failed")
            result["error"] = embedding_result.get(
                "error", "Embedding extraction failed."
            )
            return result

        result["distance"] = embedding_result["euclidean_distance"]
        result["cosine_similarity"] = embedding_result["cosine_similarity"]

    except Exception as exc:  # per-pair failures are recorded, not fatal
        result["status"] = "failed"
        result["error"] = str(exc)

    return result


# --------------------------------------------------------------------------- #
# Threshold derivation and classification (Stage 4)
# --------------------------------------------------------------------------- #
def derive_threshold_report(results):
    """Derive Stage 4 thresholds from the scored pairs.

    Genuine distances come from pair_type == 'genuine'; every other pair type
    (impostor, twin, sibling) feeds the impostor distribution.
    """
    genuine_distances = [
        row["distance"] for row in results
        if row["status"] == "success" and row["pair_type"] == "genuine"
    ]
    impostor_distances = [
        row["distance"] for row in results
        if row["status"] == "success" and row["pair_type"] != "genuine"
    ]
    if not genuine_distances or not impostor_distances:
        return None
    return determine_thresholds(
        impostor_distances=impostor_distances,
        genuine_distances=genuine_distances,
    )


def classify_results(results, threshold_report):
    """Add vulnerability labels to successfully scored pairs."""
    for row in results:
        if row["status"] != "success":
            row["vulnerability"] = None
            row["is_false_accept"] = None
            row["is_false_reject"] = None
            continue

        classification = classify_pair(
            distance=row["distance"],
            pair_type=row["pair_type"],
            threshold_report=threshold_report,
        )
        row.update(classification)


# --------------------------------------------------------------------------- #
# Summary and reports
# --------------------------------------------------------------------------- #
def build_summary(results):
    """Aggregate counts across all processed pairs."""
    status_counts = Counter(row["status"] for row in results)
    vulnerability_counts = Counter(
        row.get("vulnerability") for row in results if row.get("vulnerability")
    )
    successful = status_counts.get("success", 0)
    return {
        "total": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "by_status": dict(status_counts),
        "vulnerability_counts": {
            grade: vulnerability_counts.get(grade, 0)
            for grade in ("HIGH", "MEDIUM", "LOW", "NONE")
        },
        "false_accepts": sum(1 for row in results if row.get("is_false_accept")),
        "false_rejects": sum(1 for row in results if row.get("is_false_reject")),
    }


def write_csv_report(results, csv_output):
    output_dir = os.path.dirname(os.path.abspath(csv_output))
    os.makedirs(output_dir, exist_ok=True)
    with open(csv_output, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


def write_json_report(threshold_report, results, summary, json_output,
                      input_mode=None):
    output_dir = os.path.dirname(os.path.abspath(json_output))
    os.makedirs(output_dir, exist_ok=True)
    payload = {
        "run_config": {"input_mode": input_mode},
        "threshold_report": threshold_report,
        "summary": summary,
        "results": results,
    }
    with open(json_output, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 5: run the end-to-end BVA pipeline over a pair manifest."
    )
    parser.add_argument("--pairs", required=True, help="Path to the pairs CSV manifest.")
    parser.add_argument(
        "--image-dir", default=None,
        help="Directory containing the images when the CSV uses bare filenames.",
    )
    parser.add_argument(
        "--input-mode", choices=("scene", "prealigned"), default="scene",
        help=("scene: run full Stage 1+2 detection/alignment (general images). "
              "prealigned: images are already aligned ArcFace crops, e.g. the "
              "ND-TWINS 112x112 dataset; Stages 1-2 are skipped by design."),
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process only the first N pairs (smoke test).",
    )
    parser.add_argument(
        "--csv-output", default="results/pipeline_report.csv",
        help="Where to write the per-pair CSV report.",
    )
    parser.add_argument(
        "--json-output", default="results/pipeline_report.json",
        help="Where to write the JSON report.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.input_mode == "prealigned":
        # Warm the ArcFace session once; dlib models are intentionally not
        # loaded in this mode.
        print("Input mode: prealigned (skipping Stage 1-2 detection/alignment).")
        embed.load_arcface_model()

    pairs = load_pairs(args.pairs, args.image_dir)
    if args.limit is not None:
        pairs = pairs[: args.limit]
        print(f"Limiting run to the first {args.limit} pairs.")

    results = []
    total = len(pairs)
    for index, row in enumerate(pairs, start=1):
        print(f"[{index}/{total}] Processing pair {row['pair_id']}...", flush=True)
        results.append(score_pair(row, args.input_mode))

    threshold_report = derive_threshold_report(results)
    if threshold_report is None:
        print(THRESHOLD_WARNING)
        for row in results:
            row["vulnerability"] = None
            row["is_false_accept"] = None
            row["is_false_reject"] = None
    else:
        classify_results(results, threshold_report)

    summary = build_summary(results)
    write_csv_report(results, args.csv_output)
    write_json_report(threshold_report, results, summary, args.json_output,
                      input_mode=args.input_mode)

    print()
    print("=== Pipeline complete ===")
    print(f"Input mode: {args.input_mode}")
    print(f"Total pairs: {summary['total']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print()
    print("=== Vulnerability thresholds ===")
    if threshold_report is None:
        print("Not derived (see warning above).")
    else:
        for key in sorted(threshold_report):
            print(f"{key}: {threshold_report[key]}")
    print()
    print("=== Vulnerability counts ===")
    for grade in ("HIGH", "MEDIUM", "LOW", "NONE"):
        print(f"{grade}: {summary['vulnerability_counts'][grade]}")
    print()
    print(f"CSV report: {args.csv_output}")
    print(f"JSON report: {args.json_output}")


if __name__ == "__main__":
    main()
