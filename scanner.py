import os
from typing import Any

from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector

SceneList = list[tuple[float, float]]
ClipList = list[dict[str, Any]]


def detect_scenes(video_path: str, threshold: float = 27.0) -> SceneList:
    if not os.path.exists(video_path):
        return []

    video = open_video(video_path)
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video)

    return [(s[0].get_seconds(), s[1].get_seconds()) for s in manager.get_scene_list()]


def snap_to_scene(value: float, scenes: SceneList, snap: str = "nearest") -> float:
    if not scenes:
        return value

    if snap == "start":
        before = [s[1] for s in scenes if s[1] <= value]
        return before[-1] if before else scenes[0][0]

    if snap == "end":
        after = [s[0] for s in scenes if s[0] >= value]
        return after[0] if after else scenes[-1][1]

    nearest = min(scenes, key=lambda s: min(abs(value - s[0]), abs(value - s[1])))
    if abs(value - nearest[0]) < abs(value - nearest[1]):
        return nearest[0]
    return nearest[1]


def refine_clips(clips: ClipList, scenes: SceneList) -> ClipList:
    if not scenes:
        return clips

    refined: ClipList = []
    for clip in clips:
        c = dict(clip)
        c["start"] = snap_to_scene(c.get("start", 0), scenes, "start")
        c["end"] = snap_to_scene(c.get("end", 0), scenes, "end")
        if c["end"] > c["start"]:
            refined.append(c)
    return refined
