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
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
# LOAD YOLO
# -----------------------------
model = YOLO("../yolov8n.pt")

VEHICLE_CLASSES = [
    "car",
    "bus",
    "truck",
    "motorcycle"
]

# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
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

        if file:

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
                "total": 0
            }

            continue

        image = cv2.imread(image_path)

        detections = model(image)

        count = 0
        cars = 0
        buses = 0
        trucks = 0
        motorcycles = 0

        if len(polygon_points) >= 3:

            polygon = np.array(
                [
                    [p["x"], p["y"]]
                    for p in polygon_points
                ],
                dtype=np.int32
            )

            cv2.polylines(
                image,
                [polygon],
                True,
                (255, 255, 0),
                3
            )

        else:

            polygon = None

        for result in detections:

            boxes = result.boxes

            for box in boxes:

                cls_id = int(box.cls[0])

                class_name = model.names[cls_id]

                if class_name not in VEHICLE_CLASSES:
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

                    # GREEN BOX
                    cv2.rectangle(
                        image,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    # LABEL
                    cv2.putText(
                        image,
                        class_name,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
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
# RUN
# -----------------------------
if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )