"""
BioTrust - Passive Liveness Detection (rPPG)
============================================
Remote Photoplethysmography for heart rate detection via webcam.

This module detects subtle color changes in facial skin caused by blood flow,
providing passive liveness detection without requiring user interaction.

Technique:
1. Extract face ROI (Region of Interest) - forehead/cheeks
2. Calculate mean color values per frame (focus on Green channel)
3. Build temporal signal over multiple frames
4. Apply FFT (Fast Fourier Transform) to find dominant frequencies
5. Validate if frequency matches normal heart rate (45-240 BPM / 0.75-4 Hz)

Advantages:
- No user action required (passive)
- Harder to spoof than static images
- Works alongside active liveness for multi-factor authentication
"""

import cv2
import numpy as np
import mediapipe as mp
from scipy import signal
from scipy.fft import fft, fftfreq
import time


class PassiveLivenessDetector:
    """
    Detects liveness by analyzing heart rate through facial color variations.
    """
    
    def __init__(self):
        """Initialize the passive liveness detector."""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Configuration
        self.WINDOW_NAME = "BioTrust - Passive Liveness"
        self.CAPTURE_DURATION = 15  # seconds
        self.FPS = 30
        self.MIN_BPM = 45  # Minimum valid heart rate
        self.MAX_BPM = 180  # Maximum valid heart rate
        self.SIGNAL_BUFFER_SIZE = self.CAPTURE_DURATION * self.FPS
        
        # Signal buffers
        self.green_values = []
        self.timestamps = []
    
    def _extract_forehead_roi(self, frame, face_landmarks):
        """
        Extract forehead region where pulse signal is strongest.
        
        Args:
            frame: Video frame
            face_landmarks: MediaPipe face landmarks
            
        Returns:
            Mean green channel value from forehead ROI
        """
        h, w, _ = frame.shape
        
        # Forehead landmarks (approximate indices from MediaPipe Face Mesh)
        # We use points around the upper face/forehead area
        forehead_indices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                           397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
                           172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
        
        # Extract forehead region coordinates
        forehead_points = []
        for idx in forehead_indices:
            if idx < len(face_landmarks.landmark):
                landmark = face_landmarks.landmark[idx]
                x, y = int(landmark.x * w), int(landmark.y * h)
                forehead_points.append([x, y])
        
        if len(forehead_points) < 10:
            return None
        
        # Create mask for forehead region
        forehead_points = np.array(forehead_points, dtype=np.int32)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillConvexPoly(mask, forehead_points, 255)
        
        # Extract mean green channel value (best for PPG signal)
        green_channel = frame[:, :, 1]  # BGR format - Green is index 1
        mean_green = cv2.mean(green_channel, mask=mask)[0]
        
        return mean_green
    
    def _bandpass_filter(self, data, fps, lowcut=0.75, highcut=4.0):
        """
        Apply bandpass filter to isolate heart rate frequencies.
        
        Args:
            data: Signal data
            fps: Frames per second
            lowcut: Low frequency cutoff (Hz) - 0.75 Hz = 45 BPM
            highcut: High frequency cutoff (Hz) - 4.0 Hz = 240 BPM
            
        Returns:
            Filtered signal
        """
        nyquist = fps / 2.0
        low = lowcut / nyquist
        high = highcut / nyquist
        
        # Butterworth bandpass filter
        b, a = signal.butter(4, [low, high], btype='band')
        filtered_data = signal.filtfilt(b, a, data)
        
        return filtered_data
    
    def _estimate_heart_rate(self, green_signal, fps):
        """
        Estimate heart rate using FFT on the green channel signal.
        
        Args:
            green_signal: Array of mean green values over time
            fps: Frames per second
            
        Returns:
            tuple: (heart_rate_bpm, confidence, frequency_spectrum)
        """
        # Normalize and detrend signal
        green_signal = np.array(green_signal)
        green_signal = signal.detrend(green_signal)
        
        # Apply bandpass filter
        filtered_signal = self._bandpass_filter(green_signal, fps)
        
        # Apply FFT
        n = len(filtered_signal)
        fft_values = fft(filtered_signal)
        fft_freq = fftfreq(n, 1.0 / fps)
        
        # Only positive frequencies
        positive_freq_idx = np.where(fft_freq > 0)
        fft_freq = fft_freq[positive_freq_idx]
        fft_magnitude = np.abs(fft_values[positive_freq_idx])
        
        # Find frequency with maximum power in valid heart rate range
        valid_freq_mask = (fft_freq >= 0.75) & (fft_freq <= 4.0)  # 45-240 BPM
        valid_fft_freq = fft_freq[valid_freq_mask]
        valid_fft_magnitude = fft_magnitude[valid_freq_mask]
        
        if len(valid_fft_magnitude) == 0:
            return 0, 0.0, None
        
        # Find peak frequency
        peak_idx = np.argmax(valid_fft_magnitude)
        peak_freq = valid_fft_freq[peak_idx]
        heart_rate = peak_freq * 60.0  # Convert Hz to BPM
        
        # Calculate confidence based on peak prominence
        mean_magnitude = np.mean(valid_fft_magnitude)
        peak_magnitude = valid_fft_magnitude[peak_idx]
        confidence = min(peak_magnitude / (mean_magnitude + 1e-6), 10.0) / 10.0
        
        return heart_rate, confidence, (fft_freq, fft_magnitude)
    
    def verify(self, show_visualization=True):
        """
        Run passive liveness detection.
        
        Args:
            show_visualization: Show real-time signal visualization
            
        Returns:
            dict with results:
            {
                "success": bool,
                "message": str,
                "heart_rate": float (BPM),
                "confidence": float (0-1),
                "is_live": bool
            }
        """
        print("\n" + "="*70)
        print("🫀 Passive Liveness Detection (rPPG)")
        print("="*70)
        print("Looking for heart rate signal in facial video...")
        print(f"Please stay still and look at the camera for {self.CAPTURE_DURATION} seconds.\n")
        
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return {
                "success": False,
                "message": "Camera not accessible",
                "heart_rate": 0,
                "confidence": 0.0,
                "is_live": False
            }
        
        # Create window
        if show_visualization:
            cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
            cv2.moveWindow(self.WINDOW_NAME, 300, 100)
            cv2.resizeWindow(self.WINDOW_NAME, 800, 600)
        
        # Reset buffers
        self.green_values = []
        self.timestamps = []
        
        start_time = time.time()
        frame_count = 0
        
        try:
            while True:
                success, frame = cap.read()
                if not success:
                    break
                
                elapsed = time.time() - start_time
                if elapsed >= self.CAPTURE_DURATION:
                    break
                
                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape  # Get frame dimensions
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb)
                
                if results.multi_face_landmarks:
                    face_landmarks = results.multi_face_landmarks[0]
                    
                    # Extract green signal from forehead
                    mean_green = self._extract_forehead_roi(frame, face_landmarks)
                    
                    if mean_green is not None:
                        self.green_values.append(mean_green)
                        self.timestamps.append(elapsed)
                        frame_count += 1
                    
                    # Draw forehead ROI (visual feedback)
                    forehead_indices = [10, 338, 297, 332]
                    points = []
                    for idx in forehead_indices:
                        if idx < len(face_landmarks.landmark):
                            landmark = face_landmarks.landmark[idx]
                            x, y = int(landmark.x * w), int(landmark.y * h)
                            points.append((x, y))
                    
                    if len(points) >= 3:
                        for i in range(len(points)):
                            cv2.line(frame, points[i], points[(i+1) % len(points)], (0, 255, 0), 2)
                
                if show_visualization:
                    # Draw UI
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (w, 80), (30, 30, 30), -1)
                    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                    
                    # Progress bar
                    progress = elapsed / self.CAPTURE_DURATION
                    bar_width = int((w - 40) * progress)
                    cv2.rectangle(frame, (20, 55), (w - 20, 65), (60, 60, 60), -1)
                    cv2.rectangle(frame, (20, 55), (20 + bar_width, 65), (100, 255, 100), -1)
                    
                    # Text
                    cv2.putText(frame, "Passive Liveness - Analyzing Heart Rate", (20, 25),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
                    cv2.putText(frame, f"Capturing: {elapsed:.1f}s / {self.CAPTURE_DURATION}s", (20, 45),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
                    cv2.putText(frame, f"Samples: {len(self.green_values)}", (w - 150, 25),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
                    
                    cv2.imshow(self.WINDOW_NAME, frame)
                
                # Check for window close or ESC
                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    break
                
                try:
                    if show_visualization and cv2.getWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except:
                    break
        
        finally:
            cap.release()
            if show_visualization:
                cv2.destroyAllWindows()
        
        # Analyze collected signal
        print(f"\n📊 Analysis: Collected {len(self.green_values)} samples over {elapsed:.1f}s")
        
        if len(self.green_values) < self.FPS * 5:  # Need at least 5 seconds
            return {
                "success": False,
                "message": "Insufficient data - face not detected long enough",
                "heart_rate": 0,
                "confidence": 0.0,
                "is_live": False
            }
        
        # Calculate actual FPS
        actual_fps = len(self.green_values) / elapsed
        
        # Estimate heart rate
        heart_rate, confidence, spectrum = self._estimate_heart_rate(self.green_values, actual_fps)
        
        print(f"💓 Estimated Heart Rate: {heart_rate:.1f} BPM")
        print(f"📈 Confidence: {confidence:.2%}")
        
        # Validate
        is_live = (self.MIN_BPM <= heart_rate <= self.MAX_BPM) and (confidence >= 0.3)
        
        if is_live:
            print("✅ RESULT: Heart rate detected - LIVE PERSON")
        else:
            print("❌ RESULT: No valid heart rate - POSSIBLE SPOOF")
        
        return {
            "success": is_live,
            "message": f"Heart rate: {heart_rate:.1f} BPM (confidence: {confidence:.2%})",
            "heart_rate": heart_rate,
            "confidence": confidence,
            "is_live": is_live
        }


def quick_verify():
    """Quick verification function."""
    detector = PassiveLivenessDetector()
    result = detector.verify(show_visualization=True)
    return result["is_live"]


if __name__ == "__main__":
    print("🫀 BioTrust - Passive Liveness Detection Demo\n")
    
    detector = PassiveLivenessDetector()
    result = detector.verify(show_visualization=True)
    
    print("\n" + "="*70)
    print("FINAL RESULT:")
    print(f"  Status: {'✓ LIVE PERSON' if result['is_live'] else '✗ SPOOF DETECTED'}")
    print(f"  Heart Rate: {result['heart_rate']:.1f} BPM")
    print(f"  Confidence: {result['confidence']:.2%}")
    print(f"  Message: {result['message']}")
    print("="*70)
