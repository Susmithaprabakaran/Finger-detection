import cv2
import numpy as np
import mediapipe as mp
from collections import defaultdict, deque
import time
from color_palette import show_color_picker

# Setting up hand tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.8)
mp_draw = mp.solutions.drawing_utils

# Basic drawing settings
deque_len = 1024
drawing_enabled = False
current_color = (0, 0, 255)  # Starting with red
current_brush_size = 2

# Keep track of drawing points for each color
color_points = defaultdict(lambda: deque(maxlen=deque_len))
cooldown_time = 1
last_button_time = time.time()

# Create two canvases - one for the current frame and one to keep all drawings
persistent_canvas = np.ones((720, 1080, 3), dtype=np.uint8) * 255
temp_canvas = persistent_canvas.copy()
cv2.namedWindow("Air Canvas", cv2.WINDOW_AUTOSIZE)

# For smooth drawing
prev_x, prev_y = 0, 0
smoothing = 0.3

def draw_buttons(img):
    # Draw the clear button
    cv2.rectangle(img, (20, 10), (140, 60), (50, 50, 50), -1)
    cv2.putText(img, "CLEAR", (40, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Draw the color picker button with current color
    cv2.rectangle(img, (160, 10), (260, 60), current_color, -1)
    text_color = (255, 255, 255) if sum(current_color) < 382 else (0, 0, 0)
    cv2.putText(img, "COLOR", (175, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)

    # Draw the save button
    cv2.rectangle(img, (500, 10), (620, 60), (100, 100, 100), -1)
    cv2.putText(img, "SAVE", (525, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Show current brush size
    cv2.putText(img, f"Size: {current_brush_size}", (280, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)

def save_canvas():
    # Save the drawing with timestamp
    filename = f"air_canvas_{int(time.time())}.png"
    cv2.imwrite(filename, persistent_canvas)
    print(f"Canvas saved as {filename}")

def main():
    global current_color, drawing_enabled, prev_x, prev_y, color_points, last_button_time, current_brush_size
    global persistent_canvas, temp_canvas

    # Start webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Flip frame for natural interaction
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        # Reset canvas and draw buttons
        temp_canvas = persistent_canvas.copy()
        draw_buttons(frame)

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                # Draw hand landmarks
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Get index and thumb positions
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                x, y = int(index_tip.x * w), int(index_tip.y * h)

                # Make drawing smoother
                smoothed_x = int(prev_x + smoothing * (x - prev_x))
                smoothed_y = int(prev_y + smoothing * (y - prev_y))
                prev_x, prev_y = smoothed_x, smoothed_y
                smoothed = (smoothed_x, smoothed_y)
                cv2.circle(frame, smoothed, 8, (0, 0, 0), -1)

                # Check if fingers are pinched
                thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
                pinch_distance = np.hypot(thumb_x - x, thumb_y - y)
                drawing_enabled = pinch_distance >= 40

                # Handle button clicks
                if smoothed_y < 65:
                    now = time.time()
                    if now - last_button_time > cooldown_time:
                        if 20 <= smoothed_x <= 140:  # Clear
                            color_points.clear()
                            persistent_canvas.fill(255)
                        elif 160 <= smoothed_x <= 260:  # Color picker
                            new_color = show_color_picker(current_color)
                            if new_color:
                                current_color = new_color
                        elif 500 <= smoothed_x <= 620:  # Save
                            save_canvas()
                        last_button_time = now
                elif drawing_enabled:
                    color_points[current_color].appendleft(smoothed)
                else:
                    color_points[current_color].appendleft(None)
        else:
            color_points[current_color].appendleft(None)

        # Draw lines for all colors
        for color, points in color_points.items():
            for i in range(1, len(points)):
                if points[i - 1] is None or points[i] is None:
                    continue
                cv2.line(frame, points[i - 1], points[i], color, current_brush_size)
                cv2.line(temp_canvas, points[i - 1], points[i], color, current_brush_size)
                cv2.line(persistent_canvas, points[i - 1], points[i], color, current_brush_size)

        # Show both windows
        cv2.imshow("Air Canvas", temp_canvas)
        cv2.imshow("Tracking", frame)

        # Handle keyboard input
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('+') or key == ord('='):
            current_brush_size = min(20, current_brush_size + 1)
        elif key == ord('-'):
            current_brush_size = max(1, current_brush_size - 1)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
