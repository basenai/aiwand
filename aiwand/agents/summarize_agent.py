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


class SummarizeAgent:
    """AI agent for summarizing text"""

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
                name="SummarizeAgent",
                model=model,
                instructions="""You are a helpful assistant that provides high-quality, concise summaries of text.
                
                Rules for summarizing:
                1. Create a powerful, concise summary that covers all key points
                2. Maintain the original meaning and important details
                3. Organize information logically and clearly
                4. Highlight the most important concepts, findings, or arguments
                5. Remove redundancy and unnecessary details
                6. Keep the summary between 15-25% of the original length
                7. For very short texts, provide a more condensed version that captures the essence
                """,
            )

            self.logger.info("Summarize agent initialized successfully")

        except Exception as e:
            self.logger.warning(f"Failed to initialize AI summarize agent: {e}")
            self.agent = None

    def is_available(self) -> bool:
        """Check if the agent is available for use"""
        return self.agent is not None and HAS_AI_AGENTS and bool(self.config.API_KEY)

    async def summarize_async(self, text: str) -> str:
        """Summarize text asynchronously with comprehensive error handling"""
        if not self.is_available():
            return "AI service not available. Please check your API key configuration."

        if not text or not text.strip():
            return "No text provided for summarizing."

        # Sanitize input
        text = text.strip()[:2500]  # Limit input length but allow longer text for summarization

        try:
            result = await asyncio.wait_for(
                cast(Any, _agents).Runner.run(self.agent, f'Summarize the following text: "{text}"'),
                timeout=30.0,
            )

            summary = result.final_output

            if not summary or not summary.strip():
                return "Unable to generate summary."

            return summary.strip()

        except asyncio.TimeoutError:
            self.logger.info("AI summarize request timed out")
            return "Request timed out. Unable to summarize text."

        except Exception as e:
            print(f"AI summarize agent error: {e}")
            return f"Error summarizing text: {str(e)}"

    def summarize(self, text: str) -> str:
        """Synchronous wrapper for summarizing text"""
        if not HAS_AI_AGENTS:
            return "AI agents library not available. Please install the required dependencies."

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.summarize_async(text))
        except Exception as e:
            self.logger.error(f"Error in synchronous summarize: {e}")
            return f"Failed to summarize text: {str(e)}"
        finally:
            try:
                if loop:
                    loop.close()
            except Exception:
                pass
