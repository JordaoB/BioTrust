import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance as dist

EAR_THRESHOLD = 0.18
CONSEC_FRAMES = 2
REQUIRED_BLINKS = 3

blink_frame_counter = 0
blink_total = 0
liveness_verified = False
blink_detected = False


prev_eye_midpoint = None  # para detectar movimento brusco

mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

def calculate_ear(eye_landmarks):
    A = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
    B = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
    C = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
    return (A + B) / (2.0 * C)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:

            h, w, _ = frame.shape
            mesh_points = np.array([
                [int(p.x * w), int(p.y * h)]
                for p in face_landmarks.landmark
            ])

            # --------- OLHOS ---------
            left_eye = mesh_points[LEFT_EYE]
            right_eye = mesh_points[RIGHT_EYE]

            left_eye_center = np.mean(left_eye, axis=0)
            right_eye_center = np.mean(right_eye, axis=0)
            eye_midpoint = (left_eye_center + right_eye_center) / 2

            # --------- DETECÇÃO YAW (LADOS) ---------
            nose = mesh_points[1]

            dist_left = np.linalg.norm(nose - left_eye_center)
            dist_right = np.linalg.norm(nose - right_eye_center)

            symmetry_ratio = dist_left / dist_right
            face_yaw_ok = 0.85 < symmetry_ratio < 1.15

            # --------- DETECÇÃO PITCH (CIMA/BAIXO) ---------
            nose = mesh_points[1]

            nose_eye_ratio = (nose[1] - eye_midpoint[1]) / h

            face_pitch_ok = 0.02 < nose_eye_ratio < 0.12

            # --------- MOVIMENTO BRUSCO ---------
            if prev_eye_midpoint is not None:
                movement = np.linalg.norm(eye_midpoint - prev_eye_midpoint)
            else:
                movement = 0

            prev_eye_midpoint = eye_midpoint

            movement_ok = movement < 20

            # --------- FACE FRONTAL FINAL ---------
            face_frontal = face_yaw_ok and face_pitch_ok

            if not face_frontal:
                cv2.putText(frame, "LOOK STRAIGHT AT CAMERA",
                            (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 0, 255),
                            2)

            # --------- EAR ---------
            left_ear = calculate_ear(left_eye)
            right_ear = calculate_ear(right_eye)

            both_eyes_closed = (
                left_ear < EAR_THRESHOLD and
                right_ear < EAR_THRESHOLD
            )

            # --------- BLINK LOGIC ---------
            if not liveness_verified and face_frontal and movement_ok:

                if both_eyes_closed:
                    blink_frame_counter += 1

                else:
                    if blink_frame_counter >= CONSEC_FRAMES:
                        blink_total += 1
                        print("Blink count:", blink_total)
                    blink_frame_counter = 0

            # --------- VERIFICAÇÃO FINAL ---------
            if blink_total >= REQUIRED_BLINKS:
                liveness_verified = True

            # --------- UI ---------
            if not liveness_verified:
                cv2.putText(frame,
                            f"BLINK {REQUIRED_BLINKS} TIMES TO VERIFY",
                            (50, 150),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (255, 255, 0),
                            2)
            else:
                cv2.putText(frame,
                            "LIVENESS CONFIRMED",
                            (50, 150),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 255, 0),
                            3)

            ear = (left_ear + right_ear) / 2
            cv2.putText(frame,
                        f"EAR: {ear:.2f}",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2)

    cv2.imshow("BioTrust - Blink Detection", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
