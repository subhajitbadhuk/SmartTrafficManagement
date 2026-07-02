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
# LOAD YOLO MODELS
# -----------------------------
MODEL_PATH = os.path.join(BASE_DIR, "..", "best.pt")
model = YOLO(MODEL_PATH)

COCO_MODEL_PATH = os.path.join(BASE_DIR, "..", "yolov8n.pt")
coco_model = YOLO(COCO_MODEL_PATH)

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
    "bus": "bus",
    "truck": "truck",
    "motorcycle": "motorcycle",
    "autorickshaw": "autorickshaw",
    "bicycle": "bicycle"
}

DETECTION_CONFIDENCE = 0.30
DETECTION_IMAGE_SIZE = 1280
DETECTION_IOU = 0.45
COCO_CONFIDENCE = 0.25
COCO_IMAGE_SIZE = 960
DISPLAY_CONFIDENCE = 0.30
CLASS_MIN_CONFIDENCE = {
    "car": 0.32,
    "bus": 0.45,
    "truck": 0.55,
    "motorcycle": 0.35,
    "autorickshaw": 0.45,
    "bicycle": 0.35
}
COCO_VEHICLE_CLASSES = {
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck"
}
COCO_CORRECTION_IOU = 0.45
MERGE_IOU = 0.50
LANE_OVERLAP_RATIO = 0.12

CLASS_COLORS = {
    "car": (0, 200, 0),
    "bus": (255, 170, 0),
    "truck": (0, 140, 255),
    "motorcycle": (255, 0, 180),
    "autorickshaw": (0, 220, 255),
    "bicycle": (180, 80, 255)
}


def box_iou(first_box, second_box):
    ax1, ay1, ax2, ay2 = first_box
    bx1, by1, bx2, by2 = second_box

    intersection_x1 = max(ax1, bx1)
    intersection_y1 = max(ay1, by1)
    intersection_x2 = min(ax2, bx2)
    intersection_y2 = min(ay2, by2)

    intersection_width = max(0, intersection_x2 - intersection_x1)
    intersection_height = max(0, intersection_y2 - intersection_y1)
    intersection_area = intersection_width * intersection_height

    first_area = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    second_area = max(0, bx2 - bx1) * max(0, by2 - by1)
    union_area = first_area + second_area - intersection_area

    if union_area == 0:
        return 0

    return intersection_area / union_area


def get_coco_vehicle_detections(image):
    detections = coco_model(
        image,
        conf=COCO_CONFIDENCE,
        imgsz=COCO_IMAGE_SIZE,
        iou=DETECTION_IOU,
        verbose=False
    )

    vehicle_detections = []

    for result in detections:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            class_name = coco_model.names[cls_id]

            if class_name not in COCO_VEHICLE_CLASSES:
                continue

            vehicle_detections.append({
                "class_name": class_name,
                "confidence": float(box.conf[0]),
                "box": tuple(map(float, box.xyxy[0]))
            })

    return vehicle_detections


def get_custom_vehicle_detections(detections, coco_detections):
    vehicle_detections = []

    for result in detections:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            detected_class_name = model.names[cls_id]
            class_name = CLASS_ALIASES.get(detected_class_name)

            if class_name is None:
                continue

            confidence = float(box.conf[0])
            minimum_confidence = CLASS_MIN_CONFIDENCE.get(
                class_name,
                DISPLAY_CONFIDENCE
            )

            if confidence < minimum_confidence:
                continue

            box_coordinates = tuple(map(float, box.xyxy[0]))
            class_name = refine_class_with_coco(
                class_name,
                box_coordinates,
                coco_detections
            )

            vehicle_detections.append({
                "class_name": class_name,
                "confidence": confidence,
                "box": box_coordinates,
                "source": "custom"
            })

    return vehicle_detections


def refine_class_with_coco(class_name, box_coordinates, coco_detections):
    best_match = None
    best_iou = 0

    for coco_detection in coco_detections:
        current_iou = box_iou(
            box_coordinates,
            coco_detection["box"]
        )

        if current_iou > best_iou:
            best_iou = current_iou
            best_match = coco_detection

    if best_match is None or best_iou < COCO_CORRECTION_IOU:
        return class_name

    # The custom model knows autorickshaw; COCO does not, so do not overwrite it.
    if class_name == "autorickshaw":
        return class_name

    return best_match["class_name"]


def merge_vehicle_detections(custom_detections, coco_detections):
    all_detections = custom_detections + [
        {
            "class_name": detection["class_name"],
            "confidence": detection["confidence"],
            "box": detection["box"],
            "source": "coco"
        }
        for detection in coco_detections
    ]

    all_detections.sort(
        key=lambda detection: detection["confidence"],
        reverse=True
    )

    merged_detections = []

    for detection in all_detections:
        duplicate_index = None

        for index, existing_detection in enumerate(merged_detections):
            if box_iou(detection["box"], existing_detection["box"]) >= MERGE_IOU:
                duplicate_index = index
                break

        if duplicate_index is None:
            merged_detections.append(detection)
            continue

        existing_detection = merged_detections[duplicate_index]

        if existing_detection["class_name"] == "autorickshaw":
            continue

        if detection["class_name"] == "autorickshaw":
            merged_detections[duplicate_index] = detection
            continue

        if (
            detection["source"] == "coco"
            and existing_detection["source"] == "custom"
            and detection["confidence"] >= 0.40
        ):
            merged_detections[duplicate_index] = detection

    return merged_detections


def create_lane_mask(image_shape, polygon):
    if polygon is None:
        return None

    mask = np.zeros(image_shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)
    return mask


def is_detection_in_lane(box_coordinates, lane_mask):
    if lane_mask is None:
        return True

    height, width = lane_mask.shape[:2]
    x1, y1, x2, y2 = map(int, box_coordinates)
    x1 = max(0, min(width - 1, x1))
    x2 = max(0, min(width, x2))
    y1 = max(0, min(height - 1, y1))
    y2 = max(0, min(height, y2))

    if x2 <= x1 or y2 <= y1:
        return False

    box_area = (x2 - x1) * (y2 - y1)
    lane_pixels = cv2.countNonZero(lane_mask[y1:y2, x1:x2])
    overlap_ratio = lane_pixels / box_area

    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)
    center_inside = lane_mask[center_y, center_x] > 0

    return center_inside or overlap_ratio >= LANE_OVERLAP_RATIO


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
               iou=DETECTION_IOU,
               verbose=False
         )

        coco_detections = get_coco_vehicle_detections(image)

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
        
        lane_mask = create_lane_mask(
            image.shape,
            polygon
        )

        custom_detections = get_custom_vehicle_detections(
            detections,
            coco_detections
        )

        merged_detections = merge_vehicle_detections(
            custom_detections,
            coco_detections
        )

        for detection in merged_detections:
            class_name = detection["class_name"]
            confidence = detection["confidence"]
            x1, y1, x2, y2 = map(
                int,
                detection["box"]
            )

            if not is_detection_in_lane(
                (x1, y1, x2, y2),
                lane_mask
            ):
                continue

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
