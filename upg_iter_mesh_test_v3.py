"""
BioTrust - Active Liveness Detection Module
============================================
TecStorm '26 Hackathon Project

Este módulo implementa a deteção de vida ativa (Active Liveness) usando 
reconhecimento facial através de webcam, sem hardware adicional.

Funcionalidade:
- Fase 0: Deteção de 3 piscadelas consecutivas (EAR - Eye Aspect Ratio)
- Fase 1: Rotação da cabeça para a esquerda e retorno ao centro
- Fase 2: Rotação da cabeça para a direita e retorno ao centro
- Fase 3: Confirmação de liveness (utilizador é humano vivo)

Tecnologias: OpenCV, MediaPipe Face Mesh, NumPy, SciPy
"""

import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance as dist

# ============================================================================
# CONFIGURAÇÕES E CONSTANTES
# ============================================================================

# Limiar para detetar se os olhos estão fechados (Eye Aspect Ratio)
# Valores menores que 0.18 indicam que os olhos estão fechados
EAR_THRESHOLD = 0.18

# Número mínimo de frames consecutivos com olhos fechados para contar como piscadela
CONSEC_FRAMES = 2

# Número de piscadelas necessárias para passar da Fase 0
REQUIRED_BLINKS = 3

# ============================================================================
# VARIÁVEIS DE ESTADO DO SISTEMA
# ============================================================================

blink_frame_counter = 0      # Contador de frames com olhos fechados
blink_total = 0              # Total de piscadelas detetadas
must_return_center = False   # Flag: utilizador deve voltar ao centro?

current_step = 0             # Fase atual: 0=piscar, 1=esquerda, 2=direita, 3=concluído
liveness_verified = False    # Flag: liveness foi confirmado?

prev_eye_midpoint = None     # Posição anterior dos olhos (para detetar movimento)

# ============================================================================
# INICIALIZAÇÃO DO MEDIAPIPE FACE MESH
# ============================================================================

# MediaPipe é uma biblioteca do Google que deteta 468 pontos faciais (landmarks)
mp_face_mesh = mp.solutions.face_mesh

# Configuração do Face Mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,                    # Apenas 1 rosto por vez
    refine_landmarks=True,              # Melhor precisão nos olhos e lábios
    min_detection_confidence=0.5,       # Confiança mínima para detetar rosto
    min_tracking_confidence=0.5         # Confiança mínima para rastrear rosto
)

# Índices dos landmarks (pontos) que formam os olhos no MediaPipe Face Mesh
# Estes índices correspondem a pontos específicos ao redor dos olhos
LEFT_EYE = [362, 385, 387, 263, 373, 380]   # 6 pontos do olho esquerdo
RIGHT_EYE = [33, 160, 158, 133, 153, 144]   # 6 pontos do olho direito

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def calculate_ear(eye_landmarks):
    """
    Calcula o Eye Aspect Ratio (EAR) - razão de aspeto do olho.
    
    O EAR mede o quão aberto está o olho baseado nas distâncias verticais
    e horizontais entre os pontos dos olhos.
    
    Fórmula: EAR = (|P2-P6| + |P3-P5|) / (2 * |P1-P4|)
    
    - Quando o olho está aberto: EAR ≈ 0.3
    - Quando o olho está fechado: EAR < 0.18
    
    Args:
        eye_landmarks: Array com 6 pontos [x,y] que definem o contorno do olho
        
    Returns:
        float: Valor do EAR (normalmente entre 0.1 e 0.4)
    """
    # Calcular distâncias verticais (altura do olho)
    A = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
    B = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
    
    # Calcular distância horizontal (largura do olho)
    C = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
    
    # Retornar a razão: média das alturas / largura
    return (A + B) / (2.0 * C)

# ============================================================================
# INICIALIZAÇÃO DA WEBCAM
# ============================================================================

# Abrir a webcam (índice 0 = câmara padrão do sistema)
cap = cv2.VideoCapture(0)

# Definir resolução da câmara para 640x480 (balance entre qualidade e performance)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Criar janela antes do loop (para melhor controlo)
WINDOW_NAME = "BioTrust - Sequential Liveness"
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

# Configurar janela para aparecer sempre no topo
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

# Posicionar janela num local visível (evita ficar escondida)
cv2.moveWindow(WINDOW_NAME, 300, 100)

# Definir tamanho da janela
cv2.resizeWindow(WINDOW_NAME, 800, 600)

# ============================================================================
# LOOP PRINCIPAL - PROCESSAMENTO DE VÍDEO FRAME A FRAME
# ============================================================================

while cap.isOpened():
    # Ler frame da webcam
    success, frame = cap.read()
    if not success:
        print("Erro ao capturar frame da webcam")
        break

    # Espelhar horizontalmente para efeito de espelho (mais intuitivo para o utilizador)
    frame = cv2.flip(frame, 1)
    
    # Converter de BGR (formato OpenCV) para RGB (formato MediaPipe)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Processar o frame com MediaPipe para detetar pontos faciais
    results = face_mesh.process(rgb)

    # ========================================================================
    # PROCESSAMENTO DO ROSTO (se foi detetado)
    # ========================================================================
    
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:

            # Obter dimensões do frame
            h, w, _ = frame.shape
            
            # Converter os 468 landmarks normalizados (0-1) para coordenadas de pixel
            mesh_points = np.array([
                [int(p.x * w), int(p.y * h)]
                for p in face_landmarks.landmark
            ])

            # ================================================================
            # ANÁLISE DOS OLHOS
            # ================================================================
            
            # Extrair os 6 pontos que formam cada olho
            left_eye = mesh_points[LEFT_EYE]
            right_eye = mesh_points[RIGHT_EYE]

            # Calcular o centro de cada olho (média das coordenadas)
            left_eye_center = np.mean(left_eye, axis=0)
            right_eye_center = np.mean(right_eye, axis=0)
            
            # Calcular o ponto médio entre os dois olhos
            eye_midpoint = (left_eye_center + right_eye_center) / 2

            # ================================================================
            # ANÁLISE DA ROTAÇÃO HORIZONTAL DA CABEÇA (YAW)
            # ================================================================
            
            # Ponto do nariz (landmark 1)
            nose = mesh_points[1]
            
            # Calcular distâncias do nariz até cada olho
            dist_left = np.linalg.norm(nose - left_eye_center)
            dist_right = np.linalg.norm(nose - right_eye_center)

            # Razão de simetria: se o rosto está centrado, esta razão ≈ 1.0
            # Se virar esquerda: razão > 1.0 (nariz mais perto do olho esquerdo)
            # Se virar direita: razão < 1.0 (nariz mais perto do olho direito)
            symmetry_ratio = dist_left / dist_right
            
            # Thresholds suaves - rosto considerado frontal (usado na Fase 0)
            face_yaw_ok = 0.85 < symmetry_ratio < 1.15

            # Thresholds fortes - rotações significativas (usado nas Fases 1 e 2)
            strong_left = symmetry_ratio > 2.05   # Cabeça muito virada para esquerda
            strong_right = symmetry_ratio < 0.45  # Cabeça muito virada para direita

            # ================================================================
            # ANÁLISE DA INCLINAÇÃO VERTICAL DA CABEÇA (PITCH)
            # ================================================================
            
            # Calcular posição relativa do nariz em relação aos olhos
            # Se o rosto está nivelado, o nariz fica ligeiramente abaixo dos olhos
            nose_eye_ratio = (nose[1] - eye_midpoint[1]) / h
            
            # Verificar se o rosto está numa inclinação aceitável
            face_pitch_ok = 0.02 < nose_eye_ratio < 0.12

            # ================================================================
            # DETEÇÃO DE MOVIMENTO EXCESSIVO
            # ================================================================
            
            # Calcular quanto o rosto se moveu desde o último frame
            if prev_eye_midpoint is not None:
                movement = np.linalg.norm(eye_midpoint - prev_eye_midpoint)
            else:
                movement = 0

            # Guardar posição atual para comparar no próximo frame
            prev_eye_midpoint = eye_midpoint
            
            # Movimento pequeno é aceitável, movimento grande não
            movement_ok = movement < 20

            # ================================================================
            # VERIFICAÇÃO: ROSTO ESTÁ FRONTAL?
            # ================================================================
            
            # Rosto frontal = centrado horizontalmente + inclinação vertical OK
            face_frontal = face_yaw_ok and face_pitch_ok

            # Se está na Fase 0 mas o rosto não está frontal, avisar
            if current_step == 0 and not face_frontal:
                cv2.putText(frame, "LOOK STRAIGHT AT CAMERA",
                            (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 0, 255),  # Vermelho
                            2)

            # ================================================================
            # CÁLCULO DO EAR (EYE ASPECT RATIO)
            # ================================================================
            
            # Calcular EAR para cada olho individualmente
            left_ear = calculate_ear(left_eye)
            right_ear = calculate_ear(right_eye)
            
            # Média dos dois olhos
            ear = (left_ear + right_ear) / 2

            # Verificar se ambos os olhos estão fechados
            both_eyes_closed = (
                left_ear < EAR_THRESHOLD and
                right_ear < EAR_THRESHOLD
            )

           # ================================================================
           # FASE 0: DETEÇÃO DE PISCADELAS (BLINK DETECTION)
           # ================================================================
           # 
           # Objetivo: O utilizador deve piscar REQUIRED_BLINKS vezes (3x)
           # Condições: Rosto deve estar frontal E sem movimento excessivo
           # Método: Contar quantos frames consecutivos os olhos ficam fechados
           #
            
            if current_step == 0 and face_frontal and movement_ok:

                if both_eyes_closed:
                    # Olhos fechados: incrementar contador de frames
                    blink_frame_counter += 1
                else:
                    # Olhos abertos: verificar se houve piscadela completa
                    if blink_frame_counter >= CONSEC_FRAMES:
                        blink_total += 1
                        print(f"✓ Piscadela {blink_total}/{REQUIRED_BLINKS} detetada!")
                    # Resetar contador
                    blink_frame_counter = 0

                # Verificar se já atingiu o número necessário de piscadelas
                if blink_total >= REQUIRED_BLINKS:
                    current_step = 1  # Avançar para Fase 1
                    blink_total = 0
                    blink_frame_counter = 0
                    print("✓ Fase 0 completa - Agora vire a cabeça para ESQUERDA")

            # ================================================================
            # FASE 1: ROTAÇÃO DA CABEÇA PARA A ESQUERDA
            # ================================================================
            # 
            # Objetivo: Virar cabeça para esquerda e depois voltar ao centro
            # Fluxo: Centro → Esquerda → Centro (para avançar)
            # Segurança: Se virar para o lado errado, reseta para Fase 0
            #
            
            if current_step == 1:

                if not must_return_center:
                    # Ainda não virou para esquerda
                    
                    if strong_left:
                        # Detetou rotação forte para esquerda!
                        must_return_center = True
                        print("✓ Esquerda detetada! Agora volte ao CENTRO")

                    elif strong_right:
                        # Virou para o lado errado (direita)
                        print("✗ Direção errada! Recomeçando...")
                        current_step = 0  # Reset para Fase 0
                        blink_total = 0

                else:
                    # Já virou para esquerda, aguarda retorno ao centro
                    
                    if face_yaw_ok:
                        # Voltou ao centro!
                        current_step = 2  # Avançar para Fase 2
                        must_return_center = False
                        print("✓ Fase 1 completa - Agora vire a cabeça para DIREITA")

            # ================================================================
            # FASE 2: ROTAÇÃO DA CABEÇA PARA A DIREITA
            # ================================================================
            # 
            # Objetivo: Virar cabeça para direita e depois voltar ao centro
            # Fluxo: Centro → Direita → Centro (para confirmar)
            # Segurança: Se virar para o lado errado, reseta para Fase 0
            #
            
            if current_step == 2:

                if not must_return_center:
                    # Ainda não virou para direita
                    
                    if strong_right:
                        # Detetou rotação forte para direita!
                        must_return_center = True
                        print("✓ Direita detetada! Agora volte ao CENTRO")

                    elif strong_left:
                        # Virou para o lado errado (esquerda)
                        print("✗ Direção errada! Recomeçando...")
                        current_step = 0  # Reset para Fase 0
                        blink_total = 0

                else:
                    # Já virou para direita, aguarda retorno ao centro
                    
                    if face_yaw_ok:
                        # Voltou ao centro!
                        current_step = 3  # Avançar para Fase 3 (Final)
                        must_return_center = False
                        print("✓✓✓ LIVENESS CONFIRMADO! ✓✓✓")

            # ================================================================
            # FASE 3: LIVENESS CONFIRMADO
            # ================================================================
            
            if current_step == 3:
                liveness_verified = True

            # ================================================================
            # INTERFACE DO UTILIZADOR (UI) - INSTRUÇÕES NA TELA
            # ================================================================
            
            if not liveness_verified:
                # Ainda não confirmou liveness - mostrar instruções

                # Determinar que texto mostrar baseado na fase atual
                if current_step == 0:
                    text = f"BLINK {REQUIRED_BLINKS} TIMES"

                elif current_step == 1:
                    text = "TURN HEAD LEFT"

                elif current_step == 2:
                    text = "TURN HEAD RIGHT"

                # Se deve voltar ao centro, substituir a mensagem
                if must_return_center:
                    text = "RETURN TO CENTER"

                # Desenhar o texto principal (amarelo)
                cv2.putText(frame,
                            text,
                            (50, 150),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (255, 255, 0),  # Amarelo (BGR)
                            2)
            else:
                # Liveness confirmado - mostrar mensagem de sucesso
                cv2.putText(frame,
                            "LIVENESS CONFIRMED",
                            (50, 150),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 255, 0),  # Verde (BGR)
                            3)

            # Mostrar o valor EAR ao vivo (útil para debug)
            cv2.putText(frame,
                        f"EAR: {ear:.2f}",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),  # Verde (BGR)
                        2)

    # ========================================================================
    # EXIBIR O FRAME NA JANELA
    # ========================================================================
    
    cv2.imshow(WINDOW_NAME, frame)
    
    # ========================================================================
    # VERIFICAR SE UTILIZADOR QUER SAIR
    # ========================================================================
    
    # Verificar se a janela ainda existe (deteta clique no X)
    try:
        window_property = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE)
        if window_property < 1:
            print("✓ Janela fechada pelo utilizador")
            break
    except:
        print("✓ Janela não existe mais")
        break
    
    # Verificar se pressionou ESC para sair
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # Código ASCII do ESC
        print("✓ ESC pressionado - Encerrando...")
        break

# ============================================================================
# LIMPEZA E ENCERRAMENTO
# ============================================================================

# Libertar a webcam
cap.release()

# Fechar todas as janelas do OpenCV
cv2.destroyAllWindows()

print("✓ Programa terminado com sucesso")
