"""
Liveness Stream API - Frame-by-frame processing for web integration
Processes frames sent from browser webcam with LivenessDetectorV3

Fixed in v2.1:
- Removed references to non-existent session.challenges_completed attribute
- Added 'instruction' field to all challenge responses
- Consistent completed_challenges tracking via session.current_challenge_count
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from backend.database import get_database
from backend.config import settings
from backend.services.transaction_settlement import settle_transaction_by_id
from bson import ObjectId
import sys
import os
import cv2
import numpy as np
import base64
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.liveness_detector_v3 import LivenessDetectorV3

router = APIRouter()

# Active sessions — in production, use Redis
active_sessions = {}


def calculate_confidence_tier(risk_score: float, rppg_quality_score: float = 0.0,
                              rppg_movement_correlation: float = 0.5) -> tuple[str, str]:
    """Calculate confidence tier (A/B/C) from risk score and rPPG metrics."""
    if risk_score <= 25:
        pre_liveness = 0.80
    elif risk_score <= 50:
        pre_liveness = 0.60
    else:
        pre_liveness = 0.40

    if rppg_quality_score > 0:
        rppg_confidence = (rppg_quality_score + rppg_movement_correlation) / 2.0
        confidence = (0.7 * pre_liveness) + (0.3 * rppg_confidence)
    else:
        confidence = pre_liveness

    if confidence >= 0.75:
        return "A", "HIGH confidence (auto-approve)"
    if confidence >= 0.55:
        return "B", "MEDIUM confidence (2FA recommended)"
    return "C", "LOW confidence (requires extra verification)"


class LivenessSession:
    """Maintains state for a liveness session"""
    def __init__(self, transaction_id, risk_level="medium"):
        self.session_id = str(uuid.uuid4())
        self.transaction_id = transaction_id
        self.detector = LivenessDetectorV3()
        self.created_at = datetime.utcnow()

        session_info = self.detector.start_web_session(risk_level)

        self.total_challenges = session_info["total_challenges"]
        self.challenges_list = session_info["challenges"]

        self.completed = False
        self.success = False
        self.failure_reason = None
        self.face_seen_once = False
        self.last_face_seen_at = None
        self.no_face_timeout_seconds = settings.LIVENESS_NO_FACE_TIMEOUT_SECONDS


class StartLivenessRequest(BaseModel):
    transaction_id: str
    risk_level: str = "medium"


class ProcessFrameRequest(BaseModel):
    frame_base64: str


class ForceFailRequest(BaseModel):
    reason: str | None = None


class LivenessResponse(BaseModel):
    session_id: str
    current_challenge: dict
    progress: float
    total_challenges: int
    completed_challenges: int = 0
    feedback: str = ""
    status: str  # "in_progress", "completed", "failed", "timeout"
    rppg_bpm: float | None = None
    rppg_raw_bpm: float | None = None
    rppg_signal_ready: bool = False
    rppg_quality_score: float | None = None
    rppg_quality_metrics: dict | None = None
    rppg_debug_visual: dict | None = None
    rppg_debug_reason: str | None = None
    rppg_movement_correlation: float = 0.5  # 0.0-1.0 liveness indicator from movement-rPPG correlation


@router.post("/start", response_model=LivenessResponse)
async def start_liveness(
    request: StartLivenessRequest,
    db=Depends(get_database)
):
    """Start a new liveness session and return the first challenge."""

    transaction = await db.transactions.find_one({
        "_id": ObjectId(request.transaction_id)
        if ObjectId.is_valid(request.transaction_id)
        else request.transaction_id
    })

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if not transaction.get("liveness_required"):
        raise HTTPException(status_code=400, detail="Liveness not required for this transaction")

    try:
        session = LivenessSession(request.transaction_id, request.risk_level)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to initialize liveness session: {str(e)}"
        )

    active_sessions[session.session_id] = session

    # Purge sessions older than 5 minutes
    now = datetime.utcnow()
    for sid in list(active_sessions.keys()):
        if (now - active_sessions[sid].created_at).total_seconds() > 300:
            del active_sessions[sid]

    challenge_info = session.detector._get_current_challenge_info()

    return LivenessResponse(
        session_id=session.session_id,
        current_challenge=challenge_info,
        progress=0.0,
        total_challenges=session.total_challenges,
        completed_challenges=0,
        feedback="Session started. Keep your face centered in the camera.",
        status="in_progress"
    )


@router.post("/frame/{session_id}", response_model=LivenessResponse)
async def process_frame(
    session_id: str,
    request: ProcessFrameRequest
):
    """Process a webcam frame and return challenge feedback."""

    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = active_sessions[session_id]

    # Session already finished — return final state
    if session.completed:
        return LivenessResponse(
            session_id=session_id,
            current_challenge={
                "name": "Completed",
                "type": "done",
                "instruction": "Verification complete"
            },
            progress=100.0,
            total_challenges=session.total_challenges,
            # Use detector's current index which is the actual count completed
            completed_challenges=session.detector.current_challenge_idx,
            feedback="Verification completed!" if session.success else "Verification failed.",
            status="completed" if session.success else "failed",
            rppg_bpm=session.detector.latest_rppg_bpm,
            rppg_raw_bpm=session.detector.latest_rppg_raw_bpm,
            rppg_signal_ready=session.detector.latest_rppg_ready,
            rppg_quality_score=getattr(session.detector, "latest_rppg_quality_score", None),
            rppg_quality_metrics=getattr(session.detector, "latest_rppg_quality_metrics", None),
            rppg_debug_visual=getattr(session.detector, "latest_rppg_debug_visual", None),
            rppg_debug_reason=session.detector.latest_rppg_debug_reason,
            rppg_movement_correlation=getattr(session.detector, "latest_rppg_movement_correlation", 0.5),
        )

    # Decode frame
    try:
        frame_data = request.frame_base64
        if "," in frame_data:
            frame_data = frame_data.split(",")[1]

        img_data = base64.b64decode(frame_data)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("Frame decode returned None")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid frame data: {str(e)}")

    # Process with detector
    result = session.detector.process_web_frame(frame)

    face_detected = bool(result.get("face_detected", True))
    now = datetime.utcnow()

    if face_detected:
        session.face_seen_once = True
        session.last_face_seen_at = now

    # Ensure current_challenge always has an 'instruction' key for the frontend
    challenge = result.get("current_challenge", {})
    if "instruction" not in challenge:
        challenge["instruction"] = challenge.get("name", "")
    result["current_challenge"] = challenge

    completed_count = result.get("completed_challenges", session.detector.current_challenge_idx)

    # If a face was already detected but then disappears for too long, fail the session.
    if (
        result.get("status") == "in_progress"
        and not face_detected
        and session.face_seen_once
        and session.last_face_seen_at is not None
    ):
        missing_for_seconds = (now - session.last_face_seen_at).total_seconds()
        if missing_for_seconds >= session.no_face_timeout_seconds:
            session.completed = True
            session.success = False
            session.failure_reason = "face_absent_timeout"
            timeout_seconds = int(session.no_face_timeout_seconds)
            return LivenessResponse(
                session_id=session_id,
                current_challenge=result["current_challenge"],
                progress=result.get("progress", 0.0),
                total_challenges=session.total_challenges,
                completed_challenges=completed_count,
                feedback=f"Face lost for more than {timeout_seconds} seconds. Verification cancelled.",
                status="failed",
                rppg_bpm=result.get("rppg_bpm"),
                rppg_raw_bpm=result.get("rppg_raw_bpm"),
                rppg_signal_ready=bool(result.get("rppg_signal_ready", False)),
                rppg_quality_score=result.get("rppg_quality_score"),
                rppg_quality_metrics=result.get("rppg_quality_metrics"),
                rppg_debug_visual=result.get("rppg_debug_visual"),
                rppg_debug_reason=result.get("rppg_debug_reason"),                rppg_movement_correlation=result.get("rppg_movement_correlation", 0.5),            )

    if result["status"] == "completed":
        session.completed = True
        session.success = True
        return LivenessResponse(
            session_id=session_id,
            current_challenge=result["current_challenge"],
            progress=100.0,
            total_challenges=session.total_challenges,
            completed_challenges=session.total_challenges,
            feedback=result["feedback"],
            status="completed",
            rppg_bpm=result.get("rppg_bpm"),
            rppg_raw_bpm=result.get("rppg_raw_bpm"),
            rppg_signal_ready=bool(result.get("rppg_signal_ready", False)),
            rppg_quality_score=result.get("rppg_quality_score"),
            rppg_quality_metrics=result.get("rppg_quality_metrics"),
            rppg_debug_visual=result.get("rppg_debug_visual"),
            rppg_debug_reason=result.get("rppg_debug_reason"),
        )

    if result["status"] == "failed":
        session.completed = True
        session.success = False
        if not session.failure_reason:
            session.failure_reason = result.get("reason") or result.get("feedback")
        return LivenessResponse(
            session_id=session_id,
            current_challenge=result["current_challenge"],
            progress=result.get("progress", 0.0),
            total_challenges=session.total_challenges,
            completed_challenges=completed_count,
            feedback=result["feedback"],
            status="failed",
            rppg_bpm=result.get("rppg_bpm"),
            rppg_raw_bpm=result.get("rppg_raw_bpm"),
            rppg_signal_ready=bool(result.get("rppg_signal_ready", False)),
            rppg_quality_score=result.get("rppg_quality_score"),
            rppg_quality_metrics=result.get("rppg_quality_metrics"),
            rppg_debug_visual=result.get("rppg_debug_visual"),
            rppg_debug_reason=result.get("rppg_debug_reason"),
        )

    return LivenessResponse(
        session_id=session_id,
        current_challenge=result["current_challenge"],
        progress=result["progress"],
        total_challenges=session.total_challenges,
        completed_challenges=completed_count,
        feedback=result["feedback"],
        status="in_progress",
        rppg_bpm=result.get("rppg_bpm"),
        rppg_raw_bpm=result.get("rppg_raw_bpm"),
        rppg_signal_ready=bool(result.get("rppg_signal_ready", False)),
        rppg_quality_score=result.get("rppg_quality_score"),
        rppg_quality_metrics=result.get("rppg_quality_metrics"),
        rppg_debug_visual=result.get("rppg_debug_visual"),
        rppg_debug_reason=result.get("rppg_debug_reason"),        rppg_movement_correlation=result.get("rppg_movement_correlation", 0.5),    )


@router.post("/complete/{session_id}")
async def complete_liveness(
    session_id: str,
    db=Depends(get_database)
):
    """Finalise verification and update transaction in DB."""

    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    if not session.completed:
        raise HTTPException(status_code=400, detail="Session not completed yet")

    transaction_id = session.transaction_id
    completed_count = session.detector.current_challenge_idx

    tx_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction_snapshot = await db.transactions.find_one({"_id": tx_obj_id}, {"risk_score": 1})
    risk_score = float((transaction_snapshot or {}).get("risk_score", 50.0) or 50.0)
    rppg_quality_score = float(session.detector.latest_rppg_quality_score or 0.0)
    rppg_movement_correlation = float(session.detector.latest_rppg_movement_correlation or 0.5)
    confidence_tier, tier_reason = calculate_confidence_tier(
        risk_score,
        rppg_quality_score,
        rppg_movement_correlation,
    )

    # Collect rPPG metrics for confidence tier calculation
    liveness_result_data = {
        "success": session.success,
        "challenges_completed": completed_count,
        "total_challenges": session.total_challenges,
        "timestamp": datetime.utcnow(),
        "reason": session.failure_reason,
        "rppg_quality_score": rppg_quality_score,
        "rppg_movement_correlation": rppg_movement_correlation,
        "rppg_metrics": session.detector.latest_rppg_quality_metrics or {},
        "confidence_tier": confidence_tier,
        "tier_reason": tier_reason,
    }

    update_result = await db.transactions.update_one(
        {
            "_id": tx_obj_id
        },
        {
            "$set": {
                "liveness_performed": True,
                "liveness_result": liveness_result_data,
                "rppg_quality_score": rppg_quality_score,
                "rppg_movement_correlation": rppg_movement_correlation,
                "confidence_tier": confidence_tier,
                "tier_reason": tier_reason,
                "requires_2fa": confidence_tier == "B",
                "status": "approved" if session.success else "rejected",
                "updated_at": datetime.utcnow()
            }
        }
    )

    if update_result.matched_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update transaction")

    settlement_result = None
    if session.success:
        # Ensure funds move after successful web liveness, matching low-risk flow.
        settlement_result = await settle_transaction_by_id(
            db=db,
            transaction_id=tx_obj_id,
            source="liveness_stream_complete",
        )

    transaction = await db.transactions.find_one({
        "_id": tx_obj_id
    })

    del active_sessions[session_id]

    if transaction and "_id" in transaction:
        transaction["_id"] = str(transaction["_id"])

    return {
        "success": session.success,
        "message": (
            "Verification approved!"
            if session.success
            else (
                f"Face lost for more than {int(session.no_face_timeout_seconds)} seconds. Verification cancelled."
                if session.failure_reason == "face_absent_timeout"
                else "Verification failed."
            )
        ),
        "transaction": transaction,
        "settlement": settlement_result,
        "rppg_quality_score": session.detector.latest_rppg_quality_score,
        "rppg_movement_correlation": session.detector.latest_rppg_movement_correlation,
        "rppg_metrics": session.detector.latest_rppg_quality_metrics or {},
    }


@router.delete("/cancel/{session_id}")
async def cancel_liveness(session_id: str):
    """Cancel an active liveness session."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": "Session cancelled"}
    return {"message": "Session not found"}


@router.post("/fail/{session_id}")
async def fail_liveness_session(
    session_id: str,
    payload: ForceFailRequest,
    db=Depends(get_database)
):
    """Force-fail an active session (e.g., identity changed during liveness)."""

    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]
    transaction_id = session.transaction_id
    tx_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id

    await db.transactions.update_one(
        {"_id": tx_obj_id},
        {
            "$set": {
                "liveness_performed": True,
                "liveness_result": {
                    "success": False,
                    "challenges_completed": session.detector.current_challenge_idx,
                    "total_challenges": session.total_challenges,
                    "timestamp": datetime.utcnow(),
                    "reason": payload.reason or "identity_mismatch_during_liveness",
                },
                "status": "rejected",
                "updated_at": datetime.utcnow(),
            }
        },
    )

    transaction = await db.transactions.find_one({"_id": tx_obj_id})
    del active_sessions[session_id]

    if transaction and "_id" in transaction:
        transaction["_id"] = str(transaction["_id"])

    return {
        "success": False,
        "message": payload.reason or "Identity mismatch detected during liveness.",
        "transaction": transaction,
    }