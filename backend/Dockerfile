FROM python:3.12-slim

# PYTHONUNBUFFERED：日志立刻出来，不然 docker logs 要等到缓冲满
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl 只用于 HEALTHCHECK；asyncmy 在 manylinux 上有预编译 wheel，不需要编译链
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 先只拷依赖清单：改代码不会让 pip 这层缓存失效
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh && mkdir -p /app/uploads

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=25s --retries=6 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
