"""
Face Identity API Routes
1:1 facial matching (enroll on first use, verify on every transaction)
OpenCV-only implementation (no dlib/C++ toolchain required)
"""

from datetime import datetime
from typing import Any
import base64
from pathlib import Path
import urllib.request

import cv2
import numpy as np
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.database import get_database
from backend.config import settings


router = APIRouter()

# For OpenCV SFace with cosine score, bigger is more similar.
# OpenCV docs suggest ~0.363 as a practical threshold.
FACE_MATCH_THRESHOLD = 0.363

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models" / "opencv_face"
DETECTOR_MODEL_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL_PATH = MODEL_DIR / "face_recognition_sface_2021dec.onnx"

DETECTOR_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

_model_init_error: str | None = None
_detector: Any = None
_recognizer: Any = None


class FaceVerifyRequest(BaseModel):
    user_id: str
    image_base64: str = Field(..., min_length=100)
    consent_to_store: bool = False


def _to_object_id(value: str) -> Any:
    if ObjectId.is_valid(value):
        return ObjectId(value)
    return value


def _download_if_missing(path: Path, url: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, str(path))


def _ensure_models_ready() -> tuple[bool, str | None]:
    global _detector, _recognizer, _model_init_error

    if _detector is not None and _recognizer is not None:
        return True, None

    if _model_init_error:
        return False, _model_init_error

    try:
        _download_if_missing(DETECTOR_MODEL_PATH, DETECTOR_MODEL_URL)
        _download_if_missing(RECOGNIZER_MODEL_PATH, RECOGNIZER_MODEL_URL)

        _detector = cv2.FaceDetectorYN.create(
            str(DETECTOR_MODEL_PATH),
            "",
            (320, 320),
            0.9,
            0.3,
            5000,
        )
        _recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_MODEL_PATH), "")
        return True, None
    except Exception as exc:
        _model_init_error = f"Could not initialize OpenCV face models: {exc}"
        return False, _model_init_error


def _face_engine_installed() -> bool:
    return hasattr(cv2, "FaceDetectorYN") and hasattr(cv2, "FaceRecognizerSF")


def _decode_image(image_base64: str) -> np.ndarray:
    payload = image_base64
    if "," in payload:
        payload = payload.split(",", 1)[1]

    try:
        raw = base64.b64decode(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image base64: {exc}")

    nparr = np.frombuffer(raw, np.uint8)
    frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame_bgr is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    return frame_bgr


def _extract_single_embedding(frame_bgr: np.ndarray) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    _detector.setInputSize((w, h))
    _, faces = _detector.detect(frame_bgr)

    if faces is None or len(faces) == 0:
        raise HTTPException(status_code=400, detail="No face detected in the image")
    if len(faces) > 1:
        raise HTTPException(status_code=400, detail="Multiple faces detected. Use only one face")

    face = faces[0]
    aligned_face = _recognizer.alignCrop(frame_bgr, face)
    embedding = _recognizer.feature(aligned_face)
    if embedding is None:
        raise HTTPException(status_code=400, detail="Could not extract face embedding")

    return embedding.flatten()


@router.get("/status/{user_id}")
async def face_status(user_id: str, db=Depends(get_database)):
    """Return whether user already has a stored master selfie/embedding."""
    if not _face_engine_installed():
        return {
            "available": False,
            "enrolled": False,
            "detail": "OpenCV face module is not available in this Python runtime",
        }

    user = await db.users.find_one({"_id": _to_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    face_identity = user.get("face_identity", {})
    return {
        "available": True,
        "model_ready": _detector is not None and _recognizer is not None,
        "model_files_ready": DETECTOR_MODEL_PATH.exists() and RECOGNIZER_MODEL_PATH.exists(),
        "enrolled": bool(face_identity.get("reference_encoding")),
        "reference_image_base64": face_identity.get("reference_image_base64"),
        "enrolled_at": face_identity.get("enrolled_at"),
        "last_verified_at": face_identity.get("last_verified_at"),
    }


@router.post("/verify")
async def verify_face_identity(payload: FaceVerifyRequest, db=Depends(get_database)):
    """
    Enroll on first use, then verify 1:1 on every following attempt.
    - If no reference exists: requires consent_to_store=True.
    - If reference exists: compares probe image against stored reference.
    """
    ready, detail = _ensure_models_ready()
    if not ready:
        raise HTTPException(
            status_code=503,
            detail=detail or "OpenCV face models are not available on the server",
        )

    user = await db.users.find_one({"_id": _to_object_id(payload.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    frame_bgr = _decode_image(payload.image_base64)
    probe_embedding = _extract_single_embedding(frame_bgr)

    face_identity = user.get("face_identity", {})
    reference_encoding = face_identity.get("reference_encoding")

    now = datetime.utcnow()

    if not reference_encoding:
        if not payload.consent_to_store:
            raise HTTPException(
                status_code=428,
                detail="Consent is required to store the master selfie on first transaction",
            )

        await db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "face_identity.reference_encoding": [float(v) for v in probe_embedding.tolist()],
                    "face_identity.reference_image_base64": payload.image_base64,
                    "face_identity.enrolled_at": now,
                    "face_identity.last_verified_at": now,
                    "face_identity.last_match": True,
                    "face_identity.last_distance": 0.0,
                    "face_identity.last_confidence": 100.0,
                }
            },
        )

        return {
            "success": True,
            "mode": "enroll",
            "match": True,
            "distance": 0.0,
            "confidence": 100.0,
            "threshold": FACE_MATCH_THRESHOLD,
            "message": "Master selfie enrolled successfully",
        }

    reference = np.array(reference_encoding, dtype=np.float32).reshape(1, -1)
    probe = np.array(probe_embedding, dtype=np.float32).reshape(1, -1)

    similarity = float(
        _recognizer.match(
            reference,
            probe,
            cv2.FaceRecognizerSF_FR_COSINE,
        )
    )
    matched = similarity >= FACE_MATCH_THRESHOLD
    distance = max(0.0, 1.0 - similarity)
    confidence = max(0.0, min(100.0, similarity * 100.0))

    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "face_identity.last_verified_at": now,
                "face_identity.last_match": bool(matched),
                "face_identity.last_distance": distance,
                "face_identity.last_confidence": confidence,
            }
        },
    )

    return {
        "success": True,
        "mode": "verify",
        "match": bool(matched),
        "distance": round(distance, 4),
        "confidence": round(confidence, 2),
        "threshold": FACE_MATCH_THRESHOLD,
        "message": "Face matched" if matched else "Face mismatch",
    }


@router.post("/reset/{user_id}")
async def reset_face_identity(user_id: str, db=Depends(get_database)):
    """Developer helper: reset stored face identity to test enrollment again."""
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="Face reset is only available in DEBUG mode")

    user = await db.users.find_one({"_id": _to_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one({"_id": user["_id"]}, {"$unset": {"face_identity": ""}})

    return {
        "success": True,
        "message": "Face identity reset. Next transaction will require new consent and master selfie enrollment.",
    }
