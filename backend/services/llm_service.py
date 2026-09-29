import concurrent.futures
import json
import logging
import os
import time
import urllib.request
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)

DEFAULT_LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
DEFAULT_LLM_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


class LLMService:
    """
    Centralized LLM service.

    All AI agents should use this class instead of
    directly creating ChatOllama objects.
    """

    def __init__(self, timeout: float = DEFAULT_LLM_TIMEOUT, model: str = DEFAULT_LLM_MODEL):
        self.timeout = timeout
        self.model = model
        self.host = OLLAMA_HOST
        try:
            self.llm = ChatOllama(
                model=self.model,
                temperature=0.2,
                base_url=self.host,
                sync_client_kwargs={"timeout": self.timeout},
                client_kwargs={"timeout": self.timeout},
            )
        except Exception:
            self.llm = ChatOllama(
                model=self.model,
                temperature=0.2,
                base_url=self.host,
            )

    def is_available(self) -> bool:
        """Check if local Ollama service is reachable and has the expected model."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"User-Agent": "DisasterResponseCoordinator"})
            with urllib.request.urlopen(req, timeout=2.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    # Check if requested model or prefix matches
                    model_match = any(self.model in m or m in self.model for m in models)
                    if not model_match:
                        logger.warning("Ollama is reachable, but model '%s' was not found in: %s", self.model, models)
                    return True
        except Exception as err:
            logger.debug("Ollama is_available check failed: %s", err)
            return False
        return False

    def invoke(self, prompt: str, timeout: float = None):
        """
        Send a prompt to the LLM with a bounded execution timeout and structured logging.
        """
        effective_timeout = timeout if timeout is not None else self.timeout
        start_time = time.time()
        logger.info(
            "Ollama request started | model=%s | timeout=%.1fs | prompt_len=%d",
            self.model,
            effective_timeout,
            len(prompt),
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.llm.invoke, prompt)
            try:
                response = future.result(timeout=effective_timeout)
                elapsed = time.time() - start_time
                content = response.content if hasattr(response, "content") else str(response)
                logger.info(
                    "Ollama response received | model=%s | elapsed=%.2fs | response_len=%d",
                    self.model,
                    elapsed,
                    len(content),
                )
                return content
            except concurrent.futures.TimeoutError as te:
                elapsed = time.time() - start_time
                logger.error(
                    "Ollama request timed out | model=%s | elapsed=%.2fs | limit=%.1fs",
                    self.model,
                    elapsed,
                    effective_timeout,
                )
                raise TimeoutError(
                    f"LLM invoke timed out after {effective_timeout}s."
                ) from te
            except Exception as err:
                elapsed = time.time() - start_time
                logger.error(
                    "Ollama invoke error | model=%s | elapsed=%.2fs | exception=%s: %s",
                    self.model,
                    elapsed,
                    type(err).__name__,
                    err,
                )
                raise


# Singleton instance
_llm_service = LLMService()


def get_llm():
    """
    Returns the shared LLM instance.
    """
    return _llm_service