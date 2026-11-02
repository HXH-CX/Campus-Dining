"""登录失败限流与短时锁定。

为什么用进程内字典而不是 Redis / 数据表：
MVP 是单进程跑，多一个外部依赖就多一处部署负担。代价必须说清楚——
① 多 worker 部署时每个进程各算各的，实际阈值会被放大成 N×5；
② 进程重启计数清零，重启即可绕过。
真要上多实例，把这里的三个读写换成 Redis 的 INCR + EXPIRE 就行，
调用方（auth_service）不用改。

策略：同一个用户名 15 分钟内失败 5 次 → 锁 15 分钟。
同一个 IP 的阈值放宽到 20 次：校园网一个出口 IP 后面可能坐着几十号人，
用同一个阈值会让一个人手滑把整栋楼锁死。
两个维度都记：只按用户名锁，攻击者可以拿一个弱密码把所有账号扫一遍；
只按 IP 锁，挂个代理就绕过。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.core.exceptions import TooManyRequests

MAX_FAILURES_PER_USER = 5
MAX_FAILURES_PER_IP = 20
WINDOW_SECONDS = 15 * 60
LOCK_SECONDS = 15 * 60
# 键数量超过这个值就顺手清一遍，避免被随机用户名撑爆内存
SWEEP_THRESHOLD = 2000


@dataclass
class _Window:
    failures: list[float] = field(default_factory=list)
    locked_until: float = 0.0


_windows: dict[str, _Window] = {}


def _keys(username: str, ip: str | None) -> list[str]:
    keys = [f"u:{username.strip().lower()}"]
    if ip:
        keys.append(f"ip:{ip}")
    return keys


def _limit(key: str) -> int:
    return MAX_FAILURES_PER_USER if key.startswith("u:") else MAX_FAILURES_PER_IP


def _sweep(now: float) -> None:
    if len(_windows) < SWEEP_THRESHOLD:
        return
    for key in list(_windows):
        window = _windows[key]
        if window.locked_until <= now and (not window.failures or now - window.failures[-1] > WINDOW_SECONDS):
            del _windows[key]


def ensure_allowed(username: str, ip: str | None) -> None:
    """锁定期内直接拒绝；返回则说明可以继续尝试。"""
    now = time.monotonic()
    for key in _keys(username, ip):
        window = _windows.get(key)
        if window is not None and window.locked_until > now:
            minutes = max(1, round((window.locked_until - now) / 60))
            raise TooManyRequests(f"尝试次数过多，请 {minutes} 分钟后再试")


def record_failure(username: str, ip: str | None) -> None:
    now = time.monotonic()
    _sweep(now)
    for key in _keys(username, ip):
        window = _windows.setdefault(key, _Window())
        # 只保留窗口内的失败记录，滑出窗口的自然不算数
        window.failures = [ts for ts in window.failures if now - ts <= WINDOW_SECONDS]
        window.failures.append(now)
        if len(window.failures) >= _limit(key):
            window.locked_until = now + LOCK_SECONDS
            window.failures.clear()


def reset(username: str, ip: str | None) -> None:
    """登录成功后清掉该用户名与该 IP 的失败记录。

    为什么要连 IP 一起清：不清的话计数只增不减，正常用户一天里几次手滑
    （或者测试脚本反复跑）攒到 20 次就会把整个出口 IP 锁死，而那时候
    谁也登不进来、只能干等 15 分钟。
    代价是"攻击者只要有一个有效账号，就能靠成功登录重置 IP 计数"——
    这个交换值得：IP 维度本来就是防大范围撞库的粗筛，不是精密防线。
    """
    for key in _keys(username, ip):
        _windows.pop(key, None)


def _clear_all() -> None:
    """仅测试用：避免用例之间互相影响。"""
    _windows.clear()
