import os
import shutil
import sys
import tempfile
from typing import Any

import streamlit as st

from analyzer import find_clip_moments
from compiler import compile_clips
from config import settings
from cutter import slice_video
from downloader import download_video
from scanner import detect_scenes, refine_clips
from transcriber import transcribe_audio


def _setup_sidebar() -> None:
    with st.sidebar:
        st.header("Settings")
        settings.llm_provider = st.selectbox(
            "LLM Provider",
            ["mistral", "groq", "openai", "ollama"],
            index=["mistral", "groq", "openai", "ollama"].index(
                settings.llm_provider
            ),
        )
        settings.llm_model = st.text_input("Model", settings.llm_model)
        st.divider()
        st.subheader("Clips")
        col1, col2 = st.columns(2)
        with col1:
            settings.min_clips = st.number_input("Min clips", 1, 20, settings.min_clips)
        with col2:
            settings.max_clips = st.number_input("Max clips", 1, 20, settings.max_clips)
        settings.clip_min_duration = st.slider(
            "Min clip duration (s)", 15, 120, int(settings.clip_min_duration), 5
        )
        settings.clip_max_duration = st.slider(
            "Max clip duration (s)", 15, 180, int(settings.clip_max_duration), 5
        )
        st.divider()
        st.subheader("Video")
        settings.subtitle_style = st.selectbox(
            "Subtitle style",
            ["default", "mrbeast", "hormozi", "karaoke"],
            index=["default", "mrbeast", "hormozi", "karaoke"].index(
                settings.subtitle_style
            ),
        )
        settings.hook_overlay = st.toggle("Hook overlay", settings.hook_overlay)
        settings.face_tracking = st.toggle("Face tracking", settings.face_tracking)
        settings.audio_normalize = st.toggle("Audio normalize", settings.audio_normalize)
        settings.thumbnail = st.toggle("Thumbnails", settings.thumbnail)
        settings.bgm_path = st.text_input("BGM file path (optional)", settings.bgm_path)
        if settings.bgm_path:
            settings.bgm_volume = st.slider("BGM volume", 0.0, 1.0, settings.bgm_volume, 0.05)
        st.divider()
        st.subheader("Watermark")
        settings.watermark_path = st.text_input("Logo file path (optional)", settings.watermark_path)
        if settings.watermark_path:
            settings.watermark_position = st.selectbox(
                "Position",
                ["top-left", "top-center", "top-right", "left-center",
                 "center", "right-center", "bottom-left", "bottom-center", "bottom-right"],
                index=["top-left", "top-center", "top-right", "left-center",
                       "center", "right-center", "bottom-left", "bottom-center",
                       "bottom-right"].index(settings.watermark_position),
            )
            col1, col2 = st.columns(2)
            with col1:
                settings.watermark_scale = st.slider("Size", 0.05, 0.5, settings.watermark_scale, 0.05)
            with col2:
                settings.watermark_opacity = st.slider("Opacity", 0.1, 1.0, settings.watermark_opacity, 0.1)

        st.divider()
        st.subheader("Reel")
        settings.compile_reel = st.toggle("Compile into single reel", settings.compile_reel)
        if settings.compile_reel:
            settings.transition_type = st.selectbox(
                "Transition",
                ["cut", "crossfade", "fadeblack", "fadewhite", "slideleft",
                 "slideright", "slidetop", "slidebottom", "zoomin"],
                index=["cut", "crossfade", "fadeblack", "fadewhite", "slideleft",
                       "slideright", "slidetop", "slidebottom", "zoomin"].index(
                    settings.transition_type
                ),
            )
            if settings.transition_type != "cut":
                settings.transition_duration = st.slider(
                    "Transition duration (s)", 0.1, 1.0, settings.transition_duration, 0.1
                )

        settings.parallel_workers = st.slider("Parallel workers", 1, 8, settings.parallel_workers)


def _normalize_clips(clip_moments: Any) -> Any:
    if isinstance(clip_moments, list) and len(clip_moments) > 0:
        first = clip_moments[0]
        if isinstance(first, dict) and any("clip" in k.lower() for k in first):
            clips_key = next(k for k in first if "clip" in k.lower())
            return first[clips_key]
        elif isinstance(first, dict) and "start" in first:
            return clip_moments
    return clip_moments


def analyze_pipeline(video_path: str, is_local: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"error": None}

    if is_local:
        dl = {
            "title": os.path.splitext(os.path.basename(video_path))[0],
            "filepath": video_path,
            "duration_seconds": 0,
        }
    else:
        with st.status("Downloading video...") as s:
            dl = download_video(video_path)
            if dl.get("error"):
                result["error"] = f"Download failed: {dl['error']}"
                return result
            s.update(label="Downloaded", state="complete")
        video_path = str(dl["filepath"])

    with st.status("Transcribing audio...") as s:
        transcribe_result = transcribe_audio(video_path)
        if transcribe_result.get("error"):
            result["error"] = f"Transcription failed: {transcribe_result['error']}"
            return result
        s.update(label="Transcribed", state="complete")

    with st.status("Analyzing with AI...") as s:
        try:
            clip_moments = find_clip_moments(transcribe_result)
        except Exception as e:
            result["error"] = f"Analysis failed: {e}"
            return result
        s.update(label="Analysis complete", state="complete")

    if not clip_moments:
        result["error"] = "No clip moments found"
        return result

    result["video_path"] = video_path
    result["clips"] = _normalize_clips(clip_moments)
    result["segments"] = transcribe_result.get("segments")
    result["title"] = dl.get("title", os.path.basename(video_path))
    result["duration"] = dl.get("duration_seconds", 0)
    return result


def render_pipeline(video_path: str, clips: Any, segments: Any) -> list[str]:
    with st.status("Detecting scene cuts...") as s:
        scenes = detect_scenes(video_path)
        s.update(label=f"Detected {len(scenes)} scene cuts" if scenes else "No scene cuts detected", state="complete")

    clips = refine_clips(clips, scenes)

    with st.status("Slicing clips...") as s:
        paths = slice_video(video_path, clips, segments=segments)
        s.update(label=f"Rendered {len(paths)} clips", state="complete")

    if settings.compile_reel and len(paths) > 1:
        output_path = os.path.join(settings.output_dir, "reel.mp4")
        with st.status("Compiling reel...") as s:
            compile_clips(
                paths,
                transition=settings.transition_type,
                duration=settings.transition_duration,
                output_path=output_path,
            )
            s.update(label="Reel compiled", state="complete")
            paths = paths + [output_path]

    return paths


def main() -> None:
    if "phase" not in st.session_state:
        st.session_state.phase = "input"

    _setup_sidebar()

    if len(sys.argv) > 1:
        url = sys.argv[1]
        result = analyze_pipeline(url)
        if result.get("error"):
            print(f"Error: {result['error']}")
        else:
            paths = render_pipeline(result["video_path"], result["clips"], result.get("segments"))
            print(f"Rendered {len(paths)} clips")
            for p in paths:
                print(f"  - {p}")
        return

    st.title("Video Clip Generator")

    if st.session_state.phase == "input":
        _input_phase()
    elif st.session_state.phase == "review":
        _review_phase()
    elif st.session_state.phase == "done":
        _done_phase()


def _input_phase() -> None:
    mode = st.radio("Mode", ["Single", "Batch"], horizontal=True, key="mode")

    if mode == "Batch":
        st.caption("Process multiple URLs sequentially (no review step)")
        urls = st.text_area(
            "URLs (one per line)",
            placeholder="https://youtube.com/...\nhttps://youtube.com/...",
            key="batch_urls",
        )
        url_list = [u.strip() for u in urls.splitlines() if u.strip()] if urls else []

        if url_list and st.button("Analyze all", type="primary"):
            all_results = []
            progress = st.progress(0, text="")
            for idx, url in enumerate(url_list):
                progress.progress((idx) / len(url_list), text=f"[{idx+1}/{len(url_list)}] {url[:60]}...")
                result = analyze_pipeline(url)
                if result.get("error"):
                    st.error(f"[{url[:60]}...] {result['error']}")
                    continue
                paths = render_pipeline(result["video_path"], result["clips"], result.get("segments"))
                all_results.append({
                    "url": url, "title": result["title"],
                    "clips": len(result["clips"]), "paths": paths,
                })
                progress.progress((idx + 1) / len(url_list), text=f"Done {idx+1}/{len(url_list)}")

            st.success(f"Processed {len(all_results)}/{len(url_list)} videos")
            for r in all_results:
                with st.expander(f"**{r['title']}** — {r['clips']} clips"):
                    for p in r["paths"]:
                        st.code(p)
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            return

    source = st.radio("Source", ["URL", "Local file"], horizontal=True, key="source")

    video_path = None
    is_local = False

    if source == "URL":
        url = st.text_input("Video URL", placeholder="https://youtube.com/...", key="url")
        if url:
            video_path = url
    else:
        uploaded = st.file_uploader("Upload video", type=["mp4", "webm", "mov", "avi", "mkv"], key="upload")
        if uploaded:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1])
            shutil.copyfileobj(uploaded, tmp)
            tmp.close()
            video_path = tmp.name
            is_local = True

    if video_path and st.button("Analyze", type="primary"):
        result = analyze_pipeline(video_path, is_local=is_local)
        if result.get("error"):
            st.error(result["error"])
            return
        st.session_state.result = result
        st.session_state.phase = "review"
        st.rerun()


def _review_phase() -> None:
    result = st.session_state.result
    clips = result["clips"]

    st.success("Analysis complete!")
    st.write(f"**{result['title']}** — {result['duration']}s &nbsp;·&nbsp; {len(clips)} clips found")
    st.write("Adjust clip boundaries and metadata below, then render.")

    edited = []
    for i, clip in enumerate(clips):
        with st.container(border=True):
            st.write(f"**Clip {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                start = st.number_input(
                    "Start (s)", value=float(clip.get("start", 0)),
                    key=f"start_{i}", step=0.5,
                )
                hook = st.text_input(
                    "Hook", value=clip.get("hook_text", ""),
                    key=f"hook_{i}",
                )
            with col2:
                end = st.number_input(
                    "End (s)", value=float(clip.get("end", 0)),
                    key=f"end_{i}", step=0.5,
                )
                strategy = st.text_input(
                    "Strategy", value=clip.get("retention_strategy", ""),
                    key=f"strategy_{i}",
                )
            edited.append({
                "start": start, "end": end,
                "hook_text": hook, "retention_strategy": strategy,
            })

    st.divider()
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", type="secondary"):
            for k in ["phase", "result"]:
                st.session_state.pop(k, None)
            st.rerun()
    with col2:
        if st.button("Render clips", type="primary"):
            st.session_state.edited_clips = edited
            st.session_state.phase = "done"
            st.rerun()


def _done_phase() -> None:
    result = st.session_state.result
    clips = st.session_state.edited_clips

    paths = render_pipeline(result["video_path"], clips, result.get("segments"))

    if not paths:
        st.error("Failed to render clips")
        st.session_state.phase = "review"
        st.rerun()
        return

    reel_path = None
    if settings.compile_reel and len(paths) > 1 and paths[-1].endswith("reel.mp4"):
        reel_path = paths.pop()

    n_clips = len(paths)
    st.success(f"Rendered {n_clips} clips!" + (" + compiled reel" if reel_path else ""))

    if reel_path:
        st.write("### Compiled Reel")
        st.code(reel_path)

    st.write("### Individual clips")
    for i, path in enumerate(paths):
        clip = clips[i] if i < len(clips) else {}
        with st.expander(f"Clip {i+1}: {clip['start']}s → {clip['end']}s", expanded=i == 0 and not reel_path):
            st.write(f"**Hook:** {clip.get('hook_text', '—')}")
            st.write(f"**Strategy:** {clip.get('retention_strategy', '—')}")
            st.code(path)

    if st.button("Start over", type="secondary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


if __name__ == "__main__":
    main()
