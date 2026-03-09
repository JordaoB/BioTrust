"""
BioTrust Structured Logging System
Uses loguru for structured, colored, and rotated logs
"""
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

# Remove default handler
logger.remove()

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Console handler - colored, human-readable
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# General application logs - rotated daily
logger.add(
    LOGS_DIR / "biotrust_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # Rotate at midnight
    retention="30 days",  # Keep logs for 30 days
    compression="zip",  # Compress old logs
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# Error logs - separate file
logger.add(
    LOGS_DIR / "errors_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="90 days",  # Keep error logs longer
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR"
)

# Transaction audit trail - JSON format for easy parsing
logger.add(
    LOGS_DIR / "audit_transactions_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="365 days",  # Keep audit logs for 1 year
    compression="zip",
    format="{message}",
    level="INFO",
    filter=lambda record: "audit_trail" in record["extra"]
)

# Liveness detection logs - separate file for analysis
logger.add(
    LOGS_DIR / "liveness_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="60 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    filter=lambda record: "liveness" in record["extra"]
)

# Security logs - authentication attempts, suspicious activities
logger.add(
    LOGS_DIR / "security_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="180 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    filter=lambda record: "security" in record["extra"]
)


def log_transaction_audit(
    transaction_id: str,
    user_id: str,
    amount: float,
    merchant_id: str,
    status: str,
    risk_score: float = None,
    risk_level: str = None,
    liveness_verified: bool = False,
    ip_address: str = None,
    user_agent: str = None,
    reason: str = None
):
    """
    Log transaction audit trail in structured JSON format
    """
    audit_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": "transaction",
        "transaction_id": transaction_id,
        "user_id": user_id,
        "amount": amount,
        "merchant_id": merchant_id,
        "status": status,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "liveness_verified": liveness_verified,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "reason": reason
    }
    
    logger.bind(audit_trail=True).info(
        f"TRANSACTION | {transaction_id} | {user_id} | €{amount:.2f} | {status} | {risk_level or 'N/A'}"
    )


def log_liveness_attempt(
    user_id: str,
    transaction_id: str,
    success: bool,
    confidence: float = None,
    reason: str = None,
    detection_time: float = None
):
    """
    Log liveness detection attempts
    """
    status = "✅ PASSED" if success else "❌ FAILED"
    logger.bind(liveness=True).info(
        f"LIVENESS {status} | User: {user_id} | TX: {transaction_id} | "
        f"Confidence: {confidence:.2f}% | Time: {detection_time:.2f}s | Reason: {reason or 'N/A'}"
    )


def log_security_event(
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    user_agent: str = None,
    details: str = None,
    severity: str = "INFO"
):
    """
    Log security-related events
    """
    logger.bind(security=True).log(
        severity,
        f"SECURITY | {event_type} | User: {user_id or 'Anonymous'} | "
        f"IP: {ip_address or 'N/A'} | Details: {details or 'N/A'}"
    )


# Export logger and helper functions
__all__ = [
    "logger",
    "log_transaction_audit",
    "log_liveness_attempt",
    "log_security_event"
]
