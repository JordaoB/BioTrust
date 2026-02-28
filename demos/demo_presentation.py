"""
BioTrust - Automated Demonstration Script
TecStorm '26 Hackathon - Payments Without Limits

This script automatically demonstrates the BioTrust system with:
- Low-risk transactions (instant approval)
- High-risk transactions (liveness detection required)
"""

import time
from datetime import datetime
from payment_system import PaymentSystem
from colorama import init, Fore, Style, Back

# Initialize colorama for Windows
init(autoreset=True)


class DemoPresentation:
    def __init__(self):
        self.payment_system = PaymentSystem()
        self.demo_scenarios = [
            {
                "name": "Cenário 1: Café Local (LOW RISK)",
                "user": "joao_regular",
                "transaction": {
                    "amount": 2.50,
                    "location": "lisboa",
                    "type": "physical",
                    "timestamp": datetime.now().isoformat()
                },
                "expected": "AUTO-APPROVE",
                "description": "Compra de rotina, valor baixo, localização habitual"
            },
            {
                "name": "Cenário 2: Supermercado (LOW RISK)",
                "user": "ana_premium",
                "transaction": {
                    "amount": 45.80,
                    "location": "braga",
                    "type": "physical",
                    "timestamp": datetime.now().isoformat()
                },
                "expected": "AUTO-APPROVE",
                "description": "Utilizadora premium, valor normal, cidade de residência"
            },
            {
                "name": "Cenário 3: Voo Internacional (HIGH RISK)",
                "user": "joao_regular",
                "transaction": {
                    "amount": 850.00,
                    "location": "madrid",
                    "type": "online",
                    "timestamp": datetime.now().isoformat()
                },
                "expected": "LIVENESS REQUIRED",
                "description": "Valor elevado, localização estrangeira, transação online"
            },
            {
                "name": "Cenário 4: Compra Suspeita (HIGH RISK)",
                "user": "pedro_suspicious",
                "transaction": {
                    "amount": 1200.00,
                    "location": "paris",
                    "type": "online",
                    "timestamp": datetime.now().isoformat()
                },
                "expected": "LIVENESS REQUIRED",
                "description": "Utilizador novo, valor muito elevado, país diferente"
            }
        ]
    
    def print_header(self):
        """Print demo header"""
        print("\n" + "="*80)
        print(Fore.CYAN + Style.BRIGHT + "🔐 BioTrust - Sistema de Autenticação Biométrica")
        print(Fore.CYAN + "   TecStorm '26 Hackathon - Payments Without Limits")
        print("="*80 + "\n")
    
    def print_scenario_header(self, scenario_num, scenario):
        """Print scenario information"""
        print("\n" + "-"*80)
        print(Fore.YELLOW + Style.BRIGHT + f"📋 {scenario['name']}")
        print("-"*80)
        print(f"👤 Utilizador: {Fore.CYAN}{scenario['user']}")
        print(f"💰 Valor: {Fore.GREEN}€{scenario['transaction']['amount']:.2f}")
        print(f"📍 Localização: {Fore.BLUE}{scenario['transaction']['location']}")
        print(f"🔖 Tipo: {scenario['transaction']['type']}")
        print(f"📝 Descrição: {Fore.WHITE}{scenario['description']}")
        print(f"🎯 Expectativa: {Fore.MAGENTA}{scenario['expected']}")
        print("-"*80 + "\n")
    
    def print_risk_analysis(self, risk_result):
        """Print risk analysis details"""
        print(Fore.YELLOW + "⚙️  MOTOR DE RISCO - Análise")
        print("-" * 40)
        print(f"Score Total: {self._colorize_score(risk_result['risk_score'])}/100")
        print(f"Decisão: {self._colorize_decision(risk_result['decision'])}")
        
        if 'risk_breakdown' in risk_result:
            print("\n📊 Breakdown de Risco:")
            breakdown = risk_result['risk_breakdown']
            print(f"  • Valor (30%):        {breakdown['amount']}/100")
            print(f"  • Localização (25%):  {breakdown['location']}/100")
            print(f"  • Horário (20%):      {breakdown['time']}/100")
            print(f"  • Comportamento (15%): {breakdown['behavior']}/100")
            print(f"  • Tipo (10%):         {breakdown['type']}/100")
        print()
    
    def _colorize_score(self, score):
        """Colorize score based on value"""
        if score <= 30:
            return Fore.GREEN + str(score) + Style.RESET_ALL
        elif score <= 70:
            return Fore.YELLOW + str(score) + Style.RESET_ALL
        else:
            return Fore.RED + str(score) + Style.RESET_ALL
    
    def _colorize_decision(self, decision):
        """Colorize decision"""
        colors = {
            "LOW_RISK": Fore.GREEN,
            "MEDIUM_RISK": Fore.YELLOW,
            "HIGH_RISK": Fore.RED
        }
        color = colors.get(decision, Fore.WHITE)
        return color + decision + Style.RESET_ALL
    
    def print_result(self, result):
        """Print final result"""
        print("\n" + "="*80)
        if result['approved']:
            print(Back.GREEN + Fore.BLACK + Style.BRIGHT + " ✅ TRANSAÇÃO APROVADA ")
            print(Style.RESET_ALL + Fore.GREEN + f"Motivo: {result.get('reason', 'N/A')}")
        else:
            print(Back.RED + Fore.WHITE + Style.BRIGHT + " ❌ TRANSAÇÃO REJEITADA ")
            print(Style.RESET_ALL + Fore.RED + f"Motivo: {result.get('reason', 'N/A')}")
        
        if 'liveness_result' in result and result['liveness_result']:
            liveness = result['liveness_result']
            if liveness.get('success'):
                print(Fore.CYAN + f"👁️  Liveness Confirmada:")
                print(f"   • {liveness['blinks_detected']} piscadelas detectadas")
                print(f"   • Movimentos: {', '.join(liveness['head_movements'])}")
        
        print("="*80 + "\n")
    
    def run_scenario(self, scenario_num, scenario, enable_liveness=True):
        """Run a single scenario"""
        self.print_scenario_header(scenario_num, scenario)
        
        # Process payment
        print(Fore.CYAN + "⏳ Processando transação...\n")
        time.sleep(1)
        
        result = self.payment_system.process_payment(
            scenario['user'],
            scenario['transaction'],
            enable_liveness=enable_liveness
        )
        
        # Print risk analysis
        if 'risk_result' in result:
            self.print_risk_analysis(result['risk_result'])
        
        # Print final result
        self.print_result(result)
        
        return result
    
    def run_demo(self, pause_between=True, enable_liveness=True):
        """Run full demo presentation"""
        self.print_header()
        
        print(Fore.WHITE + Style.BRIGHT + "Este demo vai executar 4 cenários automaticamente:")
        print("  • 2 transações de baixo risco (aprovação imediata)")
        print("  • 2 transações de alto risco (requerem liveness detection)")
        
        if not enable_liveness:
            print(Fore.RED + "\n⚠️  ATENÇÃO: Liveness detection está DESATIVADA para este demo")
        
        print("\n" + Fore.YELLOW + "Pressione ENTER para começar...")
        input()
        
        results = []
        
        for i, scenario in enumerate(self.demo_scenarios, 1):
            result = self.run_scenario(i, scenario, enable_liveness)
            results.append(result)
            
            if pause_between and i < len(self.demo_scenarios):
                print(Fore.YELLOW + "Pressione ENTER para continuar para o próximo cenário...")
                input()
        
        # Print summary
        self.print_summary(results)
        
        return results
    
    def print_summary(self, results):
        """Print demo summary"""
        print("\n" + "="*80)
        print(Fore.CYAN + Style.BRIGHT + "📊 RESUMO DA DEMONSTRAÇÃO")
        print("="*80)
        
        approved = sum(1 for r in results if r['approved'])
        rejected = len(results) - approved
        
        print(f"\n✅ Transações Aprovadas: {Fore.GREEN}{approved}/{len(results)}")
        print(f"❌ Transações Rejeitadas: {Fore.RED}{rejected}/{len(results)}")
        
        liveness_used = sum(1 for r in results if r.get('liveness_result') is not None)
        if liveness_used > 0:
            print(f"👁️  Verificações Liveness: {Fore.CYAN}{liveness_used}/{len(results)}")
        
        print("\n" + "="*80 + "\n")


def main():
    """Main entry point"""
    print(Fore.CYAN + Style.BRIGHT + "\n🎬 BioTrust - Demo Presentation Script\n")
    
    print("Escolha o modo de demonstração:")
    print("1. Demo Completo (com liveness detection)")
    print("2. Demo Rápido (sem liveness detection - apenas análise de risco)")
    print("3. Demo Automático (sem pausas)")
    print("4. Sair")
    
    choice = input("\nEscolha (1-4): ").strip()
    
    demo = DemoPresentation()
    
    if choice == "1":
        print(Fore.GREEN + "\n✓ Modo: Demo Completo (com liveness)")
        demo.run_demo(pause_between=True, enable_liveness=True)
    
    elif choice == "2":
        print(Fore.YELLOW + "\n✓ Modo: Demo Rápido (sem liveness)")
        demo.run_demo(pause_between=True, enable_liveness=False)
    
    elif choice == "3":
        print(Fore.CYAN + "\n✓ Modo: Demo Automático (sem pausas, sem liveness)")
        demo.run_demo(pause_between=False, enable_liveness=False)
    
    elif choice == "4":
        print(Fore.WHITE + "Até breve!")
        return
    
    else:
        print(Fore.RED + "Opção inválida!")
        return
    
    print(Fore.GREEN + Style.BRIGHT + "\n✅ Demo concluída com sucesso!")
    print(Fore.WHITE + "Obrigado por utilizar o BioTrust!\n")


if __name__ == "__main__":
    main()
