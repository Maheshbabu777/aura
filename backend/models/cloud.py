"""
Google Gemini API client for complex reasoning tasks.
"""

import google.generativeai as genai
from typing import Optional, List, Dict
import time
from loguru import logger

from backend.config.settings import settings


class GeminiClient:
    """Client for Google Gemini 3 Flash API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model or settings.gemini_model

        # Configure API
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_mime_type: Optional[str] = None
    ) -> str:
        """
        Generate text completion from Gemini.
        """
        models_to_try = [
            self.model_name,       # Default: gemini-3.5-flash
            "gemini-2.5-flash",    # Working fallback
            "gemini-2.5-pro",      # Pro tier fallback
            "gemini-2.0-flash",    # Older stable fallback
            "gemini-2.0-pro",      # Older pro stable fallback
            "gemini-pro"           # Universal fallback
        ]
        
        for idx, current_model in enumerate(models_to_try):
            try:
                # Combine system and prompt if system provided
                full_prompt = prompt
                if system:
                    full_prompt = f"{system}\n\n{prompt}"

                generation_config_args = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
                if response_mime_type:
                    generation_config_args["response_mime_type"] = response_mime_type

                generation_config = genai.types.GenerationConfig(**generation_config_args)
                model_instance = genai.GenerativeModel(current_model)

                logger.info(f"Gemini request: {current_model} | prompt length: {len(full_prompt)}")

                response = model_instance.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                )

                result = response.text
                logger.info(f"Gemini response: {len(result)} chars | tokens: ~{len(result.split())}")

                # Log token usage for cost tracking
                if hasattr(response, "usage_metadata"):
                    logger.info(f"Gemini tokens: {response.usage_metadata}")

                return result

            except Exception as e:
                if "429" in str(e) and idx < len(models_to_try) - 1:
                    logger.warning(f"Hit 429 rate limit on {current_model}. Falling back to {models_to_try[idx+1]}...")
                    continue
                
                logger.error(f"Gemini request failed on {current_model}: {e}")
                if idx == len(models_to_try) - 1:
                    raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Chat completion using Gemini.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Assistant's response text
        """
        models_to_try = [
            self.model_name,       # Default: gemini-3.5-flash
            "gemini-2.5-flash",    # Working fallback
            "gemini-2.5-pro",      # Pro tier fallback
            "gemini-2.0-flash",    # Older stable fallback
            "gemini-2.0-pro",      # Older pro stable fallback
            "gemini-pro"           # Universal fallback
        ]
        
        for idx, current_model in enumerate(models_to_try):
            try:
                # Convert messages to Gemini format
                chat_history = []
                for msg in messages[:-1]:  # All but last message
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({"role": role, "parts": [msg["content"]]})

                model_instance = genai.GenerativeModel(current_model)
                # Start chat with history
                chat = model_instance.start_chat(history=chat_history)

                generation_config = genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )

                # Send last message
                last_message = messages[-1]["content"]
                logger.info(f"Gemini chat: {current_model} | {len(messages)} messages")

                response = chat.send_message(last_message, generation_config=generation_config)
                result = response.text

                logger.info(f"Gemini chat response: {len(result)} chars")

                # Log token usage
                if hasattr(response, "usage_metadata"):
                    logger.info(f"Gemini tokens: {response.usage_metadata}")

                return result

            except Exception as e:
                if "429" in str(e) and idx < len(models_to_try) - 1:
                    logger.warning(f"Hit 429 rate limit on {current_model}. Falling back to {models_to_try[idx+1]}...")
                    continue
                
                logger.error(f"Gemini chat failed on {current_model}: {e}")
                if idx == len(models_to_try) - 1:
                    raise


# Singleton instance
gemini_client = GeminiClient()
