#!/bin/sh
# 容器启动：等库 → 迁移 → 补种子 → 起服务
# 与 dev.py 的区别：这里没有"要不要建 venv / 装依赖"的判断——镜像里已经装好了，
# 只剩运行期必须做的事
set -e

echo "== 同步数据库结构"
# compose 的 depends_on + healthcheck 已经保证 MySQL 可连，但单独 docker run 时没有这层保障，
# 所以迁移失败就重试，而不是让容器直接挂掉
retry=0
while ! alembic upgrade head; do
    retry=$((retry + 1))
    if [ "$retry" -ge 30 ]; then
        echo "数据库连接不上，迁移重试 ${retry} 次后放弃"
        exit 1
    fi
    echo "  迁移失败，2 秒后重试（第 ${retry} 次）"
    sleep 2
done

if [ "${SEED_ON_START:-1}" = "1" ]; then
    echo "== 补齐种子数据"
    python -m app.seed
fi

echo "== 启动 uvicorn"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
