import binascii
import os
import time

import requests

from .base import AiMusicProvider, AiMusicResult


class MiniMaxAiMusicProvider(AiMusicProvider):
    def __init__(self, config):
        self.config = config or {}
        self.base_url = self.config.get("base_url", "https://api.minimaxi.com").rstrip("/")
        self.api_key = self.config.get("api_key", "")
        self.model = self.config.get("model", "music-2.6")
        self.lyrics_model_mode = self.config.get("lyrics_mode", "write_full_song")
        self.auto_generate_lyrics = bool(self.config.get("auto_generate_lyrics", True))
        self.lyrics_optimizer = bool(self.config.get("lyrics_optimizer", False))
        self.request_timeout = float(self.config.get("request_timeout", 300))
        self.sample_rate = int(self.config.get("sample_rate", 44100))
        self.bitrate = int(self.config.get("bitrate", 256000))
        self.audio_format = self.config.get("format", "mp3")

    def generate(
        self,
        *,
        title: str,
        prompt: str,
        lyrics: str,
        style: str,
        output_dir: str,
    ) -> AiMusicResult:
        if not self.api_key:
            raise RuntimeError("MiniMax API Key 未配置")

        os.makedirs(output_dir, exist_ok=True)
        generated_title = title or "未命名AI歌曲"
        generated_style = style or self.config.get("default_style", "Mandopop, Pop")
        generated_lyrics = lyrics or ""

        if not generated_lyrics and self.auto_generate_lyrics and not self.lyrics_optimizer:
            lyrics_result = self._generate_lyrics(prompt=prompt, title=generated_title)
            generated_title = lyrics_result.get("song_title") or generated_title
            generated_style = lyrics_result.get("style_tags") or generated_style
            generated_lyrics = lyrics_result.get("lyrics") or generated_lyrics

        music_data = self._generate_music(
            prompt=generated_style or prompt,
            lyrics=generated_lyrics,
            title=generated_title,
        )
        file_path = self._save_audio(music_data, output_dir, generated_title)

        return AiMusicResult(
            title=generated_title,
            file_path=file_path,
            file_ext=os.path.splitext(file_path)[1].lower() or f".{self.audio_format}",
            lyrics=generated_lyrics,
            style=generated_style,
            prompt=prompt,
            provider="minimax",
            provider_task_id=str(music_data.get("trace_id") or ""),
        )

    def _generate_lyrics(self, prompt, title):
        payload = {
            "mode": self.lyrics_model_mode,
            "prompt": prompt,
            "title": title,
        }
        data = self._post("/v1/lyrics_generation", payload)
        self._check_base_resp(data, "MiniMax歌词生成失败")
        return data

    def _generate_music(self, prompt, lyrics, title):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "lyrics": lyrics,
            "lyrics_optimizer": self.lyrics_optimizer and not lyrics,
            "output_format": "url",
            "audio_setting": {
                "sample_rate": self.sample_rate,
                "bitrate": self.bitrate,
                "format": self.audio_format,
            },
        }
        # title is not in the documented request schema, but keeping it out avoids
        # strict parameter validation failures.
        if not lyrics and not payload["lyrics_optimizer"]:
            raise RuntimeError("MiniMax音乐生成需要歌词，或开启 lyrics_optimizer")

        data = self._post("/v1/music_generation", payload)
        self._check_base_resp(data, "MiniMax音乐生成失败")
        music = data.get("data") or {}
        if music.get("status") not in (None, 2):
            raise RuntimeError(f"MiniMax音乐尚未生成完成，status={music.get('status')}")
        return data

    def _save_audio(self, music_data, output_dir, title):
        audio = (music_data.get("data") or {}).get("audio")
        if not audio:
            raise RuntimeError("MiniMax未返回音频数据")

        ext = f".{self.audio_format}"
        file_path = os.path.join(output_dir, f"{int(time.time())}_{self._safe_filename(title)}{ext}")
        if isinstance(audio, str) and audio.startswith(("http://", "https://")):
            response = requests.get(audio, timeout=self.request_timeout)
            response.raise_for_status()
            with open(file_path, "wb") as file:
                file.write(response.content)
            return file_path

        try:
            audio_bytes = binascii.unhexlify(audio)
        except (TypeError, binascii.Error) as exc:
            raise RuntimeError("MiniMax返回的音频既不是URL也不是hex数据") from exc

        with open(file_path, "wb") as file:
            file.write(audio_bytes)
        return file_path

    def _post(self, endpoint, payload):
        response = requests.post(
            f"{self.base_url}{endpoint}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            json={key: value for key, value in payload.items() if value not in (None, "")},
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _check_base_resp(data, prefix):
        base_resp = data.get("base_resp") or {}
        status_code = base_resp.get("status_code", 0)
        if status_code != 0:
            message = base_resp.get("status_msg") or "unknown error"
            raise RuntimeError(f"{prefix}: {status_code} {message}")

    @staticmethod
    def _safe_filename(value):
        return "".join(ch for ch in (value or "ai_music") if ch.isalnum() or ch in ("-", "_"))[:48] or "ai_music"
