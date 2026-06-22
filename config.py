from dataclasses import dataclass
from typing import Literal

LLMProvider = Literal["mistral", "groq", "openai", "ollama"]


@dataclass
class Settings:
    llm_provider: LLMProvider = "mistral"
    llm_model: str = "mistral-large-latest"
    llm_timeout_ms: int = 120000

    min_clips: int = 5
    max_clips: int = 10
    clip_min_duration: float = 45.0
    clip_max_duration: float = 75.0

    crop_aspect: str = "9:16"
    fade_duration: float = 0.5
    subtitle_style: str = "default"
    hook_overlay: bool = True
    hook_duration: float = 3.0

    audio_normalize: bool = True
    face_tracking: bool = False
    parallel_workers: int = 4

    output_dir: str = "output"
    downloads_dir: str = "downloads"

    bgm_path: str = ""
    bgm_volume: float = 0.15

    thumbnail: bool = True

    watermark_path: str = ""
    watermark_position: str = "bottom-right"
    watermark_scale: float = 0.15
    watermark_opacity: float = 0.8

    transition_type: str = "cut"
    transition_duration: float = 0.3
    compile_reel: bool = False

    @property
    def crop_filter(self) -> str:
        return "crop=w='min(iw,ih*9/16)':h=ih"

    @property
    def loudnorm_filter(self) -> str | None:
        if self.audio_normalize:
            return "loudnorm=I=-16:LRA=11:TP=-1.5"
        return None


settings = Settings()
