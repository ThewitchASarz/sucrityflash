"""
Model Router for Agent Runtime - Phase 2/3

Routes LLM calls to appropriate models based on task type.
Adds telemetry for model usage tracking.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    """Response from model with telemetry."""
    content: str
    model_name: str
    tokens_est: int
    latency_ms: int


class ModelRouter:
    """
    Routes LLM calls based on task mode.

    Modes:
    - planner: Complex reasoning for reconnaissance planning
    - summarizer: Evidence summarization and finding generation
    - triage: Quick classification and risk scoring
    """

    def __init__(self, api_key: Optional[str] = None, default_model: str = "gpt-4"):
        """
        Initialize model router.

        Args:
            api_key: OpenAI API key (reads from env if None)
            default_model: Default model to use
        """
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self.default_model = default_model

        # Model selection by mode
        self.mode_models = {
            "planner": "gpt-4",           # Complex reasoning
            "summarizer": "gpt-4",        # Evidence analysis
            "triage": "gpt-3.5-turbo",    # Quick classification
        }

    def generate(
        self,
        prompt: str,
        mode: str = "planner",
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> ModelResponse:
        """
        Generate response using appropriate model for mode.

        Args:
            prompt: User prompt
            mode: Task mode (planner, summarizer, triage)
            system_prompt: Optional system prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            ModelResponse with content and telemetry
        """
        start_time = time.time()
        model_name = self.mode_models.get(mode, self.default_model)

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            logger.info(f"Calling {model_name} for mode={mode}")

            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            latency_ms = int((time.time() - start_time) * 1000)
            content = response.choices[0].message.content or ""

            # Estimate tokens (rough heuristic: 4 chars per token)
            tokens_est = len(prompt) // 4 + len(content) // 4
            if system_prompt:
                tokens_est += len(system_prompt) // 4

            logger.info(
                f"Model response: model={model_name}, tokens_est={tokens_est}, "
                f"latency_ms={latency_ms}"
            )

            return ModelResponse(
                content=content,
                model_name=model_name,
                tokens_est=tokens_est,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Model generation failed: {e}", exc_info=True)
            latency_ms = int((time.time() - start_time) * 1000)

            # Return empty response with error context
            return ModelResponse(
                content="",
                model_name=model_name,
                tokens_est=0,
                latency_ms=latency_ms
            )

    def batch_generate(
        self,
        prompts: list[str],
        mode: str = "triage",
        system_prompt: Optional[str] = None
    ) -> list[ModelResponse]:
        """
        Generate responses for multiple prompts.

        Useful for batch triage or classification.

        Args:
            prompts: List of prompts
            mode: Task mode
            system_prompt: Optional system prompt

        Returns:
            List of ModelResponse objects
        """
        responses = []
        for prompt in prompts:
            response = self.generate(
                prompt=prompt,
                mode=mode,
                system_prompt=system_prompt,
                max_tokens=500,  # Shorter for batch
                temperature=0.3  # Lower for consistency
            )
            responses.append(response)

        return responses
