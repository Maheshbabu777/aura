"""
Ollama client for local Gemma 4 E4B model.
"""

import requests
import subprocess
import time
import os
from typing import Dict, Any, Optional, List
from loguru import logger

from backend.config.settings import settings


class OllamaClient:
    """Client for interacting with Ollama-hosted Gemma model."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = 120  # 2 minutes for model loading

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model_override: Optional[str] = None,
    ) -> str:
        """
        Generate text completion from Ollama.

        Args:
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            model_override: Use a different model for this call (e.g. 'gemma3:1b')

        Returns:
            Generated text response
        """
        url = f"{self.base_url}/api/generate"
        model = model_override or self.model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        # Only add system prompt if provided (Gemma E2B doesn't like null system)
        if system:
            payload["system"] = system

        # NOTE: num_predict causes Gemma E2B to return empty responses with certain prompts
        # Let the model use its default token limit instead

        try:
            logger.debug(f"Ollama request: {model} | prompt length: {len(prompt)}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            generated_text = result.get("response", "")

            logger.debug(f"Ollama response: {len(generated_text)} chars")
            return generated_text

        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timeout after {self.timeout}s")
            raise
        except requests.exceptions.RequestException as e:
            if "10061" in str(e) or "Connection refused" in str(e):
                logger.warning("Ollama is not running. Attempting to auto-start 'ollama serve'...")
                try:
                    # Windows specific flag to prevent command window popup
                    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
                    time.sleep(4)  # Wait for server to bind
                    
                    logger.info("Retrying Ollama request after auto-start...")
                    response = requests.post(url, json=payload, timeout=self.timeout)
                    response.raise_for_status()
                    return response.json().get("response", "")
                except Exception as start_e:
                    logger.error(f"Failed to auto-start Ollama: {start_e}")
                    raise e
            else:
                logger.error(f"Ollama request failed: {e}")
                raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Chat completion using Ollama's chat endpoint.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Assistant's response text
        """
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            logger.debug(f"Ollama chat: {self.model} | {len(messages)} messages")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            assistant_message = result.get("message", {})
            content = assistant_message.get("content", "")

            logger.debug(f"Ollama chat response: {len(content)} chars")
            return content

        except requests.exceptions.Timeout:
            logger.error(f"Ollama chat timeout after {self.timeout}s")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama chat failed: {e}")
            raise


# Singleton instance
ollama_client = OllamaClient()
