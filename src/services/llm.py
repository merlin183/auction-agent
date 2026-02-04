"""LLM 서비스"""
from functools import lru_cache
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

import sys
sys.path.append("..")
from config.settings import get_settings


@lru_cache
def get_llm_client(
    model: Optional[str] = None,
    provider: str = "anthropic",
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> BaseChatModel:
    """LLM 클라이언트 반환

    Args:
        model: 모델명 (None이면 기본값 사용)
        provider: 제공자 ("anthropic" 또는 "openai")
        temperature: 생성 온도
        max_tokens: 최대 토큰 수

    Returns:
        LLM 클라이언트
    """
    settings = get_settings()

    if provider == "anthropic":
        model_name = model or settings.default_llm_model
        return ChatAnthropic(
            model=model_name,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "openai":
        model_name = model or "gpt-4o"
        return ChatOpenAI(
            model=model_name,
            api_key=settings.openai_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_high_reasoning_llm() -> BaseChatModel:
    """고성능 추론 LLM 반환 (레드팀 등에서 사용)"""
    settings = get_settings()
    return ChatAnthropic(
        model=settings.high_reasoning_model,
        api_key=settings.anthropic_api_key,
        temperature=0.0,
        max_tokens=8192,
    )
