"""
BioTrust - rPPG Detector (CHROM Method)
========================================
Remote photoplethysmography (rPPG) detector for real-time heart-rate estimation
from webcam frames using Chrominance-based (CHROM) method.

Pipeline per frame:
1) Face detection + fixed skin ROIs (forehead + upper cheeks)
2) CHROM signal extraction: 3*R - 2*G (robust to illumination/motion)
3) Circular temporal buffer (last N seconds)
4) Butterworth bandpass filtering (0.7-3.0 Hz)
5) FFT dominant frequency -> BPM
6) BPM smoothing with moving average over latest estimates

CHROM method combines R, G, B channels to emphasize pulse signal while
reducing motion artifacts and illumination changes (vs simple GREEN extraction).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import time

import cv2
import mediapipe as mp
import numpy as np
from scipy.signal import butter, filtfilt


@dataclass
class RPPGConfig:
    fps: float = 30.0
    buffer_seconds: float = 10.0
    low_hz: float = 0.7
    high_hz: float = 3.0
    bpm_min: float = 40.0
    bpm_max: float = 150.0
    smoothing_window: int = 5
    filter_order: int = 4


class RPPG_Detector:
    """
    Real-time rPPG detector based on facial skin color variations.

    Notes:
    - Expects BGR frames (OpenCV default).
    - Returns stabilized BPM once enough signal history is available.
    """

    # Fixed Face Mesh landmark sets for skin ROIs.
    _FOREHEAD_IDX = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288]
    _LEFT_UPPER_CHEEK_IDX = [50, 101, 118, 119, 100, 126, 142, 203, 206, 205, 187, 147]
    _RIGHT_UPPER_CHEEK_IDX = [280, 330, 347, 348, 329, 355, 371, 423, 426, 425, 411, 376]

    def __init__(self, config: Optional[RPPGConfig] = None) -> None:
        self.config = config or RPPGConfig()

        self.buffer_size = int(self.config.buffer_seconds * self.config.fps)
        self.green_buffer = np.zeros(self.buffer_size, dtype=np.float64)
        self.time_buffer = np.zeros(self.buffer_size, dtype=np.float64)
        self.movement_buffer = np.zeros(self.buffer_size, dtype=np.float64)
        self.buffer_index = 0
        self.samples_collected = 0

        self.bpm_history = deque(maxlen=self.config.smoothing_window)
        self.movement_history = deque(maxlen=self.config.smoothing_window)
        self.last_face_center = None

        mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def reset(self) -> None:
        """Reset temporal buffers and BPM history."""
        self.green_buffer.fill(0.0)
        self.time_buffer.fill(0.0)
        self.movement_buffer.fill(0.0)
        self.buffer_index = 0
        self.samples_collected = 0
        self.bpm_history.clear()
        self.movement_history.clear()
        self.last_face_center = None

    def close(self) -> None:
        """Release MediaPipe resources."""
        self.face_mesh.close()

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> Dict[str, object]:
        """
        Process one frame and estimate BPM.

        Returns:
            Dict with:
            - bpm: stabilized BPM (moving average), or None
            - raw_bpm: current FFT BPM before smoothing, or None
            - face_detected: bool
            - signal_ready: bool (enough samples for estimation)
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": False,
                "signal_ready": False,
                "debug_reason": "invalid_frame",
            }

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.face_mesh.process(frame_rgb)

        if not result.multi_face_landmarks:
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": False,
                "signal_ready": self._has_min_samples(),
                "debug_reason": "face_not_detected",
            }

        face_landmarks = result.multi_face_landmarks[0]
        movement_magnitude = self._calculate_face_movement(frame_bgr, face_landmarks)
        chrom_payload = self._extract_chrom_signal(frame_bgr, face_landmarks)
        mean_green = chrom_payload["signal"] if chrom_payload is not None else None
        debug_visual = chrom_payload["debug_visual"] if chrom_payload is not None else None

        if mean_green is None:
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": True,
                "signal_ready": self._has_min_samples(),
                "quality_score": 0.0,
                "quality_metrics": {},
                "debug_visual": None,
                "debug_reason": "roi_signal_unavailable",
            }

        sample_ts = float(timestamp if timestamp is not None else time.monotonic())
        self._append_green_value(mean_green, sample_ts, movement_magnitude)

        if not self._has_min_samples():
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": True,
                "signal_ready": False,
                "quality_score": 0.0,
                "quality_metrics": {},
                "debug_visual": debug_visual,
                "debug_reason": "insufficient_signal_duration",
            }

        fft_result = self._estimate_bpm_fft()
        if fft_result is None:
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": True,
                "signal_ready": True,
                "quality_score": 0.0,
                "quality_metrics": {},
                "debug_visual": debug_visual,
                "debug_reason": "bpm_estimation_failed",
            }

        raw_bpm = float(fft_result["raw_bpm"])

        if self.config.bpm_min <= raw_bpm <= self.config.bpm_max:
            self.bpm_history.append(raw_bpm)

        stabilized_bpm = float(np.mean(self.bpm_history)) if self.bpm_history else None
        quality_metrics = {
            "snr": float(fft_result["snr"]),
            "peak_power_ratio": float(fft_result["peak_power_ratio"]),
            "pulse_rms_ratio": float(fft_result["pulse_rms_ratio"]),
        }
        quality_score = self._compute_quality_score(quality_metrics)

        debug_reason = "ok" if stabilized_bpm is not None else "raw_bpm_out_of_range"
        
        # Calculate movement-rPPG correlation (higher = more genuine)
        movement_correlation = self._calculate_movement_correlation()

        return {
            "bpm": stabilized_bpm,
            "raw_bpm": raw_bpm,
            "face_detected": True,
            "signal_ready": True,
            "quality_score": quality_score,
            "quality_metrics": quality_metrics,
            "debug_visual": debug_visual,
            "debug_reason": debug_reason,
            "movement_correlation": movement_correlation,
        }

    def _has_min_samples(self) -> bool:
        # At least 5s of signal is needed for stable spectral estimation.
        signal, timestamps = self._ordered_signal_and_timestamps()
        if signal.size < 16 or timestamps.size < 2:
            return False

        duration = float(timestamps[-1] - timestamps[0])
        if duration <= 0.0:
            return False

        return duration >= 5.0

    def _append_green_value(self, value: float, timestamp: float, movement: float = 0.0) -> None:
        self.green_buffer[self.buffer_index] = value
        self.time_buffer[self.buffer_index] = timestamp
        self.movement_buffer[self.buffer_index] = movement
        self.buffer_index = (self.buffer_index + 1) % self.buffer_size
        self.samples_collected = min(self.samples_collected + 1, self.buffer_size)

    def _ordered_signal(self) -> np.ndarray:
        if self.samples_collected < self.buffer_size:
            return self.green_buffer[: self.samples_collected].copy()

        # Rebuild chronological order from circular buffer.
        return np.concatenate(
            [self.green_buffer[self.buffer_index :], self.green_buffer[: self.buffer_index]]
        )

    def _ordered_timestamps(self) -> np.ndarray:
        if self.samples_collected < self.buffer_size:
            return self.time_buffer[: self.samples_collected].copy()

        return np.concatenate(
            [self.time_buffer[self.buffer_index :], self.time_buffer[: self.buffer_index]]
        )

    def _ordered_signal_and_timestamps(self) -> Tuple[np.ndarray, np.ndarray]:
        return self._ordered_signal(), self._ordered_timestamps()

    def _estimate_sampling_rate(self, timestamps: np.ndarray) -> Optional[float]:
        if timestamps.size < 2:
            return None

        diffs = np.diff(timestamps)
        # Keep only plausible positive frame intervals.
        diffs = diffs[(diffs > 0.0) & (diffs < 1.0)]
        if diffs.size == 0:
            return None

        dt = float(np.median(diffs))
        if dt <= 0.0:
            return None

        fs = 1.0 / dt
        # Clamp to sensible webcam processing range.
        fs = float(np.clip(fs, 5.0, 120.0))
        return fs

    def _extract_chrom_signal(self, frame_bgr: np.ndarray, face_landmarks) -> Optional[Dict[str, object]]:
        """Extract CHROM (chrominance) signal from ROIs plus debug visuals."""
        h, w = frame_bgr.shape[:2]

        forehead = self._landmarks_to_points(face_landmarks, self._FOREHEAD_IDX, w, h)
        left_cheek = self._landmarks_to_points(face_landmarks, self._LEFT_UPPER_CHEEK_IDX, w, h)
        right_cheek = self._landmarks_to_points(face_landmarks, self._RIGHT_UPPER_CHEEK_IDX, w, h)

        roi_signals: List[float] = []
        roi_points: Dict[str, List[List[float]]] = {}
        roi_values: Dict[str, float] = {}
        for name, polygon in (("forehead", forehead), ("left_cheek", left_cheek), ("right_cheek", right_cheek)):
            chrom_signal = self._mean_chrom_in_polygon(frame_bgr, polygon)
            if chrom_signal is not None:
                roi_signals.append(chrom_signal)
            roi_values[name] = float(chrom_signal)
            roi_points[name] = self._normalize_polygon(polygon, w, h)

        if not roi_signals:
            return None

        # Average CHROM signal across all ROIs
        return {
            "signal": float(np.mean(roi_signals)),
            "debug_visual": {
                "rois": roi_points,
                "roi_values": roi_values,
            },
        }

    @staticmethod
    def _normalize_polygon(polygon: np.ndarray, width: int, height: int) -> List[List[float]]:
        out: List[List[float]] = []
        w = float(max(1, width))
        h = float(max(1, height))
        for pt in polygon:
            out.append([float(pt[0]) / w, float(pt[1]) / h])
        return out

    @staticmethod
    def _landmarks_to_points(face_landmarks, indices, width: int, height: int) -> np.ndarray:
        pts = []
        for idx in indices:
            lm = face_landmarks.landmark[idx]
            x = int(np.clip(lm.x * width, 0, width - 1))
            y = int(np.clip(lm.y * height, 0, height - 1))
            pts.append((x, y))
        return np.array(pts, dtype=np.int32)

    @staticmethod
    def _mean_chrom_in_polygon(frame_bgr: np.ndarray, polygon: np.ndarray) -> Optional[float]:
        """
        Extract CHROM (Chrominance) signal from a polygon ROI.
        
        Formula: CHROM = 3*R - 2*G
        
        This combines R and G channels to emphasize cardiovascular pulse signal
        while reducing motion artifacts and illumination changes.
        """
        if polygon.shape[0] < 3:
            return None

        mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
        cv2.fillConvexPoly(mask, polygon, 255)

        pixel_count = int(np.count_nonzero(mask))
        if pixel_count == 0:
            return None

        # BGR order in OpenCV: B=0, G=1, R=2
        red_channel = frame_bgr[:, :, 2]
        green_channel = frame_bgr[:, :, 1]
        
        # CHROM formula: 3*R - 2*G (normalized)
        red_mean = float(cv2.mean(red_channel, mask=mask)[0])
        green_mean = float(cv2.mean(green_channel, mask=mask)[0])
        
        chrom_value = (3.0 * red_mean) - (2.0 * green_mean)
        return float(chrom_value)

    def _estimate_bpm_fft(self) -> Optional[Dict[str, float]]:
        signal, timestamps = self._ordered_signal_and_timestamps()
        if signal.size < 16:
            return None

        fs = self._estimate_sampling_rate(timestamps)
        if fs is None:
            return None

        # Remove DC component before filtering.
        signal = signal - np.mean(signal)
        detrended_std = float(np.std(signal))

        filtered = self._bandpass_filter(signal, fs)
        if filtered is None:
            return None
        filtered_rms = float(np.sqrt(np.mean(np.square(filtered))))
        pulse_rms_ratio = filtered_rms / (detrended_std + 1e-6)

        freqs = np.fft.rfftfreq(filtered.size, d=1.0 / fs)
        spectrum = np.abs(np.fft.rfft(filtered))

        valid = (freqs >= self.config.low_hz) & (freqs <= self.config.high_hz)
        if not np.any(valid):
            return None

        valid_freqs = freqs[valid]
        valid_spec = spectrum[valid]

        if valid_spec.size == 0:
            return None

        dominant_idx = int(np.argmax(valid_spec))
        dominant_hz = float(valid_freqs[dominant_idx])
        dominant_mag = float(valid_spec[dominant_idx])
        noise_floor = float(np.median(valid_spec) + 1e-6)
        total_band_energy = float(np.sum(valid_spec) + 1e-6)
        return {
            "raw_bpm": dominant_hz * 60.0,
            "snr": dominant_mag / noise_floor,
            "peak_power_ratio": dominant_mag / total_band_energy,
            "pulse_rms_ratio": pulse_rms_ratio,
        }

    @staticmethod
    def _score_linear(value: float, low: float, high: float) -> float:
        if high <= low:
            return 0.0
        return float(np.clip((value - low) / (high - low), 0.0, 1.0))

    def _compute_quality_score(self, metrics: Dict[str, float]) -> float:
        snr_s = self._score_linear(metrics["snr"], 1.0, 3.8)
        peak_s = self._score_linear(metrics["peak_power_ratio"], 0.08, 0.34)
        pulse_s = self._score_linear(metrics["pulse_rms_ratio"], 0.08, 0.36)
        score = (0.40 * snr_s) + (0.35 * peak_s) + (0.25 * pulse_s)
        return float(np.clip(score, 0.0, 1.0))

    def _bandpass_filter(self, signal: np.ndarray, fs: float) -> Optional[np.ndarray]:
        nyquist = 0.5 * fs
        low = self.config.low_hz / nyquist
        high = self.config.high_hz / nyquist

        if not (0.0 < low < high < 1.0):
            return None

        try:
            b, a = butter(self.config.filter_order, [low, high], btype="bandpass")
            return filtfilt(b, a, signal)
        except ValueError:
            # filtfilt can fail if the signal is too short for padding.
            return None

    def _calculate_face_movement(self, frame_bgr: np.ndarray, face_landmarks) -> float:
        """
        Calculate magnitude of face center movement between frames.
        Used to detect if video is static (fake/photo) vs real live video.
        
        Returns movement magnitude normalized to frame dimensions.
        """
        h, w = frame_bgr.shape[:2]
        # Use nose tip (landmark 1) as face center
        lm = face_landmarks.landmark[1]
        current_center = np.array([lm.x * w, lm.y * h])
        
        if self.last_face_center is None:
            self.last_face_center = current_center
            return 0.0
        
        # Calculate Euclidean distance
        distance = float(np.linalg.norm(current_center - self.last_face_center))
        # Normalize to frame diagonal for consistent scale
        max_distance = float(np.sqrt(w**2 + h**2))
        normalized_movement = distance / (max_distance + 1e-6)
        
        self.last_face_center = current_center
        self.movement_history.append(normalized_movement)
        
        return normalized_movement

    def _calculate_movement_correlation(self) -> float:
        """
        Calculate correlation between face movement and rPPG signal variation.
        
        High correlation indicates genuine liveness (person moves, pulse signal varies).
        Low/zero correlation indicates fake video/photo (movement without heart rate variation).
        
        Returns score 0.0-1.0 where:
        - 1.0 = perfect correlation (genuine)
        - 0.5 = partial correlation (medium confidence)
        - 0.0 = no correlation (likely fake)
        """
        if self.samples_collected < 10:
            return 0.5  # Not enough data yet
        
        signal = self._ordered_signal()
        movement = self._get_ordered_movement()
        
        if signal.size < 2 or movement.size < 2:
            return 0.5
        
        # Calculate signal derivative (variation)
        signal_diff = np.abs(np.diff(signal))
        movement_diff = np.abs(np.diff(movement))
        
        # If movement is near zero and signal is also near zero → likely fake static video
        mean_movement = float(np.mean(movement_diff))
        mean_signal_var = float(np.mean(signal_diff))
        
        if mean_movement < 0.001:  # Almost no movement
            if mean_signal_var < 0.5:  # And almost no signal variation
                return 0.1  # Likely static fake (photo or frozen video)
            else:
                return 0.3  # Minimal movement but signal varying (suspicious)
        
        # Calculate Pearson correlation between movement and signal variation
        if len(signal_diff) > 1 and len(movement_diff) > 1:
            try:
                # Normalize both to zero mean
                signal_norm = signal_diff - np.mean(signal_diff)
                movement_norm = movement_diff - np.mean(movement_diff)
                
                # Calculate correlation coefficient
                correlation = float(
                    np.dot(signal_norm, movement_norm) / 
                    (np.linalg.norm(signal_norm) * np.linalg.norm(movement_norm) + 1e-9)
                )
                # Map [-1, 1] to [0, 1] (only positive correlation matters for liveness)
                score = float(np.clip((correlation + 1.0) / 2.0, 0.0, 1.0))
                return score
            except (ValueError, ZeroDivisionError):
                return 0.5
        
        return 0.5

    def _get_ordered_movement(self) -> np.ndarray:
        """Get movement buffer in chronological order."""
        if self.samples_collected < self.buffer_size:
            return self.movement_buffer[: self.samples_collected].copy()
        
        return np.concatenate(
            [self.movement_buffer[self.buffer_index :], self.movement_buffer[: self.buffer_index]]
        )


__all__ = ["RPPG_Detector", "RPPGConfig"]
