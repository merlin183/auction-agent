"""Rate Limiter 유틸리티"""
import asyncio
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """비동기 Rate Limiter"""

    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Rate limit 획득"""
        async with self._lock:
            current_time = time.monotonic()

            if self.last_call_time is not None:
                elapsed = current_time - self.last_call_time
                if elapsed < self.min_interval:
                    await asyncio.sleep(self.min_interval - elapsed)

            self.last_call_time = time.monotonic()

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *args) -> None:
        pass


class SlidingWindowRateLimiter:
    """슬라이딩 윈도우 기반 Rate Limiter"""

    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: deque = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Rate limit 획득"""
        async with self._lock:
            current_time = time.monotonic()

            # 윈도우 밖의 호출 제거
            while self.calls and current_time - self.calls[0] > self.window_seconds:
                self.calls.popleft()

            # 한도 초과 시 대기
            if len(self.calls) >= self.max_calls:
                sleep_time = self.window_seconds - (current_time - self.calls[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

                # 다시 정리
                current_time = time.monotonic()
                while self.calls and current_time - self.calls[0] > self.window_seconds:
                    self.calls.popleft()

            self.calls.append(current_time)

    async def __aenter__(self) -> "SlidingWindowRateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *args) -> None:
        pass
