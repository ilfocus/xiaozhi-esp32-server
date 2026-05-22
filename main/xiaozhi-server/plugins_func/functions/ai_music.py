import asyncio
import os
import uuid
from typing import TYPE_CHECKING

from core.handle.sendAudioHandle import send_tts_message
from core.providers.ai_music import build_ai_music_provider
from core.providers.tts.dto.dto import ContentType, SentenceType, TTSMessageDTO
from core.utils.dialogue import Message
from plugins_func.register import Action, ActionResponse, ToolType, register_function

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__


ai_music_function_desc = {
    "type": "function",
    "function": {
        "name": "ai_music",
        "description": "当用户想创作、生成、制作一首AI歌曲或音乐时调用。用于根据主题、风格、歌词需求生成新歌并试听。",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "用户对歌曲的完整创作需求，例如主题、情绪、场景、曲风、人声等。",
                },
                "title": {
                    "type": "string",
                    "description": "歌曲标题。用户未指定时根据需求生成一个简短标题。",
                },
                "lyrics": {
                    "type": "string",
                    "description": "用户指定的歌词。未指定可为空。",
                },
                "style": {
                    "type": "string",
                    "description": "曲风描述，例如国风、流行、摇滚、儿歌、电子、女声等。",
                },
            },
            "required": ["prompt"],
        },
    },
}

save_ai_music_function_desc = {
    "type": "function",
    "function": {
        "name": "save_ai_music",
        "description": "当用户对刚刚生成的AI歌曲表示满意、确认保存、收藏时调用。",
        "parameters": {"type": "object", "properties": {}},
    },
}

redo_ai_music_function_desc = {
    "type": "function",
    "function": {
        "name": "redo_ai_music",
        "description": "当用户对刚刚生成的AI歌曲不满意、要求重做、换一种风格或修改后重新生成时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "revision": {
                    "type": "string",
                    "description": "用户提出的修改意见，例如换成女声、节奏更快、歌词更温柔等。",
                }
            },
        },
    },
}

play_my_music_function_desc = {
    "type": "function",
    "function": {
        "name": "play_my_music",
        "description": "当用户想播放自己之前保存/创作的AI歌曲时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "song_name": {
                    "type": "string",
                    "description": "要播放的歌曲名关键词。用户未指定时传空字符串。",
                }
            },
        },
    },
}


@register_function("ai_music", ai_music_function_desc, ToolType.SYSTEM_CTL)
def ai_music(conn: "ConnectionHandler", prompt: str, title: str = "", lyrics: str = "", style: str = ""):
    if not _submit_task(conn, _handle_ai_music(conn, prompt, title, lyrics, style)):
        return ActionResponse(action=Action.RESPONSE, response="现在音乐创作服务有点忙，稍后再试")
    return ActionResponse(action=Action.RECORD, result="AI音乐创作任务已提交", response="正在为您创作AI歌曲")


@register_function("save_ai_music", save_ai_music_function_desc, ToolType.SYSTEM_CTL)
def save_ai_music(conn: "ConnectionHandler"):
    pending = getattr(conn, "pending_ai_music", None)
    if not pending:
        return ActionResponse(action=Action.RESPONSE, response="还没有可以保存的AI歌曲，先告诉我你想创作什么歌")
    if not _submit_task(conn, _handle_save_ai_music(conn, pending)):
        return ActionResponse(action=Action.RESPONSE, response="现在保存服务有点忙，稍后再试")
    return ActionResponse(action=Action.RECORD, result="AI音乐保存任务已提交", response="正在保存您的AI歌曲")


@register_function("redo_ai_music", redo_ai_music_function_desc, ToolType.SYSTEM_CTL)
def redo_ai_music(conn: "ConnectionHandler", revision: str = ""):
    pending = getattr(conn, "pending_ai_music", None)
    if not pending:
        return ActionResponse(action=Action.RESPONSE, response="还没有可以重做的AI歌曲，先告诉我你想创作什么歌")
    prompt = pending.get("prompt", "")
    if revision:
        prompt = f"{prompt}\n修改要求：{revision}"
    if not _submit_task(
        conn,
        _handle_ai_music(
            conn,
            prompt=prompt,
            title=pending.get("title", ""),
            lyrics=pending.get("lyrics", ""),
            style=pending.get("style", ""),
        ),
    ):
        return ActionResponse(action=Action.RESPONSE, response="现在音乐创作服务有点忙，稍后再试")
    return ActionResponse(action=Action.RECORD, result="AI音乐重做任务已提交", response="正在重新制作AI歌曲")


@register_function("play_my_music", play_my_music_function_desc, ToolType.SYSTEM_CTL)
def play_my_music(conn: "ConnectionHandler", song_name: str = ""):
    if not _submit_task(conn, _handle_play_my_music(conn, song_name)):
        return ActionResponse(action=Action.RESPONSE, response="现在查询歌曲有点忙，稍后再试")
    return ActionResponse(action=Action.RECORD, result="AI音乐点播任务已提交", response="正在查找您的AI歌曲")


async def _handle_ai_music(conn: "ConnectionHandler", prompt: str, title: str, lyrics: str, style: str):
    try:
        config = _resolve_ai_music_config(conn)
        title = title or _guess_title(prompt)
        await _speak(conn, f"收到，我开始制作《{title}》，生成好以后会直接播放试听。")
        await asyncio.sleep(float(config.get("initial_notice_delay", 1.5)))
        output_dir = _build_output_dir(conn, config)
        provider = build_ai_music_provider(config)
        result = await asyncio.to_thread(
            provider.generate,
            title=title,
            prompt=prompt,
            lyrics=lyrics or "",
            style=style or config.get("default_style", ""),
            output_dir=output_dir,
        )
        conn.pending_ai_music = {
            "title": result.title,
            "lyrics": result.lyrics,
            "style": result.style,
            "prompt": result.prompt,
            "file_path": result.file_path,
            "file_ext": result.file_ext,
            "provider": result.provider,
            "provider_task_id": result.provider_task_id,
        }
        await _play_file(
            conn,
            result.file_path,
            f"制作完成，请试听《{result.title}》。满意的话可以说保存，不满意可以说重新做。",
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"AI音乐生成失败: {e}")
        await _speak(conn, "AI歌曲生成失败了，可能是音乐服务暂时不可用，请稍后再试。")


async def _handle_save_ai_music(conn: "ConnectionHandler", pending):
    try:
        from config.manage_api_client import save_ai_music as save_ai_music_meta

        if not conn.config.get("read_config_from_api", False):
            await _speak(conn, "当前没有连接智控台账号系统，无法按账号保存歌曲。")
            return
        result = await save_ai_music_meta(
            mac_address=conn.device_id,
            title=pending.get("title", "未命名AI歌曲"),
            lyrics=pending.get("lyrics", ""),
            style=pending.get("style", ""),
            prompt=pending.get("prompt", ""),
            file_path=pending.get("file_path", ""),
            file_ext=pending.get("file_ext", ""),
            provider=pending.get("provider", ""),
            provider_task_id=pending.get("provider_task_id", ""),
        )
        if not result:
            await _speak(conn, "保存失败了，请确认设备已经绑定账号。")
            return
        conn.pending_ai_music = None
        await _speak(conn, f"已保存《{result.get('title', pending.get('title', '这首歌'))}》，下次可以让我播放你创作的歌。")
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"AI音乐保存失败: {e}")
        await _speak(conn, "保存AI歌曲失败了，请稍后再试。")


async def _handle_play_my_music(conn: "ConnectionHandler", song_name: str):
    try:
        from config.manage_api_client import list_ai_music

        if not conn.config.get("read_config_from_api", False):
            await _speak(conn, "当前没有连接智控台账号系统，无法查询账号下保存的歌曲。")
            return
        songs = await list_ai_music(conn.device_id, keyword=song_name or "", limit=10)
        if not songs:
            await _speak(conn, "没有找到你保存的AI歌曲。")
            return
        song = songs[0]
        file_path = song.get("filePath") or song.get("file_path")
        title = song.get("title") or "未命名AI歌曲"
        if not file_path or not os.path.exists(file_path):
            await _speak(conn, f"找到了《{title}》，但服务器上的音频文件不见了。")
            return
        await _play_file(conn, file_path, f"为您播放保存的AI歌曲《{title}》。")
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"播放用户AI音乐失败: {e}")
        await _speak(conn, "播放你保存的AI歌曲失败了，请稍后再试。")


def _resolve_ai_music_config(conn: "ConnectionHandler"):
    plugin_config = dict(conn.config.get("plugins", {}).get("ai_music", {}) or {})
    model_id = plugin_config.get("ai_music_model_id")
    model_configs = conn.config.get("AI_MUSIC", {}) or {}
    if model_id and isinstance(model_configs, dict) and model_id in model_configs:
        resolved = dict(model_configs.get(model_id) or {})
        resolved.update(plugin_config)
        return resolved
    return plugin_config


def _submit_task(conn: "ConnectionHandler", coro):
    if not conn.loop or not conn.loop.is_running():
        return False
    conn.loop.create_task(coro)
    return True


async def _speak(conn: "ConnectionHandler", text: str):
    await _wait_for_tts_queue_idle(conn)
    sentence_id = uuid.uuid4().hex
    conn.sentence_id = sentence_id
    await send_tts_message(conn, "start", None)
    conn.client_is_speaking = True
    conn.tts.store_tts_text(sentence_id, text)
    conn.dialogue.put(Message(role="assistant", content=text))
    conn.tts.tts_text_queue.put(TTSMessageDTO(sentence_id=sentence_id, sentence_type=SentenceType.FIRST, content_type=ContentType.ACTION))
    conn.tts.tts_text_queue.put(TTSMessageDTO(sentence_id=sentence_id, sentence_type=SentenceType.MIDDLE, content_type=ContentType.TEXT, content_detail=text))
    conn.tts.tts_text_queue.put(TTSMessageDTO(sentence_id=sentence_id, sentence_type=SentenceType.LAST, content_type=ContentType.ACTION))


async def _play_file(conn: "ConnectionHandler", file_path: str, text: str):
    await _wait_for_tts_queue_idle(conn)
    sentence_id = uuid.uuid4().hex
    conn.sentence_id = sentence_id
    await send_tts_message(conn, "start", None)
    conn.client_is_speaking = True
    conn.tts.store_tts_text(sentence_id, text)
    conn.dialogue.put(Message(role="assistant", content=text))
    conn.tts.tts_text_queue.put(TTSMessageDTO(sentence_id=sentence_id, sentence_type=SentenceType.FIRST, content_type=ContentType.ACTION))
    conn.tts.tts_text_queue.put(TTSMessageDTO(sentence_id=sentence_id, sentence_type=SentenceType.MIDDLE, content_type=ContentType.TEXT, content_detail=text))
    conn.tts.tts_text_queue.put(TTSMessageDTO(sentence_id=sentence_id, sentence_type=SentenceType.MIDDLE, content_type=ContentType.FILE, content_file=file_path))
    conn.tts.tts_text_queue.put(TTSMessageDTO(sentence_id=sentence_id, sentence_type=SentenceType.LAST, content_type=ContentType.ACTION))


async def _wait_for_tts_queue_idle(conn: "ConnectionHandler", timeout: float = 5.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if conn.tts.tts_text_queue.empty():
            return
        await asyncio.sleep(0.1)


def _build_output_dir(conn: "ConnectionHandler", config):
    output_dir = config.get("output_dir", "data/generated_music")
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(_get_project_dir(), output_dir)
    owner = _safe_path(conn.device_id or "unknown")
    return os.path.join(output_dir, owner)


def _get_project_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _guess_title(prompt: str) -> str:
    words = (prompt or "AI歌曲").replace("\n", " ").strip()
    return words[:12] or "AI歌曲"


def _safe_path(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)[:80] or "unknown"
