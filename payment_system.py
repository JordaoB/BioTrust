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


class PaymentSystem:
    """
    Sistema principal de processamento de pagamentos com segurança biométrica.
    """
    
    def __init__(self):
        """Inicializa o sistema de pagamentos."""
        self.risk_engine = RiskEngine()
        self.liveness_detector = None  # Criado sob demanda
        self.transaction_log = []
        
        # Carregar perfis de utilizadores e localizações
        with open('user_profiles.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.users = data['users']
            self.locations = data['locations']
        
    def process_payment(self, user_id, transaction_data, enable_liveness=True):
        """
        Processa um pagamento completo com todas as verificações de segurança.
        
        Args:
            user_id: ID do utilizador
            transaction_data: Dict com {amount, location, type, timestamp}
            enable_liveness: Se True, faz liveness detection quando necessário
            
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
                print("\n💓 PHASE 2: Liveness Detection")
                print("-" * 70)
                print("Starting biometric verification...")
                print("Please follow the on-screen instructions:\n")
                print("  1. Blink your eyes 3 times")
                print("  2. Turn your head LEFT and return to center")
                print("  3. Turn your head RIGHT and return to center\n")
                
                print("⏳ Opening camera window... (check if it opens on top)")
                print("   If you don't see it, check your taskbar!\n")
                
                # Criar detector (apenas quando necessário)
                if self.liveness_detector is None:
                    self.liveness_detector = LivenessDetector()
                
                # Executar verificação
                liveness_result = self.liveness_detector.verify(timeout_seconds=90)
                
                result['liveness_performed'] = True
                result['liveness_result'] = liveness_result
                
                print("\n" + "-" * 70)
                print("Liveness Detection Result:")
                print(f"  Status: {'✓ PASSED' if liveness_result['success'] else '✗ FAILED'}")
                print(f"  Message: {liveness_result['message']}")
                print(f"  Blinks: {liveness_result['blinks_detected']}")
                print(f"  Movements: {', '.join(liveness_result['head_movements']) if liveness_result['head_movements'] else 'None'}")
                
                # Decisão final
                if liveness_result['success']:
                    print("\n✅ FINAL DECISION: APPROVED (Liveness Confirmed)")
                    result['approved'] = True
                else:
                    print("\n❌ FINAL DECISION: REJECTED (Liveness Failed)")
                    result['approved'] = False
        
        # Salvar no log
        self.transaction_log.append(result)
        
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
