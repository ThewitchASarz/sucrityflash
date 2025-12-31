"""
OpenAI model client for agents.

Handles LLM calls with logging and error handling.
"""
import hashlib
from typing import Dict, Any, Optional
import logging
from openai import OpenAI
from apps.api.core.config import settings

logger = logging.getLogger(__name__)


class ModelClient:
    """OpenAI API client with logging."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to settings.OPENAI_API_KEY)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)

    def query_llm(
        self,
        prompt: str,
        system_message: str = "You are a security testing assistant.",
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Query OpenAI LLM.

        Args:
            prompt: User prompt
            system_message: System message
            model: Model name (gpt-4, gpt-3.5-turbo)
            temperature: Sampling temperature
            max_tokens: Max response tokens

        Returns:
            Dict with response, prompt_hash, response_hash
        """
        logger.info(f"Querying {model} (prompt length: {len(prompt)})")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            response_text = response.choices[0].message.content

            # Compute hashes for audit
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            response_hash = hashlib.sha256(response_text.encode()).hexdigest()

            logger.info(f"LLM response: {len(response_text)} chars")

            return {
                "response": response_text,
                "prompt_hash": prompt_hash,
                "response_hash": response_hash,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            raise
