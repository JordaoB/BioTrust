"""
Liveness API Routes
Real-time biometric verification for high-risk transactions
PRIVACY-BY-DESIGN: No biometric data is stored - only verification metadata
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from backend.database import get_database
import sys
import os
import cv2

# Import liveness detector
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.liveness_detector_v2 import LivenessDetectorV2

router = APIRouter()


@router.post("/verify/{transaction_id}")
async def verify_liveness(
    transaction_id: str,
    timeout: int = 60,
    db=Depends(get_database)
):
    """
    Perform liveness verification for a transaction
    
    PRIVACY NOTE:
    - Video frames are processed in real-time and immediately discarded
    - Only verification metadata is stored (no images, no face encodings)
    - Metadata includes: challenges completed, heart rate, confidence scores
    
    Args:
        transaction_id: Transaction requiring verification
        timeout: Max time in seconds (default 60s)
    
    Returns:
        Liveness verification result with metadata only
    """
    from bson import ObjectId
    
    # Fetch transaction
    transaction_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": transaction_obj_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not transaction["liveness_required"]:
        raise HTTPException(
            status_code=400,
            detail="Liveness verification not required for this transaction"
        )
    
    if transaction["liveness_performed"]:
        raise HTTPException(
            status_code=400,
            detail="Liveness verification already completed"
        )
    
    # Initialize liveness detector
    detector = LivenessDetectorV2()
    
    try:
        # Perform verification
        # Note: In production, this would stream from frontend webcam
        # For now, opens local camera (demo mode)
        result = detector.verify(timeout=timeout)
        
        # Extract METADATA ONLY (no raw biometric data)
        liveness_result = {
            "success": result["success"],
            "challenges_completed": result.get("challenges_completed", 0),
            "heart_rate": result.get("heart_rate"),
            "heart_rate_confidence": result.get("heart_rate_confidence"),
            "anti_spoofing": {
                "early_detection_passed": result.get("anti_spoofing", {}).get("early_detection_passed", False),
                "video_detected": result.get("anti_spoofing", {}).get("video_detected", False),
                "printed_photo_detected": result.get("anti_spoofing", {}).get("printed_photo_detected", False),
                "mask_detected": result.get("anti_spoofing", {}).get("mask_detected", False),
                "final_confidence": result.get("anti_spoofing", {}).get("final_confidence", 0.0)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update transaction with liveness result
        from backend.models.transaction import TransactionStatus
        new_status = TransactionStatus.APPROVED if result["success"] else TransactionStatus.REJECTED
        
        await db.transactions.update_one(
            {"_id": transaction_obj_id},
            {
                "$set": {
                    "liveness_performed": True,
                    "liveness_result": liveness_result,
                    "status": new_status,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update user liveness verification count
        from bson import ObjectId
        await db.users.update_one(
            {"_id": ObjectId(transaction["user_id"]) if ObjectId.is_valid(transaction["user_id"]) else transaction["user_id"]},
            {"$inc": {"liveness_verifications_count": 1}}
        )
        
        return {
            "transaction_id": transaction_id,
            "liveness_result": liveness_result,
            "status": new_status,
            "privacy_note": "No biometric data stored - only verification metadata"
        }
        
    except Exception as e:
        # Log error but do not store biometric data
        return {
            "transaction_id": transaction_id,
            "success": False,
            "error": str(e),
            "liveness_result": {
                "success": False,
                "challenges_completed": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    finally:
        # Ensure detector resources are released
        detector.release()


@router.get("/status/{transaction_id}")
async def get_liveness_status(transaction_id: str, db=Depends(get_database)):
    """
    Get liveness verification status for a transaction
    Returns only metadata - no biometric data
    """
    from bson import ObjectId
    
    transaction_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": transaction_obj_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "transaction_id": transaction_id,
        "liveness_required": transaction["liveness_required"],
        "liveness_performed": transaction["liveness_performed"],
        "liveness_result": transaction.get("liveness_result"),
        "status": transaction["status"]
    }


@router.get("/requirements/{transaction_id}")
async def get_liveness_requirements(transaction_id: str, db=Depends(get_database)):
    """
    Get liveness verification requirements based on risk level
    Returns challenge count and timeout
    """
    from bson import ObjectId
    
    transaction_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": transaction_obj_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    risk_level = transaction["risk_level"]
    
    # Challenge count based on risk
    requirements = {
        "LOW": {"challenges": 3, "timeout": 30},
        "MEDIUM": {"challenges": 4, "timeout": 45},
        "HIGH": {"challenges": 5, "timeout": 60}
    }
    
    config = requirements.get(risk_level, requirements["MEDIUM"])
    
    return {
        "transaction_id": transaction_id,
        "risk_level": risk_level,
        "risk_score": transaction["risk_score"],
        "required_challenges": config["challenges"],
        "recommended_timeout": config["timeout"],
        "liveness_required": transaction["liveness_required"]
    }


@router.post("/simulate")
async def simulate_liveness(success: bool = True):
    """
    Simulate liveness verification result (for testing/demo)
    Returns mock metadata without camera access
    """
    
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
            "final_confidence": 0.92 if success else 0.45
        },
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "SIMULATION"
    }
    
    return {
        "liveness_result": mock_result,
        "privacy_note": "No biometric data stored - only verification metadata"
    }
