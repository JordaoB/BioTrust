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
import cv2
import numpy as np

# Import liveness detector
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.liveness_detector_v3 import LivenessDetectorV3

router = APIRouter()


def convert_numpy_types(obj):
    """
    Recursively convert numpy types to Python native types
    MongoDB cannot serialize numpy.bool_, numpy.int64, etc.
    """
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


@router.post("/verify/{transaction_id}")
async def verify_liveness(
    transaction_id: str,
    timeout: int = 90,
    db=Depends(get_database)
):
    """
    Perform liveness verification for a transaction
    CHAMA O LIVENESS_DETECTOR_V3.PY DIRETAMENTE
    
    Abre janela OpenCV no servidor para verificação
    """
    
    operation_start = metrics_registry.start_timer()
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
    
    # Initialize liveness detector V3
    detector = LivenessDetectorV3()
    
    # Determinar risk level baseado no score
    risk_score = transaction.get("risk_score", 50)
    if risk_score >= 60:
        risk_level = "high"
    elif risk_score > 25:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    print(f"\n{'='*70}")
    print(f"🔐 INICIANDO VERIFICAÇÃO BIOMÉTRICA")
    print(f"Transaction ID: {transaction_id}")
    print(f"Risk Score: {risk_score}")
    print(f"Risk Level: {risk_level.upper()}")
    print(f"{'='*70}\n")
    
    try:
        # CHAMA O VERIFY() DIRETAMENTE - ABRE JANELA OpenCV
        result = detector.verify(
            timeout_seconds=timeout,
            enable_passive=True,  # rPPG heart rate
            risk_level=risk_level,
            require_rppg=False  # Advisory only
        )
        
        print(f"\n{'='*70}")
        print(f"📊 RESULTADO DA VERIFICAÇÃO:")
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        print(f"Challenges: {result.get('challenges_completed', [])}")
        print(f"{'='*70}\n")
        
        # Convert numpy types to Python native types for MongoDB
        result = convert_numpy_types(result)
        
        # Update transaction
        update_data = {
            "liveness_performed": True,
            "liveness_result": {
                "success": result["success"],
                "message": result["message"],
                "challenges_completed": result.get("challenges_completed", []),
                "heart_rate": result.get("heart_rate"),
                "heart_rate_confidence": result.get("heart_rate_confidence"),
                "anti_spoofing": result.get("anti_spoofing", {}),
                "timestamp": datetime.utcnow()
            },
            "status": "approved" if result["success"] else "rejected",
            "updated_at": datetime.utcnow()
        }
        
        await db.transactions.update_one(
            {"_id": transaction_obj_id},
            {"$set": update_data}
        )

        # 💰 Settlements are centralized in backend.services.transaction_settlement
        if result["success"]:
            settlement_result = await settle_transaction_by_id(
                db=db,
                transaction_id=transaction_obj_id,
                source="liveness_verify_endpoint"
            )
            print(
                f"Settlement result | TX: {transaction_id} | "
                f"settled: {settlement_result['settled']} | reason: {settlement_result['reason']}"
            )

        metrics_registry.record_liveness(
            success=bool(result["success"]),
            duration_ms=metrics_registry.elapsed_ms(operation_start),
        )

        alerts = metrics_registry.alerts()
        if alerts["has_alerts"]:
            for alert in alerts["active_alerts"]:
                print(
                    f"[ALERT:{alert['severity'].upper()}] {alert['type']} | {alert['message']}"
                )
        
        # Fetch updated transaction
        updated_transaction = await db.transactions.find_one({"_id": transaction_obj_id})
        
        # Serialize ObjectIds
        if "_id" in updated_transaction:
            updated_transaction["_id"] = str(updated_transaction["_id"])
        if "user_id" in updated_transaction:
            updated_transaction["user_id"] = str(updated_transaction["user_id"])
        if "card_id" in updated_transaction:
            updated_transaction["card_id"] = str(updated_transaction["card_id"])
        
        return {
            "success": result["success"],
            "message": result["message"],
            "transaction": updated_transaction,
            "liveness_details": {
                "challenges_completed": result.get("challenges_completed", []),
                "heart_rate": result.get("heart_rate"),
                "confidence": result.get("heart_rate_confidence"),
                "anti_spoofing": result.get("anti_spoofing", {})
            }
        }
        
    except Exception as e:
        import traceback
        print(f"\n❌ ERRO na verificação: {str(e)}")
        print(traceback.format_exc())
        metrics_registry.record_db_error("liveness.verify", str(e))
        raise HTTPException(status_code=500, detail=f"Liveness verification failed: {str(e)}")


@router.get("/status/{transaction_id}")
async def get_liveness_status(transaction_id: str, db=Depends(get_database)):
    """Get liveness verification status for a transaction"""
    
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
    
    transaction_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": transaction_obj_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    risk_level = str(transaction["risk_level"]).upper()
    
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
