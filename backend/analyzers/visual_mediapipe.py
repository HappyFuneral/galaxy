
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
import cv2
import numpy as np
import mediapipe as mp
from backend.engine.models import Segment

@dataclass
class VisualConfig:
    sample_fps: float = 2.0
    edge_margin: float = 0.04

class MediaPipeVisualAnalyzer:
    def __init__(self, video_path: str, config: VisualConfig | None = None):
        self.video_path = video_path
        self.cfg = config or VisualConfig()
        self.hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2)
        self.face = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

    def _bbox_from_landmarks(self, landmarks):
        xs = [lm.x for lm in landmarks]
        ys = [lm.y for lm in landmarks]
        x1, x2 = max(0.0, min(xs)), min(1.0, max(xs))
        y1, y2 = max(0.0, min(ys)), min(1.0, max(ys))
        return x1, y1, x2, y2

    def _near_edge(self, bbox) -> bool:
        x1, y1, x2, y2 = bbox
        m = self.cfg.edge_margin
        return (x1 < m) or (y1 < m) or (x2 > 1.0 - m) or (y2 > 1.0 - m)

    def extract(self, segment: Segment) -> Dict[str, Any]:
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {self.video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        start_frame = int(segment.start * fps)
        end_frame = int(segment.end * fps)
        step = max(1, int(fps / self.cfg.sample_fps))

        total = 0
        hands_yes = 0
        face_yes = 0
        framing_issues = 0
        motions = []
        prev_gray = None

        for fidx in range(start_frame, end_frame, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
            ok, frame = cap.read()
            if not ok:
                break

            total += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            hands_res = self.hands.process(rgb)
            if hands_res.multi_hand_landmarks:
                hands_yes += 1
                for hand in hands_res.multi_hand_landmarks:
                    bbox = self._bbox_from_landmarks(hand.landmark)
                    if self._near_edge(bbox):
                        framing_issues += 1
                        break

            face_res = self.face.process(rgb)
            if face_res.detections:
                face_yes += 1

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                motions.append(float(np.mean(diff)) / 255.0)
            prev_gray = gray

        cap.release()

        if total == 0:
            return {"hands_visible_ratio":0.0,"face_visible_ratio":0.0,"motion_intensity":0.0,"framing_issue_ratio":1.0}

        return {
            "hands_visible_ratio": float(hands_yes / total),
            "face_visible_ratio": float(face_yes / total),
            "motion_intensity": float(np.mean(motions)) if motions else 0.0,
            "framing_issue_ratio": float(framing_issues / total),
        }
