# 🤖 Machine Learning - Anomaly Detection System

## Overview

BioTrust uses **Machine Learning** to detect fraudulent transaction patterns in real-time. The system uses an **Isolation Forest** algorithm to identify anomalous transactions based on 10 engineered features.

## ✨ Features

### 1. **Unsupervised Learning**
- No manual fraud labeling required
- Learns normal patterns automatically
- Adapts to user behavior over time

### 2. **Real-Time Detection**
- Predictions in <100ms
- Integrated into transaction flow
- Automatic risk adjustment

### 3. **10 Engineered Features**

| Feature | Description | Anomaly Indicators |
|---------|-------------|-------------------|
| **Amount** | Transaction amount normalized | >1.5x typical max amount |
| **Hour of Day** | 0-23 hour | Night transactions (21h-6h) |
| **Day of Week** | 0=Monday, 6=Sunday | Weekend transactions |
| **Distance from Home** | Kilometers from home | >2σ from mean distance |
| **Transaction Velocity** | TX count in last hour | >3 transactions/hour |
| **Daily Frequency** | TX count today | >max_per_day |
| **Amount Ratio** | Amount / user average | Large deviations |
| **Time Since Last TX** | Minutes since last TX | <5 min rapid succession |
| **Is Weekend** | Binary flag | Unusual weekend activity |
| **Is Night** | Binary flag (21h-6h) | Late night transactions |

### 4. **Human-Readable Explanations**
Each anomaly includes a reason:
- "High amount: €X,XXX (typical max: €X,XXX)"
- "Large distance: XXXkm from home (typical: XX-XXkm)"
- "High transaction frequency today: X (max: X)"
- "Rapid transactions: X in last hour"
- "Unusual timing: night/weekend transaction"

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Transaction Request                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Traditional Risk Engine                    │
│  • Amount limits                                        │
│  • Location analysis                                    │
│  • Velocity checks                                      │
│  • Merchant category                                    │
│                    Risk Score: 0-100                    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│            ML Anomaly Detector                          │
│  • Extract 10 features                                  │
│  • Isolation Forest prediction                          │
│  • Anomaly Score: 0-100                                 │
│  • Human-readable reason                                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Risk Score Adjustment                      │
│  If anomaly: risk += (anomaly_score * 0.15)             │
│  Max boost: +15 points                                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                Decision Logic                           │
│  Low Risk (<40):     Auto-approve                       │
│  Medium Risk (40-70): Require liveness                  │
│  High Risk (>70):     Require liveness                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Implementation

### File Structure

```
src/core/
  └── anomaly_detector.py        # ML detector class (430 lines)

data/
  └── train_anomaly_model.py     # Training script (120 lines)

models/
  └── anomaly_detector.pkl       # Trained model (joblib pickle)

backend/routes/
  └── transactions.py            # Integration point

docs/
  └── ML_ANOMALY_DETECTION.md    # This file
```

### Core Components

#### 1. **AnomalyDetector Class**
```python
from src.core.anomaly_detector import anomaly_detector

# Predict anomaly
is_anomaly, score, reason = anomaly_detector.predict(
    transaction_data={
        "amount": 500.0,
        "distance_from_home_km": 150.0,
        "created_at": datetime.utcnow()
    },
    user_history={
        "average_transaction": 50.0,
        "transactions_today": 3,
        "transactions_last_hour": 2,
        "last_transaction_time": datetime.utcnow()
    }
)
```

**Returns:**
- `is_anomaly` (bool): True if anomaly detected
- `score` (float): Anomaly score 0-100
- `reason` (str): Human-readable explanation

#### 2. **Training**
```python
# Train model
transactions = fetch_from_database()  # List of dicts
success = anomaly_detector.train(
    transactions, 
    contamination=0.05  # Expect 5% anomalies
)
```

#### 3. **Model Persistence**
```python
# Auto-saves after training
anomaly_detector.save_model()

# Auto-loads on initialization
detector = AnomalyDetector()  # Loads from models/anomaly_detector.pkl
```

---

## 🚀 Usage

### 1. **Initial Training**

Before first use, train the model on historical transactions:

```bash
python data/train_anomaly_model.py
```

**Output:**
```
🤖 BioTrust - Anomaly Detection Model Training
======================================================================
📊 Fetching transactions from database...
✅ Fetched 94 transactions
📈 Users in database: 7

🔧 Training model...
   Algorithm: Isolation Forest
   Features: 10 (amount, time, distance, frequency, etc.)
   Samples: 94

✅ Model trained successfully!
📊 Model Statistics:
   Average Amount: €50.23
   Std Amount: €25.45
   Average Distance: 12.5km
   Max TX/Day: 8
   Amount Range: €5 - €500

💾 Model saved to: models/anomaly_detector.pkl
```

**Minimum Requirements:**
- At least 10 transactions (preferably 100+)
- Multiple users with varied patterns
- Mix of amounts, locations, and timings

### 2. **Automatic Detection in API**

Once trained, the detector runs automatically on every transaction:

```python
# In backend/routes/transactions.py
is_anomaly, anomaly_score, anomaly_reason = anomaly_detector.predict(...)

if is_anomaly:
    risk_score += anomaly_score * 0.15  # Boost risk by up to 15 points
    logger.warning(f"🚨 ANOMALY | Score: {anomaly_score} | {anomaly_reason}")
```

### 3. **Retraining Schedule**

Retrain regularly to adapt to new patterns:

```bash
# Weekly or after significant new data
python data/train_anomaly_model.py
```

**Recommended Schedule:**
- **Weekly**: For active systems (1000+ TX/week)
- **Monthly**: For moderate systems (100+ TX/week)
- **Quarterly**: For light systems (<100 TX/week)

---

## 📊 Monitoring & Logs

### Anomaly Detection Logs

All anomalies are logged with full context:

```
2026-03-09 15:30:45 | WARNING  | 🚨 ANOMALY DETECTED | 
    Score: 85.3/100 | 
    Reason: High amount: €5,000 (typical max: €500) | 
    Risk boost: +12.8
```

### Log Location

```
logs/
  └── biotrust_2026-03-09.log     # General logs with anomaly warnings
  └── audit_transactions_*.log    # Includes anomaly_score, anomaly_reason
```

### Transaction Fields

Each transaction stores anomaly data:

```json
{
  "transaction_id": "...",
  "amount": 5000.0,
  "risk_score": 65.8,
  "anomaly_detected": true,
  "anomaly_score": 85.3,
  "anomaly_reason": "High amount: €5,000 (typical max: €500)",
  "status": "pending",
  "liveness_required": true
}
```

---

## 🎯 Detection Examples

### Example 1: High Amount Anomaly

**Transaction:**
- Amount: €10,000
- User average: €50

**Detection:**
```
✅ Anomaly Detected
Score: 95/100
Reason: High amount: €10,000 (typical max: €500)
Action: Risk +14.25 → Liveness Required
```

### Example 2: Unusual Location

**Transaction:**
- Distance from home: 500km
- User typical: 5-20km

**Detection:**
```
✅ Anomaly Detected
Score: 88/100
Reason: Large distance: 500km from home (typical: 5-20km)
Action: Risk +13.2 → Liveness Required
```

### Example 3: Rapid Transactions

**Transaction:**
- 5 transactions in last hour
- User typical: 2-3 per day

**Detection:**
```
✅ Anomaly Detected
Score: 75/100
Reason: High transaction frequency: 5 in last hour
Action: Risk +11.25 → Liveness Required
```

### Example 4: Normal Transaction

**Transaction:**
- Amount: €45 (user average: €50)
- Distance: 8km (typical: 5-20km)
- Time: 14:30 (afternoon)
- Frequency: 2nd transaction today

**Detection:**
```
✅ No Anomaly
Score: 12/100
Action: No risk adjustment
```

---

## ⚙️ Configuration

### Model Parameters

In `anomaly_detector.py`:

```python
# Isolation Forest
contamination = 0.05  # Expected % of anomalies (5%)
n_estimators = 100    # Number of trees
random_state = 42     # Reproducibility
```

### Risk Adjustment

In `transactions.py`:

```python
# Adjust risk score if anomaly detected
if is_anomaly:
    risk_boost = min(15, anomaly_score * 0.15)  # Max +15 points
    risk_score = min(100, risk_score + risk_boost)
```

**Tuning:**
- Increase multiplier (0.15 → 0.20) for more aggressive detection
- Decrease multiplier (0.15 → 0.10) for less false positives
- Adjust max_boost (15) to cap risk increase

### Anomaly Threshold

```python
# In anomaly_detector.py
is_anomaly = prediction == -1 or anomaly_score > 70
```

**Tuning:**
- Lower threshold (70 → 60) for more sensitive detection
- Raise threshold (70 → 80) for higher confidence

---

## 📈 Performance

### Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Prediction Time** | <50ms | Including feature extraction |
| **Training Time** | ~2s | For 100 transactions |
| **Model Size** | ~50KB | Compressed pickle |
| **Memory Usage** | ~10MB | Loaded model |
| **Features** | 10 | Engineered from transaction data |

### Scalability

- **100 TX**: Instant training (<1s)
- **1,000 TX**: Fast training (~5s)
- **10,000 TX**: Quick training (~30s)
- **100,000 TX**: Moderate training (~5min)

---

## 🔧 Troubleshooting

### Issue: Model Not Found

**Error:**
```
ℹ️ No saved model found, will train on first use
```

**Solution:**
```bash
python data/train_anomaly_model.py
```

### Issue: Not Enough Data

**Error:**
```
⚠️ WARNING: Need at least 10 transactions for training
```

**Solution:**
1. Run seed script: `python data/seed_database.py`
2. Or perform manual transactions via API
3. Need minimum 10 transactions (preferably 50+)

### Issue: All Transactions Flagged as Anomalies

**Cause:** Model poorly trained or contamination too high

**Solution:**
1. Ensure diverse training data (multiple users, amounts, locations)
2. Reduce contamination: `contamination=0.02` (2% instead of 5%)
3. Retrain with more data

### Issue: No Anomalies Detected

**Cause:** Threshold too high or model too lenient

**Solution:**
1. Lower threshold: `anomaly_score > 60` (instead of 70)
2. Increase contamination: `contamination=0.10` (10%)
3. Adjust risk multiplier: `0.20` (instead of 0.15)

---

## 🧪 Testing

### Manual Testing

```bash
# 1. Train model
python data/train_anomaly_model.py

# 2. Start API
python backend/main.py

# 3. Test normal transaction
curl -X POST http://localhost:8000/api/transactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID",
    "amount": 50.0,
    "type": "physical",
    "user_location": {"lat": 38.7223, "lon": -9.1393, "city": "Lisboa"}
  }'

# Expected: anomaly_detected=false, anomaly_score<30

# 4. Test anomalous transaction  
curl -X POST http://localhost:8000/api/transactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID",
    "amount": 10000.0,
    "type": "physical",
    "user_location": {"lat": 40.4168, "lon": -3.7038, "city": "Madrid"}
  }'

# Expected: anomaly_detected=true, anomaly_score>70, reason="High amount..."
```

### Verify Logs

```bash
# Check anomaly warnings
grep "ANOMALY DETECTED" logs/biotrust_*.log

# Check transaction audit trail
grep "anomaly_score" logs/audit_transactions_*.log
```

---

## 🎓 Algorithm Explanation

### Isolation Forest

**Concept:** Anomalies are "few and different", therefore easier to isolate.

**How it works:**
1. Build random decision trees
2. Anomalies are isolated faster (fewer splits)
3. Average isolation depth across trees
4. Lower depth = more anomalous

**Why Isolation Forest?**
- ✅ No labeled data required (unsupervised)
- ✅ Fast training and prediction
- ✅ Effective for high-dimensional data
- ✅ Resistant to overfitting
- ✅ Handles outliers well

**Alternatives Considered:**
- One-Class SVM: Slower, less scalable
- Local Outlier Factor: Computationally expensive
- DBSCAN: Requires density tuning
- Autoencoders: Overkill for tabular data

---

## 🚀 Future Enhancements

### Phase 2 Features

- [ ] **Ensemble Methods**: Combine Isolation Forest + LSTM
- [ ] **User Clustering**: Group similar users, detect deviations
- [ ] **Time Series Analysis**: Seasonal patterns, trends
- [ ] **Graph Analysis**: Network fraud detection
- [ ] **Explainable AI**: SHAP values for feature importance
- [ ] **Online Learning**: Incremental model updates
- [ ] **A/B Testing**: Compare models before deployment

### Advanced Features

- [ ] **Federated Learning**: Train across users without data sharing
- [ ] **Adversarial Robustness**: Detect adversarial attacks
- [ ] **Multi-Modal**: Combine transaction + liveness features
- [ ] **Reinforcement Learning**: Optimize detection thresholds

---

## 📚 References

- **Isolation Forest Paper**: Liu et al. (2008) - "Isolation Forest"
- **scikit-learn**: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- **Anomaly Detection Survey**: Chandola et al. (2009) - "Anomaly Detection: A Survey"

---

## 📞 Support

For issues or questions about the ML system:
1. Check logs in `logs/biotrust_*.log`
2. Verify model exists: `models/anomaly_detector.pkl`
3. Retrain model: `python data/train_anomaly_model.py`
4. Check anomaly scores in transaction responses

---

**Last Updated:** 2026-03-09  
**Version:** 1.0  
**Status:** ✅ Production Ready
