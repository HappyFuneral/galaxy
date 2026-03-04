from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2

try:
    import mediapipe as mp
except Exception:
    mp = None


@dataclass
class FacePoint:
    t: float
    x: float
    conf: float


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _ema(points: List[FacePoint], alpha: float) -> List[FacePoint]:
    if not points:
        return []
    alpha = max(0.01, min(0.99, float(alpha)))
    out = [points[0]]
    cur = points[0].x
    for p in points[1:]:
        cur = alpha * p.x + (1.0 - alpha) * cur
        out.append(FacePoint(t=p.t, x=cur, conf=p.conf))
    return out


def _downsample(points: List[FacePoint], max_points: int) -> List[FacePoint]:
    if max_points <= 0 or len(points) <= max_points:
        return points
    step = len(points) / max_points
    out: List[FacePoint] = []
    i = 0.0
    while int(i) < len(points) and len(out) < max_points:
        out.append(points[int(i)])
        i += step
    return out


def _rate_limit(points: List[FacePoint], max_delta_per_s: float) -> List[FacePoint]:
    if not points:
        return []
    max_delta_per_s = max(0.01, float(max_delta_per_s))
    out = [points[0]]
    for p in points[1:]:
        prev = out[-1]
        dt = max(1e-3, p.t - prev.t)
        max_delta = max_delta_per_s * dt
        dx = p.x - prev.x
        if abs(dx) > max_delta:
            p = FacePoint(t=p.t, x=prev.x + max_delta * (1 if dx > 0 else -1), conf=p.conf)
        out.append(p)
    return out


def track_speaker_face_x(
    video_path: Path,
    start: float,
    end: float,
    *,
    sample_fps: float = 2.0,
    max_width: int = 320,
    min_conf: float = 0.5,
) -> List[Dict[str, Any]]:
    dur = max(0.0, end - start)
    if dur <= 0.2 or mp is None:
        return []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)

    face_det = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=float(min_conf))
    step = max(1, int(round(src_fps / max(0.1, sample_fps))))

    points: List[FacePoint] = []
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
        abs_t = float(pos_msec / 1000.0)
        if abs_t > end + 0.05:
            break

        if frame_idx % step != 0:
            frame_idx += 1
            continue

        h, w = frame.shape[:2]
        if w > max_width:
            scale = max_width / float(w)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_det.process(rgb)

        best_x = None
        best_conf = 0.0
        if res.detections:
            for det in res.detections:
                score = float(det.score[0]) if det.score else 0.0
                bb = det.location_data.relative_bounding_box
                cx = float(bb.xmin + bb.width * 0.5)
                if score > best_conf:
                    best_conf = score
                    best_x = cx

        rel_t = max(0.0, abs_t - start)
        if best_x is not None and best_conf >= min_conf:
            points.append(FacePoint(t=rel_t, x=_clamp01(best_x), conf=_clamp01(best_conf)))

        frame_idx += 1

    cap.release()

    if not points:
        return []

    pts = _ema(points, alpha=0.25)
    pts = _rate_limit(pts, max_delta_per_s=0.35)
    pts = _downsample(pts, max_points=18)
    return [{"t": float(p.t), "x": float(p.x), "conf": float(p.conf)} for p in pts]


def build_speaker_crop_x_expr(
    speaker_face_track: List[Dict[str, Any]],
    *,
    ema_alpha: float = 0.25,
    max_points: int = 18,
    max_delta_per_s: float = 0.35,
) -> Optional[str]:
    if not speaker_face_track:
        return None

    pts: List[Tuple[float, float]] = []
    for p in speaker_face_track:
        tt = float(p.get("t", 0.0))
        xx = _clamp01(float(p.get("x", 0.5)))
        pts.append((tt, xx))
    pts.sort(key=lambda z: z[0])

    if len(pts) > max_points and max_points > 0:
        step = len(pts) / max_points
        pts2 = []
        i = 0.0
        while int(i) < len(pts) and len(pts2) < max_points:
            pts2.append(pts[int(i)])
            i += step
        pts = pts2

    def seg_expr(t0: float, x0: float, t1: float, x1: float) -> str:
        dt = max(1e-3, t1 - t0)
        return f"({x0:.6f} + ({(x1-x0):.6f})*((t-{t0:.3f})/{dt:.6f}))"

    expr = f"{pts[-1][1]:.6f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(pts[:-1], pts[1:]))):
        lerp = seg_expr(t0, x0, t1, x1)
        expr = f"if(lt(t,{t1:.3f}),{lerp},{expr})"

    out_w = "(ih*9/16)"
    x_px = f"({expr})*iw - ({out_w})/2"
    x_clamped = f"max(0,min({x_px},iw-({out_w})))"
    return x_clamped
