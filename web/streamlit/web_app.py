"""
BioTrust Web Interface
Streamlit frontend for BioTrust payment system with risk analysis and liveness detection.
"""

import streamlit as st
import requests
import json
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="BioTrust - Biometric Payment System",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1E88E5;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        color: #721c24;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.5rem;
        padding: 1rem;
        color: #856404;
    }
    </style>
""", unsafe_allow_html=True)

# API Base URL
API_BASE_URL = \"http://localhost:8000\"

# Initialize session state
if 'transaction_history' not in st.session_state:
    st.session_state.transaction_history = []

# =====================================================================
# Helper Functions
# =====================================================================

def check_api_health():
    """Check if API server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def analyze_risk_api(amount, user_id, merchant_id, location, device_id):
    """Call risk analysis API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/analyze-risk",
            json={
                "amount": amount,
                "user_id": user_id,
                "merchant_id": merchant_id,
                "location": location,
                "device_id": device_id
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error {response.status_code}: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return None, f"API connection failed: {str(e)}"

def verify_liveness_api(mode="active", enable_passive=True):
    """Call liveness verification API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/verify-liveness",
            params={"mode": mode, "enable_passive": enable_passive},
            timeout=120
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error {response.status_code}: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return None, f"API connection failed: {str(e)}"

def process_payment_api(amount, user_id, merchant_id, description, location, device_id, liveness_mode):
    """Call payment processing API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/process-payment",
            json={
                "amount": amount,
                "user_id": user_id,
                "merchant_id": merchant_id,
                "description": description,
                "location": location,
                "device_id": device_id,
                "liveness_mode": liveness_mode
            },
            timeout=120
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error {response.status_code}: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return None, f"API connection failed: {str(e)}"

def get_risk_color(risk_level):
    """Get color for risk level"""
    colors = {
        "LOW": "green",
        "MEDIUM": "orange",
        "HIGH": "red"
    }
    return colors.get(risk_level, "gray")

def get_status_color(status):
    """Get color for payment status"""
    colors = {
        "APPROVED": "green",
        "REJECTED": "red",
        "PENDING": "orange"
    }
    return colors.get(status, "gray")

# =====================================================================
# Main Application
# =====================================================================

# Header
st.markdown('<div class="main-header">🔐 BioTrust</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Biometric Trust Payment System | TecStorm \'26</div>', unsafe_allow_html=True)

# Check API status
api_status = check_api_health()

if not api_status:
    st.error("⚠️ **API Server is not running!**\n\nPlease start the API server first:\n```bash\npython api_server.py\n```")
    st.stop()

# Sidebar
with st.sidebar:
    st.header("🎯 Navigation")
    page = st.radio(
        "Select Page:",
        ["🏠 Home", "📊 Risk Analysis", "👤 Liveness Check", "💳 Payment Processing", "📜 Transaction History"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    st.header("⚙️ System Status")
    st.success("✅ API Server: Online")
    st.info("🔧 Version: 1.0.0")
    
    st.divider()
    
    st.header("ℹ️ About")
    st.markdown("""
    **BioTrust** combines:
    - 🧠 AI Risk Analysis
    - 👁️ Active Liveness Detection
    - 🫀 Passive Liveness (rPPG)
    - 🔐 Secure Payment Processing
    
    **Team:**
    - João Evaristo
    - Jordão Wiezel
    - Anna Demenchuk
    - Joana Du
    """)

# =====================================================================
# Home Page
# =====================================================================

if page == "🏠 Home":
    st.header("Welcome to BioTrust")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📊 Risk Engine")
        st.markdown("""
        Intelligent risk analysis based on:
        - Transaction amount
        - User behavior patterns
        - Device and location context
        - Merchant risk profile
        """)
    
    with col2:
        st.markdown("### 👁️ Active Liveness")
        st.markdown("""
        Challenge-response verification:
        - Eye blink detection
        - Head movement tracking
        - Real-time face mesh analysis
        - Anti-spoofing protection
        """)
    
    with col3:
        st.markdown("### 🫀 Passive Liveness")
        st.markdown("""
        Remote Photoplethysmography (rPPG):
        - Heart rate detection
        - No user interaction needed
        - Works during active test
        - Advanced anti-spoofing
        """)
    
    st.divider()
    
    st.header("🎯 How It Works")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("#### 1️⃣ Risk Analysis")
        st.info("System analyzes transaction risk factors")
    
    with col2:
        st.markdown("#### 2️⃣ Liveness Check")
        st.warning("If risk is elevated, biometric verification required")
    
    with col3:
        st.markdown("#### 3️⃣ Decision")
        st.success("Payment approved if all checks pass")
    
    with col4:
        st.markdown("#### 4️⃣ Logging")
        st.info("All transactions logged for audit")
    
    st.divider()
    
    st.header("📈 System Capabilities")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Risk Levels", "3", delta="LOW/MEDIUM/HIGH")
    
    with col2:
        st.metric("Liveness Modes", "3", delta="Active/Passive/Multi")
    
    with col3:
        st.metric("Detection Accuracy", "95%+", delta="High confidence")
    
    with col4:
        st.metric("Response Time", "< 30s", delta="Fast processing")

# =====================================================================
# Risk Analysis Page
# =====================================================================

elif page == "📊 Risk Analysis":
    st.header("📊 Transaction Risk Analysis")
    
    st.markdown("Analyze the risk level of a transaction before processing.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        amount = st.number_input("Amount (MZN)", min_value=0.01, value=2500.00, step=100.00)
        user_id = st.text_input("User ID", value="user_123")
        merchant_id = st.text_input("Merchant ID", value="merch_456")
    
    with col2:
        location = st.text_input("Location", value="Maputo, Mozambique")
        device_id = st.text_input("Device ID", value="device_789")
    
    if st.button("🔍 Analyze Risk", type="primary", use_container_width=True):
        with st.spinner("Analyzing transaction risk..."):
            result, error = analyze_risk_api(amount, user_id, merchant_id, location, device_id)
        
        if error:
            st.error(f"❌ {error}")
        else:
            st.success("✅ Risk analysis completed!")
            
            # Display results
            st.divider()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                risk_color = get_risk_color(result['risk_level'])
                st.markdown(f"### Risk Score")
                st.markdown(f"## :{risk_color}[{result['risk_score']:.1f}/100]")
            
            with col2:
                st.markdown(f"### Risk Level")
                st.markdown(f"## :{risk_color}[{result['risk_level']}]")
            
            with col3:
                st.markdown(f"### Liveness Required")
                if result['requires_liveness']:
                    st.markdown(f"## :red[YES]")
                else:
                    st.markdown(f"## :green[NO]")
            
            st.divider()
            
            # Risk factors
            st.markdown("### 📋 Risk Factors Breakdown")
            factors = result['factors']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Amount Factor", f"{factors['amount_factor']:.1f}")
                st.metric("User History Factor", f"{factors['user_history_factor']:.1f}")
            
            with col2:
                st.metric("Location Factor", f"{factors['location_factor']:.1f}")
                st.metric("Device Factor", f"{factors['device_factor']:.1f}")
            
            # Recommendation
            st.divider()
            st.info(f"**💡 Recommendation:** {result['recommendation']}")

# =====================================================================
# Liveness Check Page
# =====================================================================

elif page == "👤 Liveness Check":
    st.header("👤 Liveness Verification")
    
    st.markdown("Verify that a real person is present using biometric detection.")
    
    st.warning("⚠️ **Note:** This requires camera access on the server. Make sure your webcam is connected and accessible.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        mode = st.selectbox(
            "Verification Mode",
            ["active", "passive"],
            format_func=lambda x: "🎯 Active (Blink + Movement)" if x == "active" else "🫀 Passive (Heart Rate Only)"
        )
    
    with col2:
        enable_passive = st.checkbox("Enable rPPG (Heart Rate)", value=True, disabled=mode=="passive")
    
    st.divider()
    
    # Mode explanation
    if mode == "active":
        st.info("""
        **Active Liveness Detection:**
        - Detects eye blinks (minimum 3)
        - Tracks head movements (left and right)
        - Analyzes face mesh symmetry
        - Optional heart rate detection via rPPG
        """)
    else:
        st.info("""
        **Passive Liveness Detection:**
        - Remote Photoplethysmography (rPPG)
        - Detects heart rate from facial color changes
        - No user interaction required
        - Captures 15 seconds of video
        """)
    
    if st.button("📸 Start Verification", type="primary", use_container_width=True):
        with st.spinner("🎥 Performing liveness verification... Please look at the camera and follow instructions."):
            result, error = verify_liveness_api(mode, enable_passive if mode == "active" else False)
        
        if error:
            st.error(f"❌ {error}")
        else:
            if result['verified']:
                st.success("✅ Liveness verification successful!")
                
                st.divider()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if result['active_liveness']:
                        st.metric("Active Liveness", "✅ PASS", delta="Verified")
                    else:
                        st.metric("Active Liveness", "N/A", delta="Not tested")
                
                with col2:
                    if result['passive_liveness']:
                        st.metric("Passive Liveness", "✅ PASS", delta="Verified")
                    else:
                        st.metric("Passive Liveness", "❌ FAIL" if mode == "passive" or enable_passive else "N/A", delta="Not verified" if mode == "passive" or enable_passive else "Not tested")
                
                with col3:
                    if result['heart_rate']:
                        st.metric("Heart Rate", f"{result['heart_rate']:.1f} BPM", delta=f"{result['heart_rate_confidence']*100:.1f}% confidence")
                    else:
                        st.metric("Heart Rate", "N/A", delta="Not detected")
                
                st.divider()
                
                # Additional details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🔍 Detection Details:**")
                    st.write(f"- Blinks: {result['blink_count']}")
                    st.write(f"- Head Movements: {', '.join(result['head_movements']) if result['head_movements'] else 'None'}")
                
                with col2:
                    st.markdown("**💬 Status Message:**")
                    st.info(result['message'])
            
            else:
                st.error("❌ Liveness verification failed!")
                st.warning(result['message'])

# =====================================================================
# Payment Processing Page
# =====================================================================

elif page == "💳 Payment Processing":
    st.header("💳 Complete Payment Processing")
    
    st.markdown("Process a payment with integrated risk analysis and liveness verification.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Transaction Details")
        amount = st.number_input("Amount (MZN)", min_value=0.01, value=2500.00, step=100.00)
        description = st.text_input("Description", value="Phone purchase")
        user_id = st.text_input("User ID", value="user_123")
        merchant_id = st.text_input("Merchant ID", value="merch_456")
    
    with col2:
        st.subheader("Additional Information")
        location = st.text_input("Location", value="Maputo, Mozambique")
        device_id = st.text_input("Device ID", value="device_789")
        liveness_mode = st.selectbox(
            "Liveness Mode",
            ["active", "passive", "multi"],
            format_func=lambda x: {
                "active": "🎯 Active (Blink + Movement + rPPG)",
                "passive": "🫀 Passive (Heart Rate Only)",
                "multi": "🔄 Multi-Factor (Active + Passive Sequential)"
            }[x]
        )
    
    st.divider()
    
    if st.button("💰 Process Payment", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Risk Analysis
        status_text.text("🔍 Step 1/3: Analyzing risk...")
        progress_bar.progress(33)
        time.sleep(0.5)
        
        # Step 2 & 3: Process payment (includes liveness if needed)
        status_text.text("👤 Step 2/3: Verifying liveness (if required)...")
        progress_bar.progress(66)
        
        result, error = process_payment_api(
            amount, user_id, merchant_id, description, location, device_id, liveness_mode
        )
        
        status_text.text("✅ Step 3/3: Finalizing payment...")
        progress_bar.progress(100)
        time.sleep(0.5)
        
        progress_bar.empty()
        status_text.empty()
        
        if error:
            st.error(f"❌ {error}")
        else:
            # Add to transaction history
            st.session_state.transaction_history.insert(0, result)
            
            st.divider()
            
            # Display result based on status
            if result['status'] == "APPROVED":
                st.success(f"✅ **PAYMENT APPROVED!**")
                st.balloons()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Status", "✅ APPROVED")
                
                with col2:
                    st.metric("Amount", f"{result['amount']:.2f} MZN")
                
                with col3:
                    risk_color = get_risk_color(result['risk_level'])
                    st.metric("Risk Level", result['risk_level'])
                
                with col4:
                    if result['heart_rate']:
                        st.metric("Heart Rate", f"{result['heart_rate']:.1f} BPM")
                    else:
                        st.metric("Liveness", "✅ Verified")
                
                st.divider()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📝 Transaction Details:**")
                    st.write(f"- Transaction ID: `{result['transaction_id']}`")
                    st.write(f"- Risk Score: {result['risk_score']:.1f}/100")
                    st.write(f"- Liveness: {'✅ Verified' if result['liveness_verified'] else '❌ Failed'}")
                
                with col2:
                    st.markdown("**💬 Status Message:**")
                    st.success(result['message'])
            
            elif result['status'] == "REJECTED":
                st.error(f"❌ **PAYMENT REJECTED!**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Status", "❌ REJECTED")
                
                with col2:
                    st.metric("Amount", f"{result['amount']:.2f} MZN")
                
                with col3:
                    risk_color = get_risk_color(result['risk_level'])
                    st.metric("Risk Level", result['risk_level'])
                
                st.divider()
                
                st.markdown("**⚠️ Rejection Reason:**")
                st.error(result['message'])
                
                st.markdown("**📊 Risk Analysis:**")
                st.write(f"- Risk Score: {result['risk_score']:.1f}/100")
                st.write(f"- Liveness Verified: {'✅ Yes' if result['liveness_verified'] else '❌ No'}")
            
            else:  # PENDING
                st.warning(f"⏳ **PAYMENT PENDING**")
                st.info(result['message'])

# =====================================================================
# Transaction History Page
# =====================================================================

elif page == "📜 Transaction History":
    st.header("📜 Transaction History")
    
    if not st.session_state.transaction_history:
        st.info("No transactions yet. Process a payment to see history.")
    else:
        st.markdown(f"**Total Transactions:** {len(st.session_state.transaction_history)}")
        
        # Statistics
        approved = sum(1 for t in st.session_state.transaction_history if t['status'] == 'APPROVED')
        rejected = sum(1 for t in st.session_state.transaction_history if t['status'] == 'REJECTED')
        total_amount = sum(t['amount'] for t in st.session_state.transaction_history if t['status'] == 'APPROVED')
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Approved", approved, delta=f"{approved/(approved+rejected)*100:.1f}%" if (approved+rejected) > 0 else "0%")
        
        with col2:
            st.metric("Rejected", rejected, delta=f"{rejected/(approved+rejected)*100:.1f}%" if (approved+rejected) > 0 else "0%")
        
        with col3:
            st.metric("Total Amount", f"{total_amount:.2f} MZN")
        
        with col4:
            avg_risk = sum(t['risk_score'] for t in st.session_state.transaction_history) / len(st.session_state.transaction_history)
            st.metric("Avg Risk Score", f"{avg_risk:.1f}")
        
        st.divider()
        
        # Transaction list
        for i, transaction in enumerate(st.session_state.transaction_history):
            with st.expander(f"Transaction #{len(st.session_state.transaction_history)-i} - {transaction['status']} - {transaction['amount']:.2f} MZN"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Status:** {transaction['status']}")
                    st.write(f"**Amount:** {transaction['amount']:.2f} MZN")
                    st.write(f"**Risk Score:** {transaction['risk_score']:.1f}")
                    st.write(f"**Risk Level:** {transaction['risk_level']}")
                
                with col2:
                    st.write(f"**Liveness:** {'✅ Verified' if transaction['liveness_verified'] else '❌ Failed'}")
                    if transaction['heart_rate']:
                        st.write(f"**Heart Rate:** {transaction['heart_rate']:.1f} BPM")
                    if transaction.get('transaction_id'):
                        st.write(f"**Transaction ID:** `{transaction['transaction_id']}`")
                    st.write(f"**Timestamp:** {transaction['timestamp']}")
                
                st.info(f"**Message:** {transaction['message']}")
        
        st.divider()
        
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state.transaction_history = []
            st.rerun()

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p><strong>BioTrust</strong> - Biometric Trust Payment System | TecStorm '26</p>
    <p>Team: João Evaristo, Jordão Wiezel, Anna Demenchuk, Joana Du</p>
    <p>🔐 Secure • 🚀 Fast • 🎯 Accurate</p>
</div>
""", unsafe_allow_html=True)
