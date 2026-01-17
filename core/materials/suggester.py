"""AI-powered material suggestion using Azure OpenAI."""

import json
from typing import Dict, List, Optional

from core.azure.openai_service import AzureOpenAIService
from core.dwg_parser.elements import Room
from core.dwg_parser.parser import FloorPlan

from .library import MaterialLibrary
from .presets import StylePreset, get_preset
from .types import Material, MaterialAssignment


# Default material assignments per room type when AI fails
DEFAULT_MATERIALS: Dict[str, Dict[str, str]] = {
    "living": {
        "floor": "wood_oak_natural",
        "wall": "paint_white",
        "ceiling": "paint_white",
    },
    "bedroom": {
        "floor": "wood_oak_natural",
        "wall": "paint_beige",
        "ceiling": "paint_white",
    },
    "kitchen": {
        "floor": "ceramic_white_tile",
        "wall": "paint_white",
        "ceiling": "paint_white",
    },
    "bathroom": {
        "floor": "ceramic_white_tile",
        "wall": "ceramic_subway_tile",
        "ceiling": "paint_white",
    },
    "dining": {
        "floor": "wood_oak_natural",
        "wall": "paint_white",
        "ceiling": "paint_white",
    },
    "office": {
        "floor": "wood_oak_natural",
        "wall": "paint_gray",
        "ceiling": "paint_white",
    },
    "hallway": {
        "floor": "wood_oak_natural",
        "wall": "paint_white",
        "ceiling": "paint_white",
    },
    "generic": {
        "floor": "wood_oak_natural",
        "wall": "paint_white",
        "ceiling": "paint_white",
    },
}


class MaterialSuggester:
    """AI-powered material suggestion based on room type and style."""

    def __init__(
        self,
        library: MaterialLibrary,
        openai_service: Optional[AzureOpenAIService] = None,
    ):
        """
        Initialize the material suggester.

        Args:
            library: Material library to select from
            openai_service: Azure OpenAI service for AI suggestions
        """
        self.library = library
        self.openai = openai_service

    async def suggest(
        self,
        floor_plan: FloorPlan,
        style: StylePreset | str,
    ) -> Dict[str, MaterialAssignment]:
        """
        Suggest materials for all surfaces in a floor plan.

        Args:
            floor_plan: The floor plan to suggest materials for
            style: Style preset or preset name

        Returns:
            Dict mapping surface_id to MaterialAssignment
        """
        if isinstance(style, str):
            style = get_preset(style)

        assignments: Dict[str, MaterialAssignment] = {}

        # Process each room
        for room in floor_plan.rooms:
            room_assignments = await self.suggest_for_room(room, style)

            for surface_type, material in room_assignments.items():
                surface_id = f"{room.id}_{surface_type}"
                assignments[surface_id] = MaterialAssignment(
                    surface_id=surface_id,
                    material_id=material.id,
                    room_id=room.id,
                    surface_type=surface_type,
                )

        # Add default assignments for exterior walls and shared elements
        default_wall = self._get_default_for_style("wall", style)
        if default_wall:
            assignments["wall_exterior"] = MaterialAssignment(
                surface_id="wall_exterior",
                material_id=default_wall.id,
                surface_type="wall",
            )
            assignments["wall_interior"] = MaterialAssignment(
                surface_id="wall_interior",
                material_id=default_wall.id,
                surface_type="wall",
            )

        return assignments

    async def suggest_for_room(
        self,
        room: Room,
        style: StylePreset | str,
    ) -> Dict[str, Material]:
        """
        Suggest materials for a single room.

        Args:
            room: The room to suggest materials for
            style: Style preset or preset name

        Returns:
            Dict mapping surface type (floor, wall, ceiling) to Material
        """
        if isinstance(style, str):
            style = get_preset(style)

        # Try AI suggestion first
        if self.openai:
            try:
                ai_result = await self._ai_suggest(room, style)
                if ai_result:
                    return ai_result
            except Exception:
                pass  # Fall back to defaults

        # Fall back to rule-based defaults
        return self._get_defaults_for_room(room, style)

    async def _ai_suggest(
        self,
        room: Room,
        style: StylePreset,
    ) -> Optional[Dict[str, Material]]:
        """Use AI to suggest materials."""
        if not self.openai:
            return None

        # Get available materials for each surface type
        floor_materials = self.library.search(suitable_for="floor", style=style.id)
        wall_materials = self.library.search(suitable_for="wall", style=style.id)
        ceiling_materials = self.library.search(suitable_for="ceiling", style=style.id)

        # If no style-specific materials, get all suitable ones
        if not floor_materials:
            floor_materials = self.library.search(suitable_for="floor")
        if not wall_materials:
            wall_materials = self.library.search(suitable_for="wall")
        if not ceiling_materials:
            ceiling_materials = self.library.search(suitable_for="ceiling")

        if not floor_materials and not wall_materials and not ceiling_materials:
            return None

        # Build prompt
        prompt = self._build_prompt(room, style, floor_materials, wall_materials, ceiling_materials)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an interior design assistant. Select the most appropriate "
                    "materials for architectural surfaces based on room type and style. "
                    "Return ONLY a JSON object with the selected material IDs."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        # Get AI response
        response = await self.openai.chat_completion(
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent selections
            max_tokens=200,
        )

        # Parse response
        return self._parse_ai_response(response, floor_materials, wall_materials, ceiling_materials)

    def _build_prompt(
        self,
        room: Room,
        style: StylePreset,
        floor_materials: List[Material],
        wall_materials: List[Material],
        ceiling_materials: List[Material],
    ) -> str:
        """Build the prompt for AI material suggestion."""
        room_type = room.room_type or "generic"
        room_area = round(room.area, 1) if room.area else "unknown"

        floor_ids = [m.id for m in floor_materials[:10]]  # Limit to 10 options
        wall_ids = [m.id for m in wall_materials[:10]]
        ceiling_ids = [m.id for m in ceiling_materials[:10]]

        return f"""Room: {room_type.title()} ({room_area} sq m)
Style: {style.name} - {style.prompt_description}

Select the best material ID for each surface from the available options.

Available floor materials: {', '.join(floor_ids)}
Available wall materials: {', '.join(wall_ids)}
Available ceiling materials: {', '.join(ceiling_ids)}

Return a JSON object with exactly these keys: "floor", "wall", "ceiling"
Example: {{"floor": "wood_oak_natural", "wall": "paint_white", "ceiling": "paint_white"}}"""

    def _parse_ai_response(
        self,
        response: str,
        floor_materials: List[Material],
        wall_materials: List[Material],
        ceiling_materials: List[Material],
    ) -> Optional[Dict[str, Material]]:
        """Parse AI response and return materials."""
        try:
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code blocks
                lines = response.split("\n")
                response = "\n".join(
                    line for line in lines if not line.startswith("```")
                )

            data = json.loads(response)

            result = {}

            # Validate and get materials
            floor_id = data.get("floor")
            wall_id = data.get("wall")
            ceiling_id = data.get("ceiling")

            floor_map = {m.id: m for m in floor_materials}
            wall_map = {m.id: m for m in wall_materials}
            ceiling_map = {m.id: m for m in ceiling_materials}

            if floor_id and floor_id in floor_map:
                result["floor"] = floor_map[floor_id]
            elif floor_materials:
                result["floor"] = floor_materials[0]

            if wall_id and wall_id in wall_map:
                result["wall"] = wall_map[wall_id]
            elif wall_materials:
                result["wall"] = wall_materials[0]

            if ceiling_id and ceiling_id in ceiling_map:
                result["ceiling"] = ceiling_map[ceiling_id]
            elif ceiling_materials:
                result["ceiling"] = ceiling_materials[0]

            return result if result else None

        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _get_defaults_for_room(
        self,
        room: Room,
        style: StylePreset,
    ) -> Dict[str, Material]:
        """Get default materials for a room based on room type and style."""
        room_type = (room.room_type or "generic").lower()

        # Get default material IDs for this room type
        defaults = DEFAULT_MATERIALS.get(room_type, DEFAULT_MATERIALS["generic"])

        result = {}

        for surface_type in ["floor", "wall", "ceiling"]:
            # Try to get from style preferences first
            material = self._get_default_for_style(surface_type, style)

            # Fall back to room type defaults
            if not material:
                default_id = defaults.get(surface_type)
                if default_id:
                    material = self.library.get(default_id)

            # Fall back to any suitable material
            if not material:
                suitable = self.library.search(suitable_for=surface_type)
                if suitable:
                    material = suitable[0]

            # Ultimate fallback - create a placeholder
            if not material:
                material = Material(
                    id=f"default_{surface_type}",
                    name=f"Default {surface_type.title()}",
                    category="generic",
                    base_color=(0.8, 0.8, 0.8),
                )

            result[surface_type] = material

        return result

    def _get_default_for_style(
        self,
        surface_type: str,
        style: StylePreset,
    ) -> Optional[Material]:
        """Get a default material for a surface type based on style."""
        # Search for materials matching style
        materials = self.library.search(suitable_for=surface_type, style=style.id)

        if materials:
            return materials[0]

        # Try materials from preferred categories
        for category in style.material_affinity:
            materials = self.library.search(
                category=category, suitable_for=surface_type
            )
            if materials:
                return materials[0]

        return None
