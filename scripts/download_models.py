"""
download_models.py -- Downloads required Dlib model files into models/
Run once before using detect_align.py:
    python scripts/download_models.py
"""
import urllib.request, bz2, pathlib, sys

MODELS_DIR = pathlib.Path(__file__).resolve().parents[1] / "models"
URL = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
DEST = MODELS_DIR / "shape_predictor_68_face_landmarks.dat"


def download():
    if DEST.exists():
        print(f"Model already exists: {DEST}")
        return
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    bz2_path = MODELS_DIR / "shape_predictor_68_face_landmarks.dat.bz2"
    print(f"Downloading {URL} ...")
    urllib.request.urlretrieve(URL, bz2_path)
    print("Extracting...")
    with bz2.open(bz2_path) as f_in, open(DEST, "wb") as f_out:
        f_out.write(f_in.read())
    bz2_path.unlink()
    print(f"Done. Model saved to: {DEST}")


if __name__ == "__main__":
    download()

import io
import zipfile
from pathlib import Path

import requests

ARCFACE_ZIP_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/antelopev2.zip"
ARCFACE_FALLBACK_URL = (
    "https://huggingface.co/LPDoctor/insightface/resolve/main/models/antelopev2/glintr100.onnx"
)

def download_arcface(models_dir="models"):
 """Download the R100@Glint360K (glintr100) ONNX model as
 models/glint360k_r100.onnx.
 The model ships inside the official antelopev2 pack (GitHub releases),
 with a HuggingFace mirror of the raw .onnx as fallback.
 """
 dest = Path(models_dir) / "glint360k_r100.onnx"
 if dest.exists():
  print(f"[skip] {dest} already exists")
  return dest
 
 Path(models_dir).mkdir(parents=True, exist_ok=True)
 try:
  print("Downloading antelopev2 pack (~400 MB) from GitHub releases ...")
  r = requests.get(ARCFACE_ZIP_URL, timeout=600)
  r.raise_for_status()
  with zipfile.ZipFile(io.BytesIO(r.content)) as z:
   inner = next(n for n in z.namelist() if n.endswith("glintr100.onnx"))
   dest.write_bytes(z.read(inner))
 except Exception as e:
  print(f"Primary download failed ({e}); trying HuggingFace mirror (~261 MB) ...")
  r = requests.get(ARCFACE_FALLBACK_URL, timeout=1800)
  r.raise_for_status()
  dest.write_bytes(r.content)

 print(f"Saved {dest} ({dest.stat().st_size / 1e6:.0f} MB)")
 return dest

if __name__ == "__main__":
 download_arcface()