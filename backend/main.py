from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ultralytics import YOLO
import os
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)

# -----------------------------
# PATHS
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
FRONTEND_FOLDER = os.path.join(PROJECT_DIR, "frontend")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
# LOAD CUSTOM YOLO MODEL
# -----------------------------
MODEL_PATH = os.path.join(BASE_DIR, "..", "best.pt")
model = YOLO(MODEL_PATH)

# -----------------------------
# VEHICLE CLASSES
# -----------------------------
VEHICLE_CLASSES = {
    "car",
    "bus",
    "truck",
    "motorcycle",
    "autorickshaw",
    "bicycle"
}

CLASS_ALIASES = {
    "car": "car",
    "caravan": "car",
    "vehicle fallback": "car",
    "bus": "bus",
    "truck": "truck",
    "trailer": "truck",
    "motorcycle": "motorcycle",
    "autorickshaw": "autorickshaw",
    "bicycle": "bicycle"
}

DETECTION_CONFIDENCE = 0.25
DETECTION_IMAGE_SIZE = 1280
DISPLAY_CONFIDENCE = 0.35

CLASS_COLORS = {
    "car": (0, 200, 0),
    "bus": (255, 170, 0),
    "truck": (0, 140, 255),
    "motorcycle": (255, 0, 180),
    "autorickshaw": (0, 220, 255),
    "bicycle": (180, 80, 255)
}


def draw_detection(image, class_name, confidence, x1, y1, x2, y2):
    color = CLASS_COLORS.get(
        class_name,
        (0, 200, 0)
    )

    cv2.rectangle(
        image,
        (x1, y1),
        (x2, y2),
        color,
        2
    )

    label = f"{class_name} {confidence * 100:.0f}%"

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1

    text_size, baseline = cv2.getTextSize(
        label,
        font,
        font_scale,
        thickness
    )

    text_width, text_height = text_size
    label_x = max(x1, 0)
    label_y = max(y1 - 8, text_height + 8)

    cv2.rectangle(
        image,
        (label_x, label_y - text_height - baseline - 6),
        (label_x + text_width + 8, label_y + baseline),
        color,
        -1
    )

    cv2.putText(
        image,
        label,
        (label_x + 4, label_y - 4),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA
    )

# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return send_from_directory(
        FRONTEND_FOLDER,
        "index.html"
    )


@app.route("/<path:filename>")
def frontend_file(filename):
    return send_from_directory(
        FRONTEND_FOLDER,
        filename
    )


@app.route("/api/status")
def api_status():
    return jsonify({
        "message": "Smart Traffic Backend Running"
    })


# -----------------------------
# IMAGE ACCESS
# -----------------------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# -----------------------------
# UPLOAD IMAGES
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload():

    for i in range(1, 5):

        file = request.files.get(f"lane{i}")

        if file is None:
            return jsonify({
                "error": f"Lane {i} image not received."
            }), 400

        save_path = os.path.join(
            UPLOAD_FOLDER,
            f"road{i}.jpg"
        )

        file.save(save_path)

    return jsonify({
        "message": "Images uploaded successfully"
    })
# -----------------------------
# PROCESS TRAFFIC
# -----------------------------
@app.route("/process", methods=["POST"])
def process_traffic():

    data = request.json

    results_data = {}

    for lane_no in range(1, 5):

        lane_name = f"lane{lane_no}"

        polygon_points = data.get(
            lane_name,
            []
        )

        image_path = os.path.join(
            UPLOAD_FOLDER,
            f"road{lane_no}.jpg"
        )

        if not os.path.exists(image_path):

            results_data[lane_name] = {
                "cars": 0,
                "buses": 0,
                "trucks": 0,
                "motorcycles": 0,
                "autorickshaws": 0,
                "bicycles": 0,
                "total": 0
            }

            continue

        image = cv2.imread(image_path)

        if image is None:
           results_data[lane_name] = {
              "error": "Unable to read image."
           }
           continue

        detections = model(
               image,
               conf=DETECTION_CONFIDENCE,
               imgsz=DETECTION_IMAGE_SIZE,
               verbose=False
         )

        count = 0

        cars = 0
        buses = 0
        trucks = 0
        motorcycles = 0
        autorickshaws = 0
        bicycles = 0

        if len(polygon_points) >= 3:

            polygon = np.array(
                [[p["x"], p["y"]] for p in polygon_points],
                dtype=np.int32
            )

            overlay = image.copy()

            cv2.fillPoly(
                overlay,
                [polygon],
                (255, 255, 0)
            )

            cv2.addWeighted(
                overlay,
                0.08,
                image,
                0.92,
                0,
                image
            )

            cv2.polylines(
                image,
                [polygon],
                True,
                (255, 255, 0),
                2
            )

        else:

            polygon = None

        for result in detections:

            boxes = result.boxes

            for box in boxes:

                cls_id = int(box.cls[0])
                detected_class_name = model.names[cls_id]
                class_name = CLASS_ALIASES.get(
                    detected_class_name
                )

                if class_name is None:
                    continue

                confidence = float(box.conf[0])
                if confidence < DISPLAY_CONFIDENCE:
                   continue

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                inside = True

                if polygon is not None:

                    inside = cv2.pointPolygonTest(
                        polygon,
                        (center_x, center_y),
                        False
                    ) >= 0

                if inside:

                    count += 1

                    if class_name == "car":
                        cars += 1

                    elif class_name == "bus":
                        buses += 1

                    elif class_name == "truck":
                        trucks += 1

                    elif class_name == "motorcycle":
                        motorcycles += 1

                    elif class_name == "autorickshaw":
                        autorickshaws += 1

                    elif class_name == "bicycle":
                        bicycles += 1

                    draw_detection(
                        image,
                        class_name,
                        confidence,
                        x1,
                        y1,
                        x2,
                        y2
                    )

        detected_path = os.path.join(
            UPLOAD_FOLDER,
            f"lane{lane_no}_detected.jpg"
        )

        cv2.imwrite(
            detected_path,
            image
        )

        results_data[lane_name] = {

            "cars": cars,
            "buses": buses,
            "trucks": trucks,
            "motorcycles": motorcycles,
            "autorickshaws": autorickshaws,
            "bicycles": bicycles,
            "total": count

        }
# -----------------------------
# SIGNAL LOGIC
# -----------------------------

    lane_counts = {

        "Lane 1": results_data["lane1"]["total"],
        "Lane 2": results_data["lane2"]["total"],
        "Lane 3": results_data["lane3"]["total"],
        "Lane 4": results_data["lane4"]["total"]

    }

    max_lane = max(
        lane_counts,
        key=lane_counts.get
    )

    max_count = lane_counts[max_lane]

    # Minimum 10 sec, Maximum 40 sec
    green_time = min(
        max(10, max_count),
        40
    )

    return jsonify({

        "lane1": results_data["lane1"],
        "lane2": results_data["lane2"],
        "lane3": results_data["lane3"],
        "lane4": results_data["lane4"],

        "lane1_image":
        "http://127.0.0.1:5000/uploads/lane1_detected.jpg",

        "lane2_image":
        "http://127.0.0.1:5000/uploads/lane2_detected.jpg",

        "lane3_image":
        "http://127.0.0.1:5000/uploads/lane3_detected.jpg",

        "lane4_image":
        "http://127.0.0.1:5000/uploads/lane4_detected.jpg",

        "green_lane": max_lane,
        "green_time": green_time

    })


# -----------------------------
# RUN FLASK
# -----------------------------
if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
