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
