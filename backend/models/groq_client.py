"""
Groq API Client for AURA.
Used to offload local open-source models (like Gemma) to lightning-fast cloud LPUs.
"""

import requests
from typing import Dict, Any, Optional, List
from loguru import logger

from backend.config.settings import settings


class GroqClient:
    """Client for interacting with Groq-hosted open source models."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.timeout = 30

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> str:
        """
        Generate text completion from Groq API.
        
        Args:
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        if not self.api_key:
            logger.error("Groq API key not found.")
            raise ValueError("GROQ_API_KEY environment variable is missing.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
            
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            logger.debug(f"Groq request: {self.model} | prompt length: {len(prompt)}")
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            generated_text = result["choices"][0]["message"]["content"]
            
            logger.debug(f"Groq response: {len(generated_text)} chars")
            return generated_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Groq error details: {e.response.text}")
            raise

groq_client = GroqClient()
