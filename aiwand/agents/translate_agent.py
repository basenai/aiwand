import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Optional, cast

from aiwand.config import Config

# AI agent imports and availability flag
_agents: Optional[Any] = None
_AsyncOpenAI: Optional[Any] = None
try:  # pragma: no cover - optional dependency
    import agents as _agents_mod
    from openai import AsyncOpenAI as _AsyncOpenAI_t
    _agents = _agents_mod
    _AsyncOpenAI = _AsyncOpenAI_t
    HAS_AI_AGENTS = True
except Exception:  # pragma: no cover
    HAS_AI_AGENTS = False

if TYPE_CHECKING:  # typing-only imports
    from agents import Agent, OpenAIChatCompletionsModel, Runner  # noqa: F401
    from openai import AsyncOpenAI  # noqa: F401


class TranslateAgent:
    """AI agent for translating text between languages"""

    # Common languages for translation
    LANGUAGES = {
        "English": "en",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Italian": "it",
        "Portuguese": "pt",
        "Russian": "ru",
        "Japanese": "ja",
        "Chinese": "zh",
        "Korean": "ko",
        "Arabic": "ar",
        "Hindi": "hi",
        "Dutch": "nl",
        "Swedish": "sv",
        "Turkish": "tr",
        "Urdu": "ur",
    }

    def __init__(self, config: Config):
        self.config = config
        self.agent: Optional[Any] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the AI agent with proper error handling"""
        if not HAS_AI_AGENTS:
            self.logger.info("AI agents library not available")
            return

        if not self.config.API_KEY:
            self.logger.info("API key not configured")
            return

        try:
            set_tracing_disabled: Callable[[bool], None]
            if _agents and hasattr(_agents, "set_tracing_disabled"):
                set_tracing_disabled = cast(Callable[[bool], None], _agents.set_tracing_disabled)
            else:
                def set_tracing_disabled(_flag: bool) -> None:
                    return None

            set_tracing_disabled(True)
            # Cast optional imports to Any for safe usage
            async_client_type = cast(Any, _AsyncOpenAI)
            agents_mod = cast(Any, _agents)

            client = async_client_type(
                api_key=self.config.API_KEY,
                base_url=self.config.BASE_URL,
            )
            model = agents_mod.OpenAIChatCompletionsModel(
                model=self.config.MODEL_NAME,
                openai_client=client,
            )

            self.agent = agents_mod.Agent(
                name="TranslateAgent",
                model=model,
                instructions="""You are a professional translator that provides accurate, high-quality translations between languages.
                
                Rules for translation:
                1. Translate the text accurately while preserving the original meaning
                2. Maintain the tone, style, and formality of the original text
                3. Preserve formatting, punctuation, and special characters when appropriate
                4. Handle idioms, cultural references, and specialized terminology correctly
                5. If a term has no direct translation, provide the most appropriate equivalent
                6. For ambiguous terms, select the translation that best fits the context
                7. Ensure the translation is natural and fluent in the target language
                8. Do not add, remove, or modify content beyond what's necessary for translation
                
                Output Format:
                - Provide ONLY the translation in the target language's native script
                - Follow this with a romanized version (transliteration) on a new line
                - Do not include any explanations, notes, headers, or other text
                - Do not include labels like "Translation:" or "Romanized:"
                - Just output the translation followed by the romanization
                """,
            )

            self.logger.info("Translate agent initialized successfully")

        except Exception as e:
            self.logger.warning(f"Failed to initialize AI translate agent: {e}")
            self.agent = None

    def is_available(self) -> bool:
        """Check if the agent is available for use"""
        return self.agent is not None and HAS_AI_AGENTS and bool(self.config.API_KEY)

    async def translate_async(
        self, text: str, source_lang: str = "auto", target_lang: str = "English"
    ) -> str:
        """Translate text asynchronously with comprehensive error handling"""
        if not self.is_available():
            return "AI service not available. Please check your API key configuration."

        if not text or not text.strip():
            return "No text provided for translation."

        # Sanitize input
        text = text.strip()[:2500]  # Limit input length

        # Format the translation prompt based on source language
        if source_lang.lower() == "auto":
            prompt = f'''Translate the following text to {target_lang}: "{text}"
            
            Provide ONLY the translation in the following format:
            1. The translation in the native script of {target_lang}
            2. The romanized version (transliteration) to help with pronunciation
            
            Do not include any explanations, notes, or other text. Just the translation and romanization.'''
        else:
            prompt = f'''Translate the following text from {source_lang} to {target_lang}: "{text}"
            
            Provide ONLY the translation in the following format:
            1. The translation in the native script of {target_lang}
            2. The romanized version (transliteration) to help with pronunciation
            
            Do not include any explanations, notes, or other text. Just the translation and romanization.'''

        try:
            result = await asyncio.wait_for(
                cast(Any, _agents).Runner.run(self.agent, prompt),
                timeout=30.0,
            )

            translation = result.final_output

            if not translation or not translation.strip():
                return f"Unable to translate text to {target_lang}."

            return translation.strip()

        except asyncio.TimeoutError:
            print(f"AI translate request timed out to {target_lang}")
            return f"Request timed out. Unable to translate to {target_lang}."

        except Exception as e:
            print(f"AI translate agent error: {e}")
            return f"Error translating to {target_lang}: {str(e)}"

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "English") -> str:
        """Synchronous wrapper for translating text"""
        if not HAS_AI_AGENTS:
            return "AI agents library not available. Please install the required dependencies."

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.translate_async(text, source_lang, target_lang))
        except Exception as e:
            self.logger.error(f"Error in synchronous translate: {e}")
            return f"Failed to translate text to {target_lang}: {str(e)}"
        finally:
            try:
                if loop:
                    loop.close()
            except Exception:
                pass
