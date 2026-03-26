"""
Liveness Stream API - Frame-by-frame processing for web integration
Processes frames sent from browser webcam with LivenessDetectorV3
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from backend.database import get_database
from bson import ObjectId
import sys
import os
import cv2
import numpy as np
import base64
import uuid
import random

# Import liveness detector
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.liveness_detector_v3 import LivenessDetectorV3

router = APIRouter()

# ========== SESSÕES ATIVAS ==========
# Em produção, usar Redis ou DB. Para hackathon, memória é OK.
active_sessions = {}


class LivenessSession:
    """Mantém estado de uma sessão de liveness"""
    def __init__(self, transaction_id, risk_level="medium"):
        self.session_id = str(uuid.uuid4())
        self.transaction_id = transaction_id
        self.detector = LivenessDetectorV3()
        self.created_at = datetime.utcnow()
        
        # Inicia sessão web no detector
        session_info = self.detector.start_web_session(risk_level)
        
        self.total_challenges = session_info["total_challenges"]
        self.challenges_list = session_info["challenges"]
        
        self.completed = False
        self.success = False
        

class StartLivenessRequest(BaseModel):
    transaction_id: str
    risk_level: str = "medium"


class ProcessFrameRequest(BaseModel):
    frame_base64: str  # Frame codificado em Base64


class LivenessResponse(BaseModel):
    session_id: str
    current_challenge: dict
    progress: float  # 0-100
    total_challenges: int
    completed_challenges: int = 0
    feedback: str = ""
    status: str  # "in_progress", "completed", "failed", "timeout"


@router.post("/start", response_model=LivenessResponse)
async def start_liveness(
    request: StartLivenessRequest,
    db=Depends(get_database)
):
    """
    Inicia uma nova sessão de liveness verification
    
    Returns:
        Session ID e primeiro desafio
    """
    # Validar transação
    transaction = await db.transactions.find_one({
        "_id": ObjectId(request.transaction_id) if ObjectId.is_valid(request.transaction_id) else request.transaction_id
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not transaction.get("liveness_required"):
        raise HTTPException(status_code=400, detail="Liveness not required for this transaction")
    
    # Criar nova sessão
    session = LivenessSession(request.transaction_id, request.risk_level)
    active_sessions[session.session_id] = session
    
    # Limpar sessões antigas (> 5 minutos)
    now = datetime.utcnow()
    for sid, sess in list(active_sessions.items()):
        if (now - sess.created_at).total_seconds() > 300:
            del active_sessions[sid]
    
    # Retornar primeiro desafio
    session_info = session.detector._get_current_challenge_info()
    
    return LivenessResponse(
        session_id=session.session_id,
        current_challenge=session_info,
        progress=0.0,
        total_challenges=session.total_challenges,
        completed_challenges=0,
        feedback="Sessão iniciada. Posicione seu rosto centralizado na câmara.",
        status="in_progress"
    )


@router.post("/frame/{session_id}", response_model=LivenessResponse)
async def process_frame(
    session_id: str,
    request: ProcessFrameRequest
):
    """
    Processa um frame da webcam e retorna feedback
    
    Args:
        session_id: ID da sessão ativa
        request: Frame em Base64
        
    Returns:
        Feedback, progresso, próximo desafio
    """
    # Validar sessão
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    session = active_sessions[session_id]
    
    if session.completed:
        return LivenessResponse(
            session_id=session_id,
            current_challenge={"name": "Concluído", "instruction": "Verificação completa", "type": "done"},
            progress=100.0,
            total_challenges=len(session.detector.challenge_sequence),
            completed_challenges=len(session.challenges_completed),
            feedback="Verificação concluída com sucesso!" if session.success else "Verificação falhou.",
            status="completed" if session.success else "failed"
        )
    
    # Decodificar frame
    try:
        # Remove prefixo data:image/...;base64, se existir
        if "," in request.frame_base64:
            request.frame_base64 = request.frame_base64.split(",")[1]
        
        img_data = base64.b64decode(request.frame_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise ValueError("Failed to decode frame")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid frame data: {str(e)}")
    
    # Processar frame com detector V3 REAL
    result = session.detector.process_web_frame(frame)
    
    # Verificar se completou ou falhou
    if result["status"] == "completed":
        session.completed = True
        session.success = True
        return LivenessResponse(
            session_id=session_id,
            current_challenge=result["current_challenge"],
            progress=100.0,
            total_challenges=session.total_challenges,
            completed_challenges=result.get("completed_challenges", session.total_challenges),
            feedback=result["feedback"],
            status="completed"
        )
    
    elif result["status"] == "failed":
        session.completed = True
        session.success = False
        return LivenessResponse(
            session_id=session_id,
            current_challenge=result.get("current_challenge", {"name": "Falhou", "type": "failed"}),
            progress=result.get("progress", 0),
            total_challenges=session.total_challenges,
            completed_challenges=result.get("completed_challenges", 0),
            feedback=result["feedback"],
            status="failed"
        )
    
    # In progress - retornar feedback
    return LivenessResponse(
        session_id=session_id,
        current_challenge=result["current_challenge"],
        progress=result["progress"],
        total_challenges=session.total_challenges,
        completed_challenges=result.get("completed_challenges", 0),
        feedback=result["feedback"],
        status="in_progress"
    )


@router.post("/complete/{session_id}")
async def complete_liveness(
    session_id: str,
    db=Depends(get_database)
):
    """
    Finaliza verificação e atualiza transação
    
    Returns:
        Resultado final da verificação
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    if not session.completed:
        raise HTTPException(status_code=400, detail="Session not completed yet")
    
    # Atualizar transação no DB
    transaction_id = session.transaction_id
    update_result = await db.transactions.update_one(
        {"_id": ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id},
        {
            "$set": {
                "liveness_performed": True,
                "liveness_result": {
                    "success": session.success,
                    "challenges_completed": session.total_challenges if session.success else 0,
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
    
    # Buscar transação atualizada
    transaction = await db.transactions.find_one({
        "_id": ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    })
    
    # Limpar sessão
    del active_sessions[session_id]
    
    # Serializar ObjectId
    if transaction and "_id" in transaction:
        transaction["_id"] = str(transaction["_id"])
    
    return {
        "success": session.success,
        "message": "Verificação aprovada!" if session.success else "Verificação falhou.",
        "transaction": transaction
    }


@router.delete("/cancel/{session_id}")
async def cancel_liveness(session_id: str):
    """Cancela uma sessão de liveness"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": "Session cancelled"}
    return {"message": "Session not found"}
