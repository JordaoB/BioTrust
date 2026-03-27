"""
BioTrust - rPPG Detector
========================
Remote photoplethysmography (rPPG) detector for real-time heart-rate estimation
from webcam frames.

Pipeline per frame:
1) Face detection + fixed skin ROIs (forehead + upper cheeks)
2) Green-channel mean extraction from each ROI
3) Circular temporal buffer (last N seconds)
4) Butterworth bandpass filtering (0.7-3.0 Hz)
5) FFT dominant frequency -> BPM
6) BPM smoothing with moving average over latest estimates
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
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
        self.buffer_index = 0
        self.samples_collected = 0

        self.bpm_history = deque(maxlen=self.config.smoothing_window)

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
        self.buffer_index = 0
        self.samples_collected = 0
        self.bpm_history.clear()

    def close(self) -> None:
        """Release MediaPipe resources."""
        self.face_mesh.close()

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Optional[float]]:
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
            }

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.face_mesh.process(frame_rgb)

        if not result.multi_face_landmarks:
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": False,
                "signal_ready": self._has_min_samples(),
            }

        face_landmarks = result.multi_face_landmarks[0]
        mean_green = self._extract_green_signal(frame_bgr, face_landmarks)

        if mean_green is None:
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": True,
                "signal_ready": self._has_min_samples(),
            }

        sample_ts = float(timestamp if timestamp is not None else time.monotonic())
        self._append_green_value(mean_green, sample_ts)

        if not self._has_min_samples():
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": True,
                "signal_ready": False,
            }

        raw_bpm = self._estimate_bpm_fft()
        if raw_bpm is None:
            return {
                "bpm": None,
                "raw_bpm": None,
                "face_detected": True,
                "signal_ready": True,
            }

        if self.config.bpm_min <= raw_bpm <= self.config.bpm_max:
            self.bpm_history.append(raw_bpm)

        stabilized_bpm = float(np.mean(self.bpm_history)) if self.bpm_history else None

        return {
            "bpm": stabilized_bpm,
            "raw_bpm": raw_bpm,
            "face_detected": True,
            "signal_ready": True,
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

    def _append_green_value(self, value: float, timestamp: float) -> None:
        self.green_buffer[self.buffer_index] = value
        self.time_buffer[self.buffer_index] = timestamp
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

    def _extract_green_signal(self, frame_bgr: np.ndarray, face_landmarks) -> Optional[float]:
        h, w = frame_bgr.shape[:2]

        forehead = self._landmarks_to_points(face_landmarks, self._FOREHEAD_IDX, w, h)
        left_cheek = self._landmarks_to_points(face_landmarks, self._LEFT_UPPER_CHEEK_IDX, w, h)
        right_cheek = self._landmarks_to_points(face_landmarks, self._RIGHT_UPPER_CHEEK_IDX, w, h)

        roi_means = []
        for polygon in (forehead, left_cheek, right_cheek):
            mean_green = self._mean_green_in_polygon(frame_bgr, polygon)
            if mean_green is not None:
                roi_means.append(mean_green)

        if not roi_means:
            return None

        return float(np.mean(roi_means))

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
    def _mean_green_in_polygon(frame_bgr: np.ndarray, polygon: np.ndarray) -> Optional[float]:
        if polygon.shape[0] < 3:
            return None

        mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
        cv2.fillConvexPoly(mask, polygon, 255)

        pixel_count = int(np.count_nonzero(mask))
        if pixel_count == 0:
            return None

        green_channel = frame_bgr[:, :, 1]
        return float(cv2.mean(green_channel, mask=mask)[0])

    def _estimate_bpm_fft(self) -> Optional[float]:
        signal, timestamps = self._ordered_signal_and_timestamps()
        if signal.size < 16:
            return None

        fs = self._estimate_sampling_rate(timestamps)
        if fs is None:
            return None

        # Remove DC component before filtering.
        signal = signal - np.mean(signal)

        filtered = self._bandpass_filter(signal, fs)
        if filtered is None:
            return None

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
        return dominant_hz * 60.0

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


__all__ = ["RPPG_Detector", "RPPGConfig"]
