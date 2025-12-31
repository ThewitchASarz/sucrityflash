"""
LLM client wrapper supporting Llama 3.1 70B (local) and Claude 3.5 Sonnet (API).
CRITICAL: temperature=0 enforced for deterministic outputs.
"""
from abc import ABC, abstractmethod
from typing import Optional, Any
import json
import asyncio
from pydantic import BaseModel
import anthropic
from langchain_community.llms import Ollama
from langchain.schema import HumanMessage, SystemMessage
from config import settings


class LLMResponse(BaseModel):
    """Standardized LLM response."""
    content: str
    model: str
    usage: dict


class LLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[type[BaseModel]] = None,
        timeout: int = 300
    ) -> LLMResponse:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def validate_schema(self, content: str, schema: type[BaseModel]) -> tuple[bool, Optional[Any]]:
        """Validate response against Pydantic schema."""
        pass


class LlamaClient(LLMClient):
    """Llama 3.1 70B client (local via Ollama)."""

    def __init__(self):
        self.model = "llama3.1:70b"
        self.client = Ollama(
            model=self.model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.0  # CRITICAL: deterministic
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[type[BaseModel]] = None,
        timeout: int = 300
    ) -> LLMResponse:
        """Generate response from Llama 3.1 70B."""
        try:
            # Construct prompt
            full_prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>"

            # Generate with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(self.client.invoke, full_prompt),
                timeout=timeout
            )

            # Validate schema if provided
            if response_schema:
                valid, parsed = self.validate_schema(response, response_schema)
                if not valid:
                    raise ValueError(f"LLM output does not match schema: {parsed}")

            return LLMResponse(
                content=response,
                model=self.model,
                usage={"tokens": len(response) // 4}  # Approximate
            )

        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM generation timed out after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {str(e)}")

    def validate_schema(self, content: str, schema: type[BaseModel]) -> tuple[bool, Optional[Any]]:
        """Validate JSON response against Pydantic schema."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = content.strip()
            if json_str.startswith("```json"):
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif json_str.startswith("```"):
                json_str = json_str.split("```")[1].split("```")[0].strip()

            # Parse and validate
            data = json.loads(json_str)
            validated = schema(**data)
            return True, validated

        except (json.JSONDecodeError, ValueError) as e:
            return False, str(e)


class ClaudeClient(LLMClient):
    """Claude 3.5 Sonnet client (Anthropic API)."""

    def __init__(self):
        self.model = "claude-3-5-sonnet-20241022"
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[type[BaseModel]] = None,
        timeout: int = 300
    ) -> LLMResponse:
        """Generate response from Claude 3.5 Sonnet."""
        try:
            # Generate with timeout
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.0,  # CRITICAL: deterministic
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                ),
                timeout=timeout
            )

            content = response.content[0].text

            # Validate schema if provided
            if response_schema:
                valid, parsed = self.validate_schema(content, response_schema)
                if not valid:
                    raise ValueError(f"LLM output does not match schema: {parsed}")

            return LLMResponse(
                content=content,
                model=self.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            )

        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM generation timed out after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {str(e)}")

    def validate_schema(self, content: str, schema: type[BaseModel]) -> tuple[bool, Optional[Any]]:
        """Validate JSON response against Pydantic schema."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = content.strip()
            if json_str.startswith("```json"):
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif json_str.startswith("```"):
                json_str = json_str.split("```")[1].split("```")[0].strip()

            # Parse and validate
            data = json.loads(json_str)
            validated = schema(**data)
            return True, validated

        except (json.JSONDecodeError, ValueError) as e:
            return False, str(e)


def get_llm_client() -> LLMClient:
    """Factory function to get configured LLM client."""
    provider = settings.LLM_PROVIDER.lower()

    if provider in ["llama", "local"]:
        return LlamaClient()
    elif provider == "claude":
        return ClaudeClient()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'llama', 'local', or 'claude'.")


# Global client instance
llm_client = get_llm_client()
