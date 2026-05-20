# 项目架构与功能总览

本文档用于快速理解 `xiaozhi-esp32-server` 的整体架构、核心流程、主要功能和扩展入口。它面向后续维护者：读完后应能知道每个子项目负责什么、ESP32 设备如何接入、一次语音对话如何被处理，以及应该从哪里修改配置、接入模型或扩展工具。

## 1. 项目定位

`xiaozhi-esp32-server` 是 `xiaozhi-esp32` 固件的后端服务集合。它为 ESP32 设备提供 OTA 配置下发、WebSocket/MQTT+UDP 接入、流式语音交互、ASR/LLM/TTS 编排、视觉分析、设备控制、声纹识别、知识库、工具调用和管理控制台。

项目不是单一服务，而是一组协作模块：

- `xiaozhi-server`：Python 实时语音服务，是设备接入和 AI 编排核心。
- `manager-api`：Java Spring Boot 管理后端，负责用户、设备、智能体、模型、知识库、OTA 和系统参数。
- `manager-web`：Vue 2 Web 智控台，用于浏览器管理。
- `manager-mobile`：uni-app + Vue 3 移动端智控台。
- `digital-human`：浏览器音频交互/数字人测试模块。
- MySQL、Redis：全模块部署时用于持久化和缓存。
- 可选 MQTT 网关：让设备以 MQTT + UDP 协议接入，再转发到 Python WebSocket 服务。

## 2. 技术栈

- 实时服务：Python 3.10、asyncio、websockets、aiohttp、httpx、PyYAML。
- 音频：Opus、FFmpeg、libopus、本地/云端 ASR、流式/非流式 TTS。
- AI Provider：ASR、LLM、VLLM、TTS、VAD、Intent、Memory 都采用可配置 Provider 模式。
- 管理后端：Java 21、Spring Boot 3.4、Spring MVC、MyBatis-Plus、Shiro、Redis、Liquibase、Knife4j。
- Web 前端：Vue 2、Vue Router、Vuex、Element UI、vue-i18n、opus-recorder/opus-decoder。
- 移动端：uni-app、Vue 3、Vite、Pinia、alova、wot-design-uni。
- 部署：Docker Compose、源码部署、可选一键脚本。

## 3. 目录结构

```text
.
├── README.md                         # 项目介绍、功能清单和部署入口
├── docker-setup.sh                   # 全模块 Docker 一键安装脚本
├── Dockerfile-server*                # Python xiaozhi-server 镜像构建
├── Dockerfile-web                    # manager-api + manager-web 镜像构建
├── docs/                             # 部署、FAQ、MQTT、MCP、RAGFlow 等文档
└── main/
    ├── xiaozhi-server/               # Python 实时语音服务
    │   ├── app.py                    # Python 服务主入口
    │   ├── config.yaml               # 默认配置
    │   ├── config_from_api.yaml      # 从 manager-api 读取配置的模板
    │   ├── docker-compose.yml        # 只运行 Python Server
    │   ├── docker-compose_all.yml    # 全模块 Docker 编排
    │   ├── core/                     # WebSocket、HTTP、连接处理、Provider、工具系统
    │   ├── config/                   # 配置加载、日志、manager-api 客户端
    │   ├── plugins_func/             # 服务端插件函数
    │   ├── models/                   # 本地 ASR/VAD 等模型目录
    │   └── performance_tester*.py    # ASR/LLM/TTS/VLLM 性能测试
    ├── manager-api/                  # Java Spring Boot 管理后端
    ├── manager-web/                  # Vue 2 Web 智控台
    ├── manager-mobile/               # uni-app 移动智控台
    └── digital-human/                # 音频交互/数字人测试页面
```

第一次阅读建议从 `main/xiaozhi-server/app.py`、`main/xiaozhi-server/core/connection.py`、`main/xiaozhi-server/core/handle/`、`main/manager-api/src/main/java/xiaozhi/modules/` 和 `main/manager-web/src/views/` 开始。

## 4. 总体架构

### 4.1 单 Server 模式

单 Server 模式只运行 `xiaozhi-server`，配置来自 `main/xiaozhi-server/config.yaml` 和 `data/.config.yaml`。设备的 OTA 地址指向 Python HTTP 服务，语音会话连接 Python WebSocket 服务。

```text
ESP32
  ├─ HTTP /xiaozhi/ota/        -> xiaozhi-server SimpleHttpServer
  ├─ WebSocket /xiaozhi/v1/    -> xiaozhi-server WebSocketServer
  └─ MCP Vision HTTP           -> xiaozhi-server VisionHandler

xiaozhi-server
  ├─ 本地配置 data/.config.yaml
  ├─ Provider: VAD / ASR / LLM / TTS / VLLM / Intent / Memory
  └─ plugins_func + MCP + IoT 工具
```

这种模式轻量，适合个人调试或低配置部署；缺点是没有 Web 智控台和数据库持久化管理。

### 4.2 全模块模式

全模块模式运行 `xiaozhi-server`、`manager-api`、`manager-web`、MySQL 和 Redis。Web 智控台保存系统配置和智能体配置，Python 服务启动时或配置更新时从 `manager-api` 拉取配置。

```text
ESP32
  ├─ OTA:       manager-api /xiaozhi/ota/
  └─ WebSocket: xiaozhi-server /xiaozhi/v1/

manager-web / manager-mobile
  └─ REST API -> manager-api

xiaozhi-server
  ├─ POST /config/server-base       -> manager-api
  ├─ POST /config/agent-models      -> manager-api
  ├─ POST /config/correct-words     -> manager-api
  └─ POST /agent/chat-history/report -> manager-api

manager-api
  ├─ MySQL: 用户、设备、智能体、模型、知识库、OTA、聊天记录
  └─ Redis: 缓存、设备绑定验证码、临时状态
```

这种模式功能最完整，适合需要多用户、多智能体、设备管理、知识库、声纹和可视化配置的场景。

## 5. 核心模块

### 5.1 xiaozhi-server

`xiaozhi-server` 是设备实时连接和 AI 处理核心。主入口在 `main/xiaozhi-server/app.py`，启动时会：

1. 检查 FFmpeg。
2. 加载配置：先读 `config.yaml`，再用 `data/.config.yaml` 覆盖；如果配置了 `manager-api.url` 和 `secret`，则从 Java 后台拉取配置。
3. 生成或读取 `server.auth_key`，用于 WebSocket、OTA 和视觉接口认证。
4. 启动全局 GC 管理器。
5. 启动 `WebSocketServer`，默认监听 `8000`。
6. 启动 `SimpleHttpServer`，默认监听 `8003`，提供单 Server 模式 OTA 和视觉分析接口。

`WebSocketServer` 在 `main/xiaozhi-server/core/websocket_server.py` 中实现。它负责监听设备连接、校验认证、初始化共用 Provider，并为每个连接创建独立的 `ConnectionHandler`。

`ConnectionHandler` 在 `main/xiaozhi-server/core/connection.py` 中实现，是每台设备每次连接的会话状态中心。它维护：

- 设备信息、客户端 IP、会话 ID、绑定状态。
- 音频格式、采样率、VAD 缓冲、ASR 队列。
- 当前对话历史、说话人、TTS 队列、客户端播放状态。
- 工具处理器、IoT/MCP 能力、声纹识别实例。
- 超时关闭、打断、上报和记忆保存逻辑。

### 5.2 manager-api

`manager-api` 是 Java Spring Boot 管理后端，入口为 `main/manager-api/src/main/java/xiaozhi/AdminApplication.java`，默认端口 `8002`，上下文路径 `/xiaozhi`。

主要模块在 `main/manager-api/src/main/java/xiaozhi/modules/`：

- `security`：登录、验证码、Token、Shiro 鉴权。
- `sys`：系统参数、字典、用户、服务端管理和配置刷新通知。
- `config`：给 Python 服务提供 `/config/server-base`、`/config/agent-models`、`/config/correct-words`。
- `device`：设备注册、绑定、OTA、设备工具列表、工具调用。
- `agent`：智能体、模板、MCP 接入点、声纹、聊天记录。
- `model`：模型供应商和模型配置。
- `knowledge`：知识库、文件、RAGFlow 适配。
- `correctword`：识别文本替换词。
- `timbre`：音色管理。
- `voiceclone`：声音复刻和资源管理。

数据库迁移脚本位于 `main/manager-api/src/main/resources/db/changelog/`，使用 Liquibase 管理版本。

### 5.3 manager-web

`manager-web` 是 Vue 2 Web 智控台，入口在 `main/manager-web/src/main.js`，页面位于 `main/manager-web/src/views/`。

它提供：

- 登录、注册、找回密码。
- 首页和系统参数管理。
- 设备管理、OTA 管理、设备工具调用。
- 智能体管理、角色配置、模板配置、聊天记录。
- 模型供应商和模型配置。
- 知识库管理和文件上传。
- 声纹、音色、声音复刻、替换词、字典和用户管理。
- 多语言界面：简体中文、繁体中文、英文、德文、越南语、葡语等。

前端通过 `main/manager-web/src/apis/` 调用 `manager-api`。

### 5.4 manager-mobile

`manager-mobile` 是 uni-app + Vue 3 移动管理端。它面向 H5、App 和小程序，使用 Pinia 管理状态，使用 alova 访问后端接口。功能定位与 Web 智控台类似，但偏移动端使用。

### 5.5 digital-human

`digital-human` 是本地浏览器交互测试模块，用于验证音频播放、录音、WebSocket 交互、唤醒词和数字人链路。它适合在没有真实 ESP32 设备时测试 Python 服务的 WebSocket 和音频处理。

## 6. 设备接入与服务器交互

### 6.1 OTA 配置下发

ESP32 固件启动后会先请求 OTA 地址。这个项目有两种 OTA 来源：

- 单 Server 模式：Python `SimpleHttpServer` 提供 `/xiaozhi/ota/`。
- 全模块模式：Java `manager-api` 提供 `/xiaozhi/ota/`。

OTA 响应会告诉设备后续连接方式：

- 如果未配置 MQTT 网关，返回 `websocket.url` 和可选 `websocket.token`。
- 如果配置了 MQTT 网关，返回 `mqtt.endpoint`、`client_id`、`username`、`password`、`publish_topic`、`subscribe_topic`。
- 同时返回 `server_time`，可选返回 `activation` 和 `firmware`。

单 Server 模式下，Python 的 `OTAHandler` 会根据 `server.websocket` 自动生成或下发 WebSocket 地址，并可以从 `data/bin` 中按 `{model}_{version}.bin` 查找新版固件。

全模块模式下，Java 的 `OTAController` 会检查设备激活状态，未绑定设备会返回激活码，已绑定设备会返回对应服务配置。

### 6.2 WebSocket 会话

设备拿到 WebSocket 地址后连接 `ws://.../xiaozhi/v1/`。服务端要求请求头或查询参数中包含 `device-id`，可选包含 `client-id` 和 `authorization`。

连接建立后：

1. `WebSocketServer` 做认证和白名单校验。
2. 为连接创建 `ConnectionHandler`。
3. 设备发送 `hello`，包含音频格式、采样率、帧时长和能力。
4. 服务端 `helloHandle` 记录客户端能力，如果设备支持 MCP，则初始化设备 MCP 客户端。
5. 服务端返回 `welcome_msg`，其中包含 `session_id` 和服务端音频参数。

文本消息由 `TextMessageProcessor` 分发，支持的类型包括：

- `hello`：握手和能力交换。
- `listen`：开始/停止监听、唤醒词触发。
- `abort`：用户打断，服务端停止 TTS 并清理队列。
- `iot`：旧版 IoT 设备能力和状态。
- `mcp`：设备端 MCP 消息。
- `server`：管理后台触发的服务端控制消息。
- `ping`：心跳。

二进制消息是 Opus 音频。普通 WebSocket 下直接是 Opus 包；如果来自 MQTT 网关，则带 16 字节网关头，`ConnectionHandler` 会解析后再交给音频链路。

### 6.3 一次语音对话流程

一次完整对话大致如下：

1. 设备通过 WebSocket 建立会话并完成 `hello`。
2. 后台初始化该设备的私有配置、ASR/TTS、声纹、工具处理器、提示词和智能体参数。
3. 设备发送 `listen start` 或唤醒词事件。
4. 设备持续发送 Opus 音频二进制包。
5. `receiveAudioHandle` 调用 VAD 判断是否有人声，并把音频送入 ASR。
6. ASR 识别完成后调用 `startToChat()`。
7. `startToChat()` 做绑定检查、输出额度检查、打断处理、意图识别和唤醒词快捷回复。
8. 如果意图已被工具处理，则执行工具并回复；否则进入常规 LLM 对话。
9. LLM 输出文本后交给 TTS。
10. `sendAudioHandle` 发送 `tts sentence_start`、Opus 音频包和 `tts stop`。
11. 会话结束或长时间无语音后，服务端保存记忆、生成标题并关闭连接。

### 6.4 MQTT + UDP 接入

项目本身不直接内置 MQTT broker，而是通过外部 `xiaozhi-mqtt-gateway` 适配。设备连接 MQTT/UDP 网关，网关再连接 Python WebSocket 地址，并在 URL 后追加 `?from=mqtt_gateway`。

这种模式下：

- OTA 返回 MQTT 连接参数。
- 设备通过 MQTT 发控制消息，通过 UDP 发加密 Opus 音频。
- MQTT 网关把这些内容转成 WebSocket 消息送到 `xiaozhi-server`。
- Python 连接上会标记 `conn_from_mqtt_gateway`，发送下行音频时加 16 字节头，供网关再转回 UDP。

如果没有公网 MQTT/UDP 需求，优先使用 WebSocket，部署和排查更简单。

## 7. AI 处理和 Provider 体系

项目用配置驱动选择具体 Provider，核心配置是 `selected_module`：

```yaml
selected_module:
  VAD: SileroVAD
  ASR: FunASR
  LLM: ChatGLMLLM
  VLLM: ChatGLMVLLM
  TTS: EdgeTTS
  Intent: function_call
  Memory: mem_local_short
```

Provider 目录：

- `core/providers/vad/`：语音活动检测，例如 SileroVAD。
- `core/providers/asr/`：语音识别，支持本地和云端/流式方案。
- `core/providers/llm/`：大模型，支持 OpenAI 风格接口、Ollama、Dify、Coze、FastGPT、Gemini、阿里百炼等。
- `core/providers/vllm/`：视觉大模型。
- `core/providers/tts/`：TTS，支持 Edge、OpenAI、阿里云、讯飞、火山、Minimax、GPT-SoVITS、FishSpeech 等。
- `core/providers/intent/`：意图识别，包括不识别、LLM 意图识别和 function call。
- `core/providers/memory/`：记忆系统，包括无记忆、本地短期记忆、mem0ai、PowerMem、只上报等。

`core/utils/modules_initialize.py` 负责按配置动态初始化 Provider。全模块模式下，Python 服务会从 `manager-api` 拉取公共配置和设备/智能体私有配置，因此 Web 智控台修改模型后可以通过配置刷新生效。

## 8. 工具、MCP 和插件系统

服务端工具系统由 `UnifiedToolHandler` 和 `ToolManager` 统一管理，支持多类工具来源：

- 服务端插件：`plugins_func/functions/` 下的 Python 函数，例如天气、新闻、音乐、Home Assistant、RAGFlow、联网搜索。
- 服务端 MCP：连接服务端配置的 MCP server。
- MCP 接入点：把外部 MCP 服务接入到当前智能体。
- 设备 IoT：设备上报的旧版 IoT 能力。
- 设备 MCP：ESP32 固件端 MCP 工具，如音量、屏幕、摄像头、GPIO 等。

插件函数通过 `@register_function` 注册，带有函数名、描述和参数 schema。LLM 或 Intent 决定调用工具时，统一工具处理器会根据工具名找到对应执行器，执行后返回：

- `RESPONSE`：直接把工具结果回复给用户。
- `REQLLM`：把工具结果再交给 LLM 生成自然语言回复。
- `ERROR` / `NOTFOUND`：返回错误或未找到提示。

扩展新工具通常有三种方式：

1. 在 `plugins_func/functions/` 新增 Python 插件函数。
2. 在智控台中配置 MCP 接入点或服务端 MCP。
3. 在 ESP32 固件侧新增设备 MCP 工具，服务端通过设备 MCP 调用。

## 9. 视觉、声纹、知识库和记忆

- 视觉分析：`/mcp/vision/explain` 接收设备上传的图片和问题，验证 token 后调用 VLLM Provider 返回结果。
- 声纹识别：`voiceprint` 配置和 `VoiceprintProvider` 支持说话人识别，识别结果可作为上下文传给 LLM。
- 知识库：`knowledge` 管理模块和 `search_from_ragflow` 插件支持接入 RAGFlow。
- 记忆系统：会话关闭时可保存记忆；全模块模式还会上报聊天记录、生成聊天标题/摘要。
- 替换词：`correctword` 和 `/config/correct-words` 可对 ASR 文本进行纠错或替换。

## 10. 部署和配置

项目提供两种主部署方式：

- 最简化安装：只运行 `xiaozhi-server`。可用 Docker 或源码运行，配置保存在 `data/.config.yaml`。
- 全模块安装：运行 `xiaozhi-server`、`manager-api`、`manager-web`、MySQL、Redis。配置通过智控台管理。

关键端口：

- `8000`：Python WebSocket，设备语音会话。
- `8003`：Python HTTP，单 Server OTA 和视觉分析接口。
- `8002`：Java 管理后台和 Web 智控台，对外路径 `/xiaozhi`。
- 可选 MQTT 网关：常见 `1883` MQTT、`8884` UDP、`8007` 管理 API。

关键配置文件：

- `main/xiaozhi-server/config.yaml`：默认配置，不建议直接写密钥。
- `main/xiaozhi-server/data/.config.yaml`：本地覆盖配置，推荐放密钥和部署差异。
- `main/xiaozhi-server/config_from_api.yaml`：全模块模式下连接 `manager-api` 的模板。
- `main/xiaozhi-server/mcp_server_settings.json`：服务端 MCP 配置。
- `main/manager-api/src/main/resources/application*.yml`：Java 后台环境、数据库、Redis 和框架配置。

全模块部署后通常要完成三件事：

1. 在智控台注册第一个用户，成为超级管理员。
2. 把 `server.secret` 填入 Python 服务的 `data/.config.yaml` 中 `manager-api.secret`。
3. 在智控台配置模型密钥、`server.websocket`、OTA 地址和必要的 AI Provider 参数。

## 11. 已实现功能

项目当前已经具备：

- WebSocket 设备接入和 MQTT + UDP 网关接入。
- OTA 配置下发、固件下载、设备激活/绑定。
- 流式或非流式 ASR、LLM、TTS 编排。
- VAD、唤醒词快捷回复、实时打断、长时间无语音自动结束。
- 声纹识别和说话人上下文。
- 视觉分析，支持设备拍照后提问。
- 多 Provider 模型管理，支持本地模型和云端 API。
- 智能体、角色、提示词、模板、模型、音色和替换词管理。
- 设备管理、设备工具列表、设备工具调用。
- 服务端插件、服务端 MCP、MCP 接入点、设备 MCP、设备 IoT。
- Home Assistant、天气、新闻、音乐、RAGFlow、联网搜索等插件。
- 知识库管理和 RAGFlow 集成。
- 记忆系统、聊天历史上报、标题和摘要生成。
- Web 智控台和移动端智控台。
- 性能测试工具和数字人/浏览器音频测试工具。
- Docker、源码部署和一键部署脚本。

## 12. 关键约定和注意事项

- `config.yaml` 是默认配置，真实密钥和部署差异应写到 `data/.config.yaml`。
- 如果使用智控台，全局模型和智能体配置以 `manager-api` 为准，很多本地 `config.yaml` 配置不会生效。
- `server.auth_key` 或 `manager-api.secret` 同时用于认证、OTA token 和视觉接口 token，生产环境必须妥善保护。
- WebSocket 地址不要用浏览器直接访问；浏览器测试请使用 `digital-human`。
- 全模块 Docker 镜像从文档看默认偏 x86，arm64 需要按单独文档自行构建。
- 使用 FunASR 本地识别时必须准备 `models/SenseVoiceSmall/model.pt`。
- `manager-api` 第一个注册用户是超级管理员。
- MQTT + UDP 需要额外部署网关，并开放 MQTT、UDP 和网关 API 端口。
- 开启 WebSocket 认证时，设备必须通过 OTA 获取 token，或者在白名单中。
- 公网部署前要做好反向代理、TLS、鉴权、端口暴露和密钥保护；README 已明确提示项目未经过安全测评，不建议直接用于生产公网。

## 13. 推荐阅读路径

如果是第一次接手，建议按下面顺序阅读：

1. `README.md`：了解功能范围和部署方式。
2. `docs/Deployment.md` 或 `docs/Deployment_all.md`：理解单 Server 和全模块部署。
3. `main/xiaozhi-server/app.py`：理解 Python 服务启动。
4. `main/xiaozhi-server/core/websocket_server.py`：理解设备 WebSocket 接入。
5. `main/xiaozhi-server/core/connection.py`：理解每个设备会话状态。
6. `main/xiaozhi-server/core/handle/`：理解 hello、listen、abort、mcp、iot 等消息处理。
7. `main/xiaozhi-server/core/providers/`：理解 ASR/LLM/TTS/VAD/Intent/Memory Provider。
8. `main/xiaozhi-server/core/providers/tools/` 和 `plugins_func/`：理解工具和插件扩展。
9. `main/manager-api/src/main/java/xiaozhi/modules/`：理解后台业务模块。
10. `main/manager-web/src/views/`：理解智控台功能页面。

