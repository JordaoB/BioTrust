"""
BioTrust - Main Application Interface
=====================================
Interface principal para simulação de compras com segurança biométrica.
"""

import sys
from datetime import datetime
from payment_system import PaymentSystem


class BioTrustApp:
    """Aplicação principal do BioTrust."""
    
    def __init__(self):
        self.payment_system = PaymentSystem()
        self.current_user = None
        
    def show_header(self):
        """Mostra o cabeçalho da aplicação."""
        print("\n" + "="*70)
        print(" "*20 + "🔐 BioTrust Payment System")
        print(" "*15 + "Secure Biometric Authentication")
        print("="*70)
    
    def select_user(self):
        """Permite selecionar um utilizador."""
        print("\n📋 Select User Profile:")
        print("-" * 70)
        
        users = {
            "1": ("joao_regular", "João Silva - Lisboa | Regular User (365 days)"),
            "2": ("maria_new", "Maria Santos - Porto | New User (15 days)"),
            "3": ("ana_premium", "Ana Costa - Braga | Premium Customer (3+ years)"),
            "4": ("pedro_suspicious", "Pedro Alves - Faro | Suspicious Activity")
        }
        
        for key, (user_id, desc) in users.items():
            print(f"  {key}. {desc}")
        
        choice = input("\nEnter user number (1-4): ").strip()
        
        if choice in users:
            self.current_user = users[choice][0]
            print(f"✓ Selected: {users[choice][1]}")
            return True
        else:
            print("✗ Invalid selection")
            return False
    
    def create_custom_transaction(self):
        """Cria uma transação personalizada."""
        print("\n💳 Create Custom Transaction:")
        print("-" * 70)
        
        try:
            amount = float(input("Amount (€): "))
            location = input("Location (city): ").strip()
            
            print("\nTransaction Type:")
            print("  1. POS (Point of Sale - presencial)")
            print("  2. Online")
            print("  3. Transfer")
            
            type_choice = input("Select type (1-3): ").strip()
            type_map = {"1": "pos", "2": "online", "3": "transfer"}
            trans_type = type_map.get(type_choice, "online")
            
            return {
                "amount": amount,
                "location": location,
                "type": trans_type,
                "timestamp": datetime.now().isoformat()
            }
        except ValueError:
            print("✗ Invalid input")
            return None
    
    def show_scenario_menu(self):
        """Mostra menu com cenários pré-definidos."""
        print("\n📌 Quick Scenarios:")
        print("-" * 70)
        
        scenarios = {
            "1": {
                "name": "☕ Morning Coffee",
                "amount": 2.50,
                "location": "lisboa",  # lowercase para match JSON
                "type": "pos"
            },
            "2": {
                "name": "🍕 Lunch",
                "amount": 12.50,
                "location": "lisboa",
                "type": "pos"
            },
            "3": {
                "name": "💻 Electronics (Medium Risk)",
                "amount": 450.00,
                "location": "porto",
                "type": "online"
            },
            "4": {
                "name": "✈️ Flight Ticket (High Risk)",
                "amount": 850.00,
                "location": "madrid",
                "type": "online"
            },
            "5": {
                "name": "💎 Luxury Item (Very High Risk)",
                "amount": 2500.00,
                "location": "paris",
                "type": "online"
            },
            "6": {
                "name": "🌙 Late Night Purchase (Suspicious)",
                "amount": 300.00,
                "location": "barcelona",  # não está no JSON, vai usar fallback
                "type": "online"
            }
        }
        
        for key, scenario in scenarios.items():
            print(f"  {key}. {scenario['name']}")
            print(f"      €{scenario['amount']:.2f} | {scenario['location'].title()} | {scenario['type']}")
        
        print("  7. Custom Transaction")
        
        return scenarios
    
    def run(self):
        """Executa a aplicação principal."""
        self.show_header()
        
        # Selecionar utilizador
        if not self.select_user():
            print("Exiting...")
            return
        
        while True:
            scenarios = self.show_scenario_menu()
            
            choice = input("\nSelect scenario (1-7) or 'q' to quit: ").strip().lower()
            
            if choice == 'q':
                print("\n👋 Thank you for using BioTrust!")
                break
            
            transaction_data = None
            
            if choice in scenarios:
                scenario = scenarios[choice]
                transaction_data = {
                    "amount": scenario['amount'],
                    "location": scenario['location'],
                    "type": scenario['type'],
                    "timestamp": datetime.now().isoformat()
                }
                print(f"\n✓ Selected: {scenario['name']}")
            elif choice == '7':
                transaction_data = self.create_custom_transaction()
            
            if transaction_data:
                # Processar pagamento
                print("\nProcessing payment...")
                result = self.payment_system.process_payment(
                    self.current_user, 
                    transaction_data
                )
                
                # Aguardar antes de continuar
                input("\n\nPress ENTER to continue...")
            else:
                print("✗ Invalid selection")
        
        # Salvar log ao sair
        self.payment_system.save_transaction_log("transaction_log.json")
        print("\n✓ Session completed. Transaction log saved.")


def main():
    """Função principal."""
    try:
        app = BioTrustApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Application interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
