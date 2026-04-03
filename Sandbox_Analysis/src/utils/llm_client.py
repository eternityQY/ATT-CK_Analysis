import logging
from typing import List, Dict, Optional, Any
from openai import OpenAI, OpenAIError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMClient:
    """
    LLM API Client Wrapper
    Supports OpenAI-compatible interfaces (DeepSeek, ChatGPT, etc.)
    """

    def __init__(self, api_key: str, api_base: str, model: str):
        """
        Initialize LLM Client
        
        Args:
            api_key: API Key
            api_base: API Base URL (e.g., https://api.deepseek.com)
            model: Model name (e.g., deepseek-chat)
        """
        self.model = model
        try:
            self.client = OpenAI(
                api_key=api_key,
                base_url=api_base
            )
            logger.info(f"LLM Client initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Client: {e}")
            raise

    def generate(self, prompt: str, temperature: float = 0.5, max_tokens: int = 2000) -> str:
        """
        Generate text (Single turn)
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, temperature, max_tokens)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        Multi-turn chat interface
        
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}, ...]
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            logger.error(f"API Request failed: {e}")
            return f"[Error: LLM generation failed - {str(e)}]"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "[Error: Unexpected error during generation]"