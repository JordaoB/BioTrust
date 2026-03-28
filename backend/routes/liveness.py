"""
Liveness API Routes
Real-time biometric verification for high-risk transactions
PRIVACY-BY-DESIGN: No biometric data is stored - only verification metadata
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from backend.database import get_database
from backend.observability.metrics import metrics_registry
from backend.services.transaction_settlement import settle_transaction_by_id
from bson import ObjectId
import sys
import os
import numpy as np

# Import liveness detector
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.liveness_detector_v3 import LivenessDetectorV3

router = APIRouter()


def convert_numpy_types(obj):
    """
    Recursively convert numpy types to Python native types.
    MongoDB cannot serialize numpy.bool_, numpy.int64, etc.
    """
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, (np.float16, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


@router.post("/verify/{transaction_id}")
async def verify_liveness(
    transaction_id: str,
    timeout: int = 90,
    db=Depends(get_database),
):
    """Perform desktop/server-side liveness verification for one transaction."""
    operation_start = metrics_registry.start_timer()

    tx_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": tx_obj_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if not transaction.get("liveness_required"):
        raise HTTPException(status_code=400, detail="Liveness verification not required for this transaction")

    if transaction.get("liveness_performed"):
        raise HTTPException(status_code=400, detail="Liveness verification already completed")

    detector = LivenessDetectorV3()

    risk_score = transaction.get("risk_score", 50)
    if risk_score >= 60:
        risk_level = "high"
    elif risk_score > 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    try:
        result = detector.verify(
            timeout_seconds=timeout,
            enable_passive=True,
            risk_level=risk_level,
            require_rppg=False,
        )

        result = convert_numpy_types(result)

        resolved_heart_rate = result.get("heart_rate", result.get("rppg_bpm"))
        resolved_confidence = result.get("heart_rate_confidence")
        if resolved_confidence is None and result.get("rppg_signal_ready") is not None:
            resolved_confidence = 1.0 if bool(result.get("rppg_signal_ready")) else 0.0

        update_data = {
            "liveness_performed": True,
            "liveness_result": {
                "success": result["success"],
                "message": result["message"],
                "challenges_completed": result.get("challenges_completed", []),
                "heart_rate": resolved_heart_rate,
                "heart_rate_confidence": resolved_confidence,
                "anti_spoofing": result.get("anti_spoofing", {}),
                "timestamp": datetime.utcnow(),
            },
            "status": "approved" if result["success"] else "rejected",
            "updated_at": datetime.utcnow(),
        }

        await db.transactions.update_one({"_id": tx_obj_id}, {"$set": update_data})

        if result["success"]:
            await settle_transaction_by_id(
                db=db,
                transaction_id=tx_obj_id,
                source="liveness_verify_endpoint",
            )

        metrics_registry.record_liveness(
            success=bool(result["success"]),
            duration_ms=metrics_registry.elapsed_ms(operation_start),
        )

        updated_transaction = await db.transactions.find_one({"_id": tx_obj_id})
        if updated_transaction and "_id" in updated_transaction:
            updated_transaction["_id"] = str(updated_transaction["_id"])

        return {
            "success": result["success"],
            "message": result["message"],
            "transaction": updated_transaction,
            "liveness_details": {
                "challenges_completed": result.get("challenges_completed", []),
                "heart_rate": resolved_heart_rate,
                "confidence": resolved_confidence,
                "anti_spoofing": result.get("anti_spoofing", {}),
            },
        }

    except Exception as exc:
        metrics_registry.record_db_error("liveness.verify", str(exc))
        raise HTTPException(status_code=500, detail=f"Liveness verification failed: {exc}")


@router.get("/status/{transaction_id}")
async def get_liveness_status(transaction_id: str, db=Depends(get_database)):
    """Get liveness verification status for a transaction."""
    tx_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": tx_obj_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": transaction_id,
        "liveness_required": transaction.get("liveness_required", False),
        "liveness_performed": transaction.get("liveness_performed", False),
        "liveness_result": transaction.get("liveness_result"),
        "status": transaction.get("status"),
    }


@router.get("/requirements/{transaction_id}")
async def get_liveness_requirements(transaction_id: str, db=Depends(get_database)):
    """Get liveness requirements based on transaction risk level."""
    tx_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": tx_obj_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    risk_level = str(transaction.get("risk_level", "MEDIUM")).upper()

    requirements = {
        "LOW": {"challenges": 3, "timeout": 30},
        "MEDIUM": {"challenges": 4, "timeout": 45},
        "HIGH": {"challenges": 5, "timeout": 60},
    }
    config = requirements.get(risk_level, requirements["MEDIUM"])

    return {
        "transaction_id": transaction_id,
        "risk_level": risk_level,
        "risk_score": transaction.get("risk_score", 0),
        "required_challenges": config["challenges"],
        "recommended_timeout": config["timeout"],
        "liveness_required": transaction.get("liveness_required", False),
    }


@router.post("/simulate")
async def simulate_liveness(success: bool = True):
    """Simulate liveness verification result (for testing/demo)."""
    mock_result = {
        "success": success,
        "challenges_completed": 5 if success else 2,
        "heart_rate": 72.0 if success else None,
        "heart_rate_confidence": 0.85 if success else 0.0,
        "anti_spoofing": {
            "early_detection_passed": success,
            "video_detected": not success,
            "printed_photo_detected": False,
            "mask_detected": False,
            "final_confidence": 0.92 if success else 0.45,
        },
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "SIMULATION",
    }

    return {
        "liveness_result": mock_result,
        "privacy_note": "No biometric data stored - only verification metadata",
    }
