from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.pipeline.ffprobe import get_video_duration_seconds
from backend.pipeline.segmenter import generate_sliding_segments
from backend.pipeline.postprocess import build_vf_filtergraph
from backend.pipeline.subtitles import build_srt_items, write_srt
from backend.pipeline.audio_mix import decide_bgm_auto, export_clip_with_optional_bgm
from backend.pipeline.speaker_focus import track_speaker_face_x
from backend.pipeline.recipe import write_export_recipe

from backend.engine.models import Segment
from backend.engine.context import build_ctx_for_video
from backend.engine.runner import build_engine_runner
from backend.pipeline.guitar_focus import detect_guitar_focus
from backend.pipeline.tab_generator import generate_tab_audio_only_for_segment
from backend.pipeline.preview_tab import maybe_build_tab_ass_for_preview


@dataclass
class ClipCandidate:
    segment: Segment
    decision: str
    final_score: float
    scores: Dict[str, float]
    explanation: Dict[str, Any]
    recommendations: Dict[str, Any]
    visual_active_windows: List[Dict[str, Any]]


def _far_enough(seg: Segment, chosen: List[Segment], min_gap_s: float) -> bool:
    for c in chosen:
        if not (seg.end + min_gap_s <= c.start or c.end + min_gap_s <= seg.start):
            return False
    return True


def select_top_clips(candidates: List[ClipCandidate], max_clips: int, min_gap_s: float, min_score: float) -> List[
    ClipCandidate]:
    ranked = sorted(candidates, key=lambda x: x.final_score, reverse=True)
    chosen: List[ClipCandidate] = []
    chosen_segs: List[Segment] = []
    for c in ranked:
        if c.final_score < min_score:
            continue
        if _far_enough(c.segment, chosen_segs, min_gap_s):
            chosen.append(c)
            chosen_segs.append(c.segment)
        if len(chosen) >= max_clips:
            break
    return chosen


def notes_to_windows(note_events: list[dict], min_density: float = 1.6) -> list[dict]:
    # min_density = notes/sec
    if not note_events:
        return []
    # bin in 1.5 sec chunks, mark bins where density high
    bins = {}
    for e in note_events:
        t0 = float(e["t_start"])
        b = int(t0 / 1.5)
        bins[b] = bins.get(b, 0) + 1

    windows = []
    for b, cnt in bins.items():
        density = cnt / 1.5
        if density >= min_density:
            windows.append({"start": b * 1.5, "end": b * 1.5 + 1.5, "intensity": min(1.0, density / 4.0)})

    return windows


def run_pipeline(
        video_path: Path,
        platform: str,
        export: bool,
        export_dir: Optional[Path],
        export_size: Optional[Tuple[int, int]],
        cfg: Dict[str, Any],
        job_bgm_path_str: Optional[str] = None,
        captions: bool = False,
        burn_in: bool = False,
        speaker_focus: bool = False,
        **kwargs,
) -> Dict[str, Any]:
    if job_bgm_path_str is None and "bgm_path_str" in kwargs:
        job_bgm_path_str = kwargs.get("bgm_path_str")

    duration_s = get_video_duration_seconds(video_path)

    window_s = float(cfg["thresholds"]["sliding_window"]["window_s"])
    step_s = float(cfg["thresholds"]["sliding_window"]["step_s"])
    max_clips = int(cfg["thresholds"]["selection"]["max_clips"])
    min_gap_s = float(cfg["thresholds"]["selection"]["min_gap_s"])
    min_score = float(cfg["thresholds"]["selection"]["min_score"])

    segments = generate_sliding_segments(duration_s, window_s=window_s, step_s=step_s)

    vctx = build_ctx_for_video(str(video_path), cfg=cfg)
    runner = build_engine_runner(cfg=cfg)

    candidates: List[ClipCandidate] = []
    for seg in segments:
        res = runner.evaluate_segment(seg, platform=platform, vctx=vctx)
        candidates.append(ClipCandidate(
            segment=seg,
            decision=res.decision,
            final_score=float(res.final_score),
            scores=res.scores,
            explanation=res.explanation,
            recommendations=res.recommendations,
            visual_active_windows=list(res.active_windows or []),
        ))

    selected = select_top_clips(candidates, max_clips=max_clips, min_gap_s=min_gap_s, min_score=min_score)

    fallback_used = False
    if not selected:
        fallback_used = True
        ranked = sorted(candidates, key=lambda x: x.final_score, reverse=True)
        chosen: List[ClipCandidate] = []
        chosen_segs: List[Segment] = []
        for c in ranked:
            if _far_enough(c.segment, chosen_segs, min_gap_s):
                chosen.append(c)
                chosen_segs.append(c.segment)
            if len(chosen) >= max_clips:
                break
        selected = chosen

    exports: List[Dict[str, Any]] = []
    post_cfg = cfg.get("postprocess", {}) or {}
    mix_cfg = cfg.get("audio_mix", {}) or {}
    perf = cfg.get("performance", {}) or {}
    tab_cfg = ((cfg.get("tab") or {}).get("audio_only") or {})

    speech_vad_only = bool(perf.get("speech_vad_only", True))
    max_whisper_clips = int(perf.get("max_whisper_clips", 2))
    whisper_on_selected_only = bool(perf.get("whisper_on_selected_only", True))

    if export and export_dir and selected:
        export_dir.mkdir(parents=True, exist_ok=True)
        bgm_path = Path(job_bgm_path_str) if job_bgm_path_str else None
        debug_dir = export_dir / "_debug_ffmpeg"

        for i, clip in enumerate(selected, start=1):
            filename = f"clip_{i:02d}_{platform}.mp4"
            out = export_dir / filename
            export_id = out.stem

            speech_feat = vctx.speech.extract(clip.segment)
            music_feat = vctx.music.extract(clip.segment)
            visual_feat = vctx.visual.extract(clip.segment)

            gf = detect_guitar_focus(music_feat=music_feat, visual_feat=visual_feat, speech_feat=speech_feat, cfg=cfg)

            tab_out = None
            tab_json = None
            stem = f"clip_{i:02d}_{platform}"

            # 1) TAB generálás (csak ha gitár fókusz vagy forced)
            force_tab = bool((cfg.get("tab") or {}).get("force", False))
            if (cfg.get("tab") or {}).get("enabled", True) and (gf.is_guitar_focused or force_tab):
                tab_out = generate_tab_audio_only_for_segment(
                    input_video=video_path,
                    start=clip.segment.start,
                    end=clip.segment.end,
                    out_dir=export_dir,
                    stem=stem,
                    cfg=tab_cfg,
                )
                tab_json = (tab_out or {}).get("exports", {}).get("files", {}).get("json")

            # 2) TAB overlay (ASS) – ha VAN tab_json, akkor próbáld meg mindig

            speech_ratio = float(speech_feat.get("speech_ratio", 0.0))
            music_activity = float(music_feat.get("music_activity", 0.0))

            mix_dec = decide_bgm_auto(speech_ratio, music_activity, mix_cfg)

            srt_path = export_dir / f"clip_{i:02d}_{platform}.srt"
            items = []
            do_whisper = bool(captions) and (not speech_vad_only) and (
                        not whisper_on_selected_only or i <= max_whisper_clips)
            if do_whisper:
                from backend.pipeline.speech_whisper import transcribe_clip_whisper
                segs = transcribe_clip_whisper(video_path, clip.segment.start, clip.segment.end, cfg=cfg)
                items = build_srt_items(segs)
                if items:
                    write_srt(items, srt_path)

            speaker_track = None
            if speaker_focus:
                speaker_track = track_speaker_face_x(
                    video_path,
                    clip.segment.start,
                    clip.segment.end,
                    sample_fps=2.0,
                    max_width=320,
                    min_conf=0.5,
                )

            burn_in_srt = str(srt_path) if (burn_in and items) else None

            from backend.pipeline.guitar_solo import solo_overlay_from_tab_json
            solo_windows = solo_overlay_from_tab_json(Path(tab_json)).windows if tab_json else []

            tab_ass = maybe_build_tab_ass_for_preview(
                tab_json=tab_json,
                out_dir=export_dir / f"{stem}.tab.ass",
                stem=stem,
                clip_duration_s=float(duration_s),
                cfg=cfg,
            )

            vf = build_vf_filtergraph(
                post_cfg,
                active_windows=clip.visual_active_windows,
                clip_duration_s=clip.segment.duration,
                burn_in_srt_path=burn_in_srt,
                tab_ass_path=str(tab_ass) if tab_ass else None,  # ⬅️ EZ AZ ÚJ
                speaker_face_track=speaker_track,
                apply_speaker_crop=bool(speaker_focus and speaker_track),
                guitar_solo_windows=solo_windows
            )

            export_clip_with_optional_bgm(
                input_video=video_path,
                output_video=out,
                start=clip.segment.start,
                end=clip.segment.end,
                vf=vf,
                bgm_path=bgm_path,
                mix_cfg=mix_cfg,
                use_bgm=mix_dec.use_bgm,
                burn_in=burn_in,
                srt_path=srt_path if (burn_in and items) else None,
                debug_dir=debug_dir,
                debug_stem=f"clip_{i:02d}_{platform}",
            )

            # ---- NEW: recipe autosave for mobile preview/re-export ----
            recipe_path = export_dir / f"{export_id}.recipe.json"
            write_export_recipe(
                recipe_path=recipe_path,
                input_video=video_path,
                platform=platform,
                segment={"start": float(clip.segment.start), "end": float(clip.segment.end)},
                overrides={
                    # keep these separate so mobile can tweak them
                    "postprocess": {},
                    "audio_mix": {},
                    # to preserve highlight timing for preview editing:
                    "active_windows": clip.visual_active_windows,
                },
                bgm_path=bgm_path if bgm_path and bgm_path.exists() else None,
                use_bgm=bool(mix_dec.use_bgm),
                burn_in_srt_path=Path(burn_in_srt) if burn_in_srt else None,
                speaker_face_track=speaker_track,
                apply_speaker_crop=bool(speaker_focus and speaker_track),
            )

            exports.append({
                "filename": filename,
                "export_id": export_id,
                "recipe": str(recipe_path),
                "start": clip.segment.start,
                "end": clip.segment.end,
                "srt": str(srt_path) if items else None,
                "bgm_used": mix_dec.use_bgm,
                "bgm_reason": mix_dec.reason,
                "speech_ratio": speech_ratio,
                "music_activity": music_activity,
                "burn_in": bool(burn_in and items),
                "speaker_focus": bool(speaker_focus),
                "guitar_focus": {"is": gf.is_guitar_focused, "confidence": gf.confidence, "reasons": gf.reasons},
                "tab": tab_out,
                "tab_json": tab_json,
                "tab_ass": str(tab_ass) if tab_ass else None,
            })

    return {
        "video_path": str(video_path),
        "duration_s": duration_s,
        "platform": platform,
        "segments_considered": len(segments),
        "fallback_used": fallback_used,
        "candidates": [
            {"start": c.segment.start, "end": c.segment.end, "decision": c.decision, "final_score": c.final_score,
             "scores": c.scores, "explanation": c.explanation, "recommendations": c.recommendations}
            for c in candidates
        ],
        "selected": [
            {"start": c.segment.start, "end": c.segment.end, "decision": c.decision, "final_score": c.final_score,
             "scores": c.scores, "explanation": c.explanation, "recommendations": c.recommendations,
             "active_windows": c.visual_active_windows}
            for c in selected
        ],
        "exports": exports,
    }
