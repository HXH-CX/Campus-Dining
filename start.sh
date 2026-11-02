#!/usr/bin/env bash
# 校园食光 macOS / Linux 启动入口
# 逻辑都在 dev.py，两个平台共用一份
set -euo pipefail
cd "$(dirname "$0")"
exec python3 dev.py "$@"
