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


class StartLivenessRequest(BaseModel):
    transaction_id: str
    risk_level: str = "medium"


class ProcessFrameRequest(BaseModel):
    frame_base64: str


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
    rppg_debug_reason: str | None = None


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

    session = LivenessSession(request.transaction_id, request.risk_level)
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
            rppg_debug_reason=session.detector.latest_rppg_debug_reason,
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

    # Ensure current_challenge always has an 'instruction' key for the frontend
    challenge = result.get("current_challenge", {})
    if "instruction" not in challenge:
        challenge["instruction"] = challenge.get("name", "")
    result["current_challenge"] = challenge

    completed_count = result.get("completed_challenges", session.detector.current_challenge_idx)

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
            rppg_debug_reason=result.get("rppg_debug_reason"),
        )

    if result["status"] == "failed":
        session.completed = True
        session.success = False
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
        rppg_debug_reason=result.get("rppg_debug_reason"),
    )


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

    update_result = await db.transactions.update_one(
        {
            "_id": tx_obj_id
        },
        {
            "$set": {
                "liveness_performed": True,
                "liveness_result": {
                    "success": session.success,
                    "challenges_completed": completed_count,
                    "total_challenges": session.total_challenges,
                    "timestamp": datetime.utcnow()
                },
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
        "message": "Verification approved!" if session.success else "Verification failed.",
        "transaction": transaction,
        "settlement": settlement_result,
    }


@router.delete("/cancel/{session_id}")
async def cancel_liveness(session_id: str):
    """Cancel an active liveness session."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": "Session cancelled"}
    return {"message": "Session not found"}