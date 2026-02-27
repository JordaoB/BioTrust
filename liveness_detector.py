"""
BioTrust - Liveness Detector API Module
========================================
Versão API-friendly do Active Liveness Detection que retorna resultado programaticamente.
Baseado em upg_iter_mesh_test_v3.py mas adaptado para integração com outros sistemas.
"""

import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance as dist
import sys
import time  # Para dar tempo à janela aparecer

class LivenessDetector:
    """
    Classe para deteção de liveness que pode ser chamada programaticamente.
    Retorna True se liveness for confirmado, False caso contrário.
    """
    
    def __init__(self):
        # Configurações
        self.EAR_THRESHOLD = 0.18
        self.CONSEC_FRAMES = 2
        self.REQUIRED_BLINKS = 3
        
        # Estado
        self.blink_frame_counter = 0
        self.blink_total = 0
        self.must_return_center = False
        self.current_step = 0  # 0=blink, 1=left, 2=right, 3=done
        self.liveness_verified = False
        self.prev_eye_midpoint = None
        
        # MediaPipe
        mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Landmarks dos olhos
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        
        # Janela
        self.WINDOW_NAME = "BioTrust - Liveness Verification"
        
    def calculate_ear(self, eye_landmarks):
        """Calcula o Eye Aspect Ratio"""
        A = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
        B = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
        C = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
        return (A + B) / (2.0 * C)
    
    def verify(self, timeout_seconds=60):
        """
        Executa o processo de verificação de liveness.
        
        Args:
            timeout_seconds: Tempo máximo de espera (segundos)
            
        Returns:
            dict com resultado:
            {
                "success": True/False,
                "message": "Liveness confirmed" ou razão da falha,
                "blinks_detected": int,
                "head_movements": list
            }
        """
        # RESET DO ESTADO (importante para múltiplas chamadas)
        self.blink_frame_counter = 0
        self.blink_total = 0
        self.must_return_center = False
        self.current_step = 0
        self.liveness_verified = False
        self.prev_eye_midpoint = None
        
        print("🎥 Initializing camera...")
        
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not cap.isOpened():
            print("❌ ERROR: Could not open camera!")
            return {
                "success": False,
                "message": "Camera not accessible",
                "blinks_detected": 0,
                "head_movements": []
            }
        
        print("✓ Camera opened successfully")
        
        # Criar janela e configurar para aparecer sempre em cima
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        
        # Forçar janela a ficar sempre no topo (topmost)
        cv2.setWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
        
        # Posicionar janela no centro do ecrã (aproximadamente)
        cv2.moveWindow(self.WINDOW_NAME, 300, 100)
        
        # Definir tamanho fixo da janela
        cv2.resizeWindow(self.WINDOW_NAME, 800, 600)
        
        print("✓ Window created and positioned")
        print(f"⏱️  Timeout set to {timeout_seconds} seconds")
        print("👁️  Waiting for your face...\n")
        
        # Dar um pequeno delay para a janela aparecer antes de iniciar
        time.sleep(0.3)
        
        movements = []
        frame_count = 0
        max_frames = timeout_seconds * 30  # 30 fps aproximado
        
        print(f"🔄 Entering main loop (max {max_frames} frames / {timeout_seconds}s)")
        print(f"🔍 Initial state: step={self.current_step}, blinks={self.blink_total}, verified={self.liveness_verified}\n")
        
        try:
            while cap.isOpened() and frame_count < max_frames:
                success, frame = cap.read()
                if not success:
                    print(f"⚠️  Frame {frame_count}: Could not read from camera")
                    break
                
                frame_count += 1
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb)
                
                # Debug periodic (every 30 frames = ~1 second)
                if frame_count % 30 == 0:
                    print(f"📊 Frame {frame_count}: step={self.current_step}, blinks={self.blink_total}, verified={self.liveness_verified}")
                
                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        h, w, _ = frame.shape
                        mesh_points = np.array([
                            [int(p.x * w), int(p.y * h)]
                            for p in face_landmarks.landmark
                        ])
                        
                        # Análise dos olhos
                        left_eye = mesh_points[self.LEFT_EYE]
                        right_eye = mesh_points[self.RIGHT_EYE]
                        left_eye_center = np.mean(left_eye, axis=0)
                        right_eye_center = np.mean(right_eye, axis=0)
                        eye_midpoint = (left_eye_center + right_eye_center) / 2
                        
                        # Análise de rotação (Yaw)
                        nose = mesh_points[1]
                        dist_left = np.linalg.norm(nose - left_eye_center)
                        dist_right = np.linalg.norm(nose - right_eye_center)
                        symmetry_ratio = dist_left / dist_right
                        
                        face_yaw_ok = 0.85 < symmetry_ratio < 1.15
                        strong_left = symmetry_ratio > 2.05
                        strong_right = symmetry_ratio < 0.45
                        
                        # Análise de inclinação (Pitch)
                        nose_eye_ratio = (nose[1] - eye_midpoint[1]) / h
                        face_pitch_ok = 0.02 < nose_eye_ratio < 0.12
                        
                        # Movimento
                        if self.prev_eye_midpoint is not None:
                            movement = np.linalg.norm(eye_midpoint - self.prev_eye_midpoint)
                        else:
                            movement = 0
                        self.prev_eye_midpoint = eye_midpoint
                        movement_ok = movement < 20
                        
                        face_frontal = face_yaw_ok and face_pitch_ok
                        
                        # Avisos na tela
                        if self.current_step == 0 and not face_frontal:
                            cv2.putText(frame, "LOOK STRAIGHT AT CAMERA",
                                      (50, 200), cv2.FONT_HERSHEY_SIMPLEX,
                                      0.8, (0, 0, 255), 2)
                        
                        # Cálculo EAR
                        left_ear = self.calculate_ear(left_eye)
                        right_ear = self.calculate_ear(right_eye)
                        ear = (left_ear + right_ear) / 2
                        both_eyes_closed = (left_ear < self.EAR_THRESHOLD and 
                                          right_ear < self.EAR_THRESHOLD)
                        
                        # FASE 0: BLINK
                        if self.current_step == 0 and face_frontal and movement_ok:
                            if both_eyes_closed:
                                self.blink_frame_counter += 1
                            else:
                                if self.blink_frame_counter >= self.CONSEC_FRAMES:
                                    self.blink_total += 1
                                    print(f"✓ Blink {self.blink_total}/{self.REQUIRED_BLINKS}")
                                self.blink_frame_counter = 0
                            
                            if self.blink_total >= self.REQUIRED_BLINKS:
                                self.current_step = 1
                                print("✓ Blink phase complete - Turn LEFT")
                        
                        # FASE 1: LEFT
                        if self.current_step == 1:
                            if not self.must_return_center:
                                if strong_left:
                                    self.must_return_center = True
                                    movements.append("left")
                                    print("✓ Left detected - Return to CENTER")
                                elif strong_right:
                                    print("✗ Wrong direction - RESET")
                                    self.current_step = 0
                                    self.blink_total = 0
                            else:
                                if face_yaw_ok:
                                    self.current_step = 2
                                    self.must_return_center = False
                                    print("✓ Centered - Now turn RIGHT")
                        
                        # FASE 2: RIGHT
                        if self.current_step == 2:
                            if not self.must_return_center:
                                if strong_right:
                                    self.must_return_center = True
                                    movements.append("right")
                                    print("✓ Right detected - Return to CENTER")
                                elif strong_left:
                                    print("✗ Wrong direction - RESET")
                                    self.current_step = 0
                                    self.blink_total = 0
                            else:
                                if face_yaw_ok:
                                    self.current_step = 3
                                    self.must_return_center = False
                                    print("✓✓✓ LIVENESS CONFIRMED ✓✓✓")
                        
                        # FASE 3: CONFIRMED
                        if self.current_step == 3:
                            print(f"🎉 Setting liveness_verified=True at frame {frame_count}")
                            self.liveness_verified = True
                        
                        # UI
                        if not self.liveness_verified:
                            if self.current_step == 0:
                                text = f"BLINK {self.REQUIRED_BLINKS} TIMES"
                            elif self.current_step == 1:
                                text = "TURN HEAD LEFT"
                            elif self.current_step == 2:
                                text = "TURN HEAD RIGHT"
                            
                            if self.must_return_center:
                                text = "RETURN TO CENTER"
                            
                            cv2.putText(frame, text, (50, 150),
                                      cv2.FONT_HERSHEY_SIMPLEX,
                                      0.8, (255, 255, 0), 2)
                        else:
                            cv2.putText(frame, "LIVENESS CONFIRMED",
                                      (50, 150), cv2.FONT_HERSHEY_SIMPLEX,
                                      1, (0, 255, 0), 3)
                            cv2.putText(frame, "Press ESC to continue",
                                      (50, 200), cv2.FONT_HERSHEY_SIMPLEX,
                                      0.6, (255, 255, 255), 1)
                        
                        cv2.putText(frame, f"EAR: {ear:.2f}", (50, 50),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Mostrar frame
                cv2.imshow(self.WINDOW_NAME, frame)
                
                # Verificar se janela foi fechada
                try:
                    if cv2.getWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except:
                    break
                
                # Verificar teclas
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    break
                
                # Se confirmou liveness, esperar 2 segundos e sair
                if self.liveness_verified:
                    print(f"✅ Liveness verified at frame {frame_count}, waiting 2 seconds before exit...")
                    cv2.waitKey(2000)
                    break
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print(f"\n🔚 Loop ended. Frames processed: {frame_count}/{max_frames}")
            print(f"🔍 Final state: step={self.current_step}, blinks={self.blink_total}, verified={self.liveness_verified}\n")
        
        # Retornar resultado
        if self.liveness_verified:
            return {
                "success": True,
                "message": "Liveness confirmed successfully",
                "blinks_detected": self.REQUIRED_BLINKS,
                "head_movements": movements
            }
        elif frame_count >= max_frames:
            return {
                "success": False,
                "message": "Timeout - verification took too long",
                "blinks_detected": self.blink_total,
                "head_movements": movements
            }
        else:
            return {
                "success": False,
                "message": "Verification cancelled by user",
                "blinks_detected": self.blink_total,
                "head_movements": movements
            }


# Função auxiliar para usar de forma independente
def verify_liveness(timeout_seconds=60):
    """
    Função simples para verificar liveness.
    Retorna True se confirmado, False caso contrário.
    """
    detector = LivenessDetector()
    result = detector.verify(timeout_seconds)
    return result["success"]


if __name__ == "__main__":
    # Teste standalone
    print("=== BioTrust Liveness Detector ===")
    print("Iniciando verificação de liveness...\n")
    
    detector = LivenessDetector()
    result = detector.verify()
    
    print("\n" + "="*50)
    print("RESULTADO:")
    print(f"  Status: {'✓ APROVADO' if result['success'] else '✗ REJEITADO'}")
    print(f"  Mensagem: {result['message']}")
    print(f"  Piscadelas: {result['blinks_detected']}")
    print(f"  Movimentos: {', '.join(result['head_movements']) if result['head_movements'] else 'Nenhum'}")
    print("="*50)
    
    sys.exit(0 if result['success'] else 1)
