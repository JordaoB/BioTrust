"""
BioTrust - Payment Processing System
====================================
Sistema de orquestração que integra:
1. Risk Engine (análise de risco)
2. Liveness Detection (verificação biométrica)

Fluxo: Transaction → Risk Analysis → Liveness (se necessário) → Decision
"""

import json
from datetime import datetime
from risk_engine import RiskEngine
from liveness_detector import LivenessDetector
from passive_liveness import PassiveLivenessDetector
from transaction_logger import TransactionLogger


class PaymentSystem:
    """
    Sistema principal de processamento de pagamentos com segurança biométrica.
    """
    
    def __init__(self):
        """Inicializa o sistema de pagamentos."""
        self.risk_engine = RiskEngine()
        self.liveness_detector = None  # Criado sob demanda
        self.passive_detector = None  # Criado sob demanda
        self.transaction_log = []  # Legacy - mantido para compatibilidade
        self.logger = TransactionLogger()  # Novo sistema de logging
        
        # Carregar perfis de utilizadores e localizações
        with open('user_profiles.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.users = data['users']
            self.locations = data['locations']
        
    def process_payment(self, user_id, transaction_data, enable_liveness=True, liveness_mode="active"):
        """
        Processa um pagamento completo com todas as verificações de segurança.
        
        Args:
            user_id: ID do utilizador
            transaction_data: Dict com {amount, location, type, timestamp}
            enable_liveness: Se True, faz liveness detection quando necessário
            liveness_mode: Tipo de liveness - "active", "passive", ou "multi"
            
        Returns:
            dict com resultado completo:
            {
                "approved": True/False,
                "risk_score": int,
                "decision_reason": str,
                "liveness_performed": True/False,
                "liveness_result": dict (se aplicável),
                "transaction_id": str,
                "timestamp": str
            }
        """
        # Gerar ID único para transação
        transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"
        timestamp = datetime.now().isoformat()
        
        print("\n" + "="*70)
        print(f"🔐 BioTrust Payment Processing - Transaction {transaction_id}")
        print("="*70)
        
        # FASE 1: Análise de Risco
        print("\n📊 PHASE 1: Risk Analysis")
        print("-" * 70)
        
        # Preparar dados para o risk engine
        # Converter location string para dict de localização
        if isinstance(transaction_data['location'], str):
            location_key = transaction_data['location'].lower()
            location = self.locations.get(location_key, {
                "city": transaction_data['location'],
                "country": "Portugal",
                "coordinates": {"lat": 38.7223, "lon": -9.1393}
            })
        else:
            location = transaction_data['location']
        
        # Obter perfil do utilizador
        user_profile = self.users.get(user_id, self.users.get('joao_regular'))  # Default fallback
        
        # Montar transação completa para o risk engine
        full_transaction = {
            'amount': transaction_data['amount'],
            'location': location,
            'timestamp': datetime.fromisoformat(transaction_data['timestamp']) if isinstance(transaction_data['timestamp'], str) else transaction_data['timestamp'],
            'transaction_type': transaction_data.get('type', 'online'),
            'user_profile': user_profile
        }
        
        risk_result = self.risk_engine.analyze_transaction(full_transaction)
        
        print(f"User: {user_id}")
        print(f"Amount: €{transaction_data['amount']:.2f}")
        print(f"Location: {transaction_data['location']}")
        print(f"Risk Score: {risk_result['risk_score']}/100")
        print(f"Decision: {risk_result['decision'].upper().replace('_', ' ')}")
        
        # Mostrar breakdown dos fatores
        print("\nRisk Breakdown:")
        for factor, score in risk_result['factors'].items():
            bar = "█" * int(score / 5)
            print(f"  {factor:20s}: {int(score):3d}/100 {bar}")
        
        result = {
            "transaction_id": transaction_id,
            "timestamp": timestamp,
            "user_id": user_id,
            "amount": transaction_data['amount'],
            "location": transaction_data['location'],
            "risk_score": risk_result['risk_score'],
            "decision_reason": risk_result['reason'],  # Corrigido: 'reason' não 'explanation'
            "liveness_performed": False,
            "liveness_result": None,
            "approved": False
        }
        
        # FASE 2: Decisão baseada no risco
        if risk_result['decision'] == 'approve':
            # Risco baixo - aprovar diretamente
            print("\n✅ DECISION: APPROVED (Low Risk)")
            print("-" * 70)
            result['approved'] = True
            
        elif risk_result['decision'] == 'reject':
            # Risco altíssimo - rejeitar diretamente
            print("\n❌ DECISION: REJECTED (High Risk)")
            print("-" * 70)
            result['approved'] = False
            
        elif risk_result['decision'] == 'require_liveness':
            # Risco médio - exigir liveness
            print("\n🔍 DECISION: Liveness Detection Required")
            print("-" * 70)
            
            if not enable_liveness:
                print("⚠️  Liveness disabled in this mode - REJECTED by default")
                result['approved'] = False
            else:
                # FASE 3: Liveness Detection
                print(f"\n💓 PHASE 2: Liveness Detection (Mode: {liveness_mode.upper()})")
                print("-" * 70)
                
                liveness_passed = False
                combined_result = {}
                
                # ACTIVE LIVENESS (with integrated passive)
                if liveness_mode in ["active", "multi"]:
                    print("🎭 Starting ACTIVE Liveness Detection...")
                    if liveness_mode == "active":
                        print("🫀 Passive liveness (rPPG) running in parallel...")
                    print("Please follow the on-screen instructions:")
                    print("  1. Blink your eyes 3 times")
                    print("  2. Turn your head LEFT and return to center")
                    print("  3. Turn your head RIGHT and return to center\n")
                    
                    # Criar detector (apenas quando necessário)
                    if self.liveness_detector is None:
                        self.liveness_detector = LivenessDetector()
                    
                    # Executar verificação (enable_passive=True for active mode, False for multi)
                    enable_passive_parallel = (liveness_mode == "active")
                    active_result = self.liveness_detector.verify(timeout_seconds=90, enable_passive=enable_passive_parallel)
                    combined_result['active'] = active_result
                    
                    print("\n" + "-" * 70)
                    print("Active Liveness Result:")
                    print(f"  Status: {'✓ PASSED' if active_result['success'] else '✗ FAILED'}")
                    print(f"  Message: {active_result['message']}")
                    print(f"  Blinks: {active_result['blinks_detected']}")
                    print(f"  Movements: {', '.join(active_result['head_movements']) if active_result['head_movements'] else 'None'}")
                    
                    # Show passive results if available
                    if 'heart_rate' in active_result:
                        print(f"  Heart Rate: {active_result['heart_rate']:.1f} BPM")
                        print(f"  HR Confidence: {active_result['heart_rate_confidence']:.1%}")
                        print(f"  Passive: {'✓ PASS' if active_result.get('passive_liveness', False) else '✗ FAIL'}")
                    
                    if liveness_mode == "active":
                        liveness_passed = active_result['success']
                
                # PASSIVE LIVENESS (rPPG)
                if liveness_mode in ["passive", "multi"]:
                    print("\n🫀 Starting PASSIVE Liveness Detection (rPPG)...")
                    print("Please stay still and look at the camera.\n")
                    
                    # Criar detector passivo
                    if self.passive_detector is None:
                        self.passive_detector = PassiveLivenessDetector()
                    
                    # Executar verificação
                    passive_result = self.passive_detector.verify(show_visualization=True)
                    combined_result['passive'] = passive_result
                    
                    print("\n" + "-" * 70)
                    print("Passive Liveness Result:")
                    print(f"  Status: {'✓ LIVE PERSON' if passive_result['is_live'] else '✗ SPOOF DETECTED'}")
                    print(f"  Heart Rate: {passive_result['heart_rate']:.1f} BPM")
                    print(f"  Confidence: {passive_result['confidence']:.2%}")
                    
                    if liveness_mode == "passive":
                        liveness_passed = passive_result['is_live']
                
                # MULTI-FACTOR: Ambos devem passar
                if liveness_mode == "multi":
                    active_ok = combined_result.get('active', {}).get('success', False)
                    passive_ok = combined_result.get('passive', {}).get('is_live', False)
                    liveness_passed = active_ok and passive_ok
                    
                    print("\n" + "-" * 70)
                    print("Multi-Factor Liveness:")
                    print(f"  Active Liveness: {'✓' if active_ok else '✗'}")
                    print(f"  Passive Liveness: {'✓' if passive_ok else '✗'}")
                    print(f"  Combined Result: {'✓ PASSED' if liveness_passed else '✗ FAILED'}")
                
                result['liveness_performed'] = True
                result['liveness_result'] = combined_result
                result['liveness_mode'] = liveness_mode
                
                # Decisão final
                if liveness_passed:
                    print("\n✅ FINAL DECISION: APPROVED (Liveness Confirmed)")
                    result['approved'] = True
                else:
                    print("\n❌ FINAL DECISION: REJECTED (Liveness Failed)")
                    result['approved'] = False
        
        # Salvar no log (legacy)
        self.transaction_log.append(result)
        
        # Salvar no novo sistema de logging persistente
        log_entry = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "amount": transaction_data['amount'],
            "location": transaction_data['location'],
            "type": transaction_data['type'],
            "timestamp": transaction_data['timestamp'],
            "risk_score": risk_result['risk_score'],
            "risk_decision": risk_result['decision'],
            "approved": result['approved'],
            "liveness_performed": result['liveness_performed'],
            "liveness_success": result.get('liveness_result', {}).get('success', False) if result['liveness_performed'] else None,
            "logged_at": datetime.now().isoformat()
        }
        self.logger.log_transaction(log_entry)
        
        # Resumo final
        print("\n" + "="*70)
        print("📋 TRANSACTION SUMMARY")
        print("="*70)
        print(f"Transaction ID: {transaction_id}")
        print(f"User: {user_id}")
        print(f"Amount: €{transaction_data['amount']:.2f}")
        print(f"Risk Score: {risk_result['risk_score']}/100")
        print(f"Liveness Performed: {'Yes' if result['liveness_performed'] else 'No'}")
        print(f"Status: {'✅ APPROVED' if result['approved'] else '❌ REJECTED'}")
        print("="*70 + "\n")
        
        return result
    
    def get_transaction_history(self):
        """Retorna histórico de transações processadas."""
        return self.transaction_log
    
    def save_transaction_log(self, filename="transaction_log.json"):
        """Salva o log de transações em ficheiro JSON."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.transaction_log, f, indent=2, ensure_ascii=False)
        print(f"✓ Transaction log saved to {filename}")


# Função auxiliar para uso rápido
def quick_payment(user_id, amount, location, transaction_type="online"):
    """
    Função rápida para processar um pagamento.
    
    Args:
        user_id: ID do utilizador
        amount: Valor em euros
        location: Localização (string ou dict)
        transaction_type: Tipo de transação
        
    Returns:
        True se aprovado, False se rejeitado
    """
    system = PaymentSystem()
    
    transaction_data = {
        "amount": amount,
        "location": location,
        "type": transaction_type,
        "timestamp": datetime.now().isoformat()
    }
    
    result = system.process_payment(user_id, transaction_data)
    return result['approved']


if __name__ == "__main__":
    # Teste standalone
    print("🔐 BioTrust Payment System - Test Mode\n")
    
    system = PaymentSystem()
    
    # Teste 1: Compra de baixo risco (deve aprovar direto)
    print("\n" + "#"*70)
    print("TEST 1: Low Risk Purchase")
    print("#"*70)
    
    transaction1 = {
        "amount": 3.50,
        "location": "Lisboa",
        "type": "pos",
        "timestamp": datetime.now().isoformat()
    }
    
    result1 = system.process_payment("joao_silva", transaction1)
    input("\nPress ENTER to continue to next test...")
    
    # Teste 2: Compra de alto risco (deve pedir liveness)
    print("\n" + "#"*70)
    print("TEST 2: High Risk Purchase (Will Trigger Liveness)")
    print("#"*70)
    
    transaction2 = {
        "amount": 850.00,
        "location": "Madrid",
        "type": "online",
        "timestamp": datetime.now().isoformat()
    }
    
    result2 = system.process_payment("joao_silva", transaction2)
    
    # Salvar log
    system.save_transaction_log()
