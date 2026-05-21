import math
import os
import time
import wave

from .base import AiMusicProvider, AiMusicResult


class MockAiMusicProvider(AiMusicProvider):
    """本地演示 Provider：生成短 WAV，便于没有外部 API 时验证流程。"""

    def __init__(self, config):
        self.duration_seconds = float(config.get("mock_duration_seconds", 8))
        self.sample_rate = int(config.get("mock_sample_rate", 24000))

    def generate(
        self,
        *,
        title: str,
        prompt: str,
        lyrics: str,
        style: str,
        output_dir: str,
    ) -> AiMusicResult:
        os.makedirs(output_dir, exist_ok=True)
        safe_title = _safe_filename(title or "ai_music")
        file_path = os.path.join(output_dir, f"{int(time.time())}_{safe_title}.wav")
        self._write_demo_wav(file_path)
        return AiMusicResult(
            title=title or "未命名AI歌曲",
            file_path=file_path,
            file_ext=".wav",
            lyrics=lyrics,
            style=style,
            prompt=prompt,
            provider="mock",
            provider_task_id="",
        )

    def _write_demo_wav(self, file_path):
        total_frames = int(self.sample_rate * self.duration_seconds)
        with wave.open(file_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            for index in range(total_frames):
                t = index / self.sample_rate
                envelope = min(1.0, index / (self.sample_rate * 0.4))
                envelope *= min(1.0, (total_frames - index) / (self.sample_rate * 0.4))
                value = int(12000 * envelope * math.sin(2 * math.pi * 440 * t))
                wav.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))


def _safe_filename(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_"))[:48] or "ai_music"
