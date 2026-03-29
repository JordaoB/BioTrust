"""
BioTrust - Advanced Liveness Detector V3
========================================
ANTI-SPOOFING SYSTEM WITH RANDOMIZED CHALLENGES

Features:
- 5 types of challenges (blink, smile, turn_left, turn_right, eyebrows_up)
- Randomized sequence (3-5 challenges per session)
- Multi-layer video detection (texture, moiré, color variance, heart rate)
- Natural movement variance analysis

Version: 2.2 (fixed: EAR threshold, CONSEC_FRAMES, anti-spoof thresholds,
              face_pitch range, smile baseline accumulation)
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
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from .rppg_detector import RPPG_Detector, RPPGConfig
except ImportError:
    from src.core.rppg_detector import RPPG_Detector, RPPGConfig

try:
    from backend.utils.logger import logger, log_liveness_attempt
    LOGGING_ENABLED = True
except ImportError:
    LOGGING_ENABLED = False
    print("[WARNING] Logger not available - running without structured logging")


class LivenessDetectorV3:
    """
    Advanced liveness detector with randomized challenges and deep anti-spoofing.
    """

    def __init__(self):

        # ========== CHALLENGE CONFIGURATION ==========
        self.CHALLENGE_TYPES = {
            "blink": {
                "name": "Blink 3 times",
                "instruction": "Blink your eyes 3 times",
                "required_count": 3,
                "timeout_frames": 450
            },
            "smile": {
                "name": "Smile",
                "instruction": "Smile at the camera",
                "required_count": 1,
                "timeout_frames": 300
            },
            "turn_left": {
                "name": "Turn your head LEFT",
                "instruction": "Turn your head to your left",
                "required_count": 1,
                "timeout_frames": 360
            },
            "turn_right": {
                "name": "Turn your head RIGHT",
                "instruction": "Turn your head to your right",
                "required_count": 1,
                "timeout_frames": 360
            },
            "eyebrows_up": {
                "name": "Raise your eyebrows",
                "instruction": "Raise your eyebrows",
                "required_count": 1,
                "timeout_frames": 450
            }
        }

        # Challenge state
        self.challenge_sequence = []
        self.current_challenge_idx = 0
        self.challenge_counter = 0
        self.challenge_start_frame = 0
        self.must_return_neutral = False
        self.challenge_armed = False
        self.frontal_stable_counter = 0

        # ========== DETECTION THRESHOLDS ==========
        # FIX #1: EAR raised 0.18→0.22 (more permissive for compressed webcam streams)
        self.EAR_THRESHOLD = 0.22
        self.SMILE_MOUTH_WIDTH_RATIO = 1.25
        self.EYEBROW_EYE_RATIO_THRESHOLD = 0.36
        self.HEAD_TURN_RATIO_LEFT = 1.15
        self.HEAD_TURN_RATIO_RIGHT = 0.80
        self.HEAD_FRONTAL_RANGE = (0.85, 1.15)
        # FIX #1: CONSEC_FRAMES 2→1 (at 12fps over network, 2 consecutive is too strict)
        self.CONSEC_FRAMES = 1
        self.CHALLENGE_ARM_FRAMES = 12
        self.MIN_FACE_FRAME_RATIO = 0.08
        self.MAX_FACE_FRAME_RATIO = 0.52
        self.FACE_CENTER_TOLERANCE_X = 0.20
        self.FACE_CENTER_TOLERANCE_Y = 0.24
        self.SCALE_DRIFT_TOLERANCE = 0.22
        self.TURN_HOLD_FRAMES = 6
        self.NEUTRAL_RETURN_HOLD_FRAMES = 5

        # ========== ANTI-SPOOFING THRESHOLDS ==========
        # FIX #2: All thresholds relaxed for H.264/MJPEG compressed laptop webcams
        # TEXTURE: 0.18→0.08  (compressed streams have lower Laplacian variance)
        # MOIRE:   0.40→0.55  (raise ceiling so legitimate cameras don't false-positive)
        # COLOR_VAR: 50→25    (JPEG artifacts reduce color variance)
        self.TEXTURE_THRESHOLD = 0.08
        self.MOIRE_THRESHOLD = 0.55
        self.COLOR_VARIANCE_MIN = 25
        self.MOVEMENT_VARIANCE_MIN = 0.8
        self.RPPG_CONFIDENCE_MIN = 0.35
        self.RPPG_SIGNAL_VARIABILITY_MIN = 0.4
        self.MIN_BPM = 45
        self.MAX_BPM = 160
        # Additional web anti-spoofing guardrails for static photo/screen attacks.
        self.STATIC_FACE_DIFF_MIN = 0.90
        self.STATIC_MOVEMENT_VAR_MIN = 0.030

        # ========== STATE VARIABLES ==========
        self.liveness_verified = False
        self.prev_eye_midpoint = None
        self.blink_frame_counter = 0
        self.mouth_open_armed = False
        self.challenge_armed = False
        self.frontal_stable_counter = 0
        self.turn_hold_counter = 0
        self.neutral_hold_counter = 0
        self.stable_scale_buffer = []
        self.challenge_face_scale_ref = None

        # Anti-spoofing data
        self.texture_scores = []
        self.moire_scores = []
        self.color_variance_history = []
        self.micro_movements = []
        self.green_values = []
        self.timestamps = []
        self.face_diff_scores = []
        self.prev_face_gray = None

        # Baseline for smile — FIX #4: accumulator list instead of overwrite
        self.baseline_mouth_width = None
        self.baseline_frames_collected = 0
        self._baseline_accumulator = []

        # ========== MEDIAPIPE SETUP ==========
        mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.MOUTH_OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
        self.MOUTH_VERTICAL = [13, 14]
        self.LEFT_EYEBROW = [70, 63, 105, 66, 107]
        self.RIGHT_EYEBROW = [300, 293, 334, 296, 336]
        self.FOREHEAD = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323]

        self.WINDOW_NAME = "BioTrust V3 - Advanced Liveness"

        # Dedicated rPPG pipeline integrated into liveness responses.
        self.rppg_detector = RPPG_Detector(RPPGConfig(fps=30.0, buffer_seconds=10.0))
        self.latest_rppg_bpm = None
        self.latest_rppg_raw_bpm = None
        self.latest_rppg_ready = False
        self.latest_rppg_quality_score = 0.0
        self.latest_rppg_quality_metrics = {}
        self.latest_rppg_debug_visual = None
        self.latest_rppg_debug_reason = None
        self.rppg_precheck_completed = False
        self.rppg_bpm_stable_streak = 0
        self.rppg_precheck_start_frame = 0
        self.WEB_EXPECTED_FPS = 12.0
        self.RPPG_PRECHECK_REQUIRED_STREAK = 4
        self.RPPG_PRECHECK_MAX_WAIT_SECONDS = 12.0
        self.latest_rppg_movement_correlation = 0.0

    # ========== DETECTION METHODS ==========

    def calculate_ear(self, eye_landmarks):
        A = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
        B = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
        C = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
        return (A + B) / (2.0 * C)

    def calculate_mar(self, mouth_vertical_landmarks, mouth_landmarks=None):
        vertical_dist = dist.euclidean(mouth_vertical_landmarks[0], mouth_vertical_landmarks[1])
        if mouth_landmarks is None or len(mouth_landmarks) < 11:
            return vertical_dist
        left_corner = mouth_landmarks[0]
        right_corner = mouth_landmarks[10]
        mouth_width = dist.euclidean(left_corner, right_corner)
        return vertical_dist / (mouth_width + 1e-6)

    def detect_smile(self, mouth_landmarks):
        """
        FIX #4: Accumulate a true mean baseline over the first 30 frames.
        Previous code overwrote baseline_mouth_width every frame, so the
        baseline was just frame-30's value — easily inflated if the user
        was already smiling while reading instructions.
        """
        if len(mouth_landmarks) < 4:
            return False

        left_corner = mouth_landmarks[0]
        right_corner = mouth_landmarks[6] if len(mouth_landmarks) > 6 else mouth_landmarks[-1]
        current_width = dist.euclidean(left_corner, right_corner)

        if self.baseline_mouth_width is None:
            if self.baseline_frames_collected < 30:
                self._baseline_accumulator.append(current_width)
                self.baseline_frames_collected += 1
                if self.baseline_frames_collected == 30:
                    self.baseline_mouth_width = np.mean(self._baseline_accumulator)
                return False
            # Safety fallback — should not reach here, but just in case
            self.baseline_mouth_width = current_width

        width_ratio = current_width / (self.baseline_mouth_width + 1e-6)
        return width_ratio > self.SMILE_MOUTH_WIDTH_RATIO

    def detect_eyebrows_raised(self, left_brow, right_brow, left_eye, right_eye):
        left_brow_y = np.mean([p[1] for p in left_brow])
        right_brow_y = np.mean([p[1] for p in right_brow])
        left_eye_y = np.mean([p[1] for p in left_eye])
        right_eye_y = np.mean([p[1] for p in right_eye])
        avg_distance = ((left_eye_y - left_brow_y) + (right_eye_y - right_brow_y)) / 2
        interocular = np.linalg.norm(np.mean(left_eye, axis=0) - np.mean(right_eye, axis=0)) + 1e-6
        normalized_distance = avg_distance / interocular
        return normalized_distance > self.EYEBROW_EYE_RATIO_THRESHOLD

    def is_face_scale_stable(self, current_face_scale):
        if self.challenge_face_scale_ref is None:
            return True
        if current_face_scale <= 0:
            return False
        drift = abs(current_face_scale - self.challenge_face_scale_ref) / (self.challenge_face_scale_ref + 1e-6)
        return drift <= self.SCALE_DRIFT_TOLERANCE

    def analyze_head_pose(self, nose, left_eye_center, right_eye_center):
        dist_left = np.linalg.norm(nose - left_eye_center)
        dist_right = np.linalg.norm(nose - right_eye_center)
        symmetry_ratio = dist_left / (dist_right + 1e-6)
        is_frontal = self.HEAD_FRONTAL_RANGE[0] < symmetry_ratio < self.HEAD_FRONTAL_RANGE[1]
        is_left = symmetry_ratio > self.HEAD_TURN_RATIO_LEFT
        is_right = symmetry_ratio < self.HEAD_TURN_RATIO_RIGHT
        return is_frontal, is_left, is_right, symmetry_ratio

    # ========== ANTI-SPOOFING METHODS ==========

    def analyze_texture(self, face_roi):
        if face_roi.size == 0:
            return 0.5
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return min(variance / 200.0, 1.0)

    def detect_moire_pattern(self, face_roi):
        if face_roi.size == 0 or min(face_roi.shape[:2]) < 20:
            return 0.0
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)
        magnitude = magnitude / (np.max(magnitude) + 1e-6)
        h, w = magnitude.shape
        center = magnitude[h//3:2*h//3, w//3:2*w//3]
        outer = np.concatenate([
            magnitude[:h//3, :].flatten(),
            magnitude[2*h//3:, :].flatten(),
            magnitude[:, :w//3].flatten(),
            magnitude[:, 2*w//3:].flatten()
        ])
        center_energy = np.mean(center)
        outer_energy = np.mean(outer)
        return min(outer_energy / (center_energy + 1e-6) / 5.0, 1.0)

    def analyze_color_variance(self, face_roi):
        if face_roi.size == 0:
            return 0
        b_var = np.var(face_roi[:, :, 0])
        g_var = np.var(face_roi[:, :, 1])
        r_var = np.var(face_roi[:, :, 2])
        return (b_var + g_var + r_var) / 3.0

    def check_movement_naturalness(self):
        if len(self.micro_movements) < 60:
            return True
        recent_movements = np.array(self.micro_movements[-90:])
        movement_var = np.var(recent_movements)
        return movement_var > self.MOVEMENT_VARIANCE_MIN

    def analyze_face_temporal_diff(self, face_roi):
        if face_roi.size == 0:
            return None

        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        gray = cv2.resize(gray, (96, 96), interpolation=cv2.INTER_AREA)

        if self.prev_face_gray is None:
            self.prev_face_gray = gray
            return None

        diff = cv2.absdiff(gray, self.prev_face_gray)
        self.prev_face_gray = gray
        return float(np.mean(diff))

    def extract_rppg_signal(self, frame, face_landmarks):
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
        mean_green = cv2.mean(frame[:, :, 1], mask=mask)[0]
        return mean_green

    def analyze_heart_rate(self, fps):
        min_samples = int(fps * 5)
        if len(self.green_values) < min_samples:
            return 0, 0.0, False
        signal_array = np.array(self.green_values)
        signal_detrended = signal.detrend(signal_array)
        nyquist = fps / 2.0
        low = 0.83 / nyquist
        high = 2.5 / nyquist
        b, a = signal.butter(4, [low, high], btype='band')
        filtered = signal.filtfilt(b, a, signal_detrended)
        n = len(filtered)
        fft_vals = fft(filtered)
        fft_freq = fftfreq(n, 1.0 / fps)
        positive_idx = np.where(fft_freq > 0)
        fft_freq = fft_freq[positive_idx]
        fft_mag = np.abs(fft_vals[positive_idx])
        valid_mask = (fft_freq >= 0.83) & (fft_freq <= 2.5)
        valid_freq = fft_freq[valid_mask]
        valid_mag = fft_mag[valid_mask]
        if len(valid_mag) == 0:
            return 0, 0.0, False
        peak_idx = np.argmax(valid_mag)
        peak_freq = valid_freq[peak_idx]
        heart_rate = peak_freq * 60.0
        mean_mag = np.mean(valid_mag)
        peak_mag = valid_mag[peak_idx]
        confidence = min(peak_mag / (mean_mag + 1e-6) / 10.0, 1.0)
        signal_variability = np.std(np.diff(signal_array))
        variability_ok = signal_variability >= self.RPPG_SIGNAL_VARIABILITY_MIN
        is_valid = (self.MIN_BPM <= heart_rate <= self.MAX_BPM) and \
                   (confidence >= self.RPPG_CONFIDENCE_MIN) and \
                   variability_ok
        return heart_rate, confidence, is_valid

    # ========== WEB SESSION METHODS ==========

    def start_web_session(self, risk_level="medium"):
        """
        Initialize a web-based liveness session.
        NOTE: No cv2.flip() here — the browser CSS handles mirroring for display.
        The raw (un-flipped) frame is what MediaPipe expects.
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
        self.turn_hold_counter = 0
        self.neutral_hold_counter = 0
        self.stable_scale_buffer = []
        self.challenge_face_scale_ref = None
        self.baseline_mouth_width = None
        self.baseline_frames_collected = 0
        self._baseline_accumulator = []   # FIX #4: reset accumulator on new session
        self.frame_count_web = 0

        # Clear anti-spoofing data
        self.texture_scores = []
        self.moire_scores = []
        self.color_variance_history = []
        self.micro_movements = []
        self.green_values = []
        self.timestamps = []
        self.face_diff_scores = []
        self.prev_face_gray = None

        self.rppg_detector.reset()
        self.latest_rppg_bpm = None
        self.latest_rppg_raw_bpm = None
        self.latest_rppg_ready = False
        self.latest_rppg_quality_score = 0.0
        self.latest_rppg_quality_metrics = {}
        self.latest_rppg_debug_visual = None
        self.latest_rppg_debug_reason = None
        self.latest_rppg_movement_correlation = 0.0
        self.rppg_precheck_start_frame = self.frame_count_web
        self.rppg_precheck_completed = False
        self.rppg_bpm_stable_streak = 0

        # Generate challenge sequence
        risk_mapping = {
            "low": (2, 3),
            "medium": (3, 4),
            "high": (4, 5),
            "critical": (5, 5)
        }
        min_challenges, max_challenges = risk_mapping.get(risk_level, (3, 4))
        num_challenges = random.randint(min_challenges, min(max_challenges, len(self.CHALLENGE_TYPES)))
        available_challenges = list(self.CHALLENGE_TYPES.keys())
        self.challenge_sequence = random.sample(available_challenges, num_challenges)

        print(f"\n[WEB SESSION] Started with {len(self.challenge_sequence)} challenges: {self.challenge_sequence}")

        first_challenge = self.challenge_sequence[0]
        return {
            "total_challenges": len(self.challenge_sequence),
            "challenges": [self.CHALLENGE_TYPES[c]["name"] for c in self.challenge_sequence],
            "current_challenge": {
                "type": first_challenge,
                "name": self.CHALLENGE_TYPES[first_challenge]["name"],
                "instruction": self.CHALLENGE_TYPES[first_challenge]["instruction"],
            }
        }

    def process_web_frame(self, frame):
        """
        Process a single frame from browser webcam.

        IMPORTANT: Do NOT flip the frame here.
        The browser applies CSS scaleX(-1) for the mirror preview.
        The raw frame (as sent by the browser) is the correct orientation for MediaPipe.
        """
        if not hasattr(self, 'frame_count_web'):
            return {"status": "failed", "feedback": "Session not started - call start_web_session() first"}

        self.frame_count_web += 1

        rppg_result = self.rppg_detector.process_frame(frame)
        self.latest_rppg_bpm = rppg_result.get("bpm")
        self.latest_rppg_raw_bpm = rppg_result.get("raw_bpm")
        self.latest_rppg_ready = bool(rppg_result.get("signal_ready", False))
        self.latest_rppg_quality_score = float(rppg_result.get("quality_score", 0.0) or 0.0)
        self.latest_rppg_quality_metrics = rppg_result.get("quality_metrics") or {}
        self.latest_rppg_debug_visual = rppg_result.get("debug_visual")
        self.latest_rppg_debug_reason = rppg_result.get("debug_reason")
        self.latest_rppg_movement_correlation = float(rppg_result.get("movement_correlation", 0.5) or 0.5)

        def with_rppg(payload):
            # Show BPM when signal is actually ready so users get realtime feedback,
            # while precheck gate (blink + stability) still blocks spoof progression.
            payload.setdefault("face_detected", True)
            payload["rppg_bpm"] = self.latest_rppg_bpm if self.latest_rppg_ready else None
            payload["rppg_raw_bpm"] = self.latest_rppg_raw_bpm if self.latest_rppg_ready else None
            payload["rppg_signal_ready"] = self.latest_rppg_ready
            payload["rppg_quality_score"] = self.latest_rppg_quality_score
            payload["rppg_quality_metrics"] = self.latest_rppg_quality_metrics
            payload["rppg_debug_visual"] = self.latest_rppg_debug_visual
            payload["rppg_debug_reason"] = self.latest_rppg_debug_reason
            payload["rppg_movement_correlation"] = self.latest_rppg_movement_correlation
            return payload

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        h, w, _ = frame.shape

        if not results.multi_face_landmarks:
            base_progress = (
                20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0)
                if self.rppg_precheck_completed
                else (self.current_challenge_idx / len(self.challenge_sequence)) * 100
            )
            return with_rppg({
                "status": "in_progress",
                "progress": base_progress,
                "current_challenge": self._get_current_challenge_info(),
                "feedback": "Face not detected - position yourself in front of the camera.",
                "completed_challenges": self.current_challenge_idx,
                "face_detected": False,
            })

        face_landmarks = results.multi_face_landmarks[0]
        landmarks = np.array([[int(lm.x * w), int(lm.y * h)] for lm in face_landmarks.landmark])

        # Anti-spoofing (every 3 frames)
        x_coords = landmarks[:, 0]
        y_coords = landmarks[:, 1]
        x_min, x_max = max(0, int(min(x_coords))), min(w, int(max(x_coords)))
        y_min, y_max = max(0, int(min(y_coords))), min(h, int(max(y_coords)))
        face_w = max(1, x_max - x_min)
        face_h = max(1, y_max - y_min)
        face_frame_ratio = (face_w * face_h) / float(max(1, w * h))
        face_cx = (x_min + x_max) / 2.0
        face_cy = (y_min + y_max) / 2.0
        dx_norm = abs(face_cx - (w / 2.0)) / float(max(1.0, w / 2.0))
        dy_norm = abs(face_cy - (h / 2.0)) / float(max(1.0, h / 2.0))

        current_challenge_key = None
        if self.rppg_precheck_completed and self.current_challenge_idx < len(self.challenge_sequence):
            current_challenge_key = self.challenge_sequence[self.current_challenge_idx]

        # During active head-turn execution, allow wider face center drift.
        # Otherwise the turn itself can be blocked by strict centering checks.
        is_turn_challenge_active = (
            current_challenge_key in ("turn_left", "turn_right")
            and self.challenge_armed
            and not self.must_return_neutral
        )
        center_tolerance_x = self.FACE_CENTER_TOLERANCE_X * (1.75 if is_turn_challenge_active else 1.0)
        center_tolerance_y = self.FACE_CENTER_TOLERANCE_Y * (1.35 if is_turn_challenge_active else 1.0)

        if dx_norm > center_tolerance_x or dy_norm > center_tolerance_y:
            return with_rppg({
                "status": "in_progress",
                "progress": 20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0),
                "current_challenge": self._get_current_challenge_info(),
                "feedback": "Center your face in the camera to continue.",
                "completed_challenges": self.current_challenge_idx
            })

        if face_frame_ratio < self.MIN_FACE_FRAME_RATIO:
            return with_rppg({
                "status": "in_progress",
                "progress": 20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0),
                "current_challenge": self._get_current_challenge_info(),
                "feedback": "You are too far from the camera. Move a bit closer and keep your face centered.",
                "completed_challenges": self.current_challenge_idx
            })

        if face_frame_ratio > self.MAX_FACE_FRAME_RATIO:
            return with_rppg({
                "status": "in_progress",
                "progress": 20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0),
                "current_challenge": self._get_current_challenge_info(),
                "feedback": "Do not move too close to the camera. Step back slightly and keep a stable distance.",
                "completed_challenges": self.current_challenge_idx
            })

        if x_max > x_min and y_max > y_min and self.frame_count_web % 3 == 0:
            face_roi = frame[y_min:y_max, x_min:x_max]
            self.texture_scores.append(self.analyze_texture(face_roi))
            self.moire_scores.append(self.detect_moire_pattern(face_roi))
            self.color_variance_history.append(self.analyze_color_variance(face_roi))
            temporal_diff = self.analyze_face_temporal_diff(face_roi)
            if temporal_diff is not None:
                self.face_diff_scores.append(temporal_diff)

            # Continuous spoofing check with rolling window (not only at frame 30).
            # This catches attacks that appear later during the session.
            if len(self.texture_scores) >= 10:
                window = min(20, len(self.texture_scores))
                avg_texture = float(np.mean(self.texture_scores[-window:]))
                avg_moire = float(np.mean(self.moire_scores[-window:]))
                avg_color_var = float(np.mean(self.color_variance_history[-window:]))
                avg_face_diff = float(np.mean(self.face_diff_scores[-window:])) if self.face_diff_scores else 999.0
                movement_var = float(np.var(self.micro_movements[-45:])) if len(self.micro_movements) >= 45 else 999.0

                if avg_texture < self.TEXTURE_THRESHOLD:
                    return with_rppg({"status": "failed", "progress": 0,
                            "feedback": "SPOOFING DETECTED: Screen/monitor detected",
                            "anti_spoofing_failed": True, "reason": "screen_detected",
                            "current_challenge": self._get_current_challenge_info(),
                        "completed_challenges": 0})
                if avg_moire > self.MOIRE_THRESHOLD:
                    return with_rppg({"status": "failed", "progress": 0,
                            "feedback": "SPOOFING DETECTED: Interference pattern detected",
                            "anti_spoofing_failed": True, "reason": "moire_detected",
                            "current_challenge": self._get_current_challenge_info(),
                        "completed_challenges": 0})
                if avg_color_var < self.COLOR_VARIANCE_MIN:
                    return with_rppg({"status": "failed", "progress": 0,
                            "feedback": "SPOOFING DETECTED: Recorded video detected",
                            "anti_spoofing_failed": True, "reason": "video_detected",
                            "current_challenge": self._get_current_challenge_info(),
                        "completed_challenges": 0})

                # Static face heuristic: very low temporal variation + very low movement variance
                # strongly indicates a printed photo or phone screen held in front of camera.
                if avg_face_diff < self.STATIC_FACE_DIFF_MIN and movement_var < self.STATIC_MOVEMENT_VAR_MIN:
                    return with_rppg({"status": "failed", "progress": 0,
                            "feedback": "SPOOFING DETECTED: Static face pattern detected",
                            "anti_spoofing_failed": True, "reason": "static_face_detected",
                            "current_challenge": self._get_current_challenge_info(),
                        "completed_challenges": 0})

        # Extract facial features
        left_eye = landmarks[self.LEFT_EYE]
        right_eye = landmarks[self.RIGHT_EYE]
        left_eye_center = np.mean(left_eye, axis=0)
        right_eye_center = np.mean(right_eye, axis=0)
        current_face_scale = np.linalg.norm(left_eye_center - right_eye_center)
        eye_midpoint = (left_eye_center + right_eye_center) / 2

        nose = landmarks[1]
        mouth_outer = landmarks[self.MOUTH_OUTER[:min(len(self.MOUTH_OUTER), len(landmarks))]]
        mouth_vertical = landmarks[self.MOUTH_VERTICAL]
        left_brow = landmarks[self.LEFT_EYEBROW]
        right_brow = landmarks[self.RIGHT_EYEBROW]

        # Micro-movements
        movement = 0.0
        if self.prev_eye_midpoint is not None:
            movement = np.linalg.norm(eye_midpoint - self.prev_eye_midpoint)
            self.micro_movements.append(movement)
        self.prev_eye_midpoint = eye_midpoint

        # Phase 1 (mandatory): acquire stable rPPG before starting active challenges.
        if self.latest_rppg_ready and self.latest_rppg_bpm is not None:
            self.rppg_bpm_stable_streak += 1
        else:
            self.rppg_bpm_stable_streak = max(0, self.rppg_bpm_stable_streak - 1)

        if not self.rppg_precheck_completed:
            required_streak = self.RPPG_PRECHECK_REQUIRED_STREAK
            precheck_elapsed_frames = max(0, self.frame_count_web - self.rppg_precheck_start_frame)
            precheck_elapsed_seconds = precheck_elapsed_frames / max(self.WEB_EXPECTED_FPS, 1.0)

            if self.rppg_bpm_stable_streak >= required_streak:
                self.rppg_precheck_completed = True
                self.challenge_start_frame = self.frame_count_web
                self.challenge_armed = False
                self.frontal_stable_counter = 0
                return with_rppg({
                    "status": "in_progress",
                    "progress": 20.0,
                    "current_challenge": self._get_current_challenge_info(),
                    "feedback": "rPPG captured. Starting liveness challenges...",
                    "completed_challenges": self.current_challenge_idx
                })

            # Mobile fallback: if rPPG signal does not stabilize in time, continue with
            # active challenges instead of blocking indefinitely on this precheck screen.
            if precheck_elapsed_seconds >= self.RPPG_PRECHECK_MAX_WAIT_SECONDS:
                self.rppg_precheck_completed = True
                self.challenge_start_frame = self.frame_count_web
                self.challenge_armed = False
                self.frontal_stable_counter = 0
                return with_rppg({
                    "status": "in_progress",
                    "progress": 20.0,
                    "current_challenge": self._get_current_challenge_info(),
                    "feedback": "Weak rPPG signal on device. Continuing with liveness challenges...",
                    "completed_challenges": self.current_challenge_idx
                })

            streak_progress = (self.rppg_bpm_stable_streak / required_streak) * 20.0
            elapsed_progress = (precheck_elapsed_seconds / self.RPPG_PRECHECK_MAX_WAIT_SECONDS) * 19.5
            precheck_progress = min(20.0, max(streak_progress, elapsed_progress))

            if not self.latest_rppg_ready:
                precheck_feedback = "Measuring rPPG... keep your face centered and steady."
            else:
                precheck_feedback = "BPM captured. Starting challenges..."

            return with_rppg({
                "status": "in_progress",
                "progress": precheck_progress,
                "current_challenge": {
                    "type": "rppg_precheck",
                    "name": "Capture heart rate",
                    "instruction": "Look at the camera for a few seconds while we capture your BPM"
                },
                "feedback": precheck_feedback,
                "completed_challenges": 0
            })

        # Head pose
        is_frontal, is_left, is_right, _ = self.analyze_head_pose(nose, left_eye_center, right_eye_center)

        # FIX #3: face_pitch range widened 0.02–0.13 → 0.01–0.22
        # Rationale: at normal laptop webcam distance, nose sits ~15–18% below
        # eye midpoint relative to frame height — well outside the old 0.13 ceiling.
        nose_eye_ratio = (nose[1] - eye_midpoint[1]) / (h + 1e-6)
        face_pitch_ok = 0.01 < nose_eye_ratio < 0.22
        face_frontal = is_frontal and face_pitch_ok
        movement_ok = movement < 24

        # Detection metrics
        left_ear = self.calculate_ear(left_eye)
        right_ear = self.calculate_ear(right_eye)
        both_eyes_closed = (left_ear < self.EAR_THRESHOLD and right_ear < self.EAR_THRESHOLD)
        is_smiling = self.detect_smile(mouth_outer)
        are_eyebrows_raised = self.detect_eyebrows_raised(left_brow, right_brow, left_eye, right_eye)

        # All challenges done?
        if self.current_challenge_idx >= len(self.challenge_sequence):
            return with_rppg({
                "status": "completed",
                "progress": 100,
                "current_challenge": {"name": "Completed", "type": "done", "instruction": "Verification complete"},
                "feedback": "All checks completed!",
                "completed_challenges": len(self.challenge_sequence)
            })

        current_challenge = self.challenge_sequence[self.current_challenge_idx]
        challenge_info = self.CHALLENGE_TYPES[current_challenge]

        # Timeout check
        frames_in_challenge = self.frame_count_web - self.challenge_start_frame
        if frames_in_challenge > challenge_info["timeout_frames"]:
            return with_rppg({
                "status": "failed",
                "progress": 20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0),
                "current_challenge": self._get_current_challenge_info(),
                "feedback": f"Time expired: {challenge_info['name']}",
                "completed_challenges": self.current_challenge_idx
            })

        # Arm challenge — require stable frontal pose first
        if not self.challenge_armed:
            if face_frontal and movement_ok:
                self.frontal_stable_counter += 1
                self.stable_scale_buffer.append(float(current_face_scale))
                if len(self.stable_scale_buffer) > 45:
                    self.stable_scale_buffer = self.stable_scale_buffer[-45:]
                if self.frontal_stable_counter >= self.CHALLENGE_ARM_FRAMES:
                    self.challenge_armed = True
                    self.challenge_counter = 0
                    self.blink_frame_counter = 0
                    self.must_return_neutral = False
                    self.turn_hold_counter = 0
                    self.neutral_hold_counter = 0
                    window = self.stable_scale_buffer[-self.CHALLENGE_ARM_FRAMES:]
                    self.challenge_face_scale_ref = float(np.median(window)) if window else float(current_face_scale)
                    return with_rppg({
                        "status": "in_progress",
                        "progress": 20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0),
                        "current_challenge": self._get_current_challenge_info(),
                        "feedback": f"Ready! {challenge_info['instruction']}",
                        "completed_challenges": self.current_challenge_idx
                    })
            else:
                self.frontal_stable_counter = max(0, self.frontal_stable_counter - 1)
                self.stable_scale_buffer = self.stable_scale_buffer[-20:]

            return with_rppg({
                "status": "in_progress",
                "progress": 20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0),
                "current_challenge": self._get_current_challenge_info(),
                "feedback": "Look straight at the camera...",
                "completed_challenges": self.current_challenge_idx
            })

        # ========== CHALLENGE LOGIC ==========
        challenge_satisfied = False
        feedback = challenge_info["instruction"]
        face_scale_stable = self.is_face_scale_stable(current_face_scale)

        if not face_scale_stable:
            self.challenge_armed = False
            self.frontal_stable_counter = 0
            self.challenge_counter = 0
            self.blink_frame_counter = 0
            self.turn_hold_counter = 0
            self.neutral_hold_counter = 0
            self.challenge_face_scale_ref = None
            return with_rppg({
                "status": "in_progress",
                "progress": 20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0),
                "current_challenge": self._get_current_challenge_info(),
                "feedback": "Distance changed too much. Return to center and keep a stable distance to continue.",
                "completed_challenges": self.current_challenge_idx
            })

        if current_challenge == "blink":
            # FIX #1: CONSEC_FRAMES=1 — count blink when eyes open after being closed
            # even for just 1 frame (cloud latency makes 2-frame requirement unreliable)
            if face_frontal and movement_ok:
                if both_eyes_closed:
                    self.blink_frame_counter += 1
                else:
                    if self.blink_frame_counter >= self.CONSEC_FRAMES:
                        self.challenge_counter += 1
                        print(f"  [BLINK] {self.challenge_counter}/{challenge_info['required_count']}")
                    self.blink_frame_counter = 0
            else:
                self.blink_frame_counter = 0

            if self.challenge_counter >= challenge_info["required_count"]:
                challenge_satisfied = True

            feedback = f"{challenge_info['instruction']} ({self.challenge_counter}/{challenge_info['required_count']})"

        elif current_challenge == "smile":
            # Hold smile for 15 frames (~1.5s at 10fps, ~0.5s at 30fps)
            SMILE_HOLD = 15
            if is_smiling and face_frontal:
                self.challenge_counter += 1
                if self.challenge_counter >= SMILE_HOLD:
                    challenge_satisfied = True
            else:
                self.challenge_counter = max(0, self.challenge_counter - 1)
            feedback = challenge_info["instruction"]

        elif current_challenge == "turn_left":
            # FIX: browser CSS mirrors the preview (scaleX(-1)) but sends raw frame.
            # When the user turns to THEIR left, MediaPipe sees the head turn RIGHT
            # in the raw frame — so we must detect is_right here.
            if not self.must_return_neutral:
                if is_right:
                    self.turn_hold_counter += 1
                    if self.turn_hold_counter >= self.TURN_HOLD_FRAMES:
                        self.must_return_neutral = True
                        self.neutral_hold_counter = 0
                        feedback = "Turn detected - return to center"
                else:
                    self.turn_hold_counter = max(0, self.turn_hold_counter - 1)
            else:
                if face_frontal:
                    self.neutral_hold_counter += 1
                    if self.neutral_hold_counter >= self.NEUTRAL_RETURN_HOLD_FRAMES:
                        challenge_satisfied = True
                else:
                    self.neutral_hold_counter = max(0, self.neutral_hold_counter - 1)
                    feedback = "Return to center..."

        elif current_challenge == "turn_right":
            # FIX: same mirror logic — user turning RIGHT appears as LEFT in raw frame.
            if not self.must_return_neutral:
                if is_left:
                    self.turn_hold_counter += 1
                    if self.turn_hold_counter >= self.TURN_HOLD_FRAMES:
                        self.must_return_neutral = True
                        self.neutral_hold_counter = 0
                        feedback = "Turn detected - return to center"
                else:
                    self.turn_hold_counter = max(0, self.turn_hold_counter - 1)
            else:
                if face_frontal:
                    self.neutral_hold_counter += 1
                    if self.neutral_hold_counter >= self.NEUTRAL_RETURN_HOLD_FRAMES:
                        challenge_satisfied = True
                else:
                    self.neutral_hold_counter = max(0, self.neutral_hold_counter - 1)
                    feedback = "Return to center..."

        elif current_challenge == "eyebrows_up":
            EYEBROW_HOLD = 15
            if are_eyebrows_raised and face_frontal:
                self.challenge_counter += 1
                if self.challenge_counter >= EYEBROW_HOLD:
                    challenge_satisfied = True
            else:
                self.challenge_counter = max(0, self.challenge_counter - 1)
            feedback = challenge_info["instruction"]

        # Challenge completed — advance
        if challenge_satisfied:
            print(f"[WEB] Challenge {self.current_challenge_idx + 1}/{len(self.challenge_sequence)} DONE: {challenge_info['name']}")
            self.current_challenge_idx += 1
            self.challenge_start_frame = self.frame_count_web
            self.challenge_armed = False
            self.frontal_stable_counter = 0
            self.challenge_counter = 0
            self.blink_frame_counter = 0
            self.must_return_neutral = False
            self.turn_hold_counter = 0
            self.neutral_hold_counter = 0
            self.challenge_face_scale_ref = None

            if self.current_challenge_idx >= len(self.challenge_sequence):
                return with_rppg({
                    "status": "completed",
                    "progress": 100,
                    "current_challenge": {"name": "Completed", "type": "done", "instruction": "Verification complete"},
                    "feedback": "Verification complete!",
                    "completed_challenges": len(self.challenge_sequence)
                })

            return with_rppg({
                "status": "in_progress",
                "progress": 20.0 + ((self.current_challenge_idx / len(self.challenge_sequence)) * 80.0),
                "current_challenge": self._get_current_challenge_info(),
                "feedback": f"Challenge {self.current_challenge_idx}/{len(self.challenge_sequence)} completed!",
                "completed_challenges": self.current_challenge_idx
            })

        # Progress within current challenge (capped at 99% until truly done)
        challenge_range_start = 20.0
        challenge_range_size = 80.0
        base_progress = challenge_range_start + (
            (self.current_challenge_idx / len(self.challenge_sequence)) * challenge_range_size
        )
        if current_challenge == "blink":
            within = self.challenge_counter / challenge_info["required_count"]
        elif current_challenge in ("smile", "eyebrows_up"):
            within = self.challenge_counter / 15
        elif current_challenge in ("turn_left", "turn_right"):
            within = 0.5 if self.must_return_neutral else 0.0
        else:
            within = 0.0

        within = min(within, 0.99)
        progress = base_progress + ((within / len(self.challenge_sequence)) * challenge_range_size)

        return with_rppg({
            "status": "in_progress",
            "progress": min(progress, 99.0),
            "current_challenge": self._get_current_challenge_info(),
            "feedback": feedback,
            "completed_challenges": self.current_challenge_idx
        })

    def _get_current_challenge_info(self):
        if self.current_challenge_idx >= len(self.challenge_sequence):
            return {"name": "Completed", "type": "done", "instruction": "Verification complete"}
        challenge_key = self.challenge_sequence[self.current_challenge_idx]
        challenge = self.CHALLENGE_TYPES[challenge_key]
        return {
            "type": challenge_key,
            "name": challenge["name"],
            "instruction": challenge["instruction"]
        }

    # ========== DESKTOP VERIFY (unchanged) ==========

    def verify(self, timeout_seconds=90, enable_passive=True, risk_level="medium", require_rppg=False):
        """
        Run complete liveness verification via desktop OpenCV window.
        This method is for server-side/desktop use only — not called by the web flow.
        """
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
        self.turn_hold_counter = 0
        self.neutral_hold_counter = 0
        self.stable_scale_buffer = []
        self.challenge_face_scale_ref = None
        self.baseline_mouth_width = None
        self.baseline_frames_collected = 0
        self._baseline_accumulator = []
        self.wrong_move_count = 0
        self.wrong_move_cooldown = 0

        self.texture_scores = []
        self.moire_scores = []
        self.color_variance_history = []
        self.micro_movements = []
        self.green_values = []
        self.timestamps = []
        self.face_diff_scores = []
        self.prev_face_gray = None

        self.rppg_detector.reset()
        self.latest_rppg_bpm = None
        self.latest_rppg_raw_bpm = None
        self.latest_rppg_ready = False
        self.latest_rppg_debug_reason = None
        self.rppg_precheck_completed = False
        self.rppg_bpm_stable_streak = 0
        self.rppg_precheck_start_frame = 0

        risk_mapping = {
            "low": (3, 4), "medium": (4, 5), "high": (5, 6), "critical": (6, 7)
        }
        min_challenges, max_challenges = risk_mapping.get(risk_level, (4, 5))
        num_challenges = random.randint(min_challenges, min(max_challenges, len(self.CHALLENGE_TYPES)))
        available_challenges = list(self.CHALLENGE_TYPES.keys())
        self.challenge_sequence = random.sample(available_challenges, num_challenges)
        random.shuffle(self.challenge_sequence)

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            return {"success": False, "message": "[FAIL] Camera not accessible", "challenges_completed": []}

        frame_count = 0
        max_frames = timeout_seconds * 30
        challenges_completed = []

        try:
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_count += 1
                # Desktop mode: flip for mirror display (user sees themselves mirrored)
                frame = cv2.flip(frame, 1)

                rppg_result = self.rppg_detector.process_frame(frame)
                self.latest_rppg_bpm = rppg_result.get("bpm")
                self.latest_rppg_raw_bpm = rppg_result.get("raw_bpm")
                self.latest_rppg_ready = bool(rppg_result.get("signal_ready", False))
                self.latest_rppg_debug_reason = rppg_result.get("debug_reason")

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb)
                h, w, _ = frame.shape

                if results.multi_face_landmarks:
                    face_landmarks = results.multi_face_landmarks[0]
                    landmarks = np.array([[int(lm.x * w), int(lm.y * h)] for lm in face_landmarks.landmark])

                    left_eye = landmarks[self.LEFT_EYE]
                    right_eye = landmarks[self.RIGHT_EYE]
                    left_eye_center = np.mean(left_eye, axis=0)
                    right_eye_center = np.mean(right_eye, axis=0)
                    current_face_scale = np.linalg.norm(left_eye_center - right_eye_center)
                    eye_midpoint = (left_eye_center + right_eye_center) / 2
                    nose = landmarks[1]
                    mouth_outer = landmarks[self.MOUTH_OUTER[:min(len(self.MOUTH_OUTER), len(landmarks))]]
                    mouth_vertical = landmarks[self.MOUTH_VERTICAL]
                    left_brow = landmarks[self.LEFT_EYEBROW]
                    right_brow = landmarks[self.RIGHT_EYEBROW]

                    movement = 0.0
                    if self.prev_eye_midpoint is not None:
                        movement = np.linalg.norm(eye_midpoint - self.prev_eye_midpoint)
                    self.prev_eye_midpoint = eye_midpoint

                    is_frontal, is_left, is_right, _ = self.analyze_head_pose(nose, left_eye_center, right_eye_center)
                    nose_eye_ratio = (nose[1] - eye_midpoint[1]) / (h + 1e-6)
                    # FIX #3 applied to desktop mode too for consistency
                    face_frontal = is_frontal and (0.01 < nose_eye_ratio < 0.22)
                    movement_ok = movement < 24

                    left_ear = self.calculate_ear(left_eye)
                    right_ear = self.calculate_ear(right_eye)
                    both_eyes_closed = (left_ear < self.EAR_THRESHOLD and right_ear < self.EAR_THRESHOLD)
                    is_smiling = self.detect_smile(mouth_outer)
                    are_eyebrows_raised = self.detect_eyebrows_raised(left_brow, right_brow, left_eye, right_eye)

                    if self.current_challenge_idx < len(self.challenge_sequence):
                        current_challenge = self.challenge_sequence[self.current_challenge_idx]
                        challenge_info = self.CHALLENGE_TYPES[current_challenge]

                        if frame_count - self.challenge_start_frame > challenge_info["timeout_frames"]:
                            break

                        if not self.challenge_armed:
                            if face_frontal and movement_ok:
                                self.frontal_stable_counter += 1
                                self.stable_scale_buffer.append(float(current_face_scale))
                                if len(self.stable_scale_buffer) > 45:
                                    self.stable_scale_buffer = self.stable_scale_buffer[-45:]
                                if self.frontal_stable_counter >= self.CHALLENGE_ARM_FRAMES:
                                    self.challenge_armed = True
                                    self.challenge_counter = 0
                                    self.blink_frame_counter = 0
                                    self.turn_hold_counter = 0
                                    self.neutral_hold_counter = 0
                                    window = self.stable_scale_buffer[-self.CHALLENGE_ARM_FRAMES:]
                                    self.challenge_face_scale_ref = float(np.median(window)) if window else float(current_face_scale)
                            else:
                                self.frontal_stable_counter = 0
                                self.stable_scale_buffer = self.stable_scale_buffer[-20:]
                            continue

                        face_scale_stable = self.is_face_scale_stable(current_face_scale)
                        if not face_scale_stable:
                            self.challenge_armed = False
                            self.frontal_stable_counter = 0
                            self.challenge_counter = 0
                            self.blink_frame_counter = 0
                            self.turn_hold_counter = 0
                            self.neutral_hold_counter = 0
                            self.challenge_face_scale_ref = None
                            continue

                        challenge_satisfied = False
                        if current_challenge == "blink":
                            if face_frontal and movement_ok:
                                if both_eyes_closed:
                                    self.blink_frame_counter += 1
                                else:
                                    if self.blink_frame_counter >= self.CONSEC_FRAMES:
                                        self.challenge_counter += 1
                                    self.blink_frame_counter = 0
                            else:
                                self.blink_frame_counter = 0
                            if self.challenge_counter >= challenge_info["required_count"]:
                                challenge_satisfied = True

                        elif current_challenge == "smile":
                            if is_smiling and face_frontal:
                                self.challenge_counter += 1
                                if self.challenge_counter >= 15:
                                    challenge_satisfied = True

                        elif current_challenge == "turn_left":
                            if not self.must_return_neutral:
                                if is_left:
                                    self.turn_hold_counter += 1
                                    if self.turn_hold_counter >= self.TURN_HOLD_FRAMES:
                                        self.must_return_neutral = True
                                        self.neutral_hold_counter = 0
                                else:
                                    self.turn_hold_counter = max(0, self.turn_hold_counter - 1)
                            else:
                                if face_frontal:
                                    self.neutral_hold_counter += 1
                                    if self.neutral_hold_counter >= self.NEUTRAL_RETURN_HOLD_FRAMES:
                                        challenge_satisfied = True
                                else:
                                    self.neutral_hold_counter = max(0, self.neutral_hold_counter - 1)

                        elif current_challenge == "turn_right":
                            if not self.must_return_neutral:
                                if is_right:
                                    self.turn_hold_counter += 1
                                    if self.turn_hold_counter >= self.TURN_HOLD_FRAMES:
                                        self.must_return_neutral = True
                                        self.neutral_hold_counter = 0
                                else:
                                    self.turn_hold_counter = max(0, self.turn_hold_counter - 1)
                            else:
                                if face_frontal:
                                    self.neutral_hold_counter += 1
                                    if self.neutral_hold_counter >= self.NEUTRAL_RETURN_HOLD_FRAMES:
                                        challenge_satisfied = True
                                else:
                                    self.neutral_hold_counter = max(0, self.neutral_hold_counter - 1)

                        elif current_challenge == "eyebrows_up":
                            if are_eyebrows_raised and face_frontal:
                                self.challenge_counter += 1
                                if self.challenge_counter >= 15:
                                    challenge_satisfied = True

                        if challenge_satisfied:
                            challenges_completed.append(current_challenge)
                            self.current_challenge_idx += 1
                            self.challenge_counter = 0
                            self.blink_frame_counter = 0
                            self.challenge_armed = False
                            self.frontal_stable_counter = 0
                            self.challenge_start_frame = frame_count
                            self.must_return_neutral = False
                            self.turn_hold_counter = 0
                            self.neutral_hold_counter = 0
                            self.challenge_face_scale_ref = None

                            if self.current_challenge_idx >= len(self.challenge_sequence):
                                self.liveness_verified = True
                                break

                cv2.imshow(self.WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        if not self.liveness_verified:
            return {"success": False, "message": "[FAIL] Not all challenges completed",
                    "challenges_completed": challenges_completed}

        if require_rppg and self.latest_rppg_bpm is None:
            return {
                "success": False,
                "message": "[FAIL] Liveness passed but rPPG BPM not stable/available",
                "challenges_completed": challenges_completed,
                "rppg_bpm": self.latest_rppg_bpm,
                "rppg_raw_bpm": self.latest_rppg_raw_bpm,
                "rppg_signal_ready": self.latest_rppg_ready,
            }

        return {
            "success": True,
            "message": "[SUCCESS] LIVENESS VERIFIED",
            "challenges_completed": challenges_completed,
            "rppg_bpm": self.latest_rppg_bpm,
            "rppg_raw_bpm": self.latest_rppg_raw_bpm,
            "rppg_signal_ready": self.latest_rppg_ready,
        }


# Backwards compatibility
LivenessDetectorV2 = LivenessDetectorV3


def verify_liveness(timeout_seconds=90, enable_passive=True, risk_level="medium", require_rppg=False):
    detector = LivenessDetectorV3()
    return detector.verify(
        timeout_seconds=timeout_seconds,
        enable_passive=enable_passive,
        risk_level=risk_level,
        require_rppg=require_rppg
    )


if __name__ == "__main__":
    import sys
    risk = sys.argv[1].lower() if len(sys.argv) > 1 else "medium"
    result = verify_liveness(timeout_seconds=90, enable_passive=True, risk_level=risk, require_rppg=False)
    print(f"\nSuccess: {result['success']}")
    print(f"Message: {result['message']}")