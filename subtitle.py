from typing import Any


def _srt_time(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    h, remainder = divmod(total_ms, 3600000)
    m, remainder = divmod(remainder, 60000)
    s, ms = divmod(remainder, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ass_time(seconds: float) -> str:
    total_cs = int(round(seconds * 100))
    h, remainder = divmod(total_cs, 360000)
    m, remainder = divmod(remainder, 6000)
    s, cs = divmod(remainder, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


_StyleDict = dict[str, Any]

_STYLE_DEFS: dict[str, _StyleDict] = {
    "default": {
        "name": "Default",
        "fontname": "Arial",
        "fontsize": 18,
        "bold": 0,
        "italic": 0,
        "underline": 0,
        "strikeout": 0,
        "scale_x": 100,
        "scale_y": 100,
        "spacing": 0,
        "angle": 0,
        "border_style": 1,
        "outline": 2,
        "shadow": 1,
        "alignment": 2,
        "margin_l": 20,
        "margin_r": 20,
        "margin_v": 30,
        "alpha": 0,
        "encoding": 1,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H000000FF",
        "outline_color": "&H00000000",
        "shadow_color": "&H00000000",
    },
    "mrbeast": {
        "name": "MrBeast",
        "fontname": "Impact",
        "fontsize": 26,
        "bold": 1,
        "primary_color": "&H0000FFFF",
        "outline_color": "&H00000000",
        "outline": 4,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 40,
    },
    "hormozi": {
        "name": "Hormozi",
        "fontname": "Arial",
        "fontsize": 20,
        "bold": 1,
        "border_style": 3,
        "outline": 0,
        "shadow": 0,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00000000",
        "outline_color": "&H00000000",
        "background_color": "&H00660000",
        "alignment": 2,
        "margin_v": 10,
    },
    "karaoke": {
        "name": "Karaoke",
        "fontname": "Arial",
        "fontsize": 18,
        "bold": 0,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000FFFF",
        "outline_color": "&H00000000",
        "outline": 2,
        "shadow": 1,
        "alignment": 2,
        "margin_v": 30,
    },
}

_Segment = dict[str, Any]


def _build_style(style_name: str) -> tuple[str, str]:
    base = dict(_STYLE_DEFS["default"])
    overrides = _STYLE_DEFS.get(style_name, {})
    base.update(overrides)
    s = base
    fmt = (
        f"Style: {s['name']},{s['fontname']},{s['fontsize']},"
        f"{s['primary_color']},{s['secondary_color']},{s['outline_color']},{s['shadow_color']},"
        f"{s['bold']},{s['italic']},{s['underline']},{s['strikeout']},"
        f"{s['scale_x']},{s['scale_y']},{s['spacing']},{s['angle']},"
        f"{s['border_style']},{s['outline']},{s['shadow']},{s['alignment']},"
        f"{s['margin_l']},{s['margin_r']},{s['margin_v']},{s['encoding']}"
    )
    return s["name"], fmt


def _make_ass(
    segments: list[_Segment] | None,
    clip_start: float,
    clip_end: float,
    style: str = "default",
) -> str:
    style_name, style_fmt = _build_style(style)

    lines = [
        "[Script Info]",
        "Title: Clipper subtitles",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",  # noqa: E501
        style_fmt,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for seg in (segments or []):
        s = seg.get("start", 0)
        e = seg.get("end", 0)
        text = seg.get("text", "").strip()
        if not text:
            continue
        if s < clip_end and e > clip_start:
            adj_s = max(s - clip_start, 0)
            adj_e = min(e - clip_start, clip_end - clip_start)
            if adj_e > adj_s:
                words = text.split()
                if style == "karaoke" and len(words) > 1:
                    word_dur = (adj_e - adj_s) / len(words)
                    k_text = ""
                    for w in words:
                        cs = int(round(word_dur * 100))
                        k_text += f"{{\\k{cs}}}{w} "
                    dialog = (
                        f"Dialogue: 0,{_ass_time(adj_s)},{_ass_time(adj_e)},"
                        f"{style_name},,0,0,0,,{k_text.strip()}"
                    )
                else:
                    dialog = (
                        f"Dialogue: 0,{_ass_time(adj_s)},{_ass_time(adj_e)},"
                        f"{style_name},,0,0,0,,{text}"
                    )
                lines.append(dialog)

    return "\n".join(lines)


def write_subtitles(
    segments: list[_Segment] | None,
    clip_start: float,
    clip_end: float,
    output_path: str,
    style: str = "default",
) -> str:
    if style == "default":
        content = _make_srt_content(segments, clip_start, clip_end)
        suffix = ".srt"
    else:
        content = _make_ass(segments, clip_start, clip_end, style)
        suffix = ".ass"

    path = output_path + suffix
    with open(path, "w") as f:
        f.write(content)
    return path


def _make_srt_content(
    segments: list[_Segment] | None,
    clip_start: float,
    clip_end: float,
) -> str:
    entries: list[str] = []
    idx = 1
    for seg in (segments or []):
        s = seg.get("start", 0)
        e = seg.get("end", 0)
        text = seg.get("text", "").strip()
        if not text:
            continue
        if s < clip_end and e > clip_start:
            adj_s = max(s - clip_start, 0)
            adj_e = min(e - clip_start, clip_end - clip_start)
            if adj_e > adj_s:
                entries.append(
                    f"{idx}\n{_srt_time(adj_s)} --> {_srt_time(adj_e)}\n{text}\n"
                )
                idx += 1
    return "".join(entries)
