"""
BioTrust - Risk Engine V2 (Motor de Risco Fintech-Grade)
=========================================================
TecStorm '26 Hackathon Project

Motor de risco rigoroso baseado em lógicas de Fintech real (Revolut, SIBS).
Cruza biometria comportamental com limites estritos para detetar fraude.

Sistema de Pontuação:
- 0-35:   Risco Baixo   → Aprovação Automática ✅
- 36-74:  Risco Médio   → Requer Liveness 🔍
- 75-100: Risco Alto    → Requer Liveness + Bloqueio se falhar 🚨

Fatores Analisados (Pesos):
1. Distância/Localização (30%) - Impossible Travel Detection
2. Montante (25%) - Amount vs Historical Average
3. Frequência/Velocity (20%) - Rapid Transaction Checks
4. Destinatário/Comerciante (15%) - Trust Level
5. Horário (10%) - Time-of-Day Risk
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math


class RiskEngine:
    """Motor de análise de risco Fintech-grade para transações."""
    
    # ========== PESOS DOS FATORES (TOTAL = 100%) ==========
    WEIGHT_LOCATION = 0.30      # 30% - Impossible Travel é CRÍTICO
    WEIGHT_AMOUNT = 0.25        # 25% - Montantes anómalos
    WEIGHT_VELOCITY = 0.20      # 20% - Frequência de transações
    WEIGHT_RECIPIENT = 0.15     # 15% - Confiança no destinatário
    WEIGHT_TIME = 0.10          # 10% - Horário da transação
    
    # ========== THRESHOLDS DE DECISÃO (MUITO MAIS RIGOROSOS) ==========
    THRESHOLD_LOW_RISK = 25     # 0-25: Aprovação direta (reduzido de 35)
    THRESHOLD_HIGH_RISK = 60    # 60-100: Alto risco + bloqueio (reduzido de 75)
    
    # ========== CONSTANTES DE RISCO ==========
    IMPOSSIBLE_TRAVEL_DISTANCE = 100  # km - Distância suspeita em curto tempo
    IMPOSSIBLE_TRAVEL_TIME_MINUTES = 30  # minutos - Janela de tempo para impossible travel
    HIGH_AMOUNT_THRESHOLD = 500       # €500+ = Agravamento forte
    MEDIUM_AMOUNT_THRESHOLD = 300     # €300+ = Agravamento médio
    LOW_AMOUNT_THRESHOLD = 100        # €100+ = Atenção
    SMALL_AMOUNT_THRESHOLD = 20       # €20- = Risco muito baixo
    RAPID_TX_COUNT_2H = 3             # 3+ transações em 2h = Risco
    RAPID_TX_COUNT_1H = 2             # 2+ transações em 1h = Risco elevado
    RAPID_TX_WINDOW_HOURS = 2         # Janela de tempo para velocity check
    SAME_RECIPIENT_LIMIT_HIGH = 3     # 3+ envios para mesmo destinatário em 1h = Risco alto
    SAME_RECIPIENT_LIMIT_MED = 2      # 2+ envios para mesmo destinatário em 1h = Risco médio
    SAME_RECIPIENT_WINDOW_HOURS = 1   # Janela de tempo para mesmo destinatário
    NIGHT_START_HOUR = 2              # 02:00
    NIGHT_END_HOUR = 6                # 06:00
    LATE_NIGHT_START = 22             # 22:00
    EARLY_MORNING_END = 8             # 08:00
    
    def __init__(self):
        """Inicializa o motor de risco."""
        self.transaction_history = []
        
    def analyze_transaction(self, transaction: Dict) -> Dict:
        """
        Analisa uma transação e retorna o score de risco com decisão.
        
        Args:
            transaction: Dicionário com dados da transação:
                - amount: float (valor em €)
                - location: dict {city, country, lat, lon}
                - timestamp: datetime
                - transaction_type: str
                - user_profile: dict com:
                  - average_transaction: float
                  - total_sent: float
                  - transactions_today: int
                  - home_location: dict {lat, lon, city, country}
                  - last_transaction_location: dict {lat, lon}
                  - last_transaction_time: datetime
                  - recent_transactions: list
                  - recipient_history: dict {email: count}
                  - merchant_history: dict {id: count}
                
        Returns:
            Dict com:
                - risk_score: int (0-100)
                - risk_level: str (low/medium/high)
                - liveness_required: bool
                - decision: str (approve/require_liveness/alert)
                - factors: dict (breakdown detalhado)
                - reason: str (explicação)
        """
        user_profile = transaction.get('user_profile', {})
        
        # ========== 1. FATOR LOCALIZAÇÃO (30%) ==========
        location_risk, location_reason = self._calculate_location_risk(
            transaction['location'],
            user_profile
        )
        
        # ========== 2. FATOR MONTANTE (25%) ==========
        amount_risk, amount_reason = self._calculate_amount_risk(
            transaction['amount'],
            user_profile
        )
        
        # ========== 3. FATOR VELOCIDADE/FREQUÊNCIA (20%) ==========
        velocity_risk, velocity_reason = self._calculate_velocity_risk(
            transaction,
            user_profile
        )
        
        # ========== 4. FATOR DESTINATÁRIO/COMERCIANTE (15%) ==========
        recipient_risk, recipient_reason = self._calculate_recipient_risk(
            transaction,
            user_profile
        )
        
        # ========== 5. FATOR HORÁRIO (10%) ==========
        time_risk, time_reason = self._calculate_time_risk(
            transaction.get('timestamp', datetime.utcnow())
        )
        
        # ========== CÁLCULO DO SCORE FINAL ==========
        risk_score = int(
            location_risk * self.WEIGHT_LOCATION +
            amount_risk * self.WEIGHT_AMOUNT +
            velocity_risk * self.WEIGHT_VELOCITY +
            recipient_risk * self.WEIGHT_RECIPIENT +
            time_risk * self.WEIGHT_TIME
        )
        
        # Garantir que está no range [0, 100]
        risk_score = max(0, min(100, risk_score))
        
        # ========== DECISÃO FINAL ==========
        if risk_score <= self.THRESHOLD_LOW_RISK:
            risk_level = "low"
            decision = "approve"
            liveness_required = False
            reason = "Low risk - Automatic approval"
        elif risk_score < self.THRESHOLD_HIGH_RISK:
            risk_level = "medium"
            decision = "require_liveness"
            liveness_required = True
            reason = "Medium risk - Biometric verification required"
        else:
            risk_level = "high"
            decision = "require_liveness"
            liveness_required = True
            reason = f"High risk - Biometric verification required. {location_reason} {amount_reason} {velocity_reason}"
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'liveness_required': liveness_required,
            'decision': decision,
            'reason': reason,
            'factors': {
                'location': {
                    'score': location_risk,
                    'weight': self.WEIGHT_LOCATION,
                    'contribution': location_risk * self.WEIGHT_LOCATION,
                    'reason': location_reason
                },
                'amount': {
                    'score': amount_risk,
                    'weight': self.WEIGHT_AMOUNT,
                    'contribution': amount_risk * self.WEIGHT_AMOUNT,
                    'reason': amount_reason
                },
                'velocity': {
                    'score': velocity_risk,
                    'weight': self.WEIGHT_VELOCITY,
                    'contribution': velocity_risk * self.WEIGHT_VELOCITY,
                    'reason': velocity_reason
                },
                'recipient': {
                    'score': recipient_risk,
                    'weight': self.WEIGHT_RECIPIENT,
                    'contribution': recipient_risk * self.WEIGHT_RECIPIENT,
                    'reason': recipient_reason
                },
                'time': {
                    'score': time_risk,
                    'weight': self.WEIGHT_TIME,
                    'contribution': time_risk * self.WEIGHT_TIME,
                    'reason': time_reason
                }
            }
        }
    
    def _calculate_location_risk(self, location: Dict, user_profile: Dict) -> tuple:
        """
        Fator 1: Distância/Localização (30%)
        
        Regras:
        - Impossible Travel (>100km em <30 min) = 100 pontos
        - Fora do país habitual = +40 pontos base
        - Distância elevada de casa = Escala progressiva
        """
        risk = 0
        reasons = []
        
        home_location = user_profile.get('home_location', {})
        last_location = user_profile.get('last_transaction_location', home_location)
        last_tx_time = user_profile.get('last_transaction_time')
        
        # Calcular distância de casa
        distance_from_home = self._haversine_distance(
            home_location.get('lat', 0),
            home_location.get('lon', 0),
            location.get('lat', 0),
            location.get('lon', 0)
        )
        
        # IMPOSSIBLE TRAVEL CHECK
        if last_tx_time and last_location:
            time_diff = (datetime.utcnow() - last_tx_time).total_seconds() / 60  # minutos
            distance_from_last = self._haversine_distance(
                last_location.get('lat', 0),
                last_location.get('lon', 0),
                location.get('lat', 0),
                location.get('lon', 0)
            )
            
            if time_diff < self.IMPOSSIBLE_TRAVEL_TIME_MINUTES and distance_from_last > self.IMPOSSIBLE_TRAVEL_DISTANCE:
                risk = 100
                reasons.append(f"IMPOSSIBLE TRAVEL: {distance_from_last:.0f}km em {time_diff:.0f}min")
                return risk, " | ".join(reasons)
        
        # PAÍS DIFERENTE (MUITO MAIS RIGOROSO)
        home_country = home_location.get('country', 'Portugal')
        current_country = location.get('country', home_country)
        if current_country != home_country:
            risk += 60  # Aumentado de 40 para 60
            reasons.append(f"Fora do país habitual ({home_country} → {current_country})")
        
        # DISTÂNCIA DE CASA (escala MUITO mais rigorosa)
        if distance_from_home < 10:
            risk += 0
        elif distance_from_home < 50:
            risk += 15  # Aumentado de 10 para 15
        elif distance_from_home < 150:
            risk += 35  # Aumentado de 25 para 35
        elif distance_from_home < 300:
            risk += 55  # Aumentado de 45 para 55
        else:
            risk += 75  # Aumentado de 65 para 75
            reasons.append(f"Muito longe de casa ({distance_from_home:.0f}km)")
        
        if not reasons:
            reasons.append(f"Localização normal ({distance_from_home:.0f}km de casa)")
        
        return min(risk, 100), " | ".join(reasons)
    
    def _calculate_amount_risk(self, amount: float, user_profile: Dict) -> tuple:
        """
        Fator 2: Montante (25%)
        
        Regras:
        - > 3x média histórica = Alto risco (60+ pontos)
        - > €500 = +25 pontos automáticos
        - < €20 = Risco baixo (10 pontos)
        """
        risk = 0
        reasons = []
        
        avg_transaction = user_profile.get('average_transaction', 50)
        
        # MONTANTES MUITO BAIXOS (seguros)
        if amount < self.SMALL_AMOUNT_THRESHOLD:
            risk = 10
            reasons.append(f"Montante baixo (€{amount:.2f})")
            return risk, " | ".join(reasons)
        
        # ESCALAS DE MONTANTES (MUITO MAIS RIGOROSAS)
        if amount >= 1000:
            risk += 80  # €1000+ = Risco altíssimo
            reasons.append(f"Montante MUITO elevado (€{amount:.2f})")
        elif amount >= self.HIGH_AMOUNT_THRESHOLD:  # €500+
            risk += 60  # Aumentado de 25 para 60
            reasons.append(f"Montante elevado (€{amount:.2f})")
        elif amount >= self.MEDIUM_AMOUNT_THRESHOLD:  # €300+
            risk += 40  # Novo threshold
            reasons.append(f"Montante médio-alto (€{amount:.2f})")
        elif amount >= self.LOW_AMOUNT_THRESHOLD:  # €100+
            risk += 20  # Novo threshold
            reasons.append(f"Montante médio (€{amount:.2f})")
        
        # COMPARAÇÃO COM MÉDIA HISTÓRICA (MUITO MAIS RIGOROSA)
        if avg_transaction > 0:
            ratio = amount / avg_transaction
            
            if ratio <= 1.0:
                pass  # Dentro da média - não adicionar risco
            elif ratio <= 1.5:
                risk += 15  # Ligeiramente acima
            elif ratio <= 2.0:
                risk += 30  # Aumentado de 15 para 30
            elif ratio <= 3.0:
                risk += 50  # Aumentado de 35 para 50
                reasons.append(f"Muito acima da média (€{amount:.2f} vs €{avg_transaction:.2f})")
            elif ratio <= 5.0:
                risk += 70  # Aumentado de 60 para 70
                reasons.append(f"MUITO acima da média (€{amount:.2f} vs €{avg_transaction:.2f})")
            else:
                risk += 90  # Aumentado de 80 para 90
                reasons.append(f"EXTREMAMENTE acima da média (€{amount:.2f} vs €{avg_transaction:.2f})")
        else:
            # Sem histórico - MUITO MAIS RIGOROSO
            if amount > 500:
                risk += 70
                reasons.append("Sem histórico + montante MUITO elevado")
            elif amount > 200:
                risk += 50  # Aumentado de 40 para 50
                reasons.append("Sem histórico + montante elevado")
            elif amount > 100:
                risk += 30
                reasons.append("Sem histórico + montante médio")
        
        if not reasons:
            reasons.append(f"Montante normal (€{amount:.2f})")
        
        return min(risk, 100), " | ".join(reasons)
    
    def _calculate_velocity_risk(self, transaction: Dict, user_profile: Dict) -> tuple:
        """
        Fator 3: Frequência/Velocity (20%)
        
        Regras:
        - Regra de Pânico: >3 transações em 2h = +30 pontos
        - 3+ envios para mesmo destinatário em 1h = +40 pontos (padrão de roubo)
        """
        risk = 0
        reasons = []
        
        recent_transactions = user_profile.get('recent_transactions', [])
        
        # CONTAGEM DE TRANSAÇÕES RECENTES (MUITO MAIS RIGOROSO)
        now = datetime.utcnow()
        cutoff_1h = now - timedelta(hours=1)
        cutoff_2h = now - timedelta(hours=self.RAPID_TX_WINDOW_HOURS)
        
        recent_1h = [tx for tx in recent_transactions if tx.get('created_at', now) > cutoff_1h]
        recent_2h = [tx for tx in recent_transactions if tx.get('created_at', now) > cutoff_2h]
        tx_count_1h = len(recent_1h)
        tx_count_2h = len(recent_2h)
        
        # Verificação em 1 hora (NOVO)
        if tx_count_1h >= 2:
            risk += 40  # 2+ TX em 1h = Risco alto
            reasons.append(f"VELOCIDADE MUITO ALTA: {tx_count_1h} transações em 1h")
        
        # Verificação em 2 horas (MAIS RIGOROSO)
        if tx_count_2h >= 4:
            risk += 60  # 4+ TX em 2h = Risco altíssimo
            reasons.append(f"VELOCIDADE EXTREMA: {tx_count_2h} transações em 2h")
        elif tx_count_2h >= self.RAPID_TX_COUNT_2H:
            risk += 40  # Aumentado de 30 para 40
            reasons.append(f"VELOCIDADE ALTA: {tx_count_2h} transações em 2h")
        
        # ENVIOS PARA MESMO DESTINATÁRIO (última 1 hora) - MUITO MAIS RIGOROSO
        recipient_email = transaction.get('recipient_email')
        if recipient_email:
            same_recipient_cutoff = now - timedelta(hours=self.SAME_RECIPIENT_WINDOW_HOURS)
            same_recipient_count = sum(
                1 for tx in recent_transactions
                if tx.get('recipient_email') == recipient_email and tx.get('created_at', now) > same_recipient_cutoff
            )
            
            if same_recipient_count >= self.SAME_RECIPIENT_LIMIT_HIGH:  # 3+
                risk += 50  # Aumentado de 40 para 50
                reasons.append(f"PADRÃO MUITO SUSPEITO: {same_recipient_count}ª transação para {recipient_email} em 1h")
            elif same_recipient_count >= self.SAME_RECIPIENT_LIMIT_MED:  # 2+
                risk += 30  # Novo threshold
                reasons.append(f"PADRÃO SUSPEITO: {same_recipient_count}ª transação para {recipient_email} em 1h")
        
        if not reasons:
            reasons.append("Frequência normal")
        
        return min(risk, 100), " | ".join(reasons)
    
    def _calculate_recipient_risk(self, transaction: Dict, user_profile: Dict) -> tuple:
        """
        Fator 4: Destinatário/Comerciante (15%)
        
        Regras (MUITO MAIS RIGOROSAS):
        - Primeira vez = 80 pontos (Risco ALTO)
        - 1-3 vezes = 60 pontos
        - 4-5 vezes = 40 pontos
        - 6-10 vezes = 20 pontos
        - 10+ vezes = 10 pontos (Confiança)
        """
        risk = 0
        reasons = []
        
        recipient_email = transaction.get('recipient_email')
        merchant_id = transaction.get('merchant_id')
        
        recipient_history = user_profile.get('recipient_history', {})
        merchant_history = user_profile.get('merchant_history', {})
        
        if recipient_email:
            count = recipient_history.get(recipient_email, 0)
            
            if count == 0:
                risk = 80  # MUITO AUMENTADO (era 50+20=70)
                reasons.append("Novo destinatário (1ª vez) - RISCO ALTO")
            elif count <= 3:
                risk = 60  # Novo threshold
                reasons.append(f"Destinatário pouco conhecido ({count}x)")
            elif count <= 5:
                risk = 40  # Novo threshold
                reasons.append(f"Destinatário conhecido ({count}x)")
            elif count <= 10:
                risk = 20  # Novo threshold
                reasons.append(f"Destinatário frequente ({count}x)")
            else:
                risk = 10  # Confiança (era 50-15=35)
                reasons.append(f"Contacto de confiança ({count}x anteriores)")
        
        elif merchant_id:
            count = merchant_history.get(merchant_id, 0)
            
            if count == 0:
                risk = 70  # Aumentado de 50+15=65
                reasons.append("Novo comerciante (1ª vez) - RISCO ALTO")
            elif count <= 3:
                risk = 50
                reasons.append(f"Comerciante pouco conhecido ({count}x)")
            elif count <= 5:
                risk = 35
                reasons.append(f"Comerciante conhecido ({count}x)")
            elif count <= 10:
                risk = 20
                reasons.append(f"Comerciante frequente ({count}x)")
            else:
                risk = 10
                reasons.append(f"Comerciante de confiança ({count}x)")
        else:
            risk = 50  # Sem destinatário = Risco médio
            reasons.append("Sem destinatário específico")
        
        return max(0, min(risk, 100)), " | ".join(reasons)
    
    def _calculate_time_risk(self, timestamp: datetime) -> tuple:
        """
        Fator 5: Horário (10%)
        
        Regras (MUITO MAIS RIGOROSAS):
        - Madrugada (02:00-06:00) = 60 pontos (Risco ALTO)
        - Noite/Madrugada (22:00-02:00) = 30 pontos
        - Manhã Cedo (06:00-08:00) = 20 pontos
        - Horário Normal = 0 pontos
        """
        risk = 0
        reasons = []
        
        hour = timestamp.hour
        
        if self.NIGHT_START_HOUR <= hour < self.NIGHT_END_HOUR:  # 02:00-06:00
            risk = 60  # MUITO AUMENTADO (era 20)
            reasons.append(f"MADRUGADA ({hour:02d}h) - RISCO MUITO ALTO")
        elif hour >= self.LATE_NIGHT_START or hour < self.NIGHT_START_HOUR:  # 22:00-02:00
            risk = 30  # Novo threshold
            reasons.append(f"Noite tardia ({hour:02d}h) - RISCO MÉDIO")
        elif self.NIGHT_END_HOUR <= hour < self.EARLY_MORNING_END:  # 06:00-08:00
            risk = 20  # Novo threshold
            reasons.append(f"Manhã muito cedo ({hour:02d}h) - RISCO BAIXO")
        else:
            risk = 0
            reasons.append(f"Horário normal ({hour:02d}h)")
        
        return risk, " | ".join(reasons)
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula distância entre dois pontos geográficos em km usando fórmula de Haversine.
        """
        R = 6371  # Raio da Terra em km
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
