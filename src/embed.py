"""Stage 3: Face embedding extraction with ArcFace-R100 (ONNX Runtime).
Consumes the aligned 160x160 uint8 RGB crops produced by Stage 2
(detect_align.process_image_pair) and produces 512-D L2-normalized
embeddings for downstream twin/sibling similarity analysis (Stage 4).
"""
import os
import cv2
import numpy as np
import onnxruntime as ort
MODEL_PATH = os.path.join("models", "glint360k_r100.onnx")
INPUT_SIZE = (112, 112)
# ArcFace-R100 input resolution
EMBEDDING_DIM = 512
_session = None
def load_arcface_model(model_path=MODEL_PATH):
 """Load and cache the ArcFace-R100 ONNX model.

 Raises FileNotFoundError with a setup hint if the model file is missing.
 """

 global _session
 if _session is not None:
   return _session
 if not os.path.exists(model_path):
   raise FileNotFoundError(
     f"ArcFace model not found at '{model_path}'. "
     "Run `python scripts/download_models.py` first, or place "
     "glint360k_r100.onnx inside the models/ directory."
)
 available = ort.get_available_providers()
 providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in
available]
 _session = ort.InferenceSession(model_path, providers=providers)
 return _session

def _preprocess(face):
  """Convert a face crop (uint8 RGB, or float32 RGB in [0, 1]) into the
  normalized NCHW float32 tensor ArcFace expects."""
  img = np.asarray(face)
  if img.dtype != np.uint8:
    scale = 255.0 if img.max() <= 1.0 else 1.0
    img = np.clip(img * scale, 0, 255).astype(np.uint8)
  if img.shape[:2] != INPUT_SIZE:
    img = cv2.resize(img, INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
  img = img.astype(np.float32)
  img = (img - 127.5) / 127.5
  
# ArcFace standard normalization
  img = img.transpose(2, 0, 1)[np.newaxis, ...]
# HWC -> NCHW
  return img

def get_embedding(face):
  """Return the 512-D L2-normalized ArcFace embedding for one face crop."""
  session = load_arcface_model()
  tensor = _preprocess(face)
  input_name = session.get_inputs()[0].name
  output = session.run(None, {input_name: tensor})[0]
  emb = output.flatten()
  if emb.shape[0] != EMBEDDING_DIM:
   raise ValueError(f"Expected {EMBEDDING_DIM}-D embedding, got {emb.shape[0]}")
  return emb / (np.linalg.norm(emb) + 1e-10)

# L2 normalization
def euclidean_distance(emb_a, emb_b):
  """Euclidean distance between two L2-normalized embeddings (lower = more similar)."""
  return float(np.linalg.norm(emb_a - emb_b))

def cosine_similarity(emb_a, emb_b):
  """Cosine similarity between two embeddings (higher = more similar)."""
  return float(np.dot(emb_a, emb_b) / ((np.linalg.norm(emb_a) * np.linalg.norm(emb_b)) +
1e-10))

def embed_pair(face_a, face_b):
  """Stage 3 driver: embed an aligned face pair and score it.
  Mirrors Stage 2's process_image_pair contract: if either face is None
  (e.g. no_face_detected upstream), the pair is excluded with status
  'missing_embedding' rather than scored.
  """
  if face_a is None or face_b is None:
   return {
     "status": "missing_embedding",
     "embedding_a": None,
     "embedding_b": None,
     "euclidean_distance": None,
     "cosine_similarity": None,
  }
  emb_a = get_embedding(face_a)
  emb_b = get_embedding(face_b)
  return {
     "status": "success",
     "embedding_a": emb_a,
     "embedding_b": emb_b,
     "euclidean_distance": euclidean_distance(emb_a, emb_b),
     "cosine_similarity": cosine_similarity(emb_a, emb_b),
  }
