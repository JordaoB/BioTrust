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
from scipy import signal
from scipy.fft import fft, fftfreq
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
        
        # Estado - Active Liveness
        self.blink_frame_counter = 0
        self.blink_total = 0
        self.must_return_center = False
        self.current_step = 0  # 0=blink, 1=left, 2=right, 3=done
        self.liveness_verified = False
        self.prev_eye_midpoint = None
        
        # Estado - Passive Liveness (rPPG)
        self.green_values = []
        self.timestamps = []
        self.MIN_BPM = 45
        self.MAX_BPM = 180
        
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
    
    def _extract_forehead_green(self, frame, face_landmarks):
        """
        Extract mean green channel value from forehead ROI for rPPG.
        """
        h, w, _ = frame.shape
        forehead_indices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323]
        
        forehead_points = []
        for idx in forehead_indices:
            if idx < len(face_landmarks.landmark):
                landmark = face_landmarks.landmark[idx]
                x, y = int(landmark.x * w), int(landmark.y * h)
                forehead_points.append([x, y])
        
        if len(forehead_points) < 5:
            return None
        
        forehead_points = np.array(forehead_points, dtype=np.int32)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillConvexPoly(mask, forehead_points, 255)
        
        green_channel = frame[:, :, 1]
        mean_green = cv2.mean(green_channel, mask=mask)[0]
        
        return mean_green
    
    def _analyze_heart_rate(self, fps):
        """
        Analyze collected green signal to estimate heart rate.
        Returns (heart_rate_bpm, confidence, is_valid)
        """
        # Need at least 3 seconds of data for parallel mode, 5 for standalone
        min_samples = int(fps * 3)
        
        if len(self.green_values) < min_samples:
            return 0, 0.0, False
        
        # Detrend and filter
        green_signal = np.array(self.green_values)
        green_signal = signal.detrend(green_signal)
        
        # Bandpass filter (0.75-4.0 Hz = 45-240 BPM)
        nyquist = fps / 2.0
        low = 0.75 / nyquist
        high = 3.0 / nyquist
        b, a = signal.butter(4, [low, high], btype='band')
        filtered_signal = signal.filtfilt(b, a, green_signal)
        
        # FFT
        n = len(filtered_signal)
        fft_values = fft(filtered_signal)
        fft_freq = fftfreq(n, 1.0 / fps)
        
        positive_freq_idx = np.where(fft_freq > 0)
        fft_freq = fft_freq[positive_freq_idx]
        fft_magnitude = np.abs(fft_values[positive_freq_idx])
        
        valid_freq_mask = (fft_freq >= 0.75) & (fft_freq <= 3.0)
        valid_fft_freq = fft_freq[valid_freq_mask]
        valid_fft_magnitude = fft_magnitude[valid_freq_mask]
        
        if len(valid_fft_magnitude) == 0:
            return 0, 0.0, False
        
        peak_idx = np.argmax(valid_fft_magnitude)
        peak_freq = valid_fft_freq[peak_idx]
        heart_rate = peak_freq * 60.0
        
        mean_magnitude = np.mean(valid_fft_magnitude)
        peak_magnitude = valid_fft_magnitude[peak_idx]
        confidence = min(peak_magnitude / (mean_magnitude + 1e-6), 10.0) / 10.0
        
        # More lenient validation for parallel mode (20% confidence instead of 25%)
        is_valid = (self.MIN_BPM <= heart_rate <= self.MAX_BPM) and (confidence >= 0.20)
        
        return heart_rate, confidence, is_valid
    
    def verify(self, timeout_seconds=60, enable_passive=True):
        """
        Executa o processo de verificação de liveness.
        
        Args:
            timeout_seconds: Tempo máximo de espera (segundos)
            enable_passive: Se True, coleta dados de rPPG em paralelo
            
        Returns:
            dict com resultado:
            {
                "success": True/False,
                "message": "Liveness confirmed" ou razão da falha,
                "blinks_detected": int,
                "head_movements": list,
                "heart_rate": float (se enable_passive),
                "heart_rate_confidence": float (se enable_passive),
                "passive_liveness": bool (se enable_passive)
            }
        """
        # RESET DO ESTADO (importante para múltiplas chamadas)
        self.blink_frame_counter = 0
        self.blink_total = 0
        self.must_return_center = False
        self.current_step = 0
        self.liveness_verified = False
        self.prev_eye_midpoint = None
        self.green_values = []
        self.timestamps = []
        
        print("🎥 Initializing camera...")
        if enable_passive:
            print("🫀 Passive liveness (rPPG) enabled - analyzing heart rate in parallel...")
        
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
        
        # Criar janela e configurar para aparecer sempre em cima
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        
        # Forçar janela a ficar sempre no topo (topmost)
        cv2.setWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
        
        # Posicionar janela no centro do ecrã (aproximadamente)
        cv2.moveWindow(self.WINDOW_NAME, 300, 100)
        
        # Definir tamanho fixo da janela
        cv2.resizeWindow(self.WINDOW_NAME, 800, 600)
        
        # Dar um pequeno delay para a janela aparecer antes de iniciar
        time.sleep(0.3)
        
        movements = []
        frame_count = 0
        max_frames = timeout_seconds * 30  # 30 fps aproximado
        
        try:
            while cap.isOpened() and frame_count < max_frames:
                success, frame = cap.read()
                if not success:
                    break
                
                frame_count += 1
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb)
                
                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        h, w, _ = frame.shape
                        mesh_points = np.array([
                            [int(p.x * w), int(p.y * h)]
                            for p in face_landmarks.landmark
                        ])
                        
                        # Collect rPPG data in parallel (if enabled)
                        if enable_passive:
                            mean_green = self._extract_forehead_green(frame, face_landmarks)
                            if mean_green is not None:
                                self.green_values.append(mean_green)
                                elapsed = frame_count / 30.0  # approximate
                                self.timestamps.append(elapsed)
                        
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
                            self.liveness_verified = True
                        
                        # UI - Professional compact design
                        if not self.liveness_verified:
                            # Determine step info
                            if self.current_step == 0:
                                step_text = "Step 1/3"
                                instruction = f"Blink {self.REQUIRED_BLINKS - self.blink_total}x"
                                color = (60, 220, 220)  # Cyan
                                progress = self.blink_total / self.REQUIRED_BLINKS
                            elif self.current_step == 1:
                                step_text = "Step 2/3"
                                if self.must_return_center:
                                    instruction = "Center"
                                    color = (100, 180, 255)  # Light blue
                                else:
                                    instruction = "Turn Left"
                                    color = (60, 220, 220)
                                progress = 0.33
                            elif self.current_step == 2:
                                step_text = "Step 3/3"
                                if self.must_return_center:
                                    instruction = "Center"
                                    color = (100, 180, 255)
                                else:
                                    instruction = "Turn Right"
                                    color = (60, 220, 220)
                                progress = 0.66
                            else:
                                step_text = "Starting..."
                                instruction = ""
                                color = (200, 200, 200)
                                progress = 0
                            
                            # Compact header bar (top - semi-transparent background)
                            overlay = frame.copy()
                            cv2.rectangle(overlay, (0, 0), (w, 50), (30, 30, 30), -1)
                            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                            
                            # Progress bar (thin, elegant)
                            bar_width = int((w - 40) * min(progress, 1.0))
                            cv2.rectangle(frame, (20, 35), (w - 20, 42), (60, 60, 60), -1)  # Background
                            cv2.rectangle(frame, (20, 35), (20 + bar_width, 42), color, -1)  # Progress
                            
                            # Step text (compact, top-left)
                            cv2.putText(frame, step_text, (20, 22),
                                      cv2.FONT_HERSHEY_SIMPLEX,
                                      0.5, (200, 200, 200), 1, cv2.LINE_AA)
                            
                            # Instruction (compact, top-right)
                            instruction_size = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                            cv2.putText(frame, instruction, (w - instruction_size[0] - 20, 25),
                                      cv2.FONT_HERSHEY_SIMPLEX,
                                      0.6, color, 2, cv2.LINE_AA)
                            
                            # Passive liveness indicator (if enabled)
                            if enable_passive and len(self.green_values) > 0:
                                hr_text = f"HR: {len(self.green_values)} samples"
                                cv2.putText(frame, hr_text, (w - 180, h - 15),
                                          cv2.FONT_HERSHEY_SIMPLEX,
                                          0.4, (100, 200, 255), 1, cv2.LINE_AA)
                            
                        else:
                            # Success banner (compact, elegant)
                            overlay = frame.copy()
                            cv2.rectangle(overlay, (0, 0), (w, 60), (0, 80, 0), -1)
                            cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
                            
                            # Success icon + text
                            if enable_passive:
                                cv2.putText(frame, "Active + Passive Verified",
                                          (w//2 - 160, 38), cv2.FONT_HERSHEY_SIMPLEX,
                                          0.7, (100, 255, 100), 2, cv2.LINE_AA)
                            else:
                                cv2.putText(frame, "Verification Complete",
                                          (w//2 - 140, 38), cv2.FONT_HERSHEY_SIMPLEX,
                                          0.8, (100, 255, 100), 2, cv2.LINE_AA)
                
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
                    cv2.waitKey(2000)
                    break
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        # Analyze heart rate if passive liveness is enabled
        heart_rate = 0
        hr_confidence = 0.0
        passive_ok = False
        
        if enable_passive and len(self.green_values) > 0:
            print(f"\n🫀 Analyzing heart rate from {len(self.green_values)} samples...")
            actual_fps = len(self.green_values) / (frame_count / 30.0) if frame_count > 0 else 30
            heart_rate, hr_confidence, passive_ok = self._analyze_heart_rate(actual_fps)
            
            print(f"💓 Heart Rate: {heart_rate:.1f} BPM")
            print(f"📈 Confidence: {hr_confidence:.1%}")
            print(f"🫀 Passive Liveness: {'✓ PASS' if passive_ok else '✗ FAIL'}")
        
        # Build result with passive liveness data
        result_base = {
            "blinks_detected": self.blink_total if not self.liveness_verified else self.REQUIRED_BLINKS,
            "head_movements": movements
        }
        
        if enable_passive:
            result_base["heart_rate"] = heart_rate
            result_base["heart_rate_confidence"] = hr_confidence
            result_base["passive_liveness"] = passive_ok
        
        # Retornar resultado
        if self.liveness_verified:
            # Active liveness passed - check passive if enabled
            if enable_passive:
                if passive_ok:
                    result_base["success"] = True
                    result_base["message"] = f"Active + Passive liveness confirmed (HR: {heart_rate:.0f} BPM)"
                else:
                    result_base["success"] = False
                    result_base["message"] = f"Active passed but passive failed (HR: {heart_rate:.0f} BPM - confidence too low)"
            else:
                result_base["success"] = True
                result_base["message"] = "Liveness confirmed successfully"
            
            return result_base
        
        elif frame_count >= max_frames:
            result_base["success"] = False
            result_base["message"] = "Timeout - verification took too long"
            return result_base
        else:
            result_base["success"] = False
            result_base["message"] = "Verification cancelled by user"
            return result_base


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
    print("Starting liveness verification...\n")
    
    detector = LivenessDetector()
    result = detector.verify()
    
    print("\n" + "="*50)
    print("RESULT:")
    print(f"  Status: {'✓ APPROVED' if result['success'] else '✗ REJECTED'}")
    print(f"  Message: {result['message']}")
    print(f"  Blinks: {result['blinks_detected']}")
    print(f"  Movements: {', '.join(result['head_movements']) if result['head_movements'] else 'None'}")
    print("="*50)
    
    sys.exit(0 if result['success'] else 1)
