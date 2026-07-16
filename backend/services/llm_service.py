from langchain_ollama import ChatOllama


class LLMService:
    """
    Centralized LLM service.

    All AI agents should use this class instead of
    directly creating ChatOllama objects.
    """

    def __init__(self):
        self.llm = ChatOllama(
            model="qwen2.5:7b",
            temperature=0.2,
        )

    def invoke(self, prompt: str):
        """
        Send a prompt to the LLM.
        """
        response = self.llm.invoke(prompt)
        return response.content


# Singleton instance
_llm_service = LLMService()


def get_llm():
    """
    Returns the shared LLM instance.
    """
    return _llm_service