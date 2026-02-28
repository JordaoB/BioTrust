"""
BioTrust API Server
FastAPI REST API for risk analysis, liveness detection, and payment processing.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import cv2
import numpy as np
import tempfile
import os
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import BioTrust modules
from src.core.risk_engine import RiskEngine
from src.core.liveness_detector import LivenessDetector
from src.core.transaction_logger import TransactionLogger

# Initialize FastAPI app
app = FastAPI(
    title="BioTrust API",
    description="Biometric Trust Payment System with Risk Analysis and Liveness Detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
risk_engine = RiskEngine()
logger = TransactionLogger()

# Mock data for API (locations and user profiles)
LOCATIONS = {
    "maputo": {
        "city": "Maputo",
        "country": "Mozambique",
        "coordinates": {"lat": -25.9692, "lon": 32.5732}
    },
    "beira": {
        "city": "Beira",
        "country": "Mozambique",
        "coordinates": {"lat": -19.8436, "lon": 34.8389}
    },
    "nampula": {
        "city": "Nampula",
        "country": "Mozambique",
        "coordinates": {"lat": -15.1165, "lon": 39.2666}
    },
    "default": {
        "city": "Unknown",
        "country": "Mozambique",
        "coordinates": {"lat": -18.665695, "lon": 35.529562}
    }
}

USER_PROFILES = {
    "default": {
        "transaction_count": 10,
        "avg_transaction": 1500.0,
        "max_transaction": 5000.0,
        "known_locations": ["maputo"],
        "usual_times": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "last_transaction": datetime.now()
    }
}

def _prepare_transaction_for_risk_engine(amount: float, user_id: str, location: Optional[str], merchant_id: str) -> dict:
    """Helper to convert API parameters to RiskEngine transaction format"""
    # Parse location
    if location:
        location_key = location.lower().split(",")[0].strip()
        location_data = LOCATIONS.get(location_key, LOCATIONS["default"])
    else:
        location_data = LOCATIONS["default"]
    
    # Get user profile (or use default)
    user_profile = USER_PROFILES.get(user_id, USER_PROFILES["default"])
    
    return {
        "amount": amount,
        "location": location_data,
        "timestamp": datetime.now(),
        "transaction_type": "online",
        "user_profile": user_profile
    }

# =====================================================================
# Request/Response Models
# =====================================================================

class RiskAnalysisRequest(BaseModel):
    """Risk analysis request model"""
    amount: float = Field(..., gt=0, description="Transaction amount in MZN")
    user_id: str = Field(..., min_length=1, description="User identifier")
    merchant_id: str = Field(..., min_length=1, description="Merchant identifier")
    location: Optional[str] = Field(None, description="Transaction location")
    device_id: Optional[str] = Field(None, description="Device identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 2500.00,
                "user_id": "user_123",
                "merchant_id": "merch_456",
                "location": "Maputo, Mozambique",
                "device_id": "device_789"
            }
        }

class RiskAnalysisResponse(BaseModel):
    """Risk analysis response model"""
    risk_score: float = Field(..., description="Risk score (0-100)")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH")
    requires_liveness: bool = Field(..., description="Whether liveness check is required")
    factors: Dict[str, Any] = Field(..., description="Risk factors breakdown")
    recommendation: str = Field(..., description="Action recommendation")
    timestamp: str = Field(..., description="Analysis timestamp")

class LivenessVerificationResponse(BaseModel):
    """Liveness verification response model"""
    verified: bool = Field(..., description="Whether liveness was verified")
    active_liveness: bool = Field(..., description="Active liveness result")
    passive_liveness: bool = Field(..., description="Passive liveness result (rPPG)")
    blink_count: int = Field(..., description="Number of blinks detected")
    head_movements: List[str] = Field(..., description="Head movements detected")
    heart_rate: Optional[float] = Field(None, description="Detected heart rate (BPM)")
    heart_rate_confidence: Optional[float] = Field(None, description="Heart rate confidence (0-1)")
    message: str = Field(..., description="Verification message")
    timestamp: str = Field(..., description="Verification timestamp")

class PaymentRequest(BaseModel):
    """Payment processing request model"""
    amount: float = Field(..., gt=0, description="Payment amount in MZN")
    user_id: str = Field(..., min_length=1, description="User identifier")
    merchant_id: str = Field(..., min_length=1, description="Merchant identifier")
    description: str = Field(..., min_length=1, description="Payment description")
    location: Optional[str] = Field(None, description="Transaction location")
    device_id: Optional[str] = Field(None, description="Device identifier")
    liveness_mode: str = Field("active", description="Liveness mode: active, passive, multi")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 2500.00,
                "user_id": "user_123",
                "merchant_id": "merch_456",
                "description": "Phone purchase",
                "location": "Maputo, Mozambique",
                "device_id": "device_789",
                "liveness_mode": "active"
            }
        }

class PaymentResponse(BaseModel):
    """Payment processing response model"""
    status: str = Field(..., description="Payment status: APPROVED, REJECTED, PENDING")
    transaction_id: Optional[str] = Field(None, description="Transaction identifier")
    amount: float = Field(..., description="Payment amount")
    risk_score: float = Field(..., description="Risk score")
    risk_level: str = Field(..., description="Risk level")
    liveness_verified: bool = Field(..., description="Liveness verification result")
    heart_rate: Optional[float] = Field(None, description="Detected heart rate")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="Processing timestamp")

# =====================================================================
# API Endpoints
# =====================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "BioTrust API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "risk_analysis": "/api/analyze-risk",
            "liveness_verification": "/api/verify-liveness",
            "payment_processing": "/api/process-payment"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "risk_engine": "operational",
            "liveness_detector": "operational",
            "transaction_logger": "operational"
        }
    }

@app.post("/api/analyze-risk", response_model=RiskAnalysisResponse)
async def analyze_risk(request: RiskAnalysisRequest):
    """
    Analyze transaction risk based on amount, user history, and context.
    
    Returns risk score (0-100), risk level, and whether liveness check is required.
    """
    try:
        # Prepare transaction data
        transaction = _prepare_transaction_for_risk_engine(
            amount=request.amount,
            user_id=request.user_id,
            location=request.location,
            merchant_id=request.merchant_id
        )
        
        # Perform risk analysis
        risk_result = risk_engine.analyze_transaction(transaction)
        
        # Map decision to risk level and liveness requirement
        decision = risk_result['decision']
        if decision == 'approve':
            risk_level = 'LOW'
            requires_liveness = False
        elif decision == 'require_liveness':
            risk_level = 'MEDIUM' if risk_result['risk_score'] < 70 else 'HIGH'
            requires_liveness = True
        else:  # block
            risk_level = 'HIGH'
            requires_liveness = True
        
        return RiskAnalysisResponse(
            risk_score=float(risk_result['risk_score']),
            risk_level=risk_level,
            requires_liveness=requires_liveness,
            factors=risk_result['factors'],
            recommendation=risk_result['reason'],
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {str(e)}")

@app.post("/api/verify-liveness")
async def verify_liveness(
    mode: str = "active",
    enable_passive: bool = True
):
    """
    Perform liveness detection using webcam.
    
    Modes:
    - active: Blink and head movement detection (with optional rPPG)
    - passive: Heart rate detection via rPPG only
    
    Note: This endpoint requires camera access on the server.
    For production, consider using client-side capture with video upload.
    """
    try:
        detector = LivenessDetector()
        
        if mode == "passive":
            # Import passive liveness module
            from src.core.passive_liveness import PassiveLivenessDetector
            passive_detector = PassiveLivenessDetector()
            result = passive_detector.verify()
            
            return LivenessVerificationResponse(
                verified=result.get('verified', False),
                active_liveness=False,
                passive_liveness=result.get('verified', False),
                blink_count=0,
                head_movements=[],
                heart_rate=result.get('heart_rate'),
                heart_rate_confidence=result.get('confidence'),
                message=result.get('message', 'No message'),
                timestamp=datetime.now().isoformat()
            )
        
        else:  # active mode
            result = detector.verify(enable_passive=enable_passive)
            
            # Map 'success' to 'verified'
            verified = result.get('success', False)
            
            return LivenessVerificationResponse(
                verified=verified,
                active_liveness=verified if not enable_passive else (verified and not result.get('passive_liveness', False)),
                passive_liveness=result.get('passive_liveness', False),
                blink_count=result.get('blinks_detected', 0),
                head_movements=result.get('head_movements', []),
                heart_rate=result.get('heart_rate'),
                heart_rate_confidence=result.get('heart_rate_confidence'),
                message=result.get('message', 'No message'),
                timestamp=datetime.now().isoformat()
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Liveness verification failed: {str(e)}")

@app.post("/api/process-payment", response_model=PaymentResponse)
async def process_payment(request: PaymentRequest):
    """
    Process payment with integrated risk analysis and liveness detection.
    
    Steps:
    1. Analyze transaction risk
    2. If risk is elevated, require liveness verification
    3. Process payment if all checks pass
    4. Log transaction
    
    Liveness modes:
    - active: Blink + head movement (with rPPG)
    - passive: Heart rate detection only
    - multi: Sequential active then passive
    """
    try:
        # Step 1: Risk Analysis
        transaction = _prepare_transaction_for_risk_engine(
            amount=request.amount,
            user_id=request.user_id,
            location=request.location,
            merchant_id=request.merchant_id
        )
        
        risk_result = risk_engine.analyze_transaction(transaction)
        
        # Map decision to risk level and liveness requirement
        decision = risk_result['decision']
        if decision == 'approve':
            risk_level = 'LOW'
            requires_liveness = False
        elif decision == 'require_liveness':
            risk_level = 'MEDIUM' if risk_result['risk_score'] < 70 else 'HIGH'
            requires_liveness = True
        else:  # block
            risk_level = 'HIGH'
            requires_liveness = True
        
        # Step 2: Liveness Verification (if required)
        liveness_verified = False
        heart_rate = None
        liveness_message = "No liveness check performed"
        
        if requires_liveness:
            detector = LivenessDetector()
            
            if request.liveness_mode == "passive":
                from src.core.passive_liveness import PassiveLivenessDetector
                passive_detector = PassiveLivenessDetector()
                liveness_result = passive_detector.verify()
                liveness_verified = liveness_result.get('verified', False)
            elif request.liveness_mode == "multi":
                # Active without passive, then passive
                active_result = detector.verify(enable_passive=False)
                if active_result.get('success', False):
                    from src.core.passive_liveness import PassiveLivenessDetector
                    passive_detector = PassiveLivenessDetector()
                    passive_result = passive_detector.verify()
                    liveness_result = {
                        'success': passive_result.get('verified', False),
                        'heart_rate': passive_result.get('heart_rate'),
                        'message': f"Active: ✓ | Passive: {'✓' if passive_result.get('verified', False) else '✗'}"
                    }
                else:
                    liveness_result = active_result
                liveness_verified = liveness_result.get('success', False)
            else:  # active mode (default)
                liveness_result = detector.verify(enable_passive=True)
                liveness_verified = liveness_result.get('success', False)
            
            heart_rate = liveness_result.get('heart_rate')
            liveness_message = liveness_result.get('message', 'Liveness check completed')
        else:
            # Low risk transaction - approved without liveness
            liveness_verified = True
            liveness_message = "Low risk - liveness check skipped"
        
        # Step 3: Determine payment status
        if liveness_verified:
            status = "APPROVED"
            # Generate transaction ID
            transaction_id = f"txn_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Log transaction
            logger.log_transaction({
                "transaction_id": transaction_id,
                "user_id": request.user_id,
                "merchant_id": request.merchant_id,
                "amount": request.amount,
                "description": request.description,
                "risk_score": risk_result['risk_score'],
                "risk_level": risk_level,
                "approved": True,
                "liveness_performed": requires_liveness,
                "liveness_verified": True,
                "heart_rate": heart_rate,
                "timestamp": datetime.now().isoformat()
            })
            message = f"Payment approved - {liveness_message}"
        else:
            status = "REJECTED"
            transaction_id = None
            
            # Log rejected transaction
            logger.log_transaction({
                "transaction_id": None,
                "user_id": request.user_id,
                "merchant_id": request.merchant_id,
                "amount": request.amount,
                "description": request.description,
                "risk_score": risk_result['risk_score'],
                "risk_level": risk_level,
                "approved": False,
                "liveness_performed": requires_liveness,
                "liveness_verified": False,
                "heart_rate": heart_rate,
                "timestamp": datetime.now().isoformat()
            })
            message = f"Payment rejected - {liveness_message}"
        
        return PaymentResponse(
            status=status,
            transaction_id=transaction_id,
            amount=request.amount,
            risk_score=float(risk_result['risk_score']),
            risk_level=risk_level,
            liveness_verified=liveness_verified,
            heart_rate=heart_rate,
            message=message,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(e)}")

# =====================================================================
# Server Startup
# =====================================================================

if __name__ == "__main__":
    print("🚀 Starting BioTrust API Server...")
    print("📚 Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")
    print("")
    print("Available endpoints:")
    print("  POST /api/analyze-risk      - Analyze transaction risk")
    print("  POST /api/verify-liveness   - Verify user liveness")
    print("  POST /api/process-payment   - Process payment with all checks")
    print("")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
