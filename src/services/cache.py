"""캐시 서비스"""
import json
from typing import Any, Optional
from datetime import timedelta

import redis.asyncio as redis

import sys
sys.path.append("..")
from config.settings import get_settings


class CacheService:
    """Redis 기반 캐시 서비스"""

    def __init__(self, redis_url: Optional[str] = None):
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Redis 연결"""
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self) -> None:
        """Redis 연결 종료"""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        """Redis 클라이언트"""
        if self._client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """캐시 저장"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        await self.client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        """캐시 삭제"""
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """키 존재 확인"""
        return await self.client.exists(key) > 0

    async def get_or_set(
        self,
        key: str,
        factory,
        ttl: Optional[timedelta] = None,
    ) -> Any:
        """캐시 조회 또는 생성"""
        value = await self.get(key)
        if value is None:
            value = await factory()
            await self.set(key, value, ttl)
        return value

    # 경매 관련 특화 메서드
    async def cache_auction_data(
        self,
        case_number: str,
        data: dict,
        ttl: timedelta = timedelta(hours=6),
    ) -> None:
        """경매 데이터 캐시"""
        key = f"auction:{case_number}"
        await self.set(key, data, ttl)

    async def get_auction_data(self, case_number: str) -> Optional[dict]:
        """경매 데이터 조회"""
        key = f"auction:{case_number}"
        return await self.get(key)

    async def cache_analysis_result(
        self,
        case_number: str,
        analysis_type: str,
        result: dict,
        ttl: timedelta = timedelta(hours=1),
    ) -> None:
        """분석 결과 캐시"""
        key = f"analysis:{case_number}:{analysis_type}"
        await self.set(key, result, ttl)

    async def get_analysis_result(
        self,
        case_number: str,
        analysis_type: str,
    ) -> Optional[dict]:
        """분석 결과 조회"""
        key = f"analysis:{case_number}:{analysis_type}"
        return await self.get(key)


# 싱글톤 인스턴스
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """캐시 서비스 싱글톤 반환"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.connect()
    return _cache_service
