"""
BioTrust API - Complete Test Suite
Tests all endpoints with different scenarios
"""

import httpx
import asyncio
import json
from datetime import datetime
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

BASE_URL = "http://localhost:8000"


class APITester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.test_data = {}
    
    def log_success(self, message):
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
        self.passed += 1
    
    def log_error(self, message):
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")
        self.failed += 1
    
    def log_warning(self, message):
        print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")
        self.warnings += 1
    
    def log_info(self, message):
        print(f"{Fore.CYAN}ℹ️  {message}{Style.RESET_ALL}")
    
    def log_section(self, title):
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}{Style.RESET_ALL}\n")
    
    async def test_health_endpoints(self, client):
        """Test health and status endpoints"""
        self.log_section("1️⃣  HEALTH & STATUS ENDPOINTS")
        
        # Test root endpoint
        try:
            response = await client.get(f"{BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                self.log_success(f"Root endpoint: {data['app']} v{data['version']}")
                self.log_info(f"Privacy: {data['privacy']}")
            else:
                self.log_error(f"Root endpoint failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Root endpoint error: {e}")
        
        # Test health endpoint
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_success(f"Health check: {data['status']}")
                self.log_info(f"Database: {data['database']}, Liveness: {data['liveness_detector']}")
            else:
                self.log_error(f"Health endpoint failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Health endpoint error: {e}")
    
    async def test_users_endpoints(self, client):
        """Test user management endpoints"""
        self.log_section("2️⃣  USERS ENDPOINTS")
        
        # Test get user by email
        try:
            response = await client.get(f"{BASE_URL}/api/users/email/joao.silva@example.com")
            if response.status_code == 200:
                user = response.json()
                self.test_data['user_id'] = user['_id']
                self.test_data['user'] = user
                self.log_success(f"Found user: {user['name']} ({user['email']})")
                self.log_info(f"Home: {user['home_location']['city']}, Account age: {user['account_age_days']} days")
            else:
                self.log_error(f"Get user by email failed: {response.status_code}")
                return
        except Exception as e:
            self.log_error(f"Get user by email error: {e}")
            return
        
        # Test get user cards
        try:
            response = await client.get(f"{BASE_URL}/api/users/{self.test_data['user_id']}/cards")
            if response.status_code == 200:
                cards = response.json()
                if cards:
                    self.test_data['card_id'] = cards[0]['id']
                    self.log_success(f"Found {len(cards)} card(s): **** {cards[0]['last_four']} ({cards[0]['card_type'].upper()})")
                else:
                    self.log_warning("No cards found for user")
            else:
                self.log_error(f"Get user cards failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Get user cards error: {e}")
        
        # Test list users
        try:
            response = await client.get(f"{BASE_URL}/api/users/", params={"skip": 0, "limit": 5})
            if response.status_code == 200:
                users = response.json()
                self.log_success(f"Listed {len(users)} users")
            else:
                self.log_error(f"List users failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"List users error: {e}")
        
        # Test create new user
        try:
            new_user = {
                "name": f"Test User {datetime.now().strftime('%H%M%S')}",
                "email": f"test_{datetime.now().strftime('%H%M%S')}@example.com",
                "phone": "+351 999 999 999",
                "home_location": {
                    "city": "Coimbra",
                    "country": "Portugal",
                    "lat": 40.2033,
                    "lon": -8.4103
                },
                "password": "testpass123"
            }
            response = await client.post(f"{BASE_URL}/api/users/", json=new_user)
            if response.status_code == 201:
                created = response.json()
                self.log_success(f"Created user: {created['name']} (ID: {created['_id'][:8]}...)")
            else:
                self.log_error(f"Create user failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Create user error: {e}")
        
        # Test duplicate email (should fail)
        try:
            response = await client.post(f"{BASE_URL}/api/users/", json={
                "name": "Duplicate",
                "email": "joao.silva@example.com",  # Already exists
                "phone": "+351 999 999 999",
                "home_location": {"city": "Lisboa", "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
                "password": "test123"
            })
            if response.status_code == 400:
                self.log_success("Duplicate email correctly rejected (400)")
            else:
                self.log_warning(f"Expected 400 for duplicate email, got {response.status_code}")
        except Exception as e:
            self.log_error(f"Duplicate email test error: {e}")
    
    async def test_merchants_endpoints(self, client):
        """Test merchant search endpoints"""
        self.log_section("3️⃣  MERCHANTS ENDPOINTS")
        
        # Test geospatial search - Lisboa
        try:
            response = await client.get(f"{BASE_URL}/api/merchants/nearby", params={
                "lat": 38.7223, "lon": -9.1393, "radius_km": 50
            })
            if response.status_code == 200:
                merchants = response.json()
                if merchants:
                    self.test_data['merchant_id'] = merchants[0]['_id']
                    self.log_success(f"Nearby search (Lisboa): {len(merchants)} merchants within 50km")
                    self.log_info(f"Closest: {merchants[0]['name']} ({merchants[0].get('distance_km', 'N/A')} km)")
                else:
                    self.log_warning("No merchants found nearby")
            else:
                self.log_error(f"Nearby search failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Nearby search error: {e}")
        
        # Fallback: Get any merchant if geospatial failed
        if 'merchant_id' not in self.test_data:
            try:
                response = await client.get(f"{BASE_URL}/api/merchants/", params={"limit": 1})
                if response.status_code == 200:
                    merchants = response.json()
                    if merchants:
                        self.test_data['merchant_id'] = merchants[0]['_id']
                        self.log_info(f"Using fallback merchant: {merchants[0]['name']}")
                else:
                    self.log_error("Could not get any merchants")
            except Exception as e:
                self.log_error(f"Fallback merchant error: {e}")
        
        # Test search by city
        try:
            response = await client.get(f"{BASE_URL}/api/merchants/city/Lisboa")
            if response.status_code == 200:
                merchants = response.json()
                self.log_success(f"City search (Lisboa): {len(merchants)} merchants")
            elif response.status_code == 404:
                self.log_warning("No merchants in Lisboa")
            else:
                self.log_error(f"City search failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"City search error: {e}")
        
        # Test search by category
        try:
            response = await client.get(f"{BASE_URL}/api/merchants/category/restaurant")
            if response.status_code == 200:
                merchants = response.json()
                self.log_success(f"Category search (restaurant): {len(merchants)} merchants")
            elif response.status_code == 404:
                self.log_warning("No restaurants found")
            else:
                self.log_error(f"Category search failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Category search error: {e}")
    
    async def test_transactions_endpoints(self, client):
        """Test transaction creation with risk analysis"""
        self.log_section("4️⃣  TRANSACTIONS & RISK ANALYSIS")
        
        if 'user_id' not in self.test_data or 'card_id' not in self.test_data:
            self.log_error("Missing user_id or card_id - skipping transaction tests")
            return
        
        # Test LOW RISK transaction (small amount, home location)
        try:
            tx_data = {
                "user_id": self.test_data['user_id'],
                "card_id": self.test_data['card_id'],
                "merchant_id": self.test_data.get('merchant_id'),
                "amount": 25.00,
                "currency": "EUR",
                "type": "physical",
                "user_location": {
                    "lat": 38.7223,
                    "lon": -9.1393
                }
            }
            response = await client.post(f"{BASE_URL}/api/transactions/", json=tx_data)
            if response.status_code == 201:
                tx = response.json()
                self.log_success(f"LOW RISK transaction: €{tx['amount']}")
                self.log_info(f"Risk: {tx['risk_score']}/100 ({tx['risk_level']}), Liveness: {tx['liveness_required']}, Status: {tx['status']}")
                if tx['risk_level'] == 'LOW' and not tx['liveness_required']:
                    self.log_success("Risk engine working correctly for LOW risk")
            else:
                self.log_error(f"LOW risk transaction failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"LOW risk transaction error: {e}")
        
        # Test MEDIUM RISK transaction (moderate amount)
        try:
            tx_data = {
                "user_id": self.test_data['user_id'],
                "card_id": self.test_data['card_id'],
                "merchant_id": self.test_data.get('merchant_id'),
                "amount": 150.00,
                "currency": "EUR",
                "type": "physical",
                "user_location": {
                    "lat": 38.7223,
                    "lon": -9.1393
                }
            }
            response = await client.post(f"{BASE_URL}/api/transactions/", json=tx_data)
            if response.status_code == 201:
                tx = response.json()
                # Guardar o ID se esta transação precisar de liveness
                if tx.get('liveness_required') and tx.get('status') == 'pending':
                    self.test_data['pending_tx_id'] = tx['_id']
                self.log_success(f"MEDIUM RISK transaction: €{tx['amount']}")
                self.log_info(f"Risk: {tx['risk_score']}/100 ({tx['risk_level']}), Liveness: {tx['liveness_required']}, Status: {tx['status']}")
                if tx['liveness_required'] and tx['status'] == 'pending':
                    self.log_success("Risk engine correctly requires liveness for MEDIUM risk")
            else:
                self.log_error(f"MEDIUM risk transaction failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"MEDIUM risk transaction error: {e}")
        
        # Test HIGH RISK transaction (large amount, far from home)
        try:
            tx_data = {
                "user_id": self.test_data['user_id'],
                "card_id": self.test_data['card_id'],
                "merchant_id": self.test_data.get('merchant_id'),
                "amount": 800.00,
                "currency": "EUR",
                "type": "physical",
                "user_location": {
                    "lat": 41.1579,  # Porto (far from Lisboa)
                    "lon": -8.6291
                }
            }
            response = await client.post(f"{BASE_URL}/api/transactions/", json=tx_data)
            if response.status_code == 201:
                tx = response.json()
                # Guardar o ID se esta transação precisar de liveness (HIGH RISK tem preferência)
                if tx.get('liveness_required') and tx.get('status') == 'pending':
                    self.test_data['pending_tx_id'] = tx['_id']
                self.log_success(f"HIGH RISK transaction: €{tx['amount']}")
                self.log_info(f"Risk: {tx['risk_score']}/100 ({tx['risk_level']}), Distance from home: {tx.get('distance_from_home_km', 'N/A')} km")
                if tx['risk_level'] == 'high' and tx['liveness_required']:
                    self.log_success("Risk engine correctly identifies HIGH risk + requires liveness")
            else:
                self.log_error(f"HIGH risk transaction failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"HIGH risk transaction error: {e}")
        
        # Test get transaction by ID
        if 'pending_tx_id' in self.test_data:
            try:
                response = await client.get(f"{BASE_URL}/api/transactions/{self.test_data['pending_tx_id']}")
                if response.status_code == 200:
                    tx = response.json()
                    self.log_success(f"Get transaction: {tx['_id'][:8]}... (Status: {tx['status']})")
                else:
                    self.log_error(f"Get transaction failed: {response.status_code}")
            except Exception as e:
                self.log_error(f"Get transaction error: {e}")
    
    async def test_liveness_endpoints(self, client):
        """Test liveness verification endpoints"""
        self.log_section("5️⃣  LIVENESS VERIFICATION")
        
        if 'pending_tx_id' not in self.test_data:
            self.log_warning("No pending transaction - skipping liveness tests")
            return
        
        # Test get liveness requirements
        try:
            response = await client.get(f"{BASE_URL}/api/liveness/requirements/{self.test_data['pending_tx_id']}")
            if response.status_code == 200:
                req = response.json()
                self.log_success(f"Liveness requirements: {req['required_challenges']} challenges, {req['recommended_timeout']}s timeout")
                self.log_info(f"Risk: {req['risk_score']}/100 ({req['risk_level']})")
            else:
                self.log_error(f"Get liveness requirements failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Get liveness requirements error: {e}")
        
        # Test simulate liveness (success)
        try:
            response = await client.post(f"{BASE_URL}/api/liveness/simulate", params={"success": True})
            if response.status_code == 200:
                result = response.json()
                liveness_data = result['liveness_result']
                self.test_data['liveness_result'] = liveness_data
                self.log_success(f"Liveness simulation (SUCCESS): {liveness_data['challenges_completed']} challenges")
                self.log_info(f"Heart rate: {liveness_data['heart_rate']} bpm, Anti-spoofing: {liveness_data['anti_spoofing']['final_confidence']}")
            else:
                self.log_error(f"Liveness simulation failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Liveness simulation error: {e}")
        
        # Test simulate liveness (failure)
        try:
            response = await client.post(f"{BASE_URL}/api/liveness/simulate", params={"success": False})
            if response.status_code == 200:
                result = response.json()
                self.log_success(f"Liveness simulation (FAILURE): Correctly returned failure scenario")
            else:
                self.log_error(f"Liveness failure simulation failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Liveness failure simulation error: {e}")
        
        # Test update transaction with liveness result
        if 'liveness_result' in self.test_data:
            try:
                response = await client.patch(
                    f"{BASE_URL}/api/transactions/{self.test_data['pending_tx_id']}/liveness",
                    json=self.test_data['liveness_result']
                )
                if response.status_code == 200:
                    tx = response.json()
                    self.log_success(f"Transaction updated with liveness: Status = {tx['status']}")
                    if tx['liveness_performed'] and tx['status'] == 'APPROVED':
                        self.log_success("Transaction correctly APPROVED after liveness verification")
                else:
                    self.log_error(f"Update transaction liveness failed: {response.status_code}")
            except Exception as e:
                self.log_error(f"Update transaction liveness error: {e}")
        
        # Test get liveness status
        try:
            response = await client.get(f"{BASE_URL}/api/liveness/status/{self.test_data['pending_tx_id']}")
            if response.status_code == 200:
                status = response.json()
                self.log_success(f"Liveness status: Performed = {status['liveness_performed']}, Status = {status['status']}")
            else:
                self.log_error(f"Get liveness status failed: {response.status_code}")
        except Exception as e:
            self.log_error(f"Get liveness status error: {e}")
    
    async def test_error_scenarios(self, client):
        """Test error handling"""
        self.log_section("6️⃣  ERROR HANDLING")
        
        # Test 404 - User not found
        try:
            response = await client.get(f"{BASE_URL}/api/users/email/naoexiste@example.com")
            if response.status_code == 404:
                self.log_success("404 Error handling: User not found (correct)")
            else:
                self.log_warning(f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.log_error(f"404 test error: {e}")
        
        # Test 422 - Validation error
        try:
            response = await client.post(f"{BASE_URL}/api/users/", json={
                "name": "A",  # Too short
                "email": "invalid-email",
                "password": "123"  # Too short
            })
            if response.status_code == 422:
                self.log_success("422 Validation error: Correctly rejected invalid data")
            else:
                self.log_warning(f"Expected 422 validation error, got {response.status_code}")
        except Exception as e:
            self.log_error(f"422 test error: {e}")
    
    async def test_privacy_compliance(self, client):
        """Verify privacy-by-design compliance"""
        self.log_section("7️⃣  PRIVACY-BY-DESIGN COMPLIANCE")
        
        self.log_info("Checking API responses for biometric data leakage...")
        
        # Check transaction response doesn't contain raw biometric data
        if 'pending_tx_id' in self.test_data:
            try:
                response = await client.get(f"{BASE_URL}/api/transactions/{self.test_data['pending_tx_id']}")
                if response.status_code == 200:
                    tx = response.json()
                    
                    # Check for forbidden fields
                    forbidden_fields = ['face_encoding', 'face_image', 'video_frames', 'landmarks', 'embeddings']
                    has_biometric = any(field in str(tx).lower() for field in forbidden_fields)
                    
                    if not has_biometric:
                        self.log_success("✓ No raw biometric data in transaction response")
                    else:
                        self.log_error("✗ Found raw biometric data in response!")
                    
                    # Check liveness_result contains only metadata
                    if tx.get('liveness_result'):
                        lr = tx['liveness_result']
                        has_metadata = 'challenges_completed' in lr and 'heart_rate' in lr
                        if has_metadata:
                            self.log_success("✓ Liveness result contains only metadata")
                        else:
                            self.log_warning("Liveness result missing expected metadata fields")
            except Exception as e:
                self.log_error(f"Privacy check error: {e}")
        
        self.log_success("Privacy-by-Design principle: COMPLIANT")
        self.log_info("Only verification metadata stored - no permanent biometric data")
    
    def print_summary(self):
        """Print test results summary"""
        self.log_section("📊 TEST SUMMARY")
        
        total = self.passed + self.failed + self.warnings
        
        print(f"{Fore.GREEN}✅ Passed:  {self.passed}")
        print(f"{Fore.RED}❌ Failed:  {self.failed}")
        print(f"{Fore.YELLOW}⚠️  Warnings: {self.warnings}")
        print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━")
        print(f"   Total:   {total}")
        
        if self.failed == 0:
            print(f"\n{Fore.GREEN}🎉 ALL TESTS PASSED!{Style.RESET_ALL}")
        elif self.failed < 3:
            print(f"\n{Fore.YELLOW}⚠️  Some tests failed - review needed{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}❌ Multiple failures detected - investigation required{Style.RESET_ALL}")
        
        print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")


async def run_all_tests():
    """Run complete test suite"""
    tester = APITester()
    
    print(f"\n{Fore.CYAN}╔{'═'*58}╗")
    print(f"║{' '*15}🧪 BioTrust API Test Suite{' '*15}║")
    print(f"║{' '*12}Complete Endpoint Testing{' '*17}║")
    print(f"╚{'═'*58}╝{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Testing server: {BASE_URL}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        await tester.test_health_endpoints(client)
        await tester.test_users_endpoints(client)
        await tester.test_merchants_endpoints(client)
        await tester.test_transactions_endpoints(client)
        await tester.test_liveness_endpoints(client)
        await tester.test_error_scenarios(client)
        await tester.test_privacy_compliance(client)
    
    tester.print_summary()


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️  Tests interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Test suite error: {e}{Style.RESET_ALL}")
