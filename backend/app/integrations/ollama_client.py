"""Ollama client and model adapter for local open-weight model inference (Gemma 2 / CodeGemma).

Supports structured JSON generation, model availability checks, model pulling,
and token count estimation for Hacktoberfest 2026 local AI development.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type
import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("outofoffice.ollama")


class OllamaClient:
    """Client interface to local Ollama inference daemon."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = settings.DEFAULT_MODEL
        self.fallback_model = settings.FALLBACK_MODEL
        self.code_model = settings.CODE_SPECIALIST_MODEL
        self.timeout = settings.MODEL_TIMEOUT_SECONDS

    def is_running(self) -> bool:
        """Checks if the local Ollama daemon is active and reachable."""
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def is_running_async(self) -> bool:
        """Asynchronously checks if the local Ollama daemon is reachable."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    def list_local_models(self) -> List[str]:
        """Lists all downloaded models available in local Ollama storage."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name", "") for m in data.get("models", [])]
                return []
        except Exception as e:
            logger.warning(f"Failed to fetch models from Ollama: {e}")
            return []

    def ensure_model_available(self, model_name: Optional[str] = None) -> bool:
        """Verifies if the specified model is present locally."""
        target = model_name or self.default_model
        models = self.list_local_models()
        # Check direct or prefix match (e.g. gemma2:9b matching gemma2:9b or gemma2:latest)
        target_clean = target.split(":")[0]
        return any(target == m or m.startswith(target_clean) for m in models)

    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        format_json: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """Asynchronously queries Ollama for text/JSON generation."""
        target_model = model or self.default_model
        temp = temperature if temperature is not None else settings.MODEL_TEMPERATURE

        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if format_json:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data = res.json()
                return data.get("response", "").strip()
            except httpx.ConnectError:
                logger.error("Could not connect to Ollama. Please make sure Ollama is running (`ollama serve`).")
                raise RuntimeError(
                    f"Ollama daemon is not running at {self.base_url}. "
                    "Please start Ollama locally to run OutOfOffice AI."
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Model '{target_model}' not found in Ollama (404). Looking for available local fallback...")
                    local_models = self.list_local_models()
                    fallback_target = None
                    for cand in [settings.DEFAULT_MODEL, settings.FALLBACK_MODEL] + local_models:
                        if cand and any(cand == m or m.startswith(cand.split(":")[0]) for m in local_models):
                            fallback_target = cand
                            break
                    if fallback_target and fallback_target != target_model:
                        logger.info(f"Retrying Ollama generation with available local model '{fallback_target}'...")
                        payload["model"] = fallback_target
                        res = await client.post(f"{self.base_url}/api/generate", json=payload)
                        res.raise_for_status()
                        return res.json().get("response", "").strip()
                logger.error(f"Error generating from model {target_model}: {e}")
                raise
            except Exception as e:
                logger.error(f"Error generating from model {target_model}: {e}")
                raise

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        format_json: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """Synchronously queries Ollama for text/JSON generation."""
        target_model = model or self.default_model
        temp = temperature if temperature is not None else settings.MODEL_TEMPERATURE

        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if format_json:
            payload["format"] = "json"

        with httpx.Client(timeout=self.timeout) as client:
            try:
                res = client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data = res.json()
                return data.get("response", "").strip()
            except httpx.ConnectError:
                logger.error("Could not connect to Ollama. Please make sure Ollama is running (`ollama serve`).")
                raise RuntimeError(
                    f"Ollama daemon is not running at {self.base_url}. "
                    "Please start Ollama locally to run OutOfOffice AI."
                )
            except Exception as e:
                logger.error(f"Error generating from model {target_model}: {e}")
                raise

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        format_json: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        """Asynchronously queries Ollama chat endpoint with a message history."""
        target_model = model or self.default_model
        temp = temperature if temperature is not None else settings.MODEL_TEMPERATURE

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temp,
            },
        }
        if format_json:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                res.raise_for_status()
                data = res.json()
                msg = data.get("message", {})
                return msg.get("content", "").strip()
            except Exception as e:
                logger.error(f"Chat API error with model {target_model}: {e}")
                raise

    async def generate_structured_async(
        self,
        prompt: str,
        schema_cls: Type[BaseModel],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BaseModel:
        """Generates and validates structured output conforming to a Pydantic schema."""
        raw_response = await self.generate_async(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            format_json=True,
        )
        try:
            parsed_json = json.loads(raw_response)
            return schema_cls.model_validate(parsed_json)
        except Exception as e:
            logger.warning(f"Raw response failed schema validation ({e}). Raw text: {raw_response}")
            # Clean possible markdown wrapping (```json ... ```)
            clean_text = raw_response.strip()
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()
            parsed_json = json.loads(clean_text)
            return schema_cls.model_validate(parsed_json)


# Global singleton Ollama client instance
ollama_client = OllamaClient()
