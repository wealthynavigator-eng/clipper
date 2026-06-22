# Clipper — Build Plan

Current pipeline: `download → transcribe → analyze(LLM) → slice(ffmpeg)`

## ✅ Phase 1 — Complete

| # | Feature | Module |
|---|---------|--------|
| 1 | Multi-LLM provider | `analyzer.py` |
| 2 | Hook overlay banner | `cutter.py` |
| 3 | Config file + Streamlit sidebar | `config.py`, `app.py` |
| 4 | Local file input | `app.py` |

## ✅ Phase 2 — Complete

| # | Feature | Module |
|---|---------|--------|
| 5 | Clip review UI (timeline + edit) | `app.py` |
| 6 | Subtitle style presets (ASS) | `subtitle.py`, `cutter.py` |
| 7 | Scene detection (PySceneDetect) | `scanner.py` |
| 8 | Batch URL processing | `app.py` |

## ✅ Phase 3 — Complete

| # | Feature | Module |
|---|---------|--------|
| 9 | Face-aware crop (MediaPipe) | `reframer.py`, `cutter.py` |
| 10 | Thumbnail generator | `cutter.py` (inline ffmpeg) |
| 11 | Audio ducking + BGM | `cutter.py` |

## ✅ Phase 4 — Complete

| # | Feature | Module |
|---|---------|--------|
| 12 | Watermark / logo overlay (position, scale, opacity) | `watermarker.py`, `cutter.py` |
| 13 | Smart transitions between clips (xfade/acrossfade) | `compiler.py`, `app.py` |

## Design principles

- Each feature is independently mergeable
- Config-driven: provider, styles, durations all settable via sidebar
- Provider-agnostic analyzer: swap Mistral / Groq / OpenAI / Ollama via dropdown
