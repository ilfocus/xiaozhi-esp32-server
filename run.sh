#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${ROOT_DIR}/main/xiaozhi-server/docker-compose_all.yml"
SERVER_IMAGE="ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest"
SERVER_SERVICE="xiaozhi-esp32-server"
SERVER_CONTAINER="xiaozhi-esp32-server"

usage() {
  cat <<EOF
Usage: ./run.sh <command>

Commands:
  start     Start all services with docker compose
  stop      Stop all services with docker compose
  restart   Rebuild server image and recreate only the server container
  status    Show service/container status
  logs      Follow server container logs
EOF
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Error: docker is not installed or not in PATH" >&2
    exit 1
  fi
}

start() {
  docker compose -f "${COMPOSE_FILE}" up -d
}

stop() {
  docker compose -f "${COMPOSE_FILE}" down
}

restart() {
  echo "Building server image: ${SERVER_IMAGE}"
  docker build -f "${ROOT_DIR}/Dockerfile-server" -t "${SERVER_IMAGE}" "${ROOT_DIR}"

  echo "Recreating server container: ${SERVER_CONTAINER}"
  docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate "${SERVER_SERVICE}"

  echo "Server restarted. Recent logs:"
  docker logs --tail 40 "${SERVER_CONTAINER}"
}

status() {
  docker compose -f "${COMPOSE_FILE}" ps
}

logs() {
  docker logs -f "${SERVER_CONTAINER}"
}

main() {
  require_docker

  case "${1:-}" in
    start)
      start
      ;;
    stop)
      stop
      ;;
    restart)
      restart
      ;;
    status)
      status
      ;;
    logs)
      logs
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo "Unknown command: $1" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
