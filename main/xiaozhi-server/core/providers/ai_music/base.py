from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class AiMusicResult:
    title: str
    file_path: str
    file_ext: str
    lyrics: str = ""
    style: str = ""
    prompt: str = ""
    provider: str = ""
    provider_task_id: str = ""


class AiMusicProvider:
    def generate(
        self,
        *,
        title: str,
        prompt: str,
        lyrics: str,
        style: str,
        output_dir: str,
    ) -> AiMusicResult:
        raise NotImplementedError


def build_ai_music_provider(config: Optional[Dict]) -> AiMusicProvider:
    config = config or {}
    provider = str(config.get("provider", "generic_http")).lower()
    if provider == "mock":
        from .mock import MockAiMusicProvider

        return MockAiMusicProvider(config)
    if provider == "minimax":
        from .minimax import MiniMaxAiMusicProvider

        return MiniMaxAiMusicProvider(config)

    from .generic_http import GenericHttpAiMusicProvider

    return GenericHttpAiMusicProvider(config)
