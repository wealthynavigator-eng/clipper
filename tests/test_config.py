from config import Settings


def test_default_settings():
    s = Settings()
    assert s.llm_provider == "mistral"
    assert s.min_clips == 5
    assert s.max_clips == 10
    assert s.clip_min_duration == 45.0
    assert s.clip_max_duration == 75.0
    assert s.crop_aspect == "9:16"
    assert s.fade_duration == 0.5
    assert s.parallel_workers == 4
    assert s.thumbnail is True
    assert s.compile_reel is False


def test_crop_filter_default():
    s = Settings()
    assert s.crop_filter == "crop=w='min(iw,ih*9/16)':h=ih"


def test_loudnorm_filter_enabled():
    s = Settings(audio_normalize=True)
    assert s.loudnorm_filter == "loudnorm=I=-16:LRA=11:TP=-1.5"


def test_loudnorm_filter_disabled():
    s = Settings(audio_normalize=False)
    assert s.loudnorm_filter is None


def test_custom_settings():
    s = Settings(
        llm_provider="groq",
        llm_model="llama-3-70b",
        min_clips=3,
        max_clips=7,
        audio_normalize=False,
        face_tracking=True,
    )
    assert s.llm_provider == "groq"
    assert s.llm_model == "llama-3-70b"
    assert s.min_clips == 3
    assert s.max_clips == 7
    assert s.audio_normalize is False
    assert s.face_tracking is True


def test_settings_immutable_defaults():
    s1 = Settings()
    s2 = Settings()
    s1.min_clips = 99
    assert s2.min_clips == 5
