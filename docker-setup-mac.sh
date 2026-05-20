#!/usr/bin/env bash
set -euo pipefail

# macOS Docker Desktop one-click setup for xiaozhi-esp32-server.
# This script intentionally does not install Docker or write to /opt.
# It prepares files under main/xiaozhi-server and starts the full Docker stack.
# admin Admin12#
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="${SCRIPT_DIR}/main/xiaozhi-server"
DATA_DIR="${SERVER_DIR}/data"
MODEL_DIR="${SERVER_DIR}/models/SenseVoiceSmall"
MODEL_PATH="${MODEL_DIR}/model.pt"
CONFIG_PATH="${DATA_DIR}/.config.yaml"
CONFIG_TEMPLATE="${SERVER_DIR}/config_from_api.yaml"
COMPOSE_FILE="${SERVER_DIR}/docker-compose_all.yml"
MODEL_URL="https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt"

info() {
  printf "\033[1;36m%s\033[0m\n" "$*"
}

warn() {
  printf "\033[1;33m%s\033[0m\n" "$*"
}

error() {
  printf "\033[1;31m%s\033[0m\n" "$*" >&2
}

confirm() {
  local prompt="${1:-Continue?}"
  local answer
  read -r -p "${prompt} [y/N] " answer
  case "${answer}" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    error "缺少命令: $1"
    return 1
  fi
}

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

get_lan_ip() {
  local ip=""

  if command -v ipconfig >/dev/null 2>&1; then
    ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
    if [ -z "${ip}" ]; then
      ip="$(ipconfig getifaddr en1 2>/dev/null || true)"
    fi
  fi

  if [ -z "${ip}" ] && command -v ifconfig >/dev/null 2>&1; then
    ip="$(ifconfig | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}')"
  fi

  printf "%s" "${ip}"
}

wait_for_log() {
  local container="$1"
  local pattern="$2"
  local timeout="${3:-300}"
  local start
  start="$(date +%s)"

  while true; do
    if docker logs "${container}" 2>&1 | grep -q "${pattern}"; then
      return 0
    fi

    if [ $(( $(date +%s) - start )) -gt "${timeout}" ]; then
      return 1
    fi

    sleep 2
  done
}

write_manager_api_config() {
  local secret="$1"
  local lan_ip="$2"

  cat > "${CONFIG_PATH}" <<EOF
server:
  ip: 0.0.0.0
  port: 8000
  http_port: 8003
  vision_explain: http://${lan_ip}:8003/mcp/vision/explain
manager-api:
  url: http://xiaozhi-esp32-server-web:8002/xiaozhi
  secret: ${secret}
prompt_template: agent-base-prompt.txt
EOF
}

configure_manager_urls() {
  local lan_ip="$1"
  local ota_url="http://${lan_ip}:8002/xiaozhi/ota/"
  local ws_url="ws://${lan_ip}:8000/xiaozhi/v1/"
  local fronted_url="http://${lan_ip}:8002"

  if [ "${lan_ip}" = "<你的Mac局域网IP>" ]; then
    warn "未获得明确局域网 IP，跳过自动写入智控台 server.ota/server.websocket。"
    return 0
  fi

  info "正在写入智控台 OTA/WebSocket 参数..."
  docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server -e \
    "UPDATE sys_params SET param_value='${ws_url}', update_date=NOW() WHERE param_code='server.websocket';
     UPDATE sys_params SET param_value='${ota_url}', update_date=NOW() WHERE param_code='server.ota';
     UPDATE sys_params SET param_value='${fronted_url}', update_date=NOW() WHERE param_code='server.fronted_url';" >/dev/null

  # manager-api caches params in Redis, so DB changes alone are not enough.
  docker exec xiaozhi-esp32-server-redis redis-cli DEL sys:params server:config >/dev/null || true
  docker restart xiaozhi-esp32-server-web >/dev/null

  if wait_for_log "xiaozhi-esp32-server-web" "Started AdminApplication in" 300; then
    info "智控台参数已更新并重新加载。"
  else
    warn "智控台重启等待超时。你可以稍后手动确认 server.websocket/server.ota。"
  fi
}

main() {
  if [ "$(uname -s)" != "Darwin" ]; then
    warn "当前系统不是 macOS。Linux 服务器建议使用 docker-setup.sh。"
  fi

  info "小智服务端 macOS Docker 一键启动脚本"
  echo
  echo "将会执行："
  echo "  1. 检查 Docker Desktop 是否可用"
  echo "  2. 准备 ${DATA_DIR}"
  echo "  3. 下载 SenseVoiceSmall/model.pt（如不存在）"
  echo "  4. 启动全模块 Docker Compose：server + web/api + MySQL + Redis"
  echo "  5. 引导你注册智控台账号并填写 server.secret"
  echo "  6. 写入 OTA/WebSocket 参数并输出 ESP32 可配置的 OTA 地址"
  echo

  confirm "继续执行吗？" || {
    warn "已取消。"
    exit 0
  }

  require_command docker || {
    error "请先安装并启动 Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
  }
  require_command curl || exit 1

  if ! docker info >/dev/null 2>&1; then
    error "Docker 当前不可用。请先启动 Docker Desktop，等待 Docker Engine 就绪后再运行。"
    exit 1
  fi

  if ! docker compose version >/dev/null 2>&1; then
    error "当前 Docker 不支持 'docker compose'。请升级 Docker Desktop。"
    exit 1
  fi

  if [ ! -f "${COMPOSE_FILE}" ]; then
    error "找不到 compose 文件: ${COMPOSE_FILE}"
    exit 1
  fi

  mkdir -p "${DATA_DIR}" "${MODEL_DIR}"

  if [ ! -f "${CONFIG_PATH}" ]; then
    if [ ! -f "${CONFIG_TEMPLATE}" ]; then
      error "找不到配置模板: ${CONFIG_TEMPLATE}"
      exit 1
    fi
    cp "${CONFIG_TEMPLATE}" "${CONFIG_PATH}"
    info "已创建配置文件: ${CONFIG_PATH}"
  else
    warn "配置文件已存在，保留: ${CONFIG_PATH}"
  fi

  if [ ! -f "${MODEL_PATH}" ]; then
    info "开始下载语音识别模型，文件较大，请耐心等待..."
    curl -fL --progress-bar "${MODEL_URL}" -o "${MODEL_PATH}"
    info "模型下载完成: ${MODEL_PATH}"
  else
    info "模型已存在，跳过下载: ${MODEL_PATH}"
  fi

  local arch
  arch="$(uname -m)"
  if [ "${arch}" = "arm64" ]; then
    warn "检测到 Apple Silicon (${arch})。官方镜像可能是 amd64，默认使用 linux/amd64 兼容模式。"
    export DOCKER_DEFAULT_PLATFORM="${DOCKER_DEFAULT_PLATFORM:-linux/amd64}"
  fi

  cd "${SERVER_DIR}"

  if docker ps -a --format '{{.Names}}' | grep -Eq '^(xiaozhi-esp32-server|xiaozhi-esp32-server-web|xiaozhi-esp32-server-db|xiaozhi-esp32-server-redis)$'; then
    warn "检测到已有小智相关容器。"
    if confirm "是否先停止并重建这些容器？"; then
      compose down
    else
      warn "将直接执行 up -d，可能复用已有容器。"
    fi
  fi

  info "正在启动 Docker 服务..."
  compose up -d

  info "等待智控台启动，最多等待 5 分钟..."
  if wait_for_log "xiaozhi-esp32-server-web" "Started AdminApplication in" 300; then
    info "智控台已启动。"
  else
    warn "等待智控台启动超时。你可以手动查看日志："
    echo "  docker logs -f xiaozhi-esp32-server-web"
  fi

  local lan_ip
  lan_ip="$(get_lan_ip)"
  if [ -z "${lan_ip}" ]; then
    warn "未能自动获取局域网 IP，请稍后手动替换下面地址中的 <你的Mac局域网IP>。"
    lan_ip="<你的Mac局域网IP>"
  fi

  echo
  info "请完成第一次智控台初始化："
  echo "  1. 打开智控台: http://${lan_ip}:8002"
  echo "     如果在本机浏览器访问，也可以用: http://127.0.0.1:8002"
  echo "  2. 注册第一个用户，它会成为超级管理员"
  echo "  3. 登录后进入：参数字典 -> 参数管理"
  echo "  4. 找到参数编码 server.secret，复制参数值"
  echo

  local secret_key
  read -r -p "请粘贴 server.secret（直接回车可跳过，之后手动配置）: " secret_key

  if [ -n "${secret_key}" ]; then
    write_manager_api_config "${secret_key}" "${lan_ip}"
    info "已写入 manager-api secret 到 ${CONFIG_PATH}"
    info "正在重启 Python 服务..."
    docker restart xiaozhi-esp32-server >/dev/null
  else
    warn "已跳过 secret 写入。Python 服务可能无法从 manager-api 拉取配置。"
  fi

  local ota_url="http://${lan_ip}:8002/xiaozhi/ota/"
  local ws_url="ws://${lan_ip}:8000/xiaozhi/v1/"
  local vision_url="http://${lan_ip}:8003/mcp/vision/explain"

  configure_manager_urls "${lan_ip}"

  echo
  info "安装/启动流程完成。"
  echo
  echo "服务地址："
  echo "  智控台:       http://${lan_ip}:8002"
  echo "  OTA 地址:     ${ota_url}"
  echo "  WebSocket:    ${ws_url}"
  echo "  视觉分析接口: ${vision_url}"
  echo
  warn "重要：ESP32 通常只需要配置 OTA 地址："
  echo "  ${ota_url}"
  echo
  warn "在拿 ESP32 测试前，请在智控台参数管理里确认："
  echo "  server.websocket = ${ws_url}"
  echo "  server.ota       = ${ota_url}"
  echo
  warn "还需要在智控台配置可用的 LLM / ASR / TTS 模型密钥，否则服务启动了也可能无法正常对话。"
  echo
  echo "常用日志命令："
  echo "  cd ${SERVER_DIR}"
  echo "  docker logs -f xiaozhi-esp32-server-web"
  echo "  docker logs -f xiaozhi-esp32-server"
}

main "$@"
