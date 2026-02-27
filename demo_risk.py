"""
BioTrust - Demonstração do Motor de Risco
==========================================

Este script demonstra o funcionamento do Motor de Risco através de
cenários realistas de transações.

Uso: python demo_risk.py
"""

import json
from datetime import datetime, timedelta
from risk_engine import RiskEngine


def load_data():
    """Carrega os perfis de utilizadores e localizações."""
    with open('user_profiles.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def print_separator(char="=", length=80):
    """Imprime uma linha separadora."""
    print(char * length)


def print_result(result, transaction):
    """Imprime o resultado da análise de forma formatada."""
    # Ícones para decisão
    icons = {
        'approve': '✅',
        'require_liveness': '🔍',
        'block': '🚨'
    }
    
    # Cores para o score (simulado com texto)
    if result['risk_score'] < 30:
        risk_level = "BAIXO"
    elif result['risk_score'] < 70:
        risk_level = "MÉDIO"
    else:
        risk_level = "ALTO"
    
    print(f"\n{icons.get(result['decision'], '❓')} DECISÃO: {result['decision'].upper()}")
    print(f"   Score de Risco: {result['risk_score']}/100 ({risk_level})")
    print(f"   Razão: {result['reason']}")
    print(f"\n   📊 Breakdown dos Fatores:")
    for factor, value in result['breakdown'].items():
        print(f"      • {factor.capitalize():<12}: {value}")
    print()


def run_scenario(engine, name, description, transaction, data):
    """Executa um cenário de teste."""
    print_separator()
    print(f"📋 CENÁRIO: {name}")
    print(f"   {description}")
    print_separator("-")
    
    # Mostrar detalhes da transação
    user = transaction['user_profile']['name']
    amount = transaction['amount']
    location = transaction['location']['city']
    trans_type = transaction.get('transaction_type', 'online')
    
    print(f"\n💳 Transação:")
    print(f"   Utilizador: {user}")
    print(f"   Valor: €{amount:.2f}")
    print(f"   Localização: {location}")
    print(f"   Tipo: {trans_type}")
    print(f"   Hora: {transaction.get('timestamp', datetime.now()).strftime('%H:%M')}")
    
    # Analisar
    result = engine.analyze_transaction(transaction)
    
    # Mostrar resultado
    print_result(result, transaction)
    
    return result


def main():
    """Função principal - executa todos os cenários de demonstração."""
    
    print_separator("=")
    print("🔐 BioTrust - Demonstração do Motor de Risco")
    print("   TecStorm '26 Hackathon Project")
    print_separator("=")
    
    # Carregar dados
    data = load_data()
    users = data['users']
    locations = data['locations']
    
    # Inicializar motor de risco
    engine = RiskEngine()
    
    # ========================================================================
    # CENÁRIO 1: Café da Manhã (Baixo Risco)
    # ========================================================================
    scenario1 = {
        'amount': 3.50,
        'location': locations['lisboa'],
        'timestamp': datetime.now().replace(hour=9, minute=30),
        'transaction_type': 'presencial',
        'user_profile': users['joao_regular']
    }
    run_scenario(
        engine,
        "Café da Manhã",
        "João compra um café na sua cidade habitual, horário normal.",
        scenario1,
        data
    )
    
    # ========================================================================
    # CENÁRIO 2: Portátil Online (Risco Médio)
    # ========================================================================
    scenario2 = {
        'amount': 899.99,
        'location': locations['porto'],
        'timestamp': datetime.now().replace(hour=15, minute=45),
        'transaction_type': 'online',
        'user_profile': users['maria_new']
    }
    run_scenario(
        engine,
        "Compra de Portátil",
        "Maria (conta nova) compra um portátil online de valor alto.",
        scenario2,
        data
    )
    
    # ========================================================================
    # CENÁRIO 3: Jantar em Madrid (Risco Médio-Alto)
    # ========================================================================
    scenario3 = {
        'amount': 85.00,
        'location': locations['madrid'],
        'timestamp': datetime.now().replace(hour=21, minute=0),
        'transaction_type': 'presencial',
        'user_profile': users['joao_regular']
    }
    run_scenario(
        engine,
        "Jantar em Madrid",
        "João faz um pagamento em Madrid (país diferente).",
        scenario3,
        data
    )
    
    # ========================================================================
    # CENÁRIO 4: Compra de Madrugada (Risco Alto)
    # ========================================================================
    scenario4 = {
        'amount': 1200.00,
        'location': locations['londres'],
        'timestamp': datetime.now().replace(hour=3, minute=30),
        'transaction_type': 'online',
        'user_profile': users['pedro_suspicious']
    }
    run_scenario(
        engine,
        "Compra Suspeita de Madrugada",
        "Pedro (conta nova, múltiplas falhas) tenta comprar de madrugada em Londres.",
        scenario4,
        data
    )
    
    # ========================================================================
    # CENÁRIO 5: Transferência Internacional (Risco Alto)
    # ========================================================================
    scenario5 = {
        'amount': 5000.00,
        'location': locations['paris'],
        'timestamp': datetime.now().replace(hour=10, minute=0),
        'transaction_type': 'transferencia',
        'user_profile': users['maria_new']
    }
    run_scenario(
        engine,
        "Transferência Internacional",
        "Maria tenta fazer uma transferência de €5000 para França.",
        scenario5,
        data
    )
    
    # ========================================================================
    # CENÁRIO 6: Utilizador Premium (Baixo Risco)
    # ========================================================================
    scenario6 = {
        'amount': 450.00,
        'location': locations['porto'],
        'timestamp': datetime.now().replace(hour=14, minute=0),
        'transaction_type': 'online',
        'user_profile': users['ana_premium']
    }
    run_scenario(
        engine,
        "Utilizador Premium",
        "Ana (conta antiga, bom histórico) compra algo compatível com seu padrão.",
        scenario6,
        data
    )
    
    # ========================================================================
    # ESTATÍSTICAS FINAIS
    # ========================================================================
    print_separator("=")
    print("📊 ESTATÍSTICAS DAS TRANSAÇÕES ANALISADAS")
    print_separator("=")
    
    stats = engine.get_statistics()
    print(f"\n   Total de Transações: {stats['total_transactions']}")
    print(f"   ✅ Aprovadas Automaticamente: {stats['approved']}")
    print(f"   🔍 Requerem Liveness: {stats['require_liveness']}")
    print(f"   🚨 Bloqueadas: {stats.get('blocked', 0)}")
    print(f"   📈 Score Médio de Risco: {stats['average_risk_score']}/100")
    print(f"   💹 Taxa de Aprovação: {stats['approval_rate']}")
    print()
    
    print_separator("=")
    print("✅ Demonstração Completa!")
    print(f"   O Motor de Risco analisou {stats['total_transactions']} transações diferentes.")
    print("   Para integração com Liveness Detection, use o campo 'decision'.")
    print_separator("=")


if __name__ == "__main__":
    main()
