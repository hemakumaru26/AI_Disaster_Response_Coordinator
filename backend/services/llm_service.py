import concurrent.futures
import logging
import os
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)

DEFAULT_LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "5.0"))


class LLMService:
    """
    Centralized LLM service.

    All AI agents should use this class instead of
    directly creating ChatOllama objects.
    """

    def __init__(self, timeout: float = DEFAULT_LLM_TIMEOUT):
        self.timeout = timeout
        try:
            self.llm = ChatOllama(
                model="qwen2.5:7b",
                temperature=0.2,
                sync_client_kwargs={"timeout": self.timeout},
                client_kwargs={"timeout": self.timeout},
            )
        except Exception:
            self.llm = ChatOllama(
                model="qwen2.5:7b",
                temperature=0.2,
            )

    def is_available(self) -> bool:
        """Check if local Ollama LLM is reachable and responsive."""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.llm.invoke, "ping")
                future.result(timeout=2.0)
                return True
        except Exception:
            return False

    def invoke(self, prompt: str, timeout: float = None):
        """
        Send a prompt to the LLM with a bounded execution timeout.
        """
        effective_timeout = timeout if timeout is not None else self.timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.llm.invoke, prompt)
            try:
                response = future.result(timeout=effective_timeout)
                if hasattr(response, "content"):
                    return response.content
                return str(response)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"LLM invoke timed out after {effective_timeout}s."
                )


# Singleton instance
_llm_service = LLMService()


def get_llm():
    """
    Returns the shared LLM instance.
    """
    return _llm_service