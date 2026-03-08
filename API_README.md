# BioTrust Backend API

FastAPI-based backend for biometric payment authentication with privacy-by-design architecture.

## 🚀 Quick Start

### 1. Start MongoDB
MongoDB should already be running as a Windows service on `localhost:27017`.

Verify connection:
```bash
# Check if MongoDB is running
mongosh --eval "db.adminCommand('ping')"
```

### 2. Configure Environment
Copy `.env.example` to `.env` and update if needed:
```bash
copy .env.example .env
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Database
Confirm database is populated:
```bash
python -m data.seed_database
```

### 5. Start API Server
```bash
python -m backend.main
```

Server will start on `http://localhost:8000`

### 6. Test API
In a new terminal:
```bash
python test_api.py
```

Or visit docs: `http://localhost:8000/docs`

---

## 📡 API Endpoints

### Health & Status
- `GET /` - API status
- `GET /health` - Detailed health check

### Users
- `GET /api/users/{user_id}` - Get user by ID
- `GET /api/users/email/{email}` - Get user by email
- `GET /api/users/{user_id}/cards` - Get user's cards
- `GET /api/users/{user_id}/transactions` - Get transaction history
- `POST /api/users/` - Create new user

### Merchants
- `GET /api/merchants/nearby?lat={lat}&lon={lon}&radius_km={radius}` - Find nearby merchants
- `GET /api/merchants/{merchant_id}` - Get merchant details
- `GET /api/merchants/category/{category}` - Find by category
- `GET /api/merchants/city/{city}` - Find by city

### Transactions
- `POST /api/transactions/` - Create transaction with risk analysis
- `GET /api/transactions/{transaction_id}` - Get transaction details
- `GET /api/transactions/user/{user_id}` - Get user transaction history
- `PATCH /api/transactions/{transaction_id}/liveness` - Update with liveness result

### Liveness Verification
- `POST /api/liveness/verify/{transaction_id}` - Perform liveness verification
- `GET /api/liveness/status/{transaction_id}` - Get verification status
- `GET /api/liveness/requirements/{transaction_id}` - Get requirements based on risk
- `POST /api/liveness/simulate` - Simulate verification (testing)

---

## 🧪 Example Usage

### 1. Get User
```bash
curl http://localhost:8000/api/users/email/joao.silva@example.com
```

### 2. Find Nearby Merchants (Lisboa)
```bash
curl "http://localhost:8000/api/merchants/nearby?lat=38.7223&lon=-9.1393&radius_km=5"
```

### 3. Create Transaction
```bash
curl -X POST http://localhost:8000/api/transactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID_HERE",
    "card_id": "CARD_ID_HERE",
    "merchant_id": "MERCHANT_ID_HERE",
    "amount": 150.00,
    "currency": "EUR",
    "transaction_type": "purchase",
    "user_location": {
      "latitude": 38.7223,
      "longitude": -9.1393
    }
  }'
```

Response will include:
- `risk_score`: 0-100 risk assessment
- `risk_level`: LOW, MEDIUM, or HIGH
- `liveness_required`: Boolean indicating if verification needed
- `status`: PENDING (if liveness required) or APPROVED

### 4. Verify Liveness (if required)
```bash
curl -X POST http://localhost:8000/api/liveness/verify/TRANSACTION_ID
```

---

## 🧠 Risk-Based Authentication

The system performs automatic risk analysis on every transaction:

### Low Risk (0-40 points)
- ✅ Approved immediately
- No liveness verification required
- Typical: Small amounts, familiar locations, normal hours

### Medium Risk (41-70 points)
- ⏳ Requires liveness verification
- 4 random challenges
- Typical: Medium amounts, unusual time/location

### High Risk (71-100 points)
- 🔒 Requires enhanced liveness verification
- 5 random challenges + strict anti-spoofing
- Typical: Large amounts, far from home, unusual patterns

### Risk Factors
- Transaction amount vs user's average
- Distance from home location
- Distance from merchant (if applicable)
- Account age and history
- Failed transactions in last week
- Unusual hours (before 6am or after 10pm)
- Unusual location (>50km from home)

---

## 🔒 Privacy-by-Design Architecture

### What We Store
✅ **Verification Metadata ONLY**:
- Challenges completed count
- Heart rate (rPPG-based, no contact)
- Confidence scores
- Anti-spoofing detection results
- Verification timestamp

### What We DON'T Store
❌ **No Biometric Data**:
- Video frames
- Face images
- Face encodings/embeddings
- Facial landmarks
- Raw rPPG signals
- Any media files

### How It Works
1. User's webcam streams to browser (local)
2. Frames processed in real-time by liveness detector
3. Only pass/fail + metadata sent to server
4. All frames discarded immediately after processing
5. MongoDB stores only verification results

**Result**: User privacy protected, no permanent biometric storage.

---

## 🗂️ Database Schema

### Users Collection
```javascript
{
  _id: ObjectId,
  email: String (unique),
  hashed_password: String (SHA256),
  full_name: String,
  phone: String,
  home_location: { latitude, longitude, city },
  account_age_days: Number,
  average_transaction: Number,
  max_transaction: Number,
  transactions_today: Number,
  failed_transactions_last_week: Number,
  card_ids: [String],
  liveness_verifications_count: Number
}
```

### Cards Collection
```javascript
{
  _id: ObjectId,
  user_id: String,
  encrypted_card_number: String (Fernet),
  last_four: String,
  hashed_cvv: String (SHA256),
  card_type: "visa" | "mastercard" | "amex",
  expiry_month: Number,
  expiry_year: Number,
  is_default: Boolean,
  is_active: Boolean
}
```

### Merchants Collection
```javascript
{
  _id: ObjectId,
  name: String,
  category: "restaurant" | "cafe" | "pharmacy" | ...,
  location: {
    type: "Point",  // GeoJSON
    coordinates: [longitude, latitude],
    address: String,
    city: String,
    postal_code: String
  },
  phone: String,
  opening_time: String,
  closing_time: String,
  is_verified: Boolean,
  total_transactions: Number
}
```

### Transactions Collection
```javascript
{
  _id: ObjectId,
  user_id: String,
  card_id: String,
  merchant_id: String,
  merchant_info: { name, category, location, city },
  amount: Number,
  currency: String,
  transaction_type: "purchase" | "withdrawal" | "transfer",
  user_location: { latitude, longitude },
  distance_from_home_km: Number,
  distance_from_merchant_km: Number,
  risk_score: Number (0-100),
  risk_level: "LOW" | "MEDIUM" | "HIGH",
  liveness_required: Boolean,
  liveness_performed: Boolean,
  liveness_result: {
    success: Boolean,
    challenges_completed: Number,
    heart_rate: Number,
    heart_rate_confidence: Number,
    anti_spoofing: {
      early_detection_passed: Boolean,
      video_detected: Boolean,
      printed_photo_detected: Boolean,
      mask_detected: Boolean,
      final_confidence: Number
    },
    timestamp: ISODate
  },
  status: "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED",
  created_at: ISODate,
  updated_at: ISODate
}
```

---

## 🛠️ Development

### Check Logs
Backend logs are output to console by default.

### MongoDB Admin
Use MongoDB Compass to view data:
- Connection: `mongodb://localhost:27017`
- Database: `biotrust`

### Test Data
5 users available:
- `joao.silva@example.com` (Lisboa)
- `maria.santos@example.com` (Porto)
- `ana.costa@example.com` (Braga)
- `pedro.oliveira@example.com`
- `sofia.rodrigues@example.com`

All passwords: `password123`

12 merchants across Lisboa, Porto, Braga, and Almada.

---

## 🎯 Next Steps

1. **Frontend Development**: Create interactive map-based shopping interface
2. **Liveness Integration**: Connect frontend webcam to liveness API
3. **Real-time Updates**: Add WebSocket for live transaction status
4. **Payment Integration**: Add actual payment processing (Stripe/PayPal)
5. **Analytics Dashboard**: Visualize transaction patterns and risk analysis

---

## 📝 License

See LICENSE file.

## 🏆 TecStorm '26 Hackathon

**Category**: Payments Without Limits  
**Team**: João Evaristo, Jordão Wiezel, Anna Demenchuk, Joana Du
