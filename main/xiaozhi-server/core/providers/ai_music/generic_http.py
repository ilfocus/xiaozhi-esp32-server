import os
import time
from urllib.parse import urljoin

import requests

from .base import AiMusicProvider, AiMusicResult
from .mock import MockAiMusicProvider


class GenericHttpAiMusicProvider(AiMusicProvider):
    def __init__(self, config):
        self.config = config or {}
        self.base_url = self.config.get("base_url", "")
        self.api_key = self.config.get("api_key", "")
        self.generate_endpoint = self.config.get("generate_endpoint", "")
        self.status_endpoint = self.config.get("status_endpoint", "")
        self.task_id_field = self.config.get("task_id_field", "id")
        self.audio_url_field = self.config.get("audio_url_field", "audio_url")
        self.status_field = self.config.get("status_field", "status")
        self.success_values = set(self.config.get("success_values", ["succeeded", "success", "completed"]))
        self.failed_values = set(self.config.get("failed_values", ["failed", "error", "canceled"]))
        self.poll_interval = float(self.config.get("poll_interval", 5))
        self.timeout_seconds = float(self.config.get("timeout_seconds", 180))
        self.request_timeout = float(self.config.get("request_timeout", 30))
        self.status_method = str(self.config.get("status_method", "GET")).upper()
        self.allow_mock = bool(self.config.get("allow_mock", True))

    def generate(
        self,
        *,
        title: str,
        prompt: str,
        lyrics: str,
        style: str,
        output_dir: str,
    ) -> AiMusicResult:
        if not self.base_url or not self.generate_endpoint:
            if self.allow_mock:
                return MockAiMusicProvider({"mock_duration_seconds": 8}).generate(
                    title=title,
                    prompt=prompt,
                    lyrics=lyrics,
                    style=style,
                    output_dir=output_dir,
                )
            raise RuntimeError("AI音乐服务未配置 base_url/generate_endpoint")

        os.makedirs(output_dir, exist_ok=True)
        payload = self._build_generate_payload(title, prompt, lyrics, style)
        response = requests.post(
            self._url(self.generate_endpoint),
            json=payload,
            headers=self._headers(),
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        data = response.json()

        audio_url = self._get_path(data, self.audio_url_field)
        task_id = self._get_path(data, self.task_id_field) or ""
        if not audio_url:
            data = self._poll_result(task_id)
            audio_url = self._get_path(data, self.audio_url_field)

        if not audio_url:
            raise RuntimeError("AI音乐服务未返回音频地址")

        file_path = self._download_audio(audio_url, output_dir, title)
        return AiMusicResult(
            title=title or self._get_path(data, "title") or "未命名AI歌曲",
            file_path=file_path,
            file_ext=os.path.splitext(file_path)[1].lower() or ".mp3",
            lyrics=lyrics,
            style=style,
            prompt=prompt,
            provider=str(self.config.get("provider", "generic_http")),
            provider_task_id=str(task_id),
        )

    def _build_generate_payload(self, title, prompt, lyrics, style):
        payload = dict(self.config.get("request_extra", {}))
        payload.update(
            {
                self.config.get("title_field", "title"): title,
                self.config.get("prompt_field", "prompt"): prompt,
                self.config.get("lyrics_field", "lyrics"): lyrics,
                self.config.get("style_field", "style"): style,
            }
        )
        return {key: value for key, value in payload.items() if value not in (None, "")}

    def _poll_result(self, task_id):
        if not task_id or not self.status_endpoint:
            return {}
        deadline = time.time() + self.timeout_seconds
        endpoint = self.status_endpoint.format(task_id=task_id)
        while time.time() < deadline:
            if self.status_method == "POST":
                response = requests.post(
                    self._url(endpoint),
                    json={self.config.get("task_id_request_field", "id"): task_id},
                    headers=self._headers(),
                    timeout=self.request_timeout,
                )
            else:
                response = requests.get(
                    self._url(endpoint),
                    headers=self._headers(),
                    timeout=self.request_timeout,
                )
            response.raise_for_status()
            data = response.json()
            status = str(self._get_path(data, self.status_field) or "").lower()
            if status in self.success_values or self._get_path(data, self.audio_url_field):
                return data
            if status in self.failed_values:
                raise RuntimeError(f"AI音乐生成失败: {status}")
            time.sleep(self.poll_interval)
        raise TimeoutError("AI音乐生成超时")

    def _download_audio(self, audio_url, output_dir, title):
        response = requests.get(audio_url, headers=self._headers(include_auth=False), timeout=self.request_timeout)
        response.raise_for_status()
        ext = self._guess_ext(audio_url, response.headers.get("content-type", ""))
        file_path = os.path.join(output_dir, f"{int(time.time())}_{self._safe_filename(title)}{ext}")
        with open(file_path, "wb") as audio_file:
            audio_file.write(response.content)
        return file_path

    def _headers(self, include_auth=True):
        headers = dict(self.config.get("headers", {}))
        if include_auth and self.api_key:
            header_name = self.config.get("api_key_header", "Authorization")
            prefix = self.config.get("api_key_prefix", "Bearer ")
            headers[header_name] = f"{prefix}{self.api_key}"
        return headers

    def _url(self, endpoint):
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return urljoin(self.base_url.rstrip("/") + "/", endpoint.lstrip("/"))

    @staticmethod
    def _get_path(data, path):
        current = data
        for part in str(path or "").split("."):
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None
        return current

    @staticmethod
    def _guess_ext(audio_url, content_type):
        lowered = audio_url.lower().split("?")[0]
        for ext in (".mp3", ".wav", ".m4a", ".ogg"):
            if lowered.endswith(ext):
                return ext
        if "wav" in content_type:
            return ".wav"
        if "mpeg" in content_type or "mp3" in content_type:
            return ".mp3"
        return ".mp3"

    @staticmethod
    def _safe_filename(value):
        return "".join(ch for ch in (value or "ai_music") if ch.isalnum() or ch in ("-", "_"))[:48] or "ai_music"
