from scanner import refine_clips, snap_to_scene

_SCENES = [
    (0.0, 10.0),
    (10.0, 25.0),
    (25.0, 40.0),
    (40.0, 60.0),
]


class TestSnapToScene:
    def test_empty_scenes_returns_value(self):
        assert snap_to_scene(5.0, []) == 5.0

    def test_snap_nearest_start(self):
        assert snap_to_scene(3.0, _SCENES, "nearest") == 0.0

    def test_snap_nearest_end(self):
        assert snap_to_scene(8.0, _SCENES, "nearest") == 10.0

    def test_snap_start_before_first(self):
        assert snap_to_scene(0.0, _SCENES, "start") == 0.0

    def test_snap_start_picks_last_scene_end_before_value(self):
        assert snap_to_scene(15.0, _SCENES, "start") == 10.0

    def test_snap_start_before_any_scene_end_returns_first_start(self):
        assert snap_to_scene(7.0, _SCENES, "start") == 0.0

    def test_snap_end_picks_first_scene_start_after_value(self):
        assert snap_to_scene(15.0, _SCENES, "end") == 25.0

    def test_snap_end_after_last_returns_last_scene_end(self):
        assert snap_to_scene(50.0, _SCENES, "end") == 60.0

    def test_snap_start_picks_last_before(self):
        scenes = [(0, 5), (5, 10), (10, 15)]
        assert snap_to_scene(12.0, scenes, "start") == 10.0

    def test_snap_end_picks_first_after(self):
        scenes = [(0, 5), (5, 10), (10, 15)]
        assert snap_to_scene(7.0, scenes, "end") == 10.0

    def test_snap_unknown_mode_defaults_to_nearest(self):
        assert snap_to_scene(3.0, _SCENES, "invalid") in (0.0, 10.0)


class TestRefineClips:
    def test_empty_scenes_returns_clips_unchanged(self):
        clips = [{"start": 5.0, "end": 15.0}]
        assert refine_clips(clips, []) == clips

    def test_empty_clips_returns_empty(self):
        assert refine_clips([], _SCENES) == []

    def test_snaps_start_to_first_scene_when_before_any_cut(self):
        clips = [{"start": 7.0, "end": 30.0}]
        refined = refine_clips(clips, _SCENES)
        assert len(refined) == 1
        assert refined[0]["start"] == 0.0
        assert refined[0]["end"] == 40.0

    def test_preserves_extra_keys(self):
        clips = [{"start": 7.0, "end": 30.0, "hook_text": "test hook"}]
        refined = refine_clips(clips, _SCENES)
        assert refined[0]["hook_text"] == "test hook"

    def test_multiple_clips(self):
        clips = [
            {"start": 5.0, "end": 15.0},
            {"start": 20.0, "end": 35.0},
            {"start": 42.0, "end": 55.0},
        ]
        refined = refine_clips(clips, _SCENES)
        assert len(refined) == 3
        assert refined[0]["start"] == 0.0
        assert refined[0]["end"] == 25.0
        assert refined[1]["start"] == 10.0
        assert refined[1]["end"] == 40.0
        assert refined[2]["start"] == 40.0
        assert refined[2]["end"] == 60.0
