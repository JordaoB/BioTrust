"""
BioTrust - Anomaly Detection System
===================================
Machine Learning system to detect anomalous transaction patterns

Features:
- Isolation Forest algorithm for outlier detection
- Feature engineering from transaction data
- Automatic model training and updating
- Real-time anomaly scoring (0-100)
- Pattern learning from historical data

Author: BioTrust Team for TecStorm '26
"""

import numpy as np
import joblib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import json

# Optional logging
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from backend.utils.logger import logger
    LOGGING_ENABLED = True
except ImportError:
    LOGGING_ENABLED = False


class AnomalyDetector:
    """
    ML-based anomaly detector for transaction patterns
    
    Uses Isolation Forest algorithm to identify unusual behavior:
    - Amount anomalies (unusual transaction values)
    - Time anomalies (unusual transaction times)
    - Location anomalies (unusual distances)
    - Frequency anomalies (too many transactions)
    - Velocity anomalies (rapid succession of transactions)
    """
    
    def __init__(self, model_path: str = "models/anomaly_detector.pkl"):
        """
        Initialize anomaly detector
        
        Args:
            model_path: Path to saved model file
        """
        self.model_path = Path(__file__).parent.parent.parent / model_path
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ML model and scaler
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        
        # Feature statistics (for normalization and thresholds)
        self.feature_stats = {
            "mean_amount": 0.0,
            "std_amount": 1.0,
            "mean_distance": 0.0,
            "std_distance": 1.0,
            "max_transactions_per_day": 10,
            "typical_amount_range": (0, 1000),
            "last_updated": None
        }
        
        # Load existing model if available
        self.load_model()
        
        if LOGGING_ENABLED:
            logger.info("🤖 Anomaly Detector initialized")
    
    
    def extract_features(self, transaction_data: Dict, user_history: Dict = None) -> np.ndarray:
        """
        Extract features from transaction for anomaly detection
        
        Features:
        1. Amount (normalized)
        2. Hour of day (0-23)
        3. Day of week (0-6)
        4. Distance from home (km)
        5. Transactions in last hour (velocity)
        6. Transactions today (frequency)
        7. Amount deviation from user average
        8. Time since last transaction (minutes)
        9. Is weekend (binary)
        10. Is night time (21h-6h) (binary)
        
        Args:
            transaction_data: Dictionary with transaction details
            user_history: Dictionary with user's transaction history
        
        Returns:
            Feature vector as numpy array
        """
        features = []
        
        # Feature 1: Transaction amount (normalized)
        amount = transaction_data.get("amount", 0.0)
        features.append(amount)
        
        # Feature 2-3: Time features
        now = datetime.utcnow()
        features.append(now.hour)  # Hour of day (0-23)
        features.append(now.weekday())  # Day of week (0=Monday, 6=Sunday)
        
        # Feature 4: Distance from home
        distance = transaction_data.get("distance_from_home_km", 0.0)
        features.append(distance)
        
        # Features 5-6: Transaction frequency (if history available)
        if user_history:
            transactions_last_hour = user_history.get("transactions_last_hour", 0)
            transactions_today = user_history.get("transactions_today", 0)
            features.append(transactions_last_hour)
            features.append(transactions_today)
            
            # Feature 7: Deviation from average amount
            avg_transaction = user_history.get("average_transaction", amount)
            if avg_transaction > 0:
                amount_ratio = amount / avg_transaction
            else:
                amount_ratio = 1.0
            features.append(amount_ratio)
            
            # Feature 8: Time since last transaction
            last_tx_time = user_history.get("last_transaction_time")
            if last_tx_time:
                time_diff = (now - last_tx_time).total_seconds() / 60  # minutes
                features.append(min(time_diff, 1440))  # cap at 24 hours
            else:
                features.append(1440)  # 24 hours if no history
        else:
            # Default values when no history
            features.extend([0, 0, 1.0, 1440])
        
        # Feature 9: Is weekend
        is_weekend = 1 if now.weekday() >= 5 else 0
        features.append(is_weekend)
        
        # Feature 10: Is night time (21h-6h)
        is_night = 1 if (now.hour >= 21 or now.hour <= 6) else 0
        features.append(is_night)
        
        return np.array(features).reshape(1, -1)
    
    
    def train(self, transactions: List[Dict], contamination: float = 0.05):
        """
        Train the anomaly detection model on historical transactions
        
        Args:
            transactions: List of transaction dictionaries
            contamination: Expected proportion of anomalies (default 5%)
        """
        if len(transactions) < 10:
            if LOGGING_ENABLED:
                logger.warning("⚠️ Insufficient data for training (need at least 10 transactions)")
            return False
        
        # Extract features from all transactions
        feature_matrix = []
        for tx in transactions:
            # Build user history context
            user_history = {
                "average_transaction": tx.get("average_transaction", 0),
                "transactions_today": tx.get("transactions_today", 0),
                "transactions_last_hour": tx.get("transactions_last_hour", 0),
                "last_transaction_time": tx.get("created_at")
            }
            
            features = self.extract_features(tx, user_history)
            feature_matrix.append(features[0])
        
        X = np.array(feature_matrix)
        
        # Train scaler
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1
        )
        self.model.fit(X_scaled)
        
        # Update feature statistics
        self.feature_stats = {
            "mean_amount": float(X[:, 0].mean()),
            "std_amount": float(X[:, 0].std()),
            "mean_distance": float(X[:, 3].mean()),
            "std_distance": float(X[:, 3].std()),
            "max_transactions_per_day": int(X[:, 5].max()) if X.shape[0] > 5 else 10,
            "typical_amount_range": (float(X[:, 0].min()), float(X[:, 0].max())),
            "last_updated": datetime.utcnow().isoformat(),
            "training_samples": len(transactions)
        }
        
        # Save model
        self.save_model()
        
        if LOGGING_ENABLED:
            logger.success(
                f"✅ Anomaly detector trained | Samples: {len(transactions)} | "
                f"Contamination: {contamination*100:.1f}% | "
                f"Avg Amount: €{self.feature_stats['mean_amount']:.2f}"
            )
        
        return True
    
    
    def predict(self, transaction_data: Dict, user_history: Dict = None) -> Tuple[bool, float, str]:
        """
        Predict if transaction is anomalous
        
        Args:
            transaction_data: Transaction details
            user_history: User's transaction history
        
        Returns:
            Tuple of (is_anomaly, anomaly_score, reason)
            - is_anomaly: True if transaction is anomalous
            - anomaly_score: 0-100 (higher = more anomalous)
            - reason: Human-readable explanation
        """
        if self.model is None or self.scaler is None:
            # No model trained yet - return neutral
            return False, 0.0, "Model not trained yet"
        
        # Extract features
        features = self.extract_features(transaction_data, user_history)
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict anomaly score
        # Isolation Forest returns -1 for anomalies, 1 for normal
        prediction = self.model.predict(features_scaled)[0]
        
        # Get anomaly score (decision function)
        # Negative values = anomalies, positive = normal
        raw_score = self.model.decision_function(features_scaled)[0]
        
        # Convert to 0-100 scale (0 = normal, 100 = very anomalous)
        # Typical range is [-0.5, 0.5], but can vary
        anomaly_score = max(0, min(100, (0.5 - raw_score) * 100))
        
        # Determine if anomalous (score > 70 or prediction = -1)
        is_anomaly = prediction == -1 or anomaly_score > 70
        
        # Generate reason
        reason = self._generate_reason(transaction_data, user_history, features[0], anomaly_score)
        
        if LOGGING_ENABLED:
            status = "🚨 ANOMALY" if is_anomaly else "✅ NORMAL"
            logger.info(
                f"{status} | Score: {anomaly_score:.1f}/100 | "
                f"Amount: €{transaction_data.get('amount', 0):.2f} | "
                f"Distance: {transaction_data.get('distance_from_home_km', 0):.1f}km | "
                f"Reason: {reason}"
            )
        
        # Convert numpy types to Python native types for MongoDB compatibility
        return bool(is_anomaly), float(anomaly_score), reason
    
    
    def _generate_reason(self, tx_data: Dict, user_history: Dict, features: np.ndarray, score: float) -> str:
        """
        Generate human-readable reason for anomaly detection
        """
        reasons = []
        
        amount = tx_data.get("amount", 0)
        distance = tx_data.get("distance_from_home_km", 0)
        
        # Check amount
        if amount > self.feature_stats["typical_amount_range"][1] * 1.5:
            reasons.append(f"Valor muito alto (€{amount:.2f})")
        
        # Check distance
        if distance > self.feature_stats["mean_distance"] + 2 * self.feature_stats["std_distance"]:
            reasons.append(f"Distância incomum ({distance:.0f}km)")
        
        # Check frequency
        if user_history:
            tx_today = user_history.get("transactions_today", 0)
            if tx_today > self.feature_stats["max_transactions_per_day"]:
                reasons.append(f"Muitas transações hoje ({tx_today})")
            
            tx_last_hour = user_history.get("transactions_last_hour", 0)
            if tx_last_hour > 3:
                reasons.append(f"Transações rápidas ({tx_last_hour} na última hora)")
        
        # Check time
        hour = int(features[1])
        if hour >= 22 or hour <= 5:
            reasons.append(f"Horário incomum ({hour}h)")
        
        # Check weekend
        if int(features[8]) == 1:
            reasons.append("Transação de fim de semana")
        
        if reasons:
            return " | ".join(reasons)
        elif score > 70:
            return "Padrão não corresponde ao comportamento normal"
        else:
            return "Transação dentro do padrão esperado"
    
    
    def save_model(self):
        """Save trained model and statistics to disk"""
        if self.model is None or self.scaler is None:
            return
        
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_stats": self.feature_stats
        }
        
        joblib.dump(model_data, self.model_path)
        
        if LOGGING_ENABLED:
            logger.info(f"💾 Anomaly model saved to {self.model_path}")
    
    
    def load_model(self) -> bool:
        """Load trained model from disk"""
        if not self.model_path.exists():
            if LOGGING_ENABLED:
                logger.info("ℹ️ No saved model found, will train on first use")
            return False
        
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
            self.feature_stats = model_data["feature_stats"]
            
            if LOGGING_ENABLED:
                last_updated = self.feature_stats.get("last_updated", "Unknown")
                samples = self.feature_stats.get("training_samples", 0)
                logger.success(
                    f"📂 Anomaly model loaded | Trained on {samples} samples | "
                    f"Last updated: {last_updated}"
                )
            
            return True
        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(f"❌ Failed to load model: {str(e)}")
            return False
    
    
    def get_model_info(self) -> Dict:
        """Get information about the trained model"""
        if self.model is None:
            return {
                "status": "not_trained",
                "message": "Model has not been trained yet"
            }
        
        return {
            "status": "ready",
            "feature_stats": self.feature_stats,
            "model_type": "Isolation Forest",
            "features": [
                "Amount",
                "Hour of day",
                "Day of week",
                "Distance from home",
                "Transactions last hour",
                "Transactions today",
                "Amount ratio to average",
                "Time since last transaction",
                "Is weekend",
                "Is night time"
            ]
        }


# Global instance
anomaly_detector = AnomalyDetector()
