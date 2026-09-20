# bva-app — Biometric Vulnerability Assessment Framework

A research prototype that quantifies facial similarity between biological
relatives — with a focus on **monozygotic (identical) twins** and biological
siblings — to assess the **vulnerability of facial-recognition systems** to
false acceptance between look-alike individuals.

This repository accompanies **Chapter 3 (Research Methodology)** of the Final
Year Project dissertation. Each source module maps directly to a section of the
methodology so that the implementation and the write-up remain traceable.

---

## Project Overview

Given two face images, the framework:

1. Pre-processes each image into a standardised representation.
2. Detects and aligns the face.
3. Generates a fixed-length face embedding (feature vector).
4. Measures the Euclidean distance between the two embeddings.
5. Classifies the pair into a **biometric vulnerability level**
   (HIGH / MEDIUM / LOW) using empirically calibrated thresholds.

The evaluation uses the **ND-Twins** dataset (12,000 JPEG images organised into
6,000 pairs — 3,000 genuine and 3,000 impostor).

---

## Pipeline Stages → Chapter 3 Mapping

| Module                | Chapter 3 Section                              | Status         |
|-----------------------|-----------------------------------------------|----------------|
| `src/preprocess.py`   | 3.7 — Image Pre-processing Pipeline           | ✅ Implemented |
| `src/detect_align.py` | 3.8 — Face Detection and Alignment            | ✅ Implemented |
| `src/embed.py`        | 3.9 — Feature Extraction (ArcFace-R100, 512-D)| ⏳ Planned     |
| `src/classify.py`     | 3.10–3.12 — Distance & Vulnerability Classes  | ⏳ Planned     |
| `src/pipeline.py`     | 3.3 — Full End-to-End Pipeline                | ⏳ Planned     |
| `app/`                | 3.13 — Prototype Web Application              | ⏳ Planned     |

**Detection / alignment:** Dlib HOG frontal-face detector + 68-point landmark
predictor.
**Embedding model:** ArcFace-R100 (iResNet-100) producing 512-dimensional
embeddings via the SOTA-FR-train-and-test framework.

---

## Folder Structure

```
bva-app/
├── src/
│   ├── __init__.py
│   └── preprocess.py       # Stage 1 — image pre-processing (Section 3.7)
├── models/                 # Dlib .dat model files (not tracked in git)
├── data/                   # ND-Twins dataset / sample images (not tracked)
├── results/                # Distance logs, reports, calibration outputs
├── notebooks/              # Experiments & threshold calibration
├── requirements.txt
└── README.md
```

The `models/`, `data/`, `results/` and `notebooks/` directories are kept in the
repository via `.gitkeep` placeholders. Large binaries (datasets, model weights)
are intentionally **not** committed.

---

## Setup

### 1. Create an environment

Using conda (recommended, because `dlib` builds are easier via conda):

```bash
conda create -n bva python=3.10 -y
conda activate bva
```

Or using a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note on `dlib`:** if the pip build fails on your platform, install it via
> conda instead: `conda install -c conda-forge dlib`.

> **Note on hardware:** face detection/alignment (Dlib) runs comfortably on
> **CPU**. The ArcFace-R100 embedding stage (Stage 3, added later) is far
> heavier — it runs on CPU but is **substantially faster on a CUDA GPU**. A GPU
> is recommended for embedding 12,000 dataset images, but is not required to run
> the pre-processing stage in this PR.

---

## Running Stage 1 (Pre-processing)

Place two sample JPEG images at `data/sample_a.jpg` and `data/sample_b.jpg`,
then run the built-in demonstration:

```bash
python src/preprocess.py
```

Or use the module programmatically:

```python
from src.preprocess import preprocess_image, quality_check, preprocess_batch

# Single image -> float32 array, shape (160, 160, 3), values in [0, 1]
arr = preprocess_image("data/sample_a.jpg")

# Quality gate before processing
report = quality_check("data/sample_a.jpg")
print(report["passed"], report["reason"])

# Batch: automatically skips unreadable / low-quality images
results = preprocess_batch(["data/sample_a.jpg", "data/sample_b.jpg"])
print(results["passed_count"], "passed /", results["total"], "total")
```

### What Stage 1 does (Section 3.7)

1. **3.7.1** BGR → RGB colour-space conversion.
2. **3.7.2** Resize to 160×160 px (bilinear interpolation).
3. **3.7.3** Normalise pixel values to `[0.0, 1.0]` (float32).
4. **3.7.4** Quality assessment — flags images that are unreadable, too small
   (< 60 px on either side), or too dark (mean brightness ≤ 10).

---

## License

Academic / research use as part of a Final Year Project.



---

## Setup — Dlib Landmark Model (required for Stage 2)

Stage 2 (`src/detect_align.py`, Section 3.8) uses the Dlib 68-point shape
predictor, whose weights file (`shape_predictor_68_face_landmarks.dat`, ~100 MB)
is **not** committed to the repository. Download it once with the helper script
before running Stage 2:

```bash
python scripts/download_models.py
```

This downloads and extracts `shape_predictor_68_face_landmarks.dat` into the
`models/` directory. If the file is missing at runtime, `detect_align.py` raises
a clear error explaining exactly where to obtain it.

### Running Stage 2 (Detection & Alignment)

Place two sample JPEG images at `data/sample_a.jpg` and `data/sample_b.jpg`,
then run the built-in demonstration:

```bash
python src/detect_align.py
```

Or use it programmatically:

```python
from src.detect_align import load_dlib_models, process_image_pair

detector, predictor = load_dlib_models("models")
result = process_image_pair("data/sample_a.jpg", "data/sample_b.jpg",
                            detector, predictor)

if result["status"] == "success":
    aligned_a = result["aligned_a"]   # (160, 160, 3) uint8 RGB
    aligned_b = result["aligned_b"]   # ready for Stage 3 embedding
else:
    print(result["message"])          # e.g. no face detected in image A
```

### What Stage 2 does (Section 3.8)

1. **3.8.1** Face detection — Dlib HOG-based frontal face detector; returns the
   largest detected face.
2. **3.8.2** Landmark detection — Dlib 68-point shape predictor; returns a
   `(68, 2)` array of landmark coordinates.
3. **3.8.3** Face alignment — affine transformation from the eye centres and
   nasal tip onto canonical positions, producing a normalised 160×160 crop.
