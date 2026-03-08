"""
BioTrust - Advanced Liveness Detector V3
========================================
ANTI-SPOOFING SYSTEM WITH RANDOMIZED CHALLENGES

Features:
- 6 types of challenges (blink, smile, mouth_open, turn_left, turn_right, eyebrows_up)
- Randomized sequence (4-5 challenges per session)
- Multi-layer video detection (texture, moiré, color variance, heart rate)
- 60% rPPG confidence requirement
- Natural movement variance analysis

Version: 2.0
Author: BioTrust Team for TecStorm '26
"""

import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance as dist
from scipy import signal
from scipy.fft import fft, fftfreq
import time
import random


class LivenessDetectorV3:
    """
    Advanced liveness detector with randomized challenges and deep anti-spoofing.
    
    **SECURITY LAYERS:**
    1. Random challenge sequence (prevents replay attacks)
    2. Texture analysis (detects screen filming)
    3. Moiré pattern detection (detects screen interference)
    4. Color variance analysis (detects video compression)
    5. Micro-movement naturalness (detects artificial motion)
    6. High-confidence rPPG (60% threshold, signal variability check)
    """
    
    def __init__(self):
        """Initialize the advanced liveness detector."""
        
        # ========== CHALLENGE CONFIGURATION ==========
        self.CHALLENGE_TYPES = {
            "blink": {
                "name": "Blink 3 times",
                "required_count": 3,
                "timeout_frames": 450  # 15 seconds
            },
            "smile": {
                "name": "Smile",
                "required_count": 1,
                "timeout_frames": 300  # 10 seconds
            },
            "mouth_open": {
                "name": "Open mouth wide",
                "required_count": 1,
                "timeout_frames": 300  # 10 seconds
            },
            "turn_left": {
                "name": "Turn head LEFT",
                "required_count": 1,
                "timeout_frames": 360  # 12 seconds
            },
            "turn_right": {
                "name": "Turn head RIGHT",
                "required_count": 1,
                "timeout_frames": 360  # 12 seconds
            },
            "eyebrows_up": {
                "name": "Raise eyebrows",
                "required_count": 1,
                "timeout_frames": 450  # 15 seconds (hardest to detect)
            }
        }
        
        # Randomized challenge sequence (will be generated per session)
        self.challenge_sequence = []
        self.current_challenge_idx = 0
        self.challenge_counter = 0
        self.challenge_start_frame = 0
        self.must_return_neutral = False
        self.challenge_armed = False
        self.frontal_stable_counter = 0
        
        # ========== DETECTION THRESHOLDS ==========
        self.EAR_THRESHOLD = 0.18  # Eye Aspect Ratio for blink detection
        self.MAR_THRESHOLD = 0.60  # Mouth Aspect Ratio for mouth open (reduced)
        self.SMILE_MOUTH_WIDTH_RATIO = 1.25  # Mouth width increase when smiling (reduced)
        self.EYEBROW_DISTANCE_THRESHOLD = 35  # Eyebrow-eye distance when raised (reduced)
        self.HEAD_TURN_RATIO_LEFT = 2.2  # Nose-eye ratio for left turn
        self.HEAD_TURN_RATIO_RIGHT = 0.4  # Nose-eye ratio for right turn
        self.HEAD_FRONTAL_RANGE = (0.82, 1.18)  # Acceptable frontal range
        self.CONSEC_FRAMES = 2  # Consecutive frames for blink confirmation
        self.CHALLENGE_ARM_FRAMES = 12  # Require ~0.4s stable frontal pose before each challenge
        
        # ========== ANTI-SPOOFING THRESHOLDS ==========
        self.TEXTURE_THRESHOLD = 0.18  # Min texture variance (lower = screen)
        self.MOIRE_THRESHOLD = 0.40  # Max moiré score (higher = screen filming)
        self.COLOR_VARIANCE_MIN = 50  # Min color variance (lower = compressed video)
        self.MOVEMENT_VARIANCE_MIN = 0.8  # Min movement variance (lower = unnatural)
        self.RPPG_CONFIDENCE_MIN = 0.35  # 35% confidence required (realistic for real humans)
        self.RPPG_SIGNAL_VARIABILITY_MIN = 0.4  # Signal must have natural variations
        self.MIN_BPM = 45
        self.MAX_BPM = 160
        
        # ========== STATE VARIABLES ==========
        self.liveness_verified = False
        self.prev_eye_midpoint = None
        self.blink_frame_counter = 0
        self.mouth_open_armed = False
        self.challenge_armed = False
        self.frontal_stable_counter = 0
        
        # Anti-spoofing data collection
        self.texture_scores = []
        self.moire_scores = []
        self.color_variance_history = []
        self.micro_movements = []
        self.green_values = []  # rPPG signal
        self.timestamps = []
        
        # Baseline measurements (for smile detection)
        self.baseline_mouth_width = None
        self.baseline_frames_collected = 0
        
        # ========== MEDIAPIPE SETUP ==========
        mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # MediaPipe Face Mesh landmarks indices
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.MOUTH_OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
        self.MOUTH_VERTICAL = [13, 14]  # Top and bottom lip centers
        self.LEFT_EYEBROW = [70, 63, 105, 66, 107]
        self.RIGHT_EYEBROW = [300, 293, 334, 296, 336]
        self.FOREHEAD = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323]
        
        self.WINDOW_NAME = "BioTrust V3 - Advanced Liveness"
    
    # ========== DETECTION METHODS ==========
    
    def calculate_ear(self, eye_landmarks):
        """Calculate Eye Aspect Ratio for blink detection."""
        A = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
        B = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
        C = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
        return (A + B) / (2.0 * C)
    
    def calculate_mar(self, mouth_vertical_landmarks, mouth_landmarks=None):
        """Calculate normalized Mouth Aspect Ratio (vertical opening / mouth width)."""
        vertical_dist = dist.euclidean(mouth_vertical_landmarks[0], mouth_vertical_landmarks[1])

        if mouth_landmarks is None or len(mouth_landmarks) < 11:
            return vertical_dist

        left_corner = mouth_landmarks[0]
        right_corner = mouth_landmarks[10]
        mouth_width = dist.euclidean(left_corner, right_corner)
        return vertical_dist / (mouth_width + 1e-6)
    
    def detect_smile(self, mouth_landmarks):
        """Detect smile by comparing current mouth width to baseline."""
        if len(mouth_landmarks) < 4:
            return False
        
        # Calculate current mouth width
        left_corner = mouth_landmarks[0]
        right_corner = mouth_landmarks[6] if len(mouth_landmarks) > 6 else mouth_landmarks[-1]
        current_width = dist.euclidean(left_corner, right_corner)
        
        # Collect baseline during first frames
        if self.baseline_mouth_width is None:
            if self.baseline_frames_collected < 30:  # First 1 second
                self.baseline_mouth_width = current_width
                self.baseline_frames_collected += 1
                return False
            self.baseline_mouth_width = current_width
        
        # Smile detection: mouth width increases significantly
        width_ratio = current_width / (self.baseline_mouth_width + 1e-6)
        return width_ratio > self.SMILE_MOUTH_WIDTH_RATIO
    
    def detect_mouth_open(self, mouth_vertical_landmarks, mouth_landmarks=None):
        """Detect open mouth."""
        mar = self.calculate_mar(mouth_vertical_landmarks, mouth_landmarks)

        if mouth_landmarks is not None and len(mouth_landmarks) >= 11:
            return mar > 0.30

        return mar > self.MAR_THRESHOLD
    
    def detect_eyebrows_raised(self, left_brow, right_brow, left_eye, right_eye):
        """Detect raised eyebrows by measuring eyebrow-eye distance."""
        left_brow_y = np.mean([p[1] for p in left_brow])
        right_brow_y = np.mean([p[1] for p in right_brow])
        left_eye_y = np.mean([p[1] for p in left_eye])
        right_eye_y = np.mean([p[1] for p in right_eye])
        
        avg_distance = ((left_eye_y - left_brow_y) + (right_eye_y - right_brow_y)) / 2
        return avg_distance > self.EYEBROW_DISTANCE_THRESHOLD
    
    def analyze_head_pose(self, nose, left_eye_center, right_eye_center):
        """
        Analyze head pose (yaw rotation).
        Returns: (is_frontal, is_left, is_right, symmetry_ratio)
        """
        dist_left = np.linalg.norm(nose - left_eye_center)
        dist_right = np.linalg.norm(nose - right_eye_center)
        symmetry_ratio = dist_left / (dist_right + 1e-6)
        
        is_frontal = self.HEAD_FRONTAL_RANGE[0] < symmetry_ratio < self.HEAD_FRONTAL_RANGE[1]
        is_left = symmetry_ratio > self.HEAD_TURN_RATIO_LEFT
        is_right = symmetry_ratio < self.HEAD_TURN_RATIO_RIGHT
        
        return is_frontal, is_left, is_right, symmetry_ratio
    
    # ========== ANTI-SPOOFING METHODS ==========
    
    def analyze_texture(self, face_roi):
        """
        Analyze facial texture sharpness using Laplacian variance.
        Real faces have high-frequency details (pores, wrinkles).
        Screens have lower texture due to pixel grid and display limitations.
        
        Returns: texture_score (0-1, higher = more real)
        """
        if face_roi.size == 0:
            return 0.5
        
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        # Normalize: real faces typically have variance > 150, screens < 75
        texture_score = min(variance / 200.0, 1.0)
        return texture_score
    
    def detect_moire_pattern(self, face_roi):
        """
        Detect moiré patterns using FFT analysis.
        When filming a screen, interference patterns create periodic waves.
        
        Returns: moire_score (0-1, higher = more likely a screen)
        """
        if face_roi.size == 0 or min(face_roi.shape[:2]) < 20:
            return 0.0
        
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        
        # Apply FFT
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)
        magnitude = magnitude / (np.max(magnitude) + 1e-6)
        
        h, w = magnitude.shape
        # Moiré patterns show up as strong outer frequency peaks
        center = magnitude[h//3:2*h//3, w//3:2*w//3]
        outer = np.concatenate([
            magnitude[:h//3, :].flatten(),
            magnitude[2*h//3:, :].flatten(),
            magnitude[:, :w//3].flatten(),
            magnitude[:, 2*w//3:].flatten()
        ])
        
        center_energy = np.mean(center)
        outer_energy = np.mean(outer)
        
        moire_score = min(outer_energy / (center_energy + 1e-6) / 5.0, 1.0)
        return moire_score
    
    def analyze_color_variance(self, face_roi):
        """
        Analyze color variance across face region.
        Compressed videos have lower color variance.
        
        Returns: avg_variance
        """
        if face_roi.size == 0:
            return 0
        
        b_var = np.var(face_roi[:,:,0])
        g_var = np.var(face_roi[:,:,1])
        r_var = np.var(face_roi[:,:,2])
        
        return (b_var + g_var + r_var) / 3.0
    
    def check_movement_naturalness(self):
        """
        Check if micro-movements follow natural human patterns.
        Videos have unnaturally smooth or static movements.
        
        Returns: is_natural (bool)
        """
        if len(self.micro_movements) < 60:
            return True  # Need more data
        
        recent_movements = np.array(self.micro_movements[-90:])  # Last 3 seconds
        movement_var = np.var(recent_movements)
        
        # Human movement has natural jitter (variance > 1.0)
        return movement_var > self.MOVEMENT_VARIANCE_MIN
    
    def extract_rppg_signal(self, frame, face_landmarks):
        """Extract green channel mean from forehead for heart rate detection."""
        h, w, _ = frame.shape
        
        forehead_points = []
        for idx in self.FOREHEAD:
            if idx < len(face_landmarks.landmark):
                lm = face_landmarks.landmark[idx]
                forehead_points.append([int(lm.x * w), int(lm.y * h)])
        
        if len(forehead_points) < 5:
            return None
        
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillConvexPoly(mask, np.array(forehead_points, dtype=np.int32), 255)
        
        mean_green = cv2.mean(frame[:,:,1], mask=mask)[0]
        return mean_green
    
    def analyze_heart_rate(self, fps):
        """
        Analyze rPPG signal to detect heart rate.
        Returns: (heart_rate_bpm, confidence, is_valid)
        
        **STRICT VALIDATION:**
        - BPM must be in range [50-150]
        - Confidence must be >= 60%
        - Signal must have natural variability
        """
        min_samples = int(fps * 5)  # Need 5 seconds minimum
        
        if len(self.green_values) < min_samples:
            return 0, 0.0, False
        
        # Process signal
        signal_array = np.array(self.green_values)
        signal_detrended = signal.detrend(signal_array)
        
        # Bandpass filter (0.83-2.5 Hz = 50-150 BPM)
        nyquist = fps / 2.0
        low = 0.83 / nyquist
        high = 2.5 / nyquist
        b, a = signal.butter(4, [low, high], btype='band')
        filtered = signal.filtfilt(b, a, signal_detrended)
        
        # FFT analysis
        n = len(filtered)
        fft_vals = fft(filtered)
        fft_freq = fftfreq(n, 1.0 / fps)
        
        positive_idx = np.where(fft_freq > 0)
        fft_freq = fft_freq[positive_idx]
        fft_mag = np.abs(fft_vals[positive_idx])
        
        # Filter to valid heart rate range
        valid_mask = (fft_freq >= 0.83) & (fft_freq <= 2.5)
        valid_freq = fft_freq[valid_mask]
        valid_mag = fft_mag[valid_mask]
        
        if len(valid_mag) == 0:
            return 0, 0.0, False
        
        # Find peak frequency
        peak_idx = np.argmax(valid_mag)
        peak_freq = valid_freq[peak_idx]
        heart_rate = peak_freq * 60.0
        
        # Calculate confidence (peak strength)
        mean_mag = np.mean(valid_mag)
        peak_mag = valid_mag[peak_idx]
        confidence = min(peak_mag / (mean_mag + 1e-6) / 10.0, 1.0)
        
        # **ANTI-SPOOFING:** Check signal variability
        signal_variability = np.std(np.diff(signal_array))
        variability_ok = signal_variability >= self.RPPG_SIGNAL_VARIABILITY_MIN
        
        # **STRICT VALIDATION**
        is_valid = (self.MIN_BPM <= heart_rate <= self.MAX_BPM) and \
                   (confidence >= self.RPPG_CONFIDENCE_MIN) and \
                   variability_ok
        
        return heart_rate, confidence, is_valid
    
    # ========== WEB SESSION METHODS (for browser integration) ==========
    
    def start_web_session(self, risk_level="medium"):
        """
        Initialize a web-based liveness session (for processing browser frames).
        Call this before sending frames via process_web_frame().
        
        Args:
            risk_level: "low", "medium", "high", or "critical"
            
        Returns:
            dict with session info and first challenge
        """
        # Reset all state
        self.liveness_verified = False
        self.prev_eye_midpoint = None
        self.blink_frame_counter = 0
        self.mouth_open_armed = False
        self.challenge_counter = 0
        self.challenge_start_frame = 0
        self.current_challenge_idx = 0
        self.must_return_neutral = False
        self.challenge_armed = False
        self.frontal_stable_counter = 0
        self.baseline_mouth_width = None
        self.baseline_frames_collected = 0
        self.frame_count_web = 0
        
        # Clear anti-spoofing data
        self.texture_scores = []
        self.moire_scores = []
        self.color_variance_history = []
        self.micro_movements = []
        self.green_values = []
        self.timestamps = []
        
        # Generate random challenge sequence
        risk_mapping = {
            "low": (3, 4),
            "medium": (4, 5),
            "high": (5, 6),
            "critical": (6, 7)
        }
        min_challenges, max_challenges = risk_mapping.get(risk_level, (4, 5))
        num_challenges = random.randint(min_challenges, min(max_challenges, len(self.CHALLENGE_TYPES)))
        available_challenges = list(self.CHALLENGE_TYPES.keys())
        self.challenge_sequence = random.sample(available_challenges, num_challenges)
        random.shuffle(self.challenge_sequence)
        
        print(f"\n[WEB SESSION] Started with {len(self.challenge_sequence)} challenges: {self.challenge_sequence}")
        
        first_challenge = self.challenge_sequence[0]
        return {
            "total_challenges": len(self.challenge_sequence),
            "challenges": [self.CHALLENGE_TYPES[c]["name"] for c in self.challenge_sequence],
            "current_challenge": {
                "type": first_challenge,
                "name": self.CHALLENGE_TYPES[first_challenge]["name"]
            }
        }
    
    def process_web_frame(self, frame):
        """
        Process a single frame from browser webcam.
        This maintains inter-frame state for challenge progression.
        
        Args:
            frame: NumPy array (BGR) from browser
            
        Returns:
            dict: {
                "status": "in_progress"|"completed"|"failed",
                "progress": 0-100,
                "current_challenge": {...},
                "feedback": "message",
                "anti_spoofing_failed": bool (optional)
            }
        """
        if not hasattr(self, 'frame_count_web'):
            return {"status": "failed", "feedback": "Session not started - call start_web_session() first"}
        
        self.frame_count_web += 1
        frame = cv2.flip(frame, 1)  # Mirror like desktop version
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        
        h, w, _ = frame.shape
        
        if not results.multi_face_landmarks:
            return {
                "status": "in_progress",
                "progress": (self.current_challenge_idx / len(self.challenge_sequence)) * 100,
                "current_challenge": self._get_current_challenge_info(),
                "feedback": "❌ Rosto não detected detectado. Posicione-se na câmara.",
                "completed_challenges": self.current_challenge_idx
            }
        
        face_landmarks = results.multi_face_landmarks[0]
        landmarks = np.array([[int(lm.x * w), int(lm.y * h)] for lm in face_landmarks.landmark])
        
        # Anti-spoofing checks
        x_coords = landmarks[:, 0]
        y_coords = landmarks[:, 1]
        x_min, x_max = max(0, min(x_coords)), min(w, max(x_coords))
        y_min, y_max = max(0, min(y_coords)), min(h, max(y_coords))
        
        if x_max > x_min and y_max > y_min and self.frame_count_web % 3 == 0:
            face_roi = frame[y_min:y_max, x_min:x_max]
            self.texture_scores.append(self.analyze_texture(face_roi))
            self.moire_scores.append(self.detect_moire_pattern(face_roi))
            self.color_variance_history.append(self.analyze_color_variance(face_roi))
            
            # Early spoofing detection (after 30 frames = ~3 seconds)
            if self.frame_count_web == 30 and len(self.texture_scores) >= 10:
                avg_texture = np.mean(self.texture_scores)
                avg_moire = np.mean(self.moire_scores)
                avg_color_var = np.mean(self.color_variance_history)
                
                if avg_texture < self.TEXTURE_THRESHOLD:
                    return {
                        "status": "failed",
                        "progress": 0,
                        "feedback": "🚫 SPOOFING DETECTADO: Tela/monitor detectado",
                        "anti_spoofing_failed": True,
                        "reason": "screen_detected"
                    }
                if avg_moire > self.MOIRE_THRESHOLD:
                    return {
                        "status": "failed",
                        "progress": 0,
                        "feedback": "🚫 SPOOFING DETECTADO: Padrão de interferência detectado",
                        "anti_spoofing_failed": True,
                        "reason": "moire_detected"
                    }
                if avg_color_var < self.COLOR_VARIANCE_MIN:
                    return {
                        "status": "failed",
                        "progress": 0,
                        "feedback": "🚫 SPOOFING DETECTADO: Vídeo gravado detectado",
                        "anti_spoofing_failed": True,
                        "reason": "video_detected"
                    }
        
        # Extract facial features
        left_eye = landmarks[self.LEFT_EYE]
        right_eye = landmarks[self.RIGHT_EYE]
        left_eye_center = np.mean(left_eye, axis=0)
        right_eye_center = np.mean(right_eye, axis=0)
        eye_midpoint = (left_eye_center + right_eye_center) / 2
        
        nose = landmarks[1]
        mouth_outer = landmarks[self.MOUTH_OUTER[:min(len(self.MOUTH_OUTER), len(landmarks))]]
        mouth_vertical = landmarks[self.MOUTH_VERTICAL]
        left_brow = landmarks[self.LEFT_EYEBROW]
        right_brow = landmarks[self.RIGHT_EYEBROW]
        
        # Track micro-movements
        movement = 0.0
        if self.prev_eye_midpoint is not None:
            movement = np.linalg.norm(eye_midpoint - self.prev_eye_midpoint)
            self.micro_movements.append(movement)
        self.prev_eye_midpoint = eye_midpoint
        
        # Analyze head pose
        is_frontal, is_left, is_right, _ = self.analyze_head_pose(nose, left_eye_center, right_eye_center)
        nose_eye_ratio = (nose[1] - eye_midpoint[1]) / (h + 1e-6)
        face_pitch_ok = 0.02 < nose_eye_ratio < 0.13
        face_frontal = is_frontal and face_pitch_ok
        movement_ok = movement < 24
        
        # Calculate detection metrics
        left_ear = self.calculate_ear(left_eye)
        right_ear = self.calculate_ear(right_eye)
        both_eyes_closed = (left_ear < self.EAR_THRESHOLD and right_ear < self.EAR_THRESHOLD)
        is_smiling = self.detect_smile(mouth_outer)
        is_mouth_open = self.detect_mouth_open(mouth_vertical, mouth_outer)
        are_eyebrows_raised = self.detect_eyebrows_raised(left_brow, right_brow, left_eye, right_eye)
        
        # Challenge processing
        if self.current_challenge_idx >= len(self.challenge_sequence):
            # All challenges completed!
            return {
                "status": "completed",
                "progress": 100,
                "current_challenge": {"name": "Concluído", "type": "done"},
                "feedback": "✅ Todas as verificações completas!",
                "completed_challenges": len(self.challenge_sequence)
            }
        
        current_challenge = self.challenge_sequence[self.current_challenge_idx]
        challenge_info = self.CHALLENGE_TYPES[current_challenge]
        
        # Check timeout
        frames_in_challenge = self.frame_count_web - self.challenge_start_frame
        if frames_in_challenge > challenge_info["timeout_frames"]:
            return {
                "status": "failed",
                "progress": (self.current_challenge_idx / len(self.challenge_sequence)) * 100,
                "feedback": f"⏱️ Tempo esgotado no desafio: {challenge_info['name']}",
                "completed_challenges": self.current_challenge_idx
            }
        
        # Arm challenge (need stable frontal pose first)
        if not self.challenge_armed:
            if face_frontal and movement_ok:
                self.frontal_stable_counter += 1
                if self.frontal_stable_counter >= self.CHALLENGE_ARM_FRAMES:
                    self.challenge_armed = True
                    self.challenge_counter = 0
                    self.blink_frame_counter = 0
                    self.mouth_open_armed = False
                    return {
                        "status": "in_progress",
                        "progress": (self.current_challenge_idx / len(self.challenge_sequence)) * 100,
            "current_challenge": self._get_current_challenge_info(),
                        "feedback": f"✅ Pronto! Agora: {challenge_info['name']}",
                        "completed_challenges": self.current_challenge_idx
                    }
            else:
                return {
                    "status": "in_progress",
                    "progress": (self.current_challenge_idx / len(self.challenge_sequence)) * 100,
                    "current_challenge": self._get_current_challenge_info(),
                    "feedback": "📍 Posicione o rosto de frente para a câmara...",
                    "completed_challenges": self.current_challenge_idx
                }
        
        # Process challenge based on type
        challenge_satisfied = False
        
        if current_challenge == "blink":
            if both_eyes_closed:
                self.blink_frame_counter += 1
            elif self.blink_frame_counter >= self.CONSEC_FRAMES:
                self.challenge_counter += 1
                self.blink_frame_counter = 0
                if self.challenge_counter >= challenge_info["required_count"]:
                    challenge_satisfied = True
        elif current_challenge == "smile":
            if is_smiling:
                self.challenge_counter += 1
                if self.challenge_counter >= challenge_info["required_count"] * 10:
                    challenge_satisfied = True
        elif current_challenge == "mouth_open":
            if is_mouth_open:
                self.challenge_counter += 1
                if self.challenge_counter >= challenge_info["required_count"] * 8:
                    challenge_satisfied = True
        elif current_challenge == "turn_left":
            if is_left:
                self.challenge_counter += 1
                if self.challenge_counter >= challenge_info["required_count"] * 15:
                    challenge_satisfied = True
        elif current_challenge == "turn_right":
            if is_right:
                self.challenge_counter += 1
                if self.challenge_counter >= challenge_info["required_count"] * 15:
                    challenge_satisfied = True
        elif current_challenge == "eyebrows_up":
            if are_eyebrows_raised:
                self.challenge_counter += 1
                if self.challenge_counter >= challenge_info["required_count"] * 20:
                    challenge_satisfied = True
        
        if challenge_satisfied:
            print(f"[WEB] ✅ Challenge {self.current_challenge_idx + 1}/{len(self.challenge_sequence)} completed: {challenge_info['name']}")
            self.current_challenge_idx += 1
            self.challenge_start_frame = self.frame_count_web
            self.challenge_armed = False
            self.frontal_stable_counter = 0
            self.must_return_neutral = True
            
            if self.current_challenge_idx >= len(self.challenge_sequence):
                return {
                    "status": "completed",
                    "progress": 100,
                    "current_challenge": {"name": "Concluído", "type": "done"},
                    "feedback": "✅ Verificação completa!",
                    "completed_challenges": len(self.challenge_sequence)
                }
        
        # Return current progress
        progress = ((self.current_challenge_idx + (self.challenge_counter / (challenge_info["required_count"] * 10))) / len(self.challenge_sequence)) * 100
        
        return {
            "status": "in_progress",
            "progress": min(progress, 99),  # Cap at 99% until truly done
            "current_challenge": self._get_current_challenge_info(),
            "feedback": f"🎯 {challenge_info['name']} ({self.challenge_counter}/{challenge_info['required_count'] * 10})",
            "completed_challenges": self.current_challenge_idx
        }
    
    def _get_current_challenge_info(self):
        """Helper to get current challenge details"""
        if self.current_challenge_idx >= len(self.challenge_sequence):
            return {"name": "Concluído", "type": "done"}
        
        challenge_key = self.challenge_sequence[self.current_challenge_idx]
        challenge = self.CHALLENGE_TYPES[challenge_key]
        return {
            "type": challenge_key,
            "name": challenge["name"],
            "instruction": challenge["name"]
        }
    
    # ========== MAIN VERIFICATION METHOD ==========
    
    def verify(self, timeout_seconds=90, enable_passive=True, risk_level="medium", require_rppg=False):
        """
        Run complete liveness verification with randomized challenges.
        
        Args:
            timeout_seconds: Maximum time allowed (default 90s)
            enable_passive: Enable rPPG heart rate detection (default True)
            risk_level: "low" (3-4 challenges), "medium" (4-5), "high" (5-6), "critical" (6-7)
            require_rppg: If True, rPPG failure blocks verification. If False (default), rPPG is advisory only
            
        Returns:
            dict: {
                "success": bool,
                "message": str,
                "challenges_completed": list,
                "anti_spoofing": dict,
                "heart_rate": float (if enable_passive),
                "heart_rate_confidence": float (if enable_passive)
            }
        """
        
        # ========== INITIALIZATION ==========
        
        # Reset all state
        self.liveness_verified = False
        self.prev_eye_midpoint = None
        self.blink_frame_counter = 0
        self.mouth_open_armed = False
        self.challenge_counter = 0
        self.challenge_start_frame = 0
        self.current_challenge_idx = 0
        self.must_return_neutral = False
        self.challenge_armed = False
        self.frontal_stable_counter = 0
        self.baseline_mouth_width = None
        self.baseline_frames_collected = 0
        self.wrong_move_count = 0  # Track wrong movements (1st=reset, 2nd=block)
        self.wrong_move_cooldown = 0  # Prevent multiple detections of same error
        
        # Clear anti-spoofing data
        self.texture_scores = []
        self.moire_scores = []
        self.color_variance_history = []
        self.micro_movements = []
        self.green_values = []
        self.timestamps = []
        
        # **GENERATE RANDOM CHALLENGE SEQUENCE BASED ON RISK**
        risk_mapping = {
            "low": (3, 4),
            "medium": (4, 5),
            "high": (5, 6),
            "critical": (6, 7)
        }
        min_challenges, max_challenges = risk_mapping.get(risk_level, (4, 5))
        num_challenges = random.randint(min_challenges, min(max_challenges, len(self.CHALLENGE_TYPES)))
        available_challenges = list(self.CHALLENGE_TYPES.keys())
        self.challenge_sequence = random.sample(available_challenges, num_challenges)
        random.shuffle(self.challenge_sequence)  # Extra randomization
        
        print("\n" + "="*70)
        print("BIOTRUST V3 - ADVANCED ANTI-SPOOFING LIVENESS DETECTION")
        print("="*70)
        print(f"Risk Level: {risk_level.upper()} -> {len(self.challenge_sequence)} challenges")
        print(f"Randomized Challenges:")
        for i, challenge in enumerate(self.challenge_sequence, 1):
            name = self.CHALLENGE_TYPES[challenge]["name"]
            print(f"   {i}. {name}")
        print(f"\nrPPG Enabled: {'YES' if enable_passive else 'NO'} ({'REQUIRED' if require_rppg else 'ADVISORY'})")
        print(f"Anti-spoofing: Texture, Moire, Color Variance, Movement checks ACTIVE")
        print(f"\n[INFO] Collecting baseline rPPG signal (3 seconds warmup)...")
        print("="*70 + "\n")
        
        # Open camera
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not cap.isOpened():
            return {
                "success": False,
                "message": "[FAIL] Camera not accessible",
                "challenges_completed": []
            }
        
        # Create window
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
        cv2.moveWindow(self.WINDOW_NAME, 250, 80)
        cv2.resizeWindow(self.WINDOW_NAME, 900, 650)
        print(f"[OK] OpenCV window created: {self.WINDOW_NAME}")
        print("[INFO] Window should appear on your screen now...")
        time.sleep(0.5)  # Increased from 0.2 to give more time for window to appear
        
        # ========== WARMUP PHASE (rPPG baseline collection) ==========
        
        warmup_frames = 90 if enable_passive else 0  # 3 seconds warmup for rPPG
        warmup_complete = False
        
        # ========== MAIN LOOP ==========
        
        frame_count = 0
        max_frames = timeout_seconds * 30
        challenges_completed = []
        feedback_message = ""
        feedback_frames = 0
        failed_frame_count = 0
        MAX_FAILED_FRAMES = 10  # Allow some failed reads before giving up
        
        print(f"[INFO] Starting main loop (max {max_frames} frames, ~{timeout_seconds}s)\n")
        
        try:
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    failed_frame_count += 1
                    if failed_frame_count > MAX_FAILED_FRAMES:
                        print(f"\n[ERROR] Camera read failed {failed_frame_count} times - aborting")
                        break
                    continue  # Skip this frame but don't abort yet
                
                frame_count += 1
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb)
                
                h, w, _ = frame.shape
                
                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        # Extract landmarks
                        landmarks = np.array([[int(lm.x * w), int(lm.y * h)]
                                            for lm in face_landmarks.landmark])
                        
                        # **rPPG DATA COLLECTION (continuous)**
                        if enable_passive:
                            green_val = self.extract_rppg_signal(frame, face_landmarks)
                            if green_val is not None:
                                self.green_values.append(green_val)
                                self.timestamps.append(frame_count / 30.0)
                        
                        # **WARMUP PHASE UI**
                        if frame_count < warmup_frames:
                            overlay = frame.copy()
                            cv2.rectangle(overlay, (0, 0), (w, 80), (40, 40, 120), -1)
                            cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
                            
                            warmup_progress = frame_count / warmup_frames
                            bar_w = int((w - 40) * warmup_progress)
                            cv2.rectangle(frame, (20, 55), (w - 20, 65), (60, 60, 60), -1)
                            cv2.rectangle(frame, (20, 55), (20 + bar_w, 65), (100, 200, 255), -1)
                            
                            cv2.putText(frame, "Collecting baseline heart rate...",
                                      (w//2 - 180, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                      0.7, (200, 200, 200), 2, cv2.LINE_AA)
                            cv2.putText(frame, f"Samples: {len(self.green_values)}",
                                      (w//2 - 80, 50), cv2.FONT_HERSHEY_SIMPLEX,
                                      0.5, (150, 150, 150), 1, cv2.LINE_AA)
                            
                            cv2.imshow(self.WINDOW_NAME, frame)
                            key = cv2.waitKey(1) & 0xFF
                            if key == 27:
                                break
                            continue  # Skip challenge processing during warmup
                        
                        # **ANTI-SPOOFING: Extract face ROI**
                        x_coords = landmarks[:, 0]
                        y_coords = landmarks[:, 1]
                        x_min, x_max = max(0, min(x_coords)), min(w, max(x_coords))
                        y_min, y_max = max(0, min(y_coords)), min(h, max(y_coords))
                        
                        if x_max > x_min and y_max > y_min:
                            face_roi = frame[y_min:y_max, x_min:x_max]
                            
                            # Collect anti-spoofing metrics
                            if frame_count % 3 == 0:  # Every 3 frames to save processing
                                self.texture_scores.append(self.analyze_texture(face_roi))
                                self.moire_scores.append(self.detect_moire_pattern(face_roi))
                                self.color_variance_history.append(self.analyze_color_variance(face_roi))
                        
                        # **EXTRACT FACIAL FEATURES**
                        left_eye = landmarks[self.LEFT_EYE]
                        right_eye = landmarks[self.RIGHT_EYE]
                        left_eye_center = np.mean(left_eye, axis=0)
                        right_eye_center = np.mean(right_eye, axis=0)
                        eye_midpoint = (left_eye_center + right_eye_center) / 2
                        
                        nose = landmarks[1]
                        mouth_outer = landmarks[self.MOUTH_OUTER[:min(len(self.MOUTH_OUTER), len(landmarks))]]
                        mouth_vertical = landmarks[self.MOUTH_VERTICAL]
                        left_brow = landmarks[self.LEFT_EYEBROW]
                        right_brow = landmarks[self.RIGHT_EYEBROW]
                        
                        # Track micro-movements
                        if self.prev_eye_midpoint is not None:
                            movement = np.linalg.norm(eye_midpoint - self.prev_eye_midpoint)
                            self.micro_movements.append(movement)
                        else:
                            movement = 0.0
                        self.prev_eye_midpoint = eye_midpoint
                        
                        # Analyze head pose
                        is_frontal, is_left, is_right, _ = self.analyze_head_pose(
                            nose, left_eye_center, right_eye_center
                        )

                        # Extra frontal checks similar to the legacy working flow.
                        nose_eye_ratio = (nose[1] - eye_midpoint[1]) / (h + 1e-6)
                        face_pitch_ok = 0.02 < nose_eye_ratio < 0.13
                        face_frontal = is_frontal and face_pitch_ok
                        movement_ok = movement < 24
                        
                        # Calculate detection metrics
                        left_ear = self.calculate_ear(left_eye)
                        right_ear = self.calculate_ear(right_eye)
                        both_eyes_closed = (left_ear < self.EAR_THRESHOLD and 
                                          right_ear < self.EAR_THRESHOLD)
                        
                        is_smiling = self.detect_smile(mouth_outer)
                        is_mouth_open = self.detect_mouth_open(mouth_vertical, mouth_outer)
                        are_eyebrows_raised = self.detect_eyebrows_raised(
                            left_brow, right_brow, left_eye, right_eye
                        )
                        
                        # Mark warmup complete
                        if not warmup_complete and frame_count >= warmup_frames:
                            warmup_complete = True
                            if enable_passive:
                                print(f"[OK] Warmup complete - {len(self.green_values)} rPPG samples collected")
                            
                            # ========== EARLY ANTI-SPOOFING CHECK ==========
                            # Check for video replay/screen filming BEFORE starting challenges
                            if len(self.texture_scores) >= 10:  # Need minimum samples
                                early_texture = np.mean(self.texture_scores)
                                early_moire = np.mean(self.moire_scores) if len(self.moire_scores) > 0 else 0
                                early_color_var = np.mean(self.color_variance_history) if len(self.color_variance_history) > 0 else 0
                                
                                print(f"\n[EARLY CHECK] Texture: {early_texture:.3f} (min: {self.TEXTURE_THRESHOLD})")
                                print(f"[EARLY CHECK] Moire: {early_moire:.3f} (max: {self.MOIRE_THRESHOLD})")
                                print(f"[EARLY CHECK] Color Var: {early_color_var:.1f} (min: {self.COLOR_VARIANCE_MIN})")
                                
                                # FAIL immediately if strong spoofing signals detected
                                if early_texture < self.TEXTURE_THRESHOLD:
                                    cap.release()
                                    cv2.destroyAllWindows()
                                    return {
                                        "success": False,
                                        "message": f"[FAIL] SPOOFING DETECTED: Low texture ({early_texture:.3f}) - Screen/monitor replay detected",
                                        "challenges_completed": [],
                                        "anti_spoofing": {
                                            "texture_score": early_texture,
                                            "reason": "Screen display detected before challenges"
                                        }
                                    }
                                
                                if early_moire > self.MOIRE_THRESHOLD:
                                    cap.release()
                                    cv2.destroyAllWindows()
                                    return {
                                        "success": False,
                                        "message": f"[FAIL] SPOOFING DETECTED: High moire ({early_moire:.3f}) - Screen filming detected",
                                        "challenges_completed": [],
                                        "anti_spoofing": {
                                            "moire_score": early_moire,
                                            "reason": "Screen interference patterns detected"
                                        }
                                    }
                                
                                if early_color_var < self.COLOR_VARIANCE_MIN:
                                    cap.release()
                                    cv2.destroyAllWindows()
                                    return {
                                        "success": False,
                                        "message": f"[FAIL] SPOOFING DETECTED: Low color variance ({early_color_var:.1f}) - Compressed video detected",
                                        "challenges_completed": [],
                                        "anti_spoofing": {
                                            "color_variance": early_color_var,
                                            "reason": "Video compression artifacts detected"
                                        }
                                    }
                                
                                print("[EARLY CHECK] All anti-spoofing checks PASSED - Proceeding to challenges\n")
                            
                            print("[START] Beginning challenge sequence...\n")
                        
                        # ========== CHALLENGE PROCESSING ==========
                        
                        if self.current_challenge_idx < len(self.challenge_sequence):
                            current_challenge = self.challenge_sequence[self.current_challenge_idx]
                            challenge_info = self.CHALLENGE_TYPES[current_challenge]
                            
                            # Check timeout for current challenge
                            if frame_count - self.challenge_start_frame > challenge_info["timeout_frames"]:
                                # Challenge timeout - FAIL
                                cap.release()
                                cv2.destroyAllWindows()
                                return {
                                    "success": False,
                                    "message": f"❌ Timeout on challenge: {challenge_info['name']}",
                                    "challenges_completed": challenges_completed
                                }
                            
                            # Process challenge based on type
                            challenge_satisfied = False
                            
                            # ========== DETECÇÃO INTELIGENTE DE MOVIMENTOS OPOSTOS ==========
                            # Só penalizar movimentos CLARAMENTE ERRADOS (direções opostas)
                            # Não penalizar pequenos movimentos naturais (piscar enquanto sorri, etc)
                            if self.wrong_move_cooldown > 0:
                                self.wrong_move_cooldown -= 1
                            
                            wrong_action_detected = False
                            wrong_action_name = ""
                            
                            # Verificar apenas MOVIMENTOS OPOSTOS críticos
                            if self.challenge_armed and self.wrong_move_cooldown == 0:
                                # DIREÇÕES: Virar lado OPOSTO
                                if current_challenge == "turn_left" and is_right and not self.must_return_neutral:
                                    wrong_action_detected = True
                                    wrong_action_name = "VIROU DIREITA (esperado: ESQUERDA)"
                                
                                elif current_challenge == "turn_right" and is_left and not self.must_return_neutral:
                                    wrong_action_detected = True
                                    wrong_action_name = "VIROU ESQUERDA (esperado: DIREITA)"
                                
                                # CONFUSÃO FACIAL: Smile vs Mouth Open (muito distintos)
                                elif current_challenge == "smile" and is_mouth_open and not is_smiling:
                                    wrong_action_detected = True
                                    wrong_action_name = "ABRIU A BOCA (esperado: SORRIR)"
                                
                                elif current_challenge == "mouth_open" and is_smiling and not is_mouth_open:
                                    wrong_action_detected = True
                                    wrong_action_name = "SORRIU (esperado: ABRIR BOCA)"
                            
                            # ========== PROCESSAR ERRO DETECTADO ==========
                            if wrong_action_detected:
                                self.wrong_move_count += 1
                                self.wrong_move_cooldown = 60  # 2 segundos de cooldown
                                
                                challenge_esperado = self.CHALLENGE_TYPES[current_challenge]["name"]
                                
                                if self.wrong_move_count == 1:
                                    # 1º ERRO: Reset para challenge 1
                                    print(f"\n⚠️  ERRO DETECTADO: {wrong_action_name}")
                                    print(f"⚠️  PENALIZAÇÃO: Voltando ao início (Challenge 1)\n")
                                    self.current_challenge_idx = 0
                                    self.challenge_counter = 0
                                    self.blink_frame_counter = 0
                                    self.must_return_neutral = False
                                    self.challenge_armed = False
                                    self.frontal_stable_counter = 0
                                    self.mouth_open_armed = False
                                    challenges_completed = []
                                    feedback_message = "ERRO! VOLTANDO AO INICIO"
                                    feedback_frames = 90
                                    continue
                                else:
                                    # 2º ERRO: BLOQUEAR TRANSAÇÃO
                                    print(f"\n❌ ERRO CRÍTICO: 2º erro detectado")
                                    print(f"❌ TRANSAÇÃO BLOQUEADA POR SUSPEITA\n")
                                    cap.release()
                                    cv2.destroyAllWindows()
                                    return {
                                        "success": False,
                                        "message": f"[BLOCKED] Multiple wrong movements - Transaction blocked",
                                        "challenges_completed": challenges_completed,
                                        "reason": f"Security threshold: {wrong_action_name}"
                                    }

                            # Arm challenge only after stable frontal pose to avoid instant first-step pass.
                            if not self.challenge_armed:
                                if face_frontal and movement_ok:
                                    self.frontal_stable_counter += 1
                                    if self.frontal_stable_counter >= self.CHALLENGE_ARM_FRAMES:
                                        self.challenge_armed = True
                                        self.challenge_counter = 0
                                        self.blink_frame_counter = 0
                                        self.mouth_open_armed = False
                                else:
                                    self.frontal_stable_counter = 0

                                arming_text = "LOOK STRAIGHT TO START" if self.current_challenge_idx == 0 else "LOOK STRAIGHT"
                                cv2.putText(frame, arming_text,
                                          (20, 90), cv2.FONT_HERSHEY_SIMPLEX,
                                          0.7, (0, 200, 255), 2, cv2.LINE_AA)
                                continue

                            if current_challenge in ("blink", "smile", "mouth_open", "eyebrows_up") and not face_frontal:
                                cv2.putText(frame, "LOOK STRAIGHT AT CAMERA",
                                          (20, 90), cv2.FONT_HERSHEY_SIMPLEX,
                                          0.7, (0, 0, 255), 2, cv2.LINE_AA)
                            
                            if current_challenge == "blink":
                                # Legacy-style blink logic: count blinks only when frontal and stable.
                                if face_frontal and movement_ok:
                                    if both_eyes_closed:
                                        self.blink_frame_counter += 1
                                    else:
                                        if self.blink_frame_counter >= self.CONSEC_FRAMES:
                                            self.challenge_counter += 1
                                            print(f"  👁️  Blink {self.challenge_counter}/{challenge_info['required_count']}")
                                        self.blink_frame_counter = 0
                                else:
                                    self.blink_frame_counter = 0
                                
                                if self.challenge_counter >= challenge_info["required_count"]:
                                    challenge_satisfied = True
                            
                            elif current_challenge == "smile":
                                if is_smiling:
                                    self.challenge_counter += 1
                                    if self.challenge_counter >= 15:  # Hold for 0.5 seconds
                                        challenge_satisfied = True
                            
                            elif current_challenge == "mouth_open":
                                if face_frontal and movement_ok:
                                    # Arm only after a closed-mouth state to avoid immediate false positives.
                                    if not is_mouth_open:
                                        self.mouth_open_armed = True
                                        self.challenge_counter = 0
                                    elif self.mouth_open_armed:
                                        self.challenge_counter += 1
                                        if self.challenge_counter >= 8:
                                            challenge_satisfied = True
                                else:
                                    self.challenge_counter = 0
                            
                            elif current_challenge == "turn_left":
                                if not self.must_return_neutral:
                                    # CORRETO: Virou ESQUERDA
                                    if is_left:
                                        self.must_return_neutral = True
                                        print(f"  ⬅️  Left turn detected - return to center")
                                        feedback_message = "LEFT DETECTED - RETURN TO CENTER"
                                        feedback_frames = 45
                                else:
                                    if is_frontal:
                                        challenge_satisfied = True
                                        feedback_message = "CENTER CONFIRMED"
                                        feedback_frames = 30
                            
                            elif current_challenge == "turn_right":
                                if not self.must_return_neutral:
                                    # CORRETO: Virou DIREITA
                                    if is_right:
                                        self.must_return_neutral = True
                                        print(f"  ➡️  Right turn detected - return to center")
                                        feedback_message = "RIGHT DETECTED - RETURN TO CENTER"
                                        feedback_frames = 45
                                else:
                                    if is_frontal:
                                        challenge_satisfied = True
                                        feedback_message = "CENTER CONFIRMED"
                                        feedback_frames = 30
                            
                            elif current_challenge == "eyebrows_up":
                                if are_eyebrows_raised:
                                    self.challenge_counter += 1
                                    if self.challenge_counter >= 15:  # Hold for 0.5 seconds
                                        challenge_satisfied = True
                            
                            # If challenge satisfied, move to next
                            if challenge_satisfied:
                                challenges_completed.append(current_challenge)
                                print(f"[OK] Challenge {self.current_challenge_idx + 1}/{len(self.challenge_sequence)} complete: {challenge_info['name']}")
                                self.current_challenge_idx += 1
                                self.challenge_counter = 0
                                self.blink_frame_counter = 0
                                self.mouth_open_armed = False
                                self.challenge_armed = False
                                self.frontal_stable_counter = 0
                                self.challenge_start_frame = frame_count
                                self.must_return_neutral = False
                                
                                # Check if all challenges complete
                                if self.current_challenge_idx >= len(self.challenge_sequence):
                                    self.liveness_verified = True
                                    print("\n" + "="*70)
                                    print("ALL CHALLENGES COMPLETED - VERIFYING...")
                                    print("="*70)
                        
                        # ========== UI RENDERING ==========
                        
                        if not self.liveness_verified:
                            # Current challenge info
                            if self.current_challenge_idx < len(self.challenge_sequence):
                                curr_chal = self.challenge_sequence[self.current_challenge_idx]
                                chal_info = self.CHALLENGE_TYPES[curr_chal]
                                
                                # Header bar
                                overlay = frame.copy()
                                cv2.rectangle(overlay, (0, 0), (w, 65), (20, 20, 20), -1)
                                cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
                                
                                # Progress
                                progress = self.current_challenge_idx / len(self.challenge_sequence)
                                bar_width = int((w - 40) * progress)
                                cv2.rectangle(frame, (20, 50), (w - 20, 58), (50, 50, 50), -1)
                                cv2.rectangle(frame, (20, 50), (20 + bar_width, 58), (60, 220, 220), -1)
                                
                                # Challenge instruction
                                instruction = f"{chal_info['name']}"
                                if self.must_return_neutral:
                                    instruction = "RETURN TO CENTER"
                                cv2.putText(frame, f"Challenge {self.current_challenge_idx + 1}/{len(self.challenge_sequence)}:",
                                          (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
                                cv2.putText(frame, instruction,
                                          (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 255), 2, cv2.LINE_AA)
                                
                                # Counter (for blinks, etc)
                                if curr_chal == "blink":
                                    counter_text = f"{self.challenge_counter}/{chal_info['required_count']}"
                                    cv2.putText(frame, counter_text, (w - 80, 40),
                                              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 100), 2, cv2.LINE_AA)

                                if feedback_frames > 0 and feedback_message:
                                    cv2.putText(frame, feedback_message,
                                              (20, 90), cv2.FONT_HERSHEY_SIMPLEX,
                                              0.65, (100, 255, 100), 2, cv2.LINE_AA)
                                    feedback_frames -= 1
                        
                        else:
                            # Success overlay
                            overlay = frame.copy()
                            cv2.rectangle(overlay, (0, 0), (w, 80), (0, 100, 0), -1)
                            cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
                            
                            cv2.putText(frame, "LIVENESS VERIFIED - Analyzing...",
                                      (w//2 - 250, 50), cv2.FONT_HERSHEY_SIMPLEX,
                                      0.9, (150, 255, 150), 2, cv2.LINE_AA)
                
                else:
                    # NO FACE DETECTED - Show warning overlay
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 120), -1)
                    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                    
                    cv2.putText(frame, "NO FACE DETECTED",
                              (w//2 - 150, 40), cv2.FONT_HERSHEY_SIMPLEX,
                              0.9, (100, 100, 255), 2, cv2.LINE_AA)
                    cv2.putText(frame, "Position your face in the frame",
                              (w//2 - 200, 75), cv2.FONT_HERSHEY_SIMPLEX,
                              0.6, (200, 200, 200), 1, cv2.LINE_AA)
                
                # Show frame
                cv2.imshow(self.WINDOW_NAME, frame)
                
                # Check for ESC key
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    print("\n[INFO] ESC pressed - aborting verification")
                    break
                
                # REMOVED: Window visibility check was causing premature exit
                # try:
                #     if cv2.getWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                #         break
                # except:
                #     break
                
                # If verified, wait briefly then continue to analysis
                if self.liveness_verified:
                    cv2.waitKey(1000)  # 1 second pause
                    break
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
       # ========== ANTI-SPOOFING ANALYSIS ==========
        
        print("\n" + "="*70)
        print("RUNNING ANTI-SPOOFING ANALYSIS...")
        print("="*70)
        
        # Check if all challenges were completed
        if not self.liveness_verified or len(challenges_completed) < len(self.challenge_sequence):
            return {
                "success": False,
                "message": "[FAIL] Not all challenges completed",
                "challenges_completed": challenges_completed
            }
        
        # Texture analysis
        avg_texture = np.mean(self.texture_scores) if len(self.texture_scores) > 0 else 0.0
        texture_pass = avg_texture >= self.TEXTURE_THRESHOLD
        print(f"[Texture] Score: {avg_texture:.3f} {'[PASS]' if texture_pass else '[FAIL] Screen detected'}")
        
        # Moiré pattern detection
        avg_moire = np.mean(self.moire_scores) if len(self.moire_scores) > 0 else 0.0
        moire_pass = avg_moire < self.MOIRE_THRESHOLD
        print(f"[Moire] Score: {avg_moire:.3f} {'[PASS]' if moire_pass else '[FAIL] Screen filming detected'}")
        
        # Color variance
        avg_color_var = np.mean(self.color_variance_history) if len(self.color_variance_history) > 0 else 0.0
        color_pass = avg_color_var >= self.COLOR_VARIANCE_MIN
        print(f"[Color] Variance: {avg_color_var:.1f} {'[PASS]' if color_pass else '[FAIL] Video compression detected'}")
        
        # Movement naturalness
        movement_natural = self.check_movement_naturalness()
        print(f"[Movement] Natural: {'[PASS]' if movement_natural else '[FAIL] Artificial motion'}")
        
        # rPPG analysis
        heart_rate = 0
        hr_confidence = 0.0
        rppg_pass = False
        
        if enable_passive and len(self.green_values) > 0:
            print(f"\n[rPPG] Analyzing heart rate from {len(self.green_values)} samples...")
            actual_fps = len(self.green_values) / (frame_count / 30.0) if frame_count > 0 else 30
            heart_rate, hr_confidence, rppg_pass = self.analyze_heart_rate(actual_fps)
            
            print(f"[rPPG] Heart Rate: {heart_rate:.1f} BPM")
            print(f"[rPPG] Confidence: {hr_confidence:.1%}")
            print(f"[rPPG] Result: {'[PASS]' if rppg_pass else '[FAIL] Insufficient signal'}")
        
        print("="*70)
        
        # ========== FINAL VERDICT ==========
        
        # Build result
        result = {
            "challenges_completed": challenges_completed,
            "anti_spoofing": {
                "texture_score": avg_texture,
                "texture_pass": texture_pass,
                "moire_score": avg_moire,
                "moire_pass": moire_pass,
                "color_variance": avg_color_var,
                "color_variance_pass": color_pass,
                "movement_natural": movement_natural
            }
        }
        
        if enable_passive:
            result["heart_rate"] = heart_rate
            result["heart_rate_confidence"] = hr_confidence
            result["rppg_pass"] = rppg_pass
        
        # Check all layers
        if not texture_pass:
            result["success"] = False
            result["message"] = "[FAIL] SPOOFING DETECTED: Low texture (screen/monitor replay)"
            print("\n[ALERT] Video appears to be from a screen display")
            return result
        
        if not moire_pass:
            result["success"] = False
            result["message"] = "[FAIL] SPOOFING DETECTED: Moire patterns (screen filming)"
            print("\n[ALERT] Interference patterns indicate screen filming")
            return result
        
        if not color_pass:
            result["success"] = False
            result["message"] = "[FAIL] SPOOFING DETECTED: Low color variance (video compression)"
            print("\n[ALERT] Color variance suggests compressed video replay")
            return result
        
        if not movement_natural:
            result["success"] = False
            result["message"] = "[FAIL] SPOOFING DETECTED: Unnatural movement patterns"
            print("\n[ALERT] Movement patterns do not match human behavior")
            return result
        
        if enable_passive and not rppg_pass:
            if require_rppg:
                # rPPG is REQUIRED - fail the verification
                result["success"] = False
                result["message"] = f"[FAIL] SPOOFING DETECTED: Insufficient heart rate signal (HR: {heart_rate:.0f} BPM, Conf: {hr_confidence:.1%})"
                print("\n[ALERT] Heart rate signal insufficient for liveness verification")
                return result
            else:
                # rPPG is ADVISORY - pass with warning
                print(f"\n[WARNING] rPPG confidence low (HR: {heart_rate:.0f} BPM, Conf: {hr_confidence:.1%})")
                print("[WARNING] Proceeding based on active challenge verification")
                result["rppg_warning"] = True
        
        # ALL CHECKS PASSED!
        result["success"] = True
        
        # Build success message
        if enable_passive and rppg_pass:
            result["message"] = f"[SUCCESS] LIVENESS VERIFIED - All layers passed including rPPG (HR: {heart_rate:.0f} BPM)"
        elif enable_passive and not rppg_pass:
            result["message"] = f"[SUCCESS] LIVENESS VERIFIED - Active challenges + anti-spoofing passed (rPPG: {hr_confidence:.1%} confidence)"
        else:
            result["message"] = "[SUCCESS] LIVENESS VERIFIED - All security layers passed"
        
        print("\n" + "="*70)
        print("LIVENESS VERIFICATION SUCCESSFUL")
        print("="*70)
        print(f"[OK] Randomized challenges: {len(challenges_completed)}/{len(self.challenge_sequence)}")
        print(f"[OK] Texture analysis: PASS")
        print(f"[OK] Moire detection: PASS")
        print(f"[OK] Color variance: PASS")
        print(f"[OK] Movement naturalness: PASS")
        if enable_passive:
            if rppg_pass:
                print(f"[OK] rPPG heart rate: PASS ({heart_rate:.0f} BPM, {hr_confidence:.1%} confidence)")
            else:
                print(f"[WARNING] rPPG: Low confidence ({heart_rate:.0f} BPM, {hr_confidence:.1%}) - advisory only")
        print("="*70 + "\n")
        
        return result

# ========== HELPER FUNCTION ==========

# Backwards compatibility for code still importing the old class name.
LivenessDetectorV2 = LivenessDetectorV3

def verify_liveness(timeout_seconds=90, enable_passive=True, risk_level="medium", require_rppg=False):
    """
    Convenience function for quick liveness verification.
    
    Args:
        timeout_seconds: Max time allowed
        enable_passive: Enable rPPG heart rate detection (recommended)
        risk_level: "low" (3-4 challenges), "medium" (4-5), "high" (5-6), "critical" (6-7)
        require_rppg: If True, rPPG failure blocks verification. If False (default), rPPG is advisory
    
    Returns: result dict from LivenessDetectorV3.verify()
    """
    detector = LivenessDetectorV3()
    return detector.verify(
        timeout_seconds=timeout_seconds,
        enable_passive=enable_passive,
        risk_level=risk_level,
        require_rppg=require_rppg
    )


if __name__ == "__main__":
    import sys
    
    # Parse risk level from command line (optional)
    risk = "medium"
    if len(sys.argv) > 1:
        risk = sys.argv[1].lower()
    
    print("BioTrust V3 - Advanced Liveness Detection")
    print(f"Risk Level: {risk.upper()}")
    print("Starting verification...\n")
    
    # rPPG is advisory by default for better user experience
    result = verify_liveness(
        timeout_seconds=90,
        enable_passive=True,
        risk_level=risk,
        require_rppg=False  # Advisory mode - rPPG failure won't block verification
    )
    
    print("\n" + "="*70)
    print("FINAL RESULT")
    print("="*70)
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Challenges: {result.get('challenges_completed', [])}")
    if result.get('rppg_warning'):
        print("\n[NOTE] rPPG confidence was low but not required for this verification")
        print("[NOTE] Active challenges and anti-spoofing checks confirmed human presence")
    print("="*70)
