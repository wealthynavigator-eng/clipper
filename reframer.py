import os
from typing import Any

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceDetector,
    FaceDetectorOptions,
    RunningMode,
)

_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/1/blaze_face_short_range.tflite"
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "face_detector_short_range.tflite")

_detector: Any = None
_init_error: str | None = None


def _ensure_model() -> str | None:
    if os.path.exists(_MODEL_PATH):
        return _MODEL_PATH
    os.makedirs(os.path.dirname(_MODEL_PATH), exist_ok=True)
    try:
        import urllib.request
        print(f"Downloading face detection model to {_MODEL_PATH}...")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        return _MODEL_PATH
    except Exception:
        return None


def _get_detector() -> Any:
    global _detector, _init_error
    if _detector is not None:
        return _detector
    if _init_error is not None:
        return None
    model_path = _ensure_model()
    if not model_path:
        _init_error = "Failed to locate or download face detection model"
        return None
    try:
        options = FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.IMAGE,
            min_detection_confidence=0.5,
        )
        _detector = FaceDetector.create_from_options(options)
        return _detector
    except Exception as e:
        _init_error = str(e)
        return None


def _frame_to_mp_image(frame: np.ndarray) -> Any:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    return mp_img


def detect_face_centers(
    video_path: str,
    start: float,
    end: float,
    num_samples: int = 20,
) -> list[int]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if total_frames > 0 else end

    clip_start_frame = int(start * fps)
    clip_end_frame = int(min(end, duration) * fps)
    clip_duration_frames = clip_end_frame - clip_start_frame

    if clip_duration_frames <= 0:
        cap.release()
        return []

    step = max(1, clip_duration_frames // num_samples)
    detector = _get_detector()
    if detector is None:
        cap.release()
        return []

    centers: list[int] = []

    for frame_idx in range(clip_start_frame, clip_end_frame, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        mp_img = _frame_to_mp_image(frame)
        result = detector.detect(mp_img)

        if result.detections:
            xs: list[int] = []
            for d in result.detections:
                bbox = d.bounding_box
                cx = bbox.origin_x + bbox.width // 2
                xs.append(cx)
            centers.append(int(np.median(xs)))

    cap.release()
    return centers


def compute_crop_x(
    video_path: str,
    start: float,
    end: float,
    video_width: int | None = None,
    video_height: int | None = None,
) -> int | None:
    if video_width is None or video_height is None:
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

    if not video_width or not video_height:
        return None

    crop_w = video_height * 9 / 16
    if crop_w >= video_width:
        return 0

    centers = detect_face_centers(video_path, start, end)

    if not centers:
        return None

    target_x = int(np.median(centers) - crop_w / 2)
    target_x = max(0, min(target_x, int(video_width - crop_w)))
    return target_x


def crop_filter(
    video_path: str,
    start: float,
    end: float,
    video_width: int | None = None,
    video_height: int | None = None,
) -> str:
    x = compute_crop_x(video_path, start, end, video_width, video_height)
    if x is not None:
        return f"crop=w='min(iw,ih*9/16)':h=ih:x={x}"
    return "crop=w='min(iw,ih*9/16)':h=ih"
