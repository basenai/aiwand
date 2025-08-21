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


class RewriteAgent:
    """AI agent for rewriting text in different styles"""

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
                name="RewriteAgent",
                model=model,
                instructions="""You are a helpful assistant that rewrites text in different styles.
                
                Rules:
                1. Rewrite the given text in the requested style
                2. Maintain the original meaning
                3. Keep approximately the same length
                4. Be creative but clear
                5. When a style is very different from the original tone, ensure it's still appropriate
                
                Style Definitions:
                - Simple: Rewrite in clear, short sentences. Avoid complex words. Keep it very easy to understand.
                - Technical: Rewrite to sound precise, specialized, and suitable for technical audiences.
                - Professional: Rewrite to sound polished, businesslike, and corporate.
                - Formal: Rewrite in a respectful, serious tone, avoiding contractions and casual language.
                - Normal: Rewrite in a neutral, balanced style without any strong tone.
                - Common: Rewrite using everyday language that most people use in daily conversation.
                - Grammar Fix: Correct grammar, spelling, punctuation, and clarity without changing the tone or meaning.
                """,
            )

            self.logger.info("Rewrite agent initialized successfully")

        except Exception as e:
            self.logger.warning(f"Failed to initialize AI rewrite agent: {e}")
            self.agent = None

    def is_available(self) -> bool:
        """Check if the agent is available for use"""
        return self.agent is not None and HAS_AI_AGENTS and bool(self.config.API_KEY)

    async def rewrite_async(self, text: str, style: str) -> str:
        """Rewrite text asynchronously with comprehensive error handling"""
        if not self.is_available():
            return "AI service not available. Please check your API key configuration."

        if not text or not text.strip():
            return "No text provided for rewriting."

        # Sanitize input
        text = text.strip()[:1000]  # Limit input length
        style = style.strip()[:50]  # Limit style length

        try:
            prompt = f'Rewrite the following text in a {style} style: "{text}"'
            result = await asyncio.wait_for(
                cast(Any, _agents).Runner.run(self.agent, prompt),
                timeout=30.0,
            )

            rewrite = result.final_output

            if not rewrite or not rewrite.strip():
                return f"Unable to rewrite text in {style} style."

            return rewrite.strip()

        except asyncio.TimeoutError:
            print(f"AI rewrite request timed out for style: {style}")
            return f"Request timed out. Unable to rewrite in {style} style."

        except Exception as e:
            print(f"AI rewrite agent error: {e}")
            return f"Error rewriting in {style} style: {str(e)}"

    def rewrite(self, text: str, style: str) -> str:
        """Synchronous wrapper for rewriting text"""
        if not HAS_AI_AGENTS:
            return (
                "AI agents library not available. Please install the required dependencies.\n\n"
                f"You requested to rewrite in {style} style: {text}"
            )

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.rewrite_async(text, style))
        except Exception as e:
            self.logger.error(f"Error in synchronous rewrite: {e}")
            return f"Failed to rewrite text in {style} style: {str(e)}"
        finally:
            try:
                if loop:
                    loop.close()
            except Exception:
                pass
