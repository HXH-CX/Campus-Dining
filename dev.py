#!/usr/bin/env python3
"""一键启动校园食光（后端 + 前端）。

为什么用 Python 而不是两个 shell 脚本：
后端本来就依赖 Python，拿它当启动器不用额外要求；而且「建 venv、装依赖、
等 MySQL、跑迁移」这些判断写一次就能同时服务 Windows / macOS / Linux，
不必维护 .bat 和 .sh 两套逻辑各写一遍。

用法：
    python dev.py                # 装好就直接起
    python dev.py --reset        # 先清空业务表再灌种子（会丢数据）
    python dev.py --reload       # 后端开热重载
    python dev.py --no-browser   # 不自动开浏览器

幂等：重复执行不会重复装依赖、不会重复灌数据，可直接当日常启动入口。
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"
IS_WIN = os.name == "nt"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# 少一个空格都会让后面的对齐全歪，所以统一在这里拼
STEP = 0


def step(title: str) -> None:
    global STEP
    STEP += 1
    print(f"\n[{STEP}] {title}")


def info(msg: str) -> None:
    print(f"    {msg}")


def fail(msg: str, hint: str = "") -> None:
    print(f"\n!!! {msg}", file=sys.stderr)
    if hint:
        print(hint, file=sys.stderr)
    sys.exit(1)


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")


def run(cmd: list[str] | str, cwd: Path, check: bool = True, quiet: bool = False) -> subprocess.CompletedProcess:
    """跑一条命令并把输出透传给用户（装依赖这种慢操作需要看得见进度）。"""
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=isinstance(cmd, str),
        stdout=subprocess.DEVNULL if quiet else None,
        check=check,
    )


def port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status < 500
    except (urllib.error.URLError, OSError):
        return False


def wait_http(url: str, timeout: int, label: str) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if http_ok(url):
            return True
        time.sleep(0.4)
    print(f"    {label} 在 {timeout}s 内没有响应")
    return False


# ---------------------------------------------------------------- 前置检查


def check_runtimes() -> None:
    step("检查运行环境")
    if sys.version_info < (3, 10):
        fail(f"Python 版本过低：{sys.version.split()[0]}", "需要 3.10+（项目用了 X | Y 的联合类型标注）")
    info(f"Python {sys.version.split()[0]}")

    node = shutil.which("node")
    if node is None:
        fail("找不到 node", "装 Node 18+：https://nodejs.org")
    version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    major = int(version.lstrip("v").split(".")[0])
    if major < 18:
        fail(f"Node 版本过低：{version}", "Vite 6 需要 Node 18+")
    info(f"Node {version}")

    if shutil.which("npm") is None:
        fail("找不到 npm", "Node 装好一般自带 npm，检查 PATH")


def ensure_venv() -> None:
    step("准备后端虚拟环境")
    python = venv_python()
    if not python.exists():
        info("首次运行，创建 backend/.venv ...")
        run([sys.executable, "-m", "venv", str(VENV)], cwd=ROOT)
        python = venv_python()

    # 用「能不能 import fastapi」来判断依赖是否装好，比放一个 .installed 标记文件可靠：
    # 换机器、删了包、venv 半残都能发现
    installed = run([str(python), "-c", "import fastapi, sqlalchemy, alembic"], cwd=BACKEND, check=False, quiet=True)
    if installed.returncode != 0:
        info("安装后端依赖（首次会慢一点）...")
        run([str(python), "-m", "pip", "install", "-q", "--upgrade", "pip"], cwd=BACKEND)
        run([str(python), "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=BACKEND)
    else:
        info("依赖已就绪")


def ensure_env_file() -> None:
    step("检查配置文件")
    env_file = BACKEND / ".env"
    example = BACKEND / ".env.example"
    if env_file.exists():
        info("backend/.env 已存在，保持不变")
        return
    if not example.exists():
        fail("找不到 backend/.env.example，无法生成配置")
    shutil.copy(example, env_file)
    info("已从 .env.example 生成 backend/.env")
    info("如果本机 MySQL 的账号密码不同，改这个文件里的 DATABASE_URL")


def db_endpoint() -> tuple[str, int] | None:
    """从 .env 的 DATABASE_URL 里抠出 host:port，用来提前探一下 MySQL 是否可达。

    只处理 mysql+xxx://user:pass@host:port/db 这种形态；解析不出来就返回 None，
    交给 alembic 自己去报错——不为猜不透的配置硬造逻辑。
    """
    env_file = BACKEND / ".env"
    if not env_file.exists():
        return None
    url = ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
    if not url or "://" not in url:
        return None
    try:
        # SQLAlchemy 的 mysql+asyncmy:// 前缀对 urlsplit 来说是合法 scheme，能直接解析
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname
        port = parsed.port or 3306
    except ValueError:
        return None
    if not host:
        return None
    return host, port


def wait_mysql() -> None:
    step("等待 MySQL")
    endpoint = db_endpoint()
    if endpoint is None:
        info("读不出 DATABASE_URL 里的地址，跳过预检（交给迁移报错）")
        return
    host, port = endpoint
    # 只探本机：远程库探不通时更可能是网络策略，直接说「连不上」会误导
    if host not in {"127.0.0.1", "localhost", "::1"}:
        info(f"数据库在 {host}:{port}，跳过本机预检")
        return
    for _ in range(40):
        if port_open(host, port):
            info(f"MySQL {host}:{port} 已就绪")
            return
        time.sleep(0.5)
    fail(
        f"连不上 MySQL（{host}:{port}）",
        "检查三件事：\n"
        "  1. MySQL 有没有启动（Windows 服务里找 MySQL80，或 net start mysql80）\n"
        "  2. 数据库建了没：CREATE DATABASE campus_dining CHARACTER SET utf8mb4;\n"
        "  3. backend/.env 里的 DATABASE_URL 账号密码对不对",
    )


def migrate() -> None:
    step("同步数据库结构")
    result = run([str(venv_python()), "-m", "alembic", "upgrade", "head"], cwd=BACKEND, check=False)
    if result.returncode != 0:
        fail(
            "迁移失败",
            "常见原因：数据库不存在、账号没权限、或用的是旧库结构与迁移记录对不上。\n"
            "从头来过可以删库重建，再跑一次本脚本。",
        )
    info("已是最新结构")


def seed(reset: bool) -> None:
    step("准备演示数据")
    if reset:
        info("--reset：清空业务表后重新灌入")
        run([str(venv_python()), "-m", "app.seed", "--reset"], cwd=BACKEND)
        return
    # seed 按用户名 / 名称判重，已有数据不会重复写入，所以每次启动都可以放心跑
    run([str(venv_python()), "-m", "app.seed"], cwd=BACKEND, check=False)
    info("种子数据已对齐（已有的不会重复写入）")


# ---------------------------------------------------------------- 起服务


def start_backend(reload: bool) -> subprocess.Popen | None:
    step("启动后端")
    if port_open("127.0.0.1", BACKEND_PORT):
        info(f"{BACKEND_PORT} 已被占用，视为已经在跑，跳过启动")
        return None
    cmd = [str(venv_python()), "-m", "uvicorn", "app.main:app", "--port", str(BACKEND_PORT)]
    if reload:
        cmd.append("--reload")
    proc = subprocess.Popen(cmd, cwd=str(BACKEND))
    info(f"uvicorn 已拉起（pid {proc.pid}）")
    return proc


def start_frontend() -> subprocess.Popen | None:
    step("启动前端")
    if port_open("127.0.0.1", FRONTEND_PORT):
        info(f"{FRONTEND_PORT} 已被占用，视为已经在跑，跳过启动")
        return None
    if not (FRONTEND / "node_modules").exists():
        info("安装前端依赖（首次会慢一点）...")
        run("npm install", cwd=FRONTEND)

    # Windows 上 npm 是 .cmd，必须经 shell 才能执行；POSIX 直接 exec
    cmd: list[str] | str = "npm run dev" if IS_WIN else ["npm", "run", "dev"]
    proc = subprocess.Popen(cmd, cwd=str(FRONTEND), shell=IS_WIN)
    info(f"vite 已拉起（pid {proc.pid}）")
    return proc


def _raise_interrupt(signum, frame):  # noqa: ARG001
    """把 SIGTERM / SIGBREAK 归一成 Ctrl-C，复用同一套清理逻辑。"""
    raise KeyboardInterrupt


def stop(procs: list[subprocess.Popen]) -> None:
    """按进程树杀：npm 会再派一个 node 子进程，只 kill 父进程会把 5173 留在后台。"""
    for proc in procs:
        if proc.poll() is not None:
            continue
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="校园食光一键启动")
    parser.add_argument("--reset", action="store_true", help="清空业务表并重新灌种子（会丢数据）")
    parser.add_argument("--reload", action="store_true", help="后端开启热重载")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    # 输出被重定向到文件 / 管道时默认是全缓冲，进度会攒到最后才吐出来，
    # 启动过程看着像卡死；这里强制逐行刷新
    sys.stdout.reconfigure(line_buffering=True)

    print("校园食光 · 本地启动")
    check_runtimes()
    ensure_venv()
    ensure_env_file()
    wait_mysql()
    migrate()
    seed(args.reset)

    procs: list[subprocess.Popen] = []
    backend = start_backend(args.reload)
    if backend:
        procs.append(backend)
    frontend = start_frontend()
    if frontend:
        procs.append(frontend)

    step("等待服务就绪")
    api = f"http://127.0.0.1:{BACKEND_PORT}/health"
    web = f"http://127.0.0.1:{FRONTEND_PORT}/"
    backend_ok = wait_http(api, 40, "后端")
    frontend_ok = wait_http(web, 60, "前端")

    if backend_ok:
        info(f"后端 http://127.0.0.1:{BACKEND_PORT}/docs")
    if frontend_ok:
        info(f"前端 http://127.0.0.1:{FRONTEND_PORT}")
    info("后台 /admin（管理员账号见 backend/app/seed.py）")

    if frontend_ok and not args.no_browser:
        webbrowser.open(f"http://127.0.0.1:{FRONTEND_PORT}")

    if not procs:
        print("\n两个服务本来就在跑，这里没有需要托管的东西。")
        return

    print("\n按 Ctrl-C 停止。")
    try:
        # Ctrl-C 走 KeyboardInterrupt；SIGTERM（被 kill / 关终端）和 SIGBREAK
        # （Windows 的 Ctrl-Break）也转成同一条路径，否则子进程会留下来占端口
        for name in ("SIGTERM", "SIGBREAK"):
            sig = getattr(signal, name, None)
            if sig is not None:
                signal.signal(sig, _raise_interrupt)
        # 谁先退出就把另一个也带下去，避免留下半套环境占着端口
        while True:
            for proc in procs:
                if proc.poll() is not None:
                    print(f"\n有服务退出了（pid {proc.pid}），一并停止其余进程。")
                    raise KeyboardInterrupt
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        stop(procs)
        print("已停止。")


if __name__ == "__main__":
    main()
