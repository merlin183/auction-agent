"""로깅 유틸리티"""
import structlog
from typing import Any


def get_logger(name: str) -> structlog.BoundLogger:
    """구조화된 로거 반환"""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(name)


class AgentLogger:
    """에이전트 전용 로거"""

    def __init__(self, agent_name: str):
        self.logger = get_logger(agent_name)
        self.agent_name = agent_name

    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(message, agent=self.agent_name, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(message, agent=self.agent_name, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self.logger.error(message, agent=self.agent_name, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(message, agent=self.agent_name, **kwargs)

    def step(self, step_name: str, **kwargs: Any) -> None:
        """에이전트 실행 단계 로깅"""
        self.logger.info(f"Step: {step_name}", agent=self.agent_name, **kwargs)

    def result(self, result_type: str, **kwargs: Any) -> None:
        """에이전트 결과 로깅"""
        self.logger.info(f"Result: {result_type}", agent=self.agent_name, **kwargs)
