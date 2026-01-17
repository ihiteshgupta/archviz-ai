"""Room renderer for single room rendering with DALL-E."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from core.azure.openai_service import AzureOpenAIService
from core.dwg_parser.elements import Room
from core.materials.library import MaterialLibrary
from core.materials.types import MaterialAssignment

from .prompt_builder import PromptBuilder
from .types import RenderConfig, RenderError, RenderResult

logger = logging.getLogger(__name__)


class RenderException(Exception):
    """Base exception for render errors."""

    def __init__(self, message: str, error_type: str = "unknown", retryable: bool = False):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


class ContentPolicyError(RenderException):
    """Content policy violation error."""

    def __init__(self, message: str):
        super().__init__(message, error_type="content_policy", retryable=False)


class RateLimitError(RenderException):
    """Rate limit exceeded error."""

    def __init__(self, message: str):
        super().__init__(message, error_type="rate_limit", retryable=True)


class TimeoutError(RenderException):
    """Request timeout error."""

    def __init__(self, message: str):
        super().__init__(message, error_type="timeout", retryable=True)


class RoomRenderer:
    """Renders individual rooms using DALL-E."""

    # Retry delays in seconds (exponential backoff)
    RETRY_DELAYS = [2, 5, 10]

    def __init__(
        self,
        openai_service: AzureOpenAIService,
        library: MaterialLibrary,
        max_retries: int = 2,
    ):
        """
        Initialize the room renderer.

        Args:
            openai_service: Azure OpenAI service for DALL-E
            library: Material library for building prompts
            max_retries: Maximum number of retries for retryable errors
        """
        self.openai_service = openai_service
        self.library = library
        self.prompt_builder = PromptBuilder(library)
        self.max_retries = max_retries

    async def render_room(
        self,
        room: Room,
        assignments: List[MaterialAssignment],
        config: RenderConfig,
    ) -> RenderResult:
        """
        Render a single room.

        Args:
            room: Room to render
            assignments: Material assignments for the room
            config: Render configuration

        Returns:
            RenderResult with image URL and metadata

        Raises:
            RenderException: If rendering fails after all retries
        """
        # Build prompt from room and materials
        prompt = self.prompt_builder.build_prompt(room, assignments, config)

        return await self._render_with_retry(room, prompt, config)

    async def render_with_custom_prompt(
        self,
        room: Room,
        custom_prompt: str,
        config: RenderConfig,
    ) -> RenderResult:
        """
        Render a room with a custom user prompt.

        Args:
            room: Room context
            custom_prompt: User's custom prompt
            config: Render configuration

        Returns:
            RenderResult with image URL and metadata

        Raises:
            RenderException: If rendering fails after all retries
        """
        # Build prompt using custom text with room context
        prompt = self.prompt_builder.build_custom_prompt(room, custom_prompt, config)

        return await self._render_with_retry(room, prompt, config)

    async def _render_with_retry(
        self,
        room: Room,
        prompt: str,
        config: RenderConfig,
    ) -> RenderResult:
        """Execute render with retry logic for retryable errors."""
        last_error: Optional[RenderException] = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self._execute_render(room, prompt, config)

            except RenderException as e:
                last_error = e
                logger.warning(
                    f"Render attempt {attempt + 1}/{self.max_retries + 1} failed "
                    f"for room {room.id}: {e}"
                )

                if not e.retryable or attempt >= self.max_retries:
                    raise

                # Wait before retry with exponential backoff
                delay = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise RenderException("Render failed for unknown reason")

    async def _execute_render(
        self,
        room: Room,
        prompt: str,
        config: RenderConfig,
    ) -> RenderResult:
        """Execute a single render request."""
        room_name = room.name or room.room_type or f"Room {room.id}"

        logger.info(f"Rendering room: {room_name}")
        logger.debug(f"Prompt: {prompt[:200]}...")

        try:
            # Call DALL-E via Azure OpenAI service
            result = await self.openai_service.generate_concept_render(
                prompt=prompt,
                style="photorealistic",
                size=config.size,
                quality=config.quality,
            )

            return RenderResult(
                room_id=room.id,
                room_name=room_name,
                image_url=result["url"],
                revised_prompt=result.get("revised_prompt", prompt),
                created_at=datetime.now(),
                config=config,
            )

        except Exception as e:
            error_str = str(e).lower()

            # Classify the error
            if "content_policy" in error_str or "safety" in error_str:
                raise ContentPolicyError(f"Content policy violation: {e}")
            elif "rate" in error_str or "limit" in error_str or "429" in error_str:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            elif "timeout" in error_str or "timed out" in error_str:
                raise TimeoutError(f"Request timed out: {e}")
            else:
                # Check if it's a retryable server error
                if "500" in error_str or "502" in error_str or "503" in error_str:
                    raise RenderException(str(e), error_type="server_error", retryable=True)
                raise RenderException(str(e), error_type="unknown", retryable=False)

    def create_error(
        self,
        room: Room,
        exception: Exception,
    ) -> RenderError:
        """
        Create a RenderError from an exception.

        Args:
            room: Room that failed to render
            exception: The exception that occurred

        Returns:
            RenderError with appropriate details
        """
        room_name = room.name or room.room_type or f"Room {room.id}"

        if isinstance(exception, RenderException):
            return RenderError(
                room_id=room.id,
                room_name=room_name,
                error_type=exception.error_type,
                message=str(exception),
                retryable=exception.retryable,
            )

        return RenderError(
            room_id=room.id,
            room_name=room_name,
            error_type="unknown",
            message=str(exception),
            retryable=False,
        )

    async def render_room_safe(
        self,
        room: Room,
        assignments: List[MaterialAssignment],
        config: RenderConfig,
    ) -> Tuple[Optional[RenderResult], Optional[RenderError]]:
        """
        Render a room without raising exceptions.

        Args:
            room: Room to render
            assignments: Material assignments
            config: Render configuration

        Returns:
            Tuple of (result, error) - one will be None
        """
        try:
            result = await self.render_room(room, assignments, config)
            return result, None
        except Exception as e:
            error = self.create_error(room, e)
            return None, error
