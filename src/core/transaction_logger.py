"""
BioTrust - Transaction Logger
=============================
Sistema de persistência de transações com estatísticas e relatórios.
"""

import json
import os
from datetime import datetime
from pathlib import Path


class TransactionLogger:
    """
    Gere o logging e persistência de todas as transações do sistema.
    """
    
    def __init__(self, log_file='transaction_log.json'):
        """
        Inicializa o logger de transações.
        
        Args:
            log_file: Caminho para o ficheiro de log
        """
        self.log_file = log_file
        self.transactions = self._load_transactions()
    
    def _load_transactions(self):
        """Carrega transações existentes do ficheiro."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️  Warning: Could not parse {self.log_file}. Starting fresh.")
                return []
        return []
    
    def _save_transactions(self):
        """Guarda transações no ficheiro."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.transactions, f, indent=2, ensure_ascii=False)
    
    def log_transaction(self, transaction_data):
        """
        Adiciona uma nova transação ao log.
        
        Args:
            transaction_data: Dict com dados da transação
        """
        # Adicionar timestamp se não existir
        if 'logged_at' not in transaction_data:
            transaction_data['logged_at'] = datetime.now().isoformat()
        
        self.transactions.append(transaction_data)
        self._save_transactions()
    
    def get_statistics(self):
        """
        Calcula estatísticas sobre todas as transações.
        
        Returns:
            dict com estatísticas gerais
        """
        if not self.transactions:
            return {
                "total_transactions": 0,
                "approved": 0,
                "rejected": 0,
                "approval_rate": 0,
                "liveness_checks": 0,
                "total_amount": 0,
                "avg_risk_score": 0
            }
        
        total = len(self.transactions)
        approved = sum(1 for t in self.transactions if t.get('approved', False))
        rejected = total - approved
        liveness_checks = sum(1 for t in self.transactions if t.get('liveness_performed', False))
        
        total_amount = sum(t.get('amount', 0) for t in self.transactions)
        risk_scores = [t.get('risk_score', 0) for t in self.transactions if 'risk_score' in t]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        return {
            "total_transactions": total,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": round((approved / total) * 100, 2) if total > 0 else 0,
            "liveness_checks": liveness_checks,
            "liveness_rate": round((liveness_checks / total) * 100, 2) if total > 0 else 0,
            "total_amount": round(total_amount, 2),
            "avg_amount": round(total_amount / total, 2) if total > 0 else 0,
            "avg_risk_score": round(avg_risk, 2)
        }
    
    def get_user_statistics(self, user_id):
        """
        Estatísticas filtradas por utilizador.
        
        Args:
            user_id: ID do utilizador
            
        Returns:
            dict com estatísticas do utilizador
        """
        user_transactions = [t for t in self.transactions if t.get('user_id') == user_id]
        
        if not user_transactions:
            return None
        
        total = len(user_transactions)
        approved = sum(1 for t in user_transactions if t.get('approved', False))
        
        return {
            "user_id": user_id,
            "total_transactions": total,
            "approved": approved,
            "rejected": total - approved,
            "approval_rate": round((approved / total) * 100, 2) if total > 0 else 0
        }
    
    def get_recent_transactions(self, limit=10):
        """
        Retorna as transações mais recentes.
        
        Args:
            limit: Número máximo de transações a retornar
            
        Returns:
            list com últimas transações
        """
        return self.transactions[-limit:] if self.transactions else []
    
    def get_transactions_by_date(self, date_str):
        """
        Retorna transações de uma data específica.
        
        Args:
            date_str: Data no formato YYYY-MM-DD
            
        Returns:
            list de transações dessa data
        """
        return [
            t for t in self.transactions 
            if t.get('logged_at', '').startswith(date_str)
        ]
    
    def print_statistics(self):
        """Imprime estatísticas formatadas."""
        stats = self.get_statistics()
        
        print("\n" + "="*70)
        print("📊 ESTATÍSTICAS DE TRANSAÇÕES")
        print("="*70)
        print(f"Total de Transações:     {stats['total_transactions']}")
        print(f"✅ Aprovadas:            {stats['approved']} ({stats['approval_rate']}%)")
        print(f"❌ Rejeitadas:           {stats['rejected']}")
        print(f"👁️  Verificações Liveness: {stats['liveness_checks']} ({stats['liveness_rate']}%)")
        print(f"💰 Volume Total:         €{stats['total_amount']:.2f}")
        print(f"💰 Valor Médio:          €{stats['avg_amount']:.2f}")
        print(f"📈 Score de Risco Médio: {stats['avg_risk_score']:.1f}/100")
        print("="*70 + "\n")
    
    def export_to_csv(self, output_file='transactions_export.csv'):
        """
        Exporta transações para CSV.
        
        Args:
            output_file: Nome do ficheiro de saída
        """
        if not self.transactions:
            print("⚠️  No transactions to export")
            return
        
        import csv
        
        # Define campos a exportar
        fields = [
            'transaction_id', 'user_id', 'amount', 'location', 
            'type', 'risk_score', 'approved', 'liveness_performed',
            'logged_at'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.transactions)
        
        print(f"✅ Exported {len(self.transactions)} transactions to {output_file}")
    
    def clear_log(self, backup=True):
        """
        Limpa o log de transações.
        
        Args:
            backup: Se True, cria backup antes de limpar
        """
        if backup and self.transactions:
            backup_file = f"transaction_log_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.transactions, f, indent=2, ensure_ascii=False)
            print(f"✅ Backup created: {backup_file}")
        
        self.transactions = []
        self._save_transactions()
        print("✅ Transaction log cleared")


def main():
    """Demonstração das funcionalidades do logger."""
    logger = TransactionLogger()
    
    print("\n🔐 BioTrust - Transaction Logger Demo\n")
    
    print("Escolha uma opção:")
    print("1. Ver estatísticas")
    print("2. Ver transações recentes")
    print("3. Exportar para CSV")
    print("4. Limpar log (com backup)")
    print("5. Sair")
    
    choice = input("\nEscolha (1-5): ").strip()
    
    if choice == "1":
        logger.print_statistics()
    
    elif choice == "2":
        limit = int(input("Quantas transações mostrar? (padrão: 10): ").strip() or "10")
        recent = logger.get_recent_transactions(limit)
        
        print(f"\n📋 Últimas {len(recent)} transações:\n")
        for i, t in enumerate(recent, 1):
            status = "✅" if t.get('approved') else "❌"
            print(f"{i}. {status} {t.get('transaction_id')} - €{t.get('amount', 0):.2f} - Risk: {t.get('risk_score', 0)}")
    
    elif choice == "3":
        logger.export_to_csv()
    
    elif choice == "4":
        confirm = input("Tem a certeza que quer limpar o log? (yes/no): ").strip().lower()
        if confirm == 'yes':
            logger.clear_log(backup=True)
        else:
            print("Operação cancelada")
    
    elif choice == "5":
        print("Até breve!")
    
    else:
        print("Opção inválida!")


if __name__ == "__main__":
    main()
