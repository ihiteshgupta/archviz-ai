"""AI-guided furniture placement using GPT-4."""

import json
import logging
from typing import Any, Optional

from core.azure.openai_service import AzureOpenAIService
from core.azure.config import AzureConfig


logger = logging.getLogger(__name__)


FURNITURE_PROMPT = """You are an interior design assistant. Given a room's specifications,
generate a furniture placement plan.

Room specifications:
- Type: {room_type}
- Dimensions: {width}m x {depth}m x {height}m
- Doors: {doors}
- Windows: {windows}
- Style: {style}

Return a JSON object with a "furniture" array. Each item should have:
- "type": furniture type (e.g., "bed_queen", "nightstand", "dresser", "desk", "chair")
- "position": [x, y, z] coordinates in meters (y=0 is floor)
- "rotation": rotation in degrees around Y axis

Place furniture logically:
- Beds against walls, not blocking doors
- Nightstands beside beds
- Clear pathways to doors
- Utilize natural light from windows

Return ONLY valid JSON, no explanation."""


class FurniturePlacer:
    """Generates furniture placement plans using GPT-4."""

    def __init__(self, openai_service: Optional[AzureOpenAIService] = None):
        """Initialize the FurniturePlacer.

        Args:
            openai_service: Optional AzureOpenAIService instance. If not provided,
                           a new instance will be created using environment config.
        """
        self.openai_service = openai_service

    def _get_openai_service(self) -> AzureOpenAIService:
        """Get or create the OpenAI service."""
        if self.openai_service is None:
            config = AzureConfig.from_env()
            self.openai_service = AzureOpenAIService(config)
        return self.openai_service

    async def generate_plan(self, room_context: dict[str, Any]) -> dict[str, Any]:
        """Generate furniture placement plan for a room.

        Args:
            room_context: Dictionary containing room specifications:
                - room_type: Type of room (e.g., "bedroom", "living_room")
                - dimensions: Dict with width, depth, height in meters
                - doors: List of door positions
                - windows: List of window positions
                - style: Design style (optional, defaults to "modern")

        Returns:
            Dictionary with "furniture" key containing list of furniture items,
            each with type, position [x, y, z], and rotation.
        """
        return await self._call_llm(room_context)

    async def _call_llm(self, room_context: dict[str, Any]) -> dict[str, Any]:
        """Call GPT-4 to generate furniture plan.

        Args:
            room_context: Room specifications dictionary.

        Returns:
            Parsed JSON response with furniture placement plan.
        """
        prompt = FURNITURE_PROMPT.format(
            room_type=room_context["room_type"],
            width=room_context["dimensions"]["width"],
            depth=room_context["dimensions"]["depth"],
            height=room_context["dimensions"]["height"],
            doors=json.dumps(room_context.get("doors", [])),
            windows=json.dumps(room_context.get("windows", [])),
            style=room_context.get("style", "modern"),
        )

        service = self._get_openai_service()
        response = await service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )

        return self._parse_response(response)

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parse the LLM response into structured furniture data.

        Args:
            response: Raw string response from the LLM.

        Returns:
            Parsed dictionary with furniture placement data.

        Raises:
            json.JSONDecodeError: If the response cannot be parsed as JSON.
        """
        # Clean response if wrapped in markdown code block
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Extract content between code blocks
            parts = cleaned.split("```")
            if len(parts) >= 2:
                content = parts[1]
                # Remove language identifier (e.g., "json")
                if content.startswith("json"):
                    content = content[4:]
                cleaned = content.strip()

        return json.loads(cleaned)
