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


class DefinitionAgent:
    """Enhanced AI agent for generating definitions with robust error handling"""

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
                name="DefinitionAgent",
                model=model,
                instructions=f"""You are a helpful assistant that provides clear, concise definitions.
                
                Rules:
                1. Provide simple, accurate definitions
                2. Keep responses under {self.config.MAX_DEFINITION_LENGTH} words
                3. Use simple language that anyone can understand
                4. If the text is unclear or not a word/phrase, explain what it appears to be
                5. Always provide a response, even for unclear input
                """,
            )

            self.logger.info(
                "AI agent initialized successfully (model=%s, base_url=%s, max_def_len=%s)",
                self.config.MODEL_NAME,
                self.config.BASE_URL,
                self.config.MAX_DEFINITION_LENGTH,
            )

        except Exception as e:
            self.logger.warning(f"Failed to initialize AI agent: {e}")
            self.agent = None

    def is_available(self) -> bool:
        """Check if the agent is available for use"""
        return self.agent is not None and HAS_AI_AGENTS and bool(self.config.API_KEY)

    async def define_async(self, text: str) -> str:
        """Get definition asynchronously with comprehensive error handling"""
        if not self.is_available():
            return "AI service not available. Please check your API key configuration."

        if not text or not text.strip():
            return "No text provided for definition."

        # Sanitize input
        text = text.strip()[:500]  # Limit input length

        try:
            result = await asyncio.wait_for(
                cast(Any, _agents).Runner.run(self.agent, f'Define: "{text}"'),
                timeout=30.0,  # 30 second timeout
            )

            definition = result.final_output

            if not definition or not definition.strip():
                return f"Unable to generate definition for: {text}"

            # Ensure definition is within length limits
            if len(definition) > self.config.MAX_DEFINITION_LENGTH * 10:  # Character limit
                definition = definition[: self.config.MAX_DEFINITION_LENGTH * 10] + "..."

            return definition.strip()

        except asyncio.TimeoutError:
            self.logger.info("AI request timed out")
            return f"Request timed out. Unable to define: {text}"

        except Exception as e:
            print(f"AI agent error: {e}")
            return f"Error getting definition for: {text}"

    def define(self, text: str) -> str:
        """Synchronous wrapper for definition generation"""
        if not HAS_AI_AGENTS:
            return (
                "AI agents library not available. Please install the required dependencies.\n\n"
                f"You requested a definition for: {text}"
            )

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.define_async(text))
        except Exception as e:
            self.logger.error(f"Error in synchronous define: {e}")
            return f"Failed to get definition for: {text}"
        finally:
            try:
                if loop:
                    loop.close()
            except Exception:
                pass
