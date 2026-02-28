"""
BioTrust - Main Application Interface
=====================================
Interface principal para simulação de compras com segurança biométrica.
"""

import sys
from datetime import datetime
from payment_system import PaymentSystem
from colorama import init, Fore, Style, Back

# Initialize colorama for Windows
init(autoreset=True)


class BioTrustApp:
    """Aplicação principal do BioTrust."""
    
    def __init__(self):
        self.payment_system = PaymentSystem()
        self.current_user = None
        
    def show_header(self):
        """Mostra o cabeçalho da aplicação."""
        print("\n" + "="*70)
        print(Fore.CYAN + Style.BRIGHT + " "*20 + "🔐 BioTrust Payment System")
        print(" "*15 + "Secure Biometric Authentication")
        print("="*70)
    
    def select_user(self):
        """Permite selecionar um utilizador."""
        print("\n" + Fore.YELLOW + "📋 Select User Profile:")
        print("-" * 70)
        
        users = {
            "1": ("joao_regular", "João Silva - Lisboa | Regular User (365 days)"),
            "2": ("maria_new", "Maria Santos - Porto | New User (15 days)"),
            "3": ("ana_premium", "Ana Costa - Braga | Premium Customer (3+ years)"),
            "4": ("pedro_suspicious", "Pedro Alves - Faro | Suspicious Activity")
        }
        
        for key, (user_id, desc) in users.items():
            print(f"  {Fore.CYAN}{key}. {Fore.WHITE}{desc}")
        
        choice = input("\n" + Fore.GREEN + "Enter user number (1-4): ").strip()
        
        if choice in users:
            self.current_user = users[choice][0]
            print(Fore.GREEN + f"✓ Selected: {users[choice][1]}")
            return True
        else:
            print(Fore.RED + "✗ Invalid selection")
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
        print("\n" + Fore.YELLOW + "📌 Quick Scenarios:")
        print("-" * 70)
        
        scenarios = {
            "1": {
                "name": "☕ Morning Coffee",
                "amount": 2.50,
                "location": "lisboa",  # lowercase para match JSON
                "type": "pos",
                "risk": "LOW"
            },
            "2": {
                "name": "🍕 Lunch",
                "amount": 12.50,
                "location": "lisboa",
                "type": "pos",
                "risk": "LOW"
            },
            "3": {
                "name": "💻 Electronics (Medium Risk)",
                "amount": 450.00,
                "location": "porto",
                "type": "online",
                "risk": "MEDIUM"
            },
            "4": {
                "name": "✈️ Flight Ticket (High Risk)",
                "amount": 850.00,
                "location": "madrid",
                "type": "online",
                "risk": "HIGH"
            },
            "5": {
                "name": "💎 Luxury Item (Very High Risk)",
                "amount": 2500.00,
                "location": "paris",
                "type": "online",
                "risk": "VERYHIGH"
            },
            "6": {
                "name": "🌙 Late Night Purchase (Suspicious)",
                "amount": 300.00,
                "location": "barcelona",  # não está no JSON, vai usar fallback
                "type": "online",
                "risk": "MEDIUM"
            }
        }
        
        for key, scenario in scenarios.items():
            risk_color = {
                "LOW": Fore.GREEN,
                "MEDIUM": Fore.YELLOW,
                "HIGH": Fore.RED,
                "VERYHIGH": Fore.MAGENTA
            }.get(scenario['risk'], Fore.WHITE)
            
            print(f"  {Fore.CYAN}{key}. {Fore.WHITE}{scenario['name']}")
            print(f"      {Fore.GREEN}€{scenario['amount']:.2f} {Fore.WHITE}| {Fore.BLUE}{scenario['location'].title()} {Fore.WHITE}| {risk_color}{scenario['type']}")
        
        print(f"  {Fore.CYAN}7. {Fore.WHITE}Custom Transaction")
        
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
            
            choice = input("\n" + Fore.GREEN + "Select scenario (1-7) or 'q' to quit: ").strip().lower()
            
            if choice == 'q':
                print("\n" + Fore.CYAN + "👋 Thank you for using BioTrust!")
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
                print(Fore.GREEN + f"\n✓ Selected: {scenario['name']}")
            elif choice == '7':
                transaction_data = self.create_custom_transaction()
            
            if transaction_data:
                # Processar pagamento
                print(Fore.CYAN + "\nProcessing payment...")
                result = self.payment_system.process_payment(
                    self.current_user, 
                    transaction_data
                )
                
                # Show statistics after transaction
                print("\n" + Fore.YELLOW + Style.BRIGHT + "📊 Session Statistics:")
                self.payment_system.logger.print_statistics()
                
                # Aguardar antes de continuar
                input("\n\n" + Fore.WHITE + "Press ENTER to continue...")
            else:
                print(Fore.RED + "✗ Invalid selection")
        
        # Salvar log ao sair
        self.payment_system.save_transaction_log("transaction_log.json")
        print("\n" + Fore.GREEN + "✓ Session completed. Transaction log saved.")


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
