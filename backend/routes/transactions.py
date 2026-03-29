"""
Transactions API Routes
Create and manage payment transactions with risk analysis
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from datetime import datetime, timedelta
from backend.database import get_database
from backend.models.transaction import (
    Transaction, TransactionCreate, TransactionStatus, RiskLevel
)
from backend.models.user import Location
from backend.utils.logger import logger, log_transaction_audit
from backend.services.transaction_settlement import settle_transaction_by_id
from backend.observability.metrics import metrics_registry
from bson import ObjectId
import sys
import os

# Import risk engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.risk_engine import RiskEngine

# Import anomaly detector
try:
    from src.core.anomaly_detector import anomaly_detector
    ANOMALY_DETECTOR_AVAILABLE = True
    logger.info("🤖 Anomaly detector loaded successfully")
except Exception as e:
    ANOMALY_DETECTOR_AVAILABLE = False
    logger.warning(f"⚠️ Anomaly detector not available: {e}")

router = APIRouter()
risk_engine = RiskEngine()


def serialize_doc(doc):
    """Convert MongoDB ObjectId to string"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def calculate_confidence_tier(risk_score: float, rppg_quality_score: float = 0.0, 
                            rppg_movement_correlation: float = 0.5) -> tuple[str, str]:
    """
    Calculate confidence tier (A/B/C) based on risk, rPPG quality, and movement.
    
    TIER A (≥75%): HIGH confidence → Auto-approve (no 2FA needed)
    TIER B (55-75%): MEDIUM confidence → Approve but flag for monitoring (2FA recommended)
    TIER C (<55%): LOW confidence → Reject or ask for extra verification
    
    Returns: (tier: str, reason: str)
    """
    # Pre-liveness confidence (based on risk alone)
    if risk_score <= 25:
        pre_liveness = 0.80  # Low risk = high confidence
    elif risk_score <= 50:
        pre_liveness = 0.60  # Medium risk = medium confidence
    else:
        pre_liveness = 0.40  # High risk = low confidence
    
    # Post-liveness adjustment (if rPPG was done)
    if rppg_quality_score > 0:
        # Combine rPPG quality & movement correlation (50/50 weight)
        rppg_confidence = (rppg_quality_score + rppg_movement_correlation) / 2.0
        # Final score: 70% risk-based, 30% rPPG-based
        confidence = (0.7 * pre_liveness) + (0.3 * rppg_confidence)
    else:
        confidence = pre_liveness
    
    # Determine tier
    if confidence >= 0.75:
        tier = "A"
        reason = "HIGH confidence (auto-approve)"
    elif confidence >= 0.55:
        tier = "B"
        reason = "MEDIUM confidence (2FA recommended)"
    else:
        tier = "C"
        reason = "LOW confidence (requires extra verification)"
    
    return tier, reason


def calculate_distance(loc1: dict, loc2: dict) -> float:
    """Calculate distance between two locations in km using Haversine formula"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth radius in km
    
    lat1, lon1 = radians(loc1["lat"]), radians(loc1["lon"])
    lat2, lon2 = radians(loc2["lat"]), radians(loc2["lon"]) 
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


@router.post("/", response_model=Transaction, status_code=201)
async def create_transaction(
    transaction_data: TransactionCreate,
    request: Request,
    db=Depends(get_database)
):
    """
    Create new transaction with risk analysis
    Determines if liveness verification is required
    """
    operation_start = metrics_registry.start_timer()
    try:
        logger.info(f"📝 New transaction request | User: {transaction_data.user_id} | Amount: €{transaction_data.amount:.2f} | Merchant: {transaction_data.merchant_id}")
        
        # Fetch user
        user_id_obj = ObjectId(transaction_data.user_id) if ObjectId.is_valid(transaction_data.user_id) else transaction_data.user_id
        user = await db.users.find_one({"_id": user_id_obj})
        if not user:
            logger.warning(f"⚠️ User not found: {transaction_data.user_id}")
            raise HTTPException(status_code=404, detail=f"User not found: {transaction_data.user_id}")

        # Mandatory requirement: user must have a stored master selfie (enrollment done).
        # Live comparison is performed in the liveness modal flow.
        face_identity = user.get("face_identity", {})
        if not face_identity.get("reference_encoding"):
            raise HTTPException(
                status_code=428,
                detail="Face identity enrollment is required before creating transactions",
            )
        
        # Get card from user's inline cards array (cards are stored in user document)
        user_cards = user.get("cards", [])
        card = None
        card_index = None
        
        # Priority 1: Use card_index if provided (direct array index)
        if transaction_data.card_index is not None:
            if 0 <= transaction_data.card_index < len(user_cards):
                card = user_cards[transaction_data.card_index]
                card_index = transaction_data.card_index
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid card index: {transaction_data.card_index}"
                )
        # Priority 2: Use default card
        elif not card:
            for idx, c in enumerate(user_cards):
                if c.get("is_default", False):
                    card = c
                    card_index = idx
                    break
        # Priority 3: Use first card
        if not card and user_cards:
            card = user_cards[0]
            card_index = 0
        
        if not card:
            raise HTTPException(status_code=404, detail="No cards found for user. Please add a card first.")
        
        # VALIDATE CARD BALANCE AND LIMITS
        card_balance = card.get("balance", 0.0)
        daily_spent = card.get("daily_spent", 0.0)
        daily_limit = card.get("daily_limit", 5000.0)
        max_transaction = card.get("max_transaction", 2000.0)
        last_reset = card.get("last_reset", datetime.utcnow().date().isoformat())
        
        # Reset daily spent if it's a new day
        today = datetime.utcnow().date().isoformat()
        if last_reset != today:
            daily_spent = 0.0
            # Update card's daily_spent and last_reset
            await db.users.update_one(
                {"_id": user_id_obj},
                {
                    "$set": {
                        f"cards.{card_index}.daily_spent": 0.0,
                        f"cards.{card_index}.last_reset": today
                    }
                }
            )
        
        # Check if card has sufficient balance
        if card_balance < transaction_data.amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. Available: €{card_balance:.2f}, Required: €{transaction_data.amount:.2f}"
            )
        
        # Check if transaction exceeds max per transaction
        if transaction_data.amount > max_transaction:
            raise HTTPException(
                status_code=400,
                detail=f"Transaction exceeds the maximum limit of €{max_transaction:.2f} per transaction"
            )
        
        # Check if transaction would exceed daily limit
        if (daily_spent + transaction_data.amount) > daily_limit:
            remaining = daily_limit - daily_spent
            raise HTTPException(
                status_code=400,
                detail=f"Daily limit exceeded. Available today: €{remaining:.2f}"
            )
        
        # Card is active by default since we don't have is_active field in inline cards
        
        # Fetch merchant if provided
        merchant = None
        merchant_info = None
        if transaction_data.merchant_id:
            merchant = await db.merchants.find_one({"_id": ObjectId(transaction_data.merchant_id) if ObjectId.is_valid(transaction_data.merchant_id) else transaction_data.merchant_id})
            if merchant:
                merchant_info = {
                    "merchant_id": str(merchant["_id"]),
                    "name": merchant["name"],
                    "category": merchant["category"],
                    "location": {
                        "lat": merchant["location"]["lat"],
                        "lon": merchant["location"]["lon"]
                    },
                    "city": merchant["location"]["city"]
                }
        
        # Calculate distances
        distance_from_home = calculate_distance(
            user["home_location"],
            transaction_data.user_location
        )
        
        distance_from_merchant = None
        if merchant_info:
            distance_from_merchant = calculate_distance(
                transaction_data.user_location,
                merchant_info["location"]
            )
        
        # Risk analysis using FINTECH-GRADE risk engine
        # Fetch recent transactions (last 24h for velocity checks)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_transactions = await db.transactions.find({
            "user_id": transaction_data.user_id,
            "created_at": {"$gte": recent_cutoff}
        }).to_list(length=100)
        
        # Build recipient and merchant history
        recipient_history = {}
        merchant_history = {}
        for tx in recent_transactions:
            if tx.get("recipient_email"):
                recipient_history[tx["recipient_email"]] = recipient_history.get(tx["recipient_email"], 0) + 1
            if tx.get("merchant_id"):
                merchant_history[tx["merchant_id"]] = merchant_history.get(tx["merchant_id"], 0) + 1
        
        transaction_for_risk = {
            "amount": transaction_data.amount,
            "location": {
                "city": transaction_data.user_location.get("city", "Unknown"),
                "country": user["home_location"].get("country", "Unknown"),
                "lat": transaction_data.user_location["lat"],
                "lon": transaction_data.user_location["lon"]
            },
            "timestamp": datetime.utcnow(),
            "transaction_type": str(transaction_data.type),
            "recipient_email": transaction_data.recipient_email,  # For transfers
            "merchant_id": transaction_data.merchant_id,  # For payments
            "user_profile": {
                "average_transaction": user.get("average_transaction", 50.0),
                "max_transaction": user.get("max_transaction", 200.0),
                "total_sent": user.get("total_sent", 0.0),
                "transactions_today": user.get("transactions_today", 0),
                "home_location": user["home_location"],
                "last_transaction_location": user.get("last_transaction_location", user["home_location"]),
                "last_transaction_time": user.get("last_transaction_time"),
                "account_age_days": user.get("account_age_days", 0),
                "recent_transactions": recent_transactions,  # For velocity checks
                "recipient_history": recipient_history,  # For trust scoring
                "merchant_history": merchant_history   # For trust scoring
            }
        }
        
        risk_analysis = risk_engine.analyze_transaction(transaction_for_risk)
        risk_score = risk_analysis['risk_score']
        risk_reason = risk_analysis.get('reason')
        risk_factors = risk_analysis.get('factors', {})
        
        # ML Anomaly Detection
        is_anomaly = False
        anomaly_score = 0.0
        anomaly_reason = None
        
        if ANOMALY_DETECTOR_AVAILABLE:
            try:
                # Count recent transactions
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                
                transactions_last_hour = await db.transactions.count_documents({
                    "user_id": transaction_data.user_id,
                    "created_at": {"$gte": one_hour_ago}
                })
                
                # Get last transaction time
                last_tx = await db.transactions.find_one(
                    {"user_id": transaction_data.user_id},
                    sort=[("created_at", -1)]
                )
                last_transaction_time = last_tx.get("created_at") if last_tx else None
                
                # Predict anomaly
                is_anomaly, anomaly_score, anomaly_reason = anomaly_detector.predict(
                    transaction_data={
                        "amount": transaction_data.amount,
                        "distance_from_home_km": distance_from_home,
                        "created_at": datetime.utcnow()
                    },
                    user_history={
                        "average_transaction": user.get("average_transaction", 0),
                        "transactions_today": user.get("transactions_today", 0),
                        "transactions_last_hour": transactions_last_hour,
                        "last_transaction_time": last_transaction_time
                    }
                )
                
                # Adjust risk score if anomaly detected
                if is_anomaly:
                    # Add 15% of anomaly score to risk score (max boost: +15 points)
                    risk_boost = min(15, anomaly_score * 0.15)
                    risk_score = min(100, risk_score + risk_boost)
                    logger.warning(f"🚨 ANOMALY DETECTED | Score: {anomaly_score:.1f}/100 | Reason: {anomaly_reason} | Risk boost: +{risk_boost:.1f}")
                else:
                    logger.info(f"✅ No anomaly detected | Score: {anomaly_score:.1f}/100")
                    
            except Exception as e:
                logger.error(f"❌ Anomaly detection failed: {e}")
                # Continue without anomaly detection
        
        risk_level = RiskLevel.LOW
        if risk_score >= 60:  # New threshold: 60+ = High Risk
            risk_level = RiskLevel.HIGH
        elif risk_score > 25:  # New threshold: 26-59 = Medium Risk
            risk_level = RiskLevel.MEDIUM
        
        # Calculate confidence tier (A/B/C) for 3-tier system
        confidence_tier, tier_reason = calculate_confidence_tier(risk_score)
        liveness_required = risk_score > 25  # Still require liveness for medium/high risk
        
        # Create transaction document
        transaction_dict = {
            "user_id": transaction_data.user_id,
            "card_id": transaction_data.card_id,
            "card_index": card_index,  # Store card index for later use
            "merchant_id": transaction_data.merchant_id,
            "merchant_info": merchant_info,
            "recipient_email": transaction_data.recipient_email,  # For transfers
            "amount": transaction_data.amount,
            "currency": transaction_data.currency,
            "transaction_type": transaction_data.type,
            "user_location": transaction_data.user_location,
            "distance_from_home_km": round(distance_from_home, 2),
            "distance_from_merchant_km": round(distance_from_merchant, 2) if distance_from_merchant else None,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "risk_factors": risk_factors,
            "anomaly_detected": bool(is_anomaly),  # Convert numpy bool to Python bool
            "anomaly_score": round(float(anomaly_score), 2),  # Convert numpy float to Python float
            "anomaly_reason": anomaly_reason,
            "confidence_tier": confidence_tier,  # A/B/C tier
            "tier_reason": tier_reason,  # Explanation for tier
            "requires_2fa": confidence_tier == "B",  # TIER B needs 2FA
            "liveness_required": liveness_required,
            "liveness_performed": False,
            "liveness_result": None,
            "status": TransactionStatus.PENDING if liveness_required else TransactionStatus.APPROVED,
            "settlement": {
                "applied": False,
                "state": "pending"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.transactions.insert_one(transaction_dict)
        transaction_id = str(result.inserted_id)
        
        # Log transaction creation
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", None)
        
        # If transaction is approved immediately (low risk), deduct from card balance
        if transaction_dict["status"] == TransactionStatus.APPROVED:
            logger.success(f"✅ Transaction APPROVED (Low Risk) | ID: {transaction_id} | User: {transaction_data.user_id} | €{transaction_data.amount:.2f}")
            settlement_result = await settle_transaction_by_id(
                db=db,
                transaction_id=result.inserted_id,
                source="create_transaction_auto_approved"
            )

            if settlement_result["settled"]:
                logger.success(
                    f"✅ Funds settled | TX: {transaction_id} | "
                    f"Card Index: {settlement_result['card_index']} | "
                    f"Amount: €{settlement_result['amount']:.2f}"
                )
            else:
                logger.warning(
                    f"⚠️ Settlement skipped | TX: {transaction_id} | Reason: {settlement_result['reason']}"
                )
            
            # Audit log for approved transaction
            log_transaction_audit(
                transaction_id=transaction_id,
                user_id=transaction_data.user_id,
                amount=transaction_data.amount,
                merchant_id=transaction_data.merchant_id,
                status="APPROVED",
                risk_score=risk_score,
                risk_level=risk_level.value,
                liveness_verified=False,
                ip_address=ip_address,
                user_agent=user_agent,
                reason="Low risk - auto-approved"
            )

        metrics_registry.record_transaction(
            status=str(transaction_dict["status"]),
            duration_ms=metrics_registry.elapsed_ms(operation_start),
        )

        alerts = metrics_registry.alerts()
        if alerts["has_alerts"]:
            for alert in alerts["active_alerts"]:
                logger.warning(
                    f"[ALERT:{alert['severity'].upper()}] {alert['type']} | {alert['message']}"
                )
        else:
            logger.warning(f"⏳ Transaction PENDING (Liveness Required) | ID: {transaction_id} | User: {transaction_data.user_id} | €{transaction_data.amount:.2f} | Risk: {risk_level.value} ({risk_score:.1f}%)")
            
            # Audit log for pending transaction
            log_transaction_audit(
                transaction_id=transaction_id,
                user_id=transaction_data.user_id,
                amount=transaction_data.amount,
                merchant_id=transaction_data.merchant_id,
                status="PENDING",
                risk_score=risk_score,
                risk_level=risk_level.value,
                liveness_verified=False,
                ip_address=ip_address,
                user_agent=user_agent,
                reason="Medium/High risk - liveness required"
            )
        
        # Update user stats
        await db.users.update_one(
            {"_id": ObjectId(transaction_data.user_id) if ObjectId.is_valid(transaction_data.user_id) else transaction_data.user_id},
            {
                "$inc": {"transactions_today": 1},
                "$set": {"last_transaction_location": transaction_data.user_location},
                "$push": {"location_history": transaction_data.user_location}
            }
        )
        
        # Update merchant stats if applicable
        if transaction_data.merchant_id:
            await db.merchants.update_one(
                {"_id": ObjectId(transaction_data.merchant_id) if ObjectId.is_valid(transaction_data.merchant_id) else transaction_data.merchant_id},
                {"$inc": {"total_transactions": 1}}
            )
        
        # Fetch created transaction
        created_transaction = await db.transactions.find_one({"_id": result.inserted_id})
        return serialize_doc(created_transaction)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"❌ Transaction creation failed | User: {transaction_data.user_id} | Amount: €{transaction_data.amount:.2f} | Error: {str(e)}")
        metrics_registry.record_db_error("transactions.create_transaction", str(e))
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str, db=Depends(get_database)):
    """Get transaction by ID"""
    transaction = await db.transactions.find_one({"_id": ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return serialize_doc(transaction)


@router.get("/user/{user_id}", response_model=List[Transaction])
async def get_user_transactions(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    db=Depends(get_database)
):
    """Get transaction history for a user"""
    cursor = db.transactions.find(
        {"user_id": user_id}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    transactions = await cursor.to_list(length=limit)
    return [serialize_doc(tx) for tx in transactions]


@router.patch("/{transaction_id}/liveness")
async def update_transaction_liveness(
    transaction_id: str,
    liveness_result: dict,
    request: Request,
    db=Depends(get_database)
):
    """
    Update transaction with liveness verification result
    Called after liveness verification is completed
    """
    
    liveness_update_start = metrics_registry.start_timer()
    transaction_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": transaction_obj_id})
    if not transaction:
        logger.warning(f"⚠️ Liveness update failed: Transaction {transaction_id} not found")
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not transaction["liveness_required"]:
        raise HTTPException(status_code=400, detail="Liveness not required for this transaction")
    
    # Determine final status based on liveness result + rPPG metrics
    liveness_success = liveness_result.get("success", False)
    confidence = liveness_result.get("confidence", 0)
    reason = liveness_result.get("reason", "N/A")
    
    # Extract rPPG metrics from liveness result
    rppg_quality_score = liveness_result.get("rppg_quality_score", 0.0) or 0.0
    rppg_movement_correlation = liveness_result.get("rppg_movement_correlation", 0.5) or 0.5
    
    # Recalculate confidence tier with rPPG data
    original_risk = transaction.get("risk_score", 50.0)
    new_tier, new_tier_reason = calculate_confidence_tier(
        original_risk,
        rppg_quality_score,
        rppg_movement_correlation
    )
    
    # Final decision:
    # If liveness passed AND tier is A/B -> approve
    # If liveness passed but tier is C -> require 2FA
    # If liveness failed -> reject
    if liveness_success and new_tier in ["A", "B"]:
        new_status = TransactionStatus.APPROVED
    elif liveness_success and new_tier == "C":
        # Tier C: mark as needing 2FA instead of auto-reject
        new_status = TransactionStatus.PENDING
        reason += " (Tier C: 2FA required)"
    else:
        new_status = TransactionStatus.REJECTED
    
    logger.info(f"🔐 Liveness verification completed | TX: {transaction_id} | Success: {liveness_success} | Confidence: {confidence:.1f}% | Tier: {new_tier} | Reason: {reason}")
    
    # Update transaction
    await db.transactions.update_one(
        {"_id": transaction_obj_id},
        {
            "$set": {
                "liveness_performed": True,
                "liveness_result": liveness_result,
                "confidence_tier": new_tier,
                "tier_reason": new_tier_reason,
                "requires_2fa": new_tier == "B",
                "status": new_status,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # If liveness was successful, deduct from card balance
    if liveness_success:
        settlement_result = await settle_transaction_by_id(
            db=db,
            transaction_id=transaction_obj_id,
            source="transactions_patch_liveness"
        )

        if settlement_result["settled"]:
            logger.success(
                f"✅ Funds settled after liveness | TX: {transaction_id} | "
                f"Card Index: {settlement_result['card_index']} | "
                f"Amount: €{settlement_result['amount']:.2f}"
            )
        else:
            logger.warning(
                f"⚠️ Settlement skipped after liveness | TX: {transaction_id} | Reason: {settlement_result['reason']}"
            )

    metrics_registry.record_liveness(
        success=bool(liveness_success),
        duration_ms=metrics_registry.elapsed_ms(liveness_update_start),
    )
    
    # Update user liveness count
    await db.users.update_one(
        {"_id": ObjectId(transaction["user_id"]) if ObjectId.is_valid(transaction["user_id"]) else transaction["user_id"]},
        {"$inc": {"liveness_verifications_count": 1}}
    )
    
    # Audit log for liveness update
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    
    if liveness_success:
        logger.success(f"✅ Transaction APPROVED (Liveness Passed) | TX: {transaction_id} | User: {transaction['user_id']} | €{transaction['amount']:.2f}")
    else:
        logger.error(f"❌ Transaction REJECTED (Liveness Failed) | TX: {transaction_id} | User: {transaction['user_id']} | €{transaction['amount']:.2f} | Reason: {reason}")
    
    log_transaction_audit(
        transaction_id=transaction_id,
        user_id=transaction["user_id"],
        amount=transaction["amount"],
        merchant_id=transaction.get("merchant_id"),
        status=new_status.value,
        risk_score=transaction.get("risk_score"),
        risk_level=transaction.get("risk_level"),
        liveness_verified=True,
        ip_address=ip_address,
        user_agent=user_agent,
        reason=f"Liveness {('passed' if liveness_success else 'failed')}: {reason}"
    )
    
    # Fetch updated transaction
    updated_transaction = await db.transactions.find_one({"_id": transaction_obj_id})
    return serialize_doc(updated_transaction)