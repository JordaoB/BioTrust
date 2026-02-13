import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance as dist

EAR_THRESHOLD = 0.18
CONSEC_FRAMES = 2
REQUIRED_BLINKS = 3

blink_frame_counter = 0
blink_total = 0
must_return_center = False

current_step = 0  # 0=blink, 1=left, 2=right, 3=done
liveness_verified = False

prev_eye_midpoint = None

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

            # --------- YAW ---------
            nose = mesh_points[1]
            dist_left = np.linalg.norm(nose - left_eye_center)
            dist_right = np.linalg.norm(nose - right_eye_center)

            symmetry_ratio = dist_left / dist_right
            
            # Threshold suave (fase 0)
            face_yaw_ok = 0.85 < symmetry_ratio < 1.15

            # Threshold forte (fases laterais)
            strong_left = symmetry_ratio > 2.05
            strong_right = symmetry_ratio < 0.45

            # --------- PITCH ---------
            nose_eye_ratio = (nose[1] - eye_midpoint[1]) / h
            face_pitch_ok = 0.02 < nose_eye_ratio < 0.12

            # --------- MOVIMENTO ---------
            if prev_eye_midpoint is not None:
                movement = np.linalg.norm(eye_midpoint - prev_eye_midpoint)
            else:
                movement = 0

            prev_eye_midpoint = eye_midpoint
            movement_ok = movement < 20

            # --------- FACE FRONTAL ---------
            face_frontal = face_yaw_ok and face_pitch_ok

            if current_step == 0 and not face_frontal:
                cv2.putText(frame, "LOOK STRAIGHT AT CAMERA",
                            (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 0, 255),
                            2)

            # --------- EAR ---------
            left_ear = calculate_ear(left_eye)
            right_ear = calculate_ear(right_eye)
            ear = (left_ear + right_ear) / 2

            both_eyes_closed = (
                left_ear < EAR_THRESHOLD and
                right_ear < EAR_THRESHOLD
            )

           # ================= STEP 0 - BLINK  ========================
            if current_step == 0 and face_frontal and movement_ok:

                if both_eyes_closed:
                    blink_frame_counter += 1
                else:
                    if blink_frame_counter >= CONSEC_FRAMES:
                        blink_total += 1
                        print("Blink count:", blink_total)
                    blink_frame_counter = 0

                if blink_total >= REQUIRED_BLINKS:
                    current_step = 1
                    blink_total = 0
                    blink_frame_counter = 0
                    print("Blink phase completed")

            # ================= STEP 1 - LEFT  ========================
            if current_step == 1:

                if not must_return_center:
                    if strong_left:
                        must_return_center = True
                        print("Left detected, return to center")

                    elif strong_right:
                        print("Wrong direction - RESET")
                        current_step = 0
                        blink_total = 0

                else:
                    if face_yaw_ok:
                        current_step = 2
                        must_return_center = False
                        print("Returned to center, now turn RIGHT")

            # ================= STEP 2 - RIGHT  ========================
            if current_step == 2:

                if not must_return_center:
                    if strong_right:
                        must_return_center = True
                        print("Right detected, return to center")

                    elif strong_left:
                        print("Wrong direction - RESET")
                        current_step = 0
                        blink_total = 0

                else:
                    if face_yaw_ok:
                        current_step = 3
                        must_return_center = False
                        print("Returned to center - Liveness Confirmed")

            # ===================== FINAL ==============================
            if current_step == 3:
                liveness_verified = True

            # ---------------- UI ----------------
            if not liveness_verified:

                if current_step == 0:
                    text = f"BLINK {REQUIRED_BLINKS} TIMES"

                elif current_step == 1:
                    text = "TURN HEAD LEFT"

                elif current_step == 2:
                    text = "TURN HEAD RIGHT"

                if must_return_center:
                    text = "RETURN TO CENTER"

                cv2.putText(frame,
                            text,
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


            cv2.putText(frame,
                        f"EAR: {ear:.2f}",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2)

    cv2.imshow("BioTrust - Sequential Liveness", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
