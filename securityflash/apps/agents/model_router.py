"""
Multi-model router for agent LLM usage.

Selects provider/model based on role and records every call for audit.
"""
import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from apps.api.core.config import settings
from apps.agents.clients.db_client import DBClient


class Role(str, Enum):
    PLANNER = "PLANNER"
    SOLVER = "SOLVER"
    VALIDATOR = "VALIDATOR"
    SUMMARIZER = "SUMMARIZER"
    CODEREVIEW = "CODEREVIEW"


@dataclass
class ModelSelection:
    provider: str
    model: str


class ModelRouter:
    """
    Provider routing with audit logging for every call.

    Providers:
        - OpenAI (Planner, Solver primary, Validator, Summarizer)
        - Anthropic (Code review primary)
        - Gemini (Solver secondary rotation)
    """

    def __init__(self, db_client: DBClient, run_id: str, agent_id: str, policy_version: str):
        self.db_client = db_client
        self.run_id = run_id
        self.agent_id = agent_id
        self.policy_version = policy_version

        # Lazy clients (created on demand)
        self._openai_client = None

    def _select_model(self, role: Role, use_secondary: bool = False) -> ModelSelection:
        """Return provider/model for a given role."""
        if role == Role.PLANNER:
            return ModelSelection(provider="openai", model="gpt-4o")
        if role == Role.CODEREVIEW:
            return ModelSelection(provider="anthropic", model="claude-3-sonnet-20240229")
        if role == Role.SOLVER:
            if use_secondary:
                return ModelSelection(provider="gemini", model="gemini-1.5-pro")
            return ModelSelection(provider="openai", model="gpt-4o-mini")
        if role == Role.SUMMARIZER:
            return ModelSelection(provider="openai", model="gpt-4o-mini")
        return ModelSelection(provider="openai", model="gpt-4o-mini")

    def _ensure_openai(self):
        from openai import OpenAI

        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    def _call_openai(
        self,
        model: str,
        prompt: str,
        system_message: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        client = self._ensure_openai()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        text = response.choices[0].message.content
        usage = response.usage
        return {
            "text": text,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens
        }

    def _call_anthropic(
        self,
        model: str,
        prompt: str,
        system_message: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        import importlib
        if importlib.util.find_spec("anthropic") is None:
            raise ValueError("anthropic package not installed for Claude routing")
        import anthropic

        if not getattr(settings, "ANTHROPIC_API_KEY", None):
            raise ValueError("ANTHROPIC_API_KEY is required for Claude routing")

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=model,
            system=system_message,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join([block.text for block in message.content])
        usage = message.usage
        total_tokens = getattr(usage, "output_tokens", 0) + getattr(usage, "input_tokens", 0)
        return {
            "text": text,
            "prompt_tokens": getattr(usage, "input_tokens", 0),
            "completion_tokens": getattr(usage, "output_tokens", 0),
            "total_tokens": total_tokens
        }

    def _call_gemini(
        self,
        model: str,
        prompt: str,
        system_message: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        import importlib
        if importlib.util.find_spec("google.generativeai") is None:
            raise ValueError("google-generativeai package not installed for Gemini routing")
        import google.generativeai as genai

        if not getattr(settings, "GEMINI_API_KEY", None):
            raise ValueError("GEMINI_API_KEY is required for Gemini routing")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model_client = genai.GenerativeModel(model)
        completion = model_client.generate_content(
            [{"role": "user", "parts": [prompt]}],
            generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            system_instruction=system_message
        )
        text = completion.text
        usage = getattr(completion, "usage_metadata", None)
        total_tokens = getattr(usage, "total_token_count", 0) if usage else 0
        return {
            "text": text,
            "prompt_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
            "completion_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
            "total_tokens": total_tokens
        }

    def invoke(
        self,
        prompt: str,
        system_message: str = "You are a security testing assistant.",
        role: Role = Role.VALIDATOR,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        use_secondary: bool = False
    ) -> str:
        """
        Execute a routed LLM call and audit the result.
        """
        selection = self._select_model(role, use_secondary=use_secondary)
        start = time.time()

        if selection.provider == "openai":
            result = self._call_openai(selection.model, prompt, system_message, temperature, max_tokens)
        elif selection.provider == "anthropic":
            result = self._call_anthropic(selection.model, prompt, system_message, temperature, max_tokens)
        elif selection.provider == "gemini":
            result = self._call_gemini(selection.model, prompt, system_message, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider {selection.provider}")

        duration_ms = int((time.time() - start) * 1000)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        response_hash = hashlib.sha256(result["text"].encode()).hexdigest()

        # Persist audit log of the call
        self.db_client.log_llm_call(
            run_id=self.run_id,
            agent_id=self.agent_id,
            provider=selection.provider,
            model=selection.model,
            role=role.value,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            policy_version=self.policy_version,
            tokens_est=result.get("total_tokens", 0),
            latency_ms=duration_ms
        )

        return result["text"]
