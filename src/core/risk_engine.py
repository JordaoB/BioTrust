"""
BioTrust - Risk Engine (Motor de Risco Contextual)
===================================================
TecStorm '26 Hackathon Project

Este módulo analisa transações em tempo real e calcula um score de risco (0-100)
para decidir se a transação deve ser aprovada automaticamente ou requerer
verificação de liveness.

Sistema de Pontuação:
- 0-30:   Risco Baixo  → Aprovação Automática ✅
- 31-70:  Risco Médio  → Requer Liveness 🔍
- 71-100: Risco Alto   → Requer Liveness + Alerta 🚨

Fatores Analisados:
1. Valor da Transação (30%)
2. Localização Geográfica (25%)
3. Horário (20%)
4. Comportamento/Frequência (15%)
5. Tipo de Transação (10%)
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math


class RiskEngine:
    """Motor de análise de risco para transações de pagamento."""
    
    # Pesos dos fatores de risco (total = 100%)
    # MUITO AGRESSIVO: Valor + Localização são os fatores dominantes
    WEIGHT_AMOUNT = 0.50      # 50% - Valor é CRÍTICO!
    WEIGHT_LOCATION = 0.45    # 45% - Localização suspeita é CRÍTICA!
    WEIGHT_TIME = 0.03        # 3%
    WEIGHT_BEHAVIOR = 0.01    # 1%
    WEIGHT_TYPE = 0.01        # 1%
    
    # Thresholds de decisão
    THRESHOLD_LOW_RISK = 30
    THRESHOLD_HIGH_RISK = 70
    
    def __init__(self):
        """Inicializa o motor de risco."""
        self.transaction_history = []
        
    def analyze_transaction(self, transaction: Dict) -> Dict:
        """
        Analisa uma transação e retorna o score de risco com decisão.
        
        Args:
            transaction: Dicionário com dados da transação:
                - amount: float (valor em €)
                - location: dict {city: str, country: str, lat: float, lon: float}
                - timestamp: datetime (hora da transação)
                - transaction_type: str (online, presencial, transferencia)
                - user_profile: dict (histórico do utilizador)
                
        Returns:
            Dict com:
                - risk_score: int (0-100)
                - decision: str (approve, require_liveness, block)
                - factors: dict (breakdown por fator)
                - reason: str (explicação)
        """
        # Calcular cada fator de risco
        amount_risk = self._calculate_amount_risk(
            transaction['amount'],
            transaction['user_profile']
        )
        
        location_risk = self._calculate_location_risk(
            transaction['location'],
            transaction['user_profile']
        )
        
        time_risk = self._calculate_time_risk(
            transaction.get('timestamp', datetime.now()),
            transaction['user_profile']
        )
        
        behavior_risk = self._calculate_behavior_risk(
            transaction['user_profile']
        )
        
        type_risk = self._calculate_type_risk(
            transaction.get('transaction_type', 'online')
        )
        
        # Calcular score total (média ponderada)
        base_score = (
            amount_risk * self.WEIGHT_AMOUNT +
            location_risk * self.WEIGHT_LOCATION +
            time_risk * self.WEIGHT_TIME +
            behavior_risk * self.WEIGHT_BEHAVIOR +
            type_risk * self.WEIGHT_TYPE
        )
        
        # AMPLIFICADOR DE RISCO: Se AMBOS amount e location são altos, multiplica o risco
        # Cenário: €5000 a 500km+ = EXTREMAMENTE SUSPEITO
        if amount_risk >= 80 and location_risk >= 80:
            # Ambos fatores críticos altos = amplifica para quase 100%
            base_score = min(base_score * 1.15, 100)  # +15% boost
        elif amount_risk >= 70 and location_risk >= 70:
            # Ambos fatores altos = amplifica moderadamente
            base_score = min(base_score * 1.10, 100)  # +10% boost
        
        risk_score = int(base_score)
        
        # Tomar decisão baseada no score
        decision, reason = self._make_decision(risk_score, {
            'amount_risk': amount_risk,
            'location_risk': location_risk,
            'time_risk': time_risk,
            'behavior_risk': behavior_risk,
            'type_risk': type_risk
        })
        
        # Adicionar à história (para análise comportamental futura)
        self.transaction_history.append({
            'transaction': transaction,
            'risk_score': risk_score,
            'decision': decision,
            'timestamp': datetime.now()
        })
        
        return {
            'risk_score': risk_score,
            'decision': decision,
            'reason': reason,
            'factors': {
                'amount': amount_risk,
                'location': location_risk,
                'time': time_risk,
                'behavior': behavior_risk,
                'type': type_risk
            },
            'breakdown': {
                'amount': f"{amount_risk * self.WEIGHT_AMOUNT:.1f} pts",
                'location': f"{location_risk * self.WEIGHT_LOCATION:.1f} pts",
                'time': f"{time_risk * self.WEIGHT_TIME:.1f} pts",
                'behavior': f"{behavior_risk * self.WEIGHT_BEHAVIOR:.1f} pts",
                'type': f"{type_risk * self.WEIGHT_TYPE:.1f} pts"
            }
        }
    
    def _calculate_amount_risk(self, amount: float, user_profile: Dict) -> float:
        """
        Calcula risco baseado no valor da transação.
        
        Score 0-100:
        - Valor baixo comparado com média do utilizador: score baixo
        - Valor muito acima da média: score alto
        """
        avg_amount = user_profile.get('average_transaction', 50)
        max_amount = user_profile.get('max_transaction', 200)
        
        # Ratio em relação à média
        ratio = amount / avg_amount if avg_amount > 0 else 1
        
        # Calcular score baseado no ratio (mais agressivo)
        if ratio <= 1.0:
            # Transação menor ou igual à média
            score = 10
        elif ratio <= 2.0:
            # Até 2x a média
            score = 20 + (ratio - 1.0) * 20
        elif ratio <= 5.0:
            # 2x a 5x a média
            score = 40 + (ratio - 2.0) * 20  # Aumentado de 15 para 20
        elif ratio <= 10.0:
            # 5x a 10x a média - MUITO SUSPEITO
            score = 85 + (ratio - 5.0) * 3
        else:
            # Mais de 10x a média - EXTREMAMENTE SUSPEITO
            score = 100
        
        # Valores absolutos altos - MUITO AGRESSIVO
        if amount > 500:
            score = max(score, 60)   # €500+ já é suspeito
        if amount > 1000:
            score = max(score, 75)   # €1000+ muito suspeito
        if amount > 2500:
            score = max(score, 85)   # €2500+ extremamente suspeito
        if amount > 5000:
            score = max(score, 95)   # €5000+ = MÁXIMO RISCO
            
        return min(score, 100)
    
    def _calculate_location_risk(self, location: Dict, user_profile: Dict) -> float:
        """
        Calcula risco baseado na localização geográfica.
        
        Fatores:
        - Distância da localização habitual
        - País diferente
        - Velocidade impossível (2 transações muito distantes em pouco tempo)
        """
        home_location = user_profile.get('home_location', {})
        last_location = user_profile.get('last_transaction_location', {})
        
        score = 0
        
        # Verificar país
        if location.get('country') != home_location.get('country'):
            score += 40  # País diferente = risco significativo
        
        # Calcular distância da localização habitual
        if 'lat' in location and 'lat' in home_location:
            distance_km = self._haversine_distance(
                location['lat'], location['lon'],
                home_location['lat'], home_location['lon']
            )
            
            # Escala EXTREMAMENTE agressiva para distâncias suspeitas
            if distance_km > 500:
                score += 100  # Muito longe = MÁXIMO RISCO
            elif distance_km > 300:
                score += 90   # >300km = quase máximo
            elif distance_km > 200:
                score += 80   # >200km = muito suspeito
            elif distance_km > 100:
                score += 60   # >100km = suspeito
            elif distance_km > 50:
                score += 35   # Cidade vizinha
            elif distance_km > 20:
                score += 15   # Proximidade
            # < 20km: 0 pontos (local)
        
        # Verificar cidade
        elif location.get('city') != home_location.get('city'):
            score += 30
        
        return min(score, 100)
    
    def _calculate_time_risk(self, timestamp: datetime, user_profile: Dict) -> float:
        """
        Calcula risco baseado no horário da transação.
        
        Fatores:
        - Horário (madrugada = mais suspeito)
        - Frequência de transações (muitas em pouco tempo)
        """
        score = 0
        hour = timestamp.hour
        
        # Análise do horário
        if 2 <= hour <= 6:
            # Madrugada (2h-6h)
            score += 40
        elif 22 <= hour or hour <= 1:
            # Noite tardia
            score += 20
        elif 6 <= hour <= 9 or 18 <= hour <= 22:
            # Manhã cedo ou noite
            score += 5
        else:
            # Horário normal (9h-18h)
            score += 0
        
        # Frequência: verificar quantas transações hoje
        transactions_today = user_profile.get('transactions_today', 0)
        if transactions_today > 10:
            score += 30
        elif transactions_today > 5:
            score += 15
        elif transactions_today > 3:
            score += 5
        
        return min(score, 100)
    
    def _calculate_behavior_risk(self, user_profile: Dict) -> float:
        """
        Calcula risco baseado no comportamento do utilizador.
        
        Fatores:
        - Conta nova vs. antiga
        - Padrão de uso consistente
        - Número de transações falhadas recentemente
        """
        score = 0
        
        # Idade da conta
        account_age_days = user_profile.get('account_age_days', 0)
        if account_age_days < 7:
            score += 40  # Conta muito nova
        elif account_age_days < 30:
            score += 20
        elif account_age_days < 90:
            score += 10
        
        # Transações falhadas recentemente
        failed_transactions = user_profile.get('failed_transactions_last_week', 0)
        if failed_transactions > 3:
            score += 30
        elif failed_transactions > 1:
            score += 15
        
        # Primeira transação do dia
        if user_profile.get('transactions_today', 0) == 0:
            score += 5
        
        return min(score, 100)
    
    def _calculate_type_risk(self, transaction_type: str) -> float:
        """
        Calcula risco baseado no tipo de transação.
        
        Tipos:
        - presencial: menor risco (PIN + cartão físico)
        - online: risco médio
        - transferencia: risco maior (mais difícil de reverter)
        """
        risk_by_type = {
            'presencial': 10,
            'online': 40,
            'transferencia': 60,
            'internacional': 70,
            'criptomoeda': 80
        }
        
        return risk_by_type.get(transaction_type.lower(), 40)
    
    def _make_decision(self, risk_score: int, factors: Dict) -> tuple:
        """
        Toma decisão baseada no score de risco.
        
        Returns:
            (decision, reason) - decisão e explicação
        """
        if risk_score < self.THRESHOLD_LOW_RISK:
            return ('approve', 'Transação de baixo risco - aprovada automaticamente')
        
        elif risk_score < self.THRESHOLD_HIGH_RISK:
            # Identificar fator dominante
            dominant_factor = max(factors, key=factors.get)
            return (
                'require_liveness',
                f'Risco médio detectado (fator: {dominant_factor}) - verificação de liveness necessária'
            )
        
        else:
            # Identificar fatores críticos
            critical_factors = [k for k, v in factors.items() if v > 70]
            factors_str = ', '.join(critical_factors) if critical_factors else 'múltiplos'
            return (
                'require_liveness',
                f'Risco alto detectado ({factors_str}) - verificação de liveness obrigatória'
            )
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula distância entre duas coordenadas GPS usando fórmula de Haversine.
        
        Returns:
            Distância em quilómetros
        """
        R = 6371  # Raio da Terra em km
        
        # Converter para radianos
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Fórmula de Haversine
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def get_statistics(self) -> Dict:
        """
        Retorna estatísticas das transações analisadas.
        """
        if not self.transaction_history:
            return {
                'total_transactions': 0,
                'approved': 0,
                'require_liveness': 0,
                'average_risk_score': 0
            }
        
        total = len(self.transaction_history)
        approved = sum(1 for t in self.transaction_history if t['decision'] == 'approve')
        require_liveness = sum(1 for t in self.transaction_history if t['decision'] == 'require_liveness')
        avg_score = sum(t['risk_score'] for t in self.transaction_history) / total
        
        return {
            'total_transactions': total,
            'approved': approved,
            'require_liveness': require_liveness,
            'blocked': total - approved - require_liveness,
            'average_risk_score': round(avg_score, 2),
            'approval_rate': f"{(approved / total * 100):.1f}%"
        }
