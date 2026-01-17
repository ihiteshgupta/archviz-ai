"""Prompt builder for DALL-E render generation."""

from typing import Dict, List, Optional

from core.dwg_parser.elements import Room
from core.materials.library import MaterialLibrary
from core.materials.types import Material, MaterialAssignment

from .types import RenderConfig


class PromptBuilder:
    """Builds DALL-E prompts from room and material data."""

    # Lighting descriptions for different settings
    LIGHTING_DESCRIPTIONS = {
        "natural": "abundant natural daylight streaming through windows",
        "warm": "warm ambient lighting with soft golden tones",
        "cool": "cool contemporary lighting with blue undertones",
        "dramatic": "dramatic accent lighting with strong shadows and highlights",
    }

    # Time of day descriptions
    TIME_DESCRIPTIONS = {
        "day": "midday sunlight",
        "evening": "golden hour sunset light",
        "night": "evening interior lighting",
    }

    def __init__(self, library: MaterialLibrary):
        """
        Initialize the prompt builder.

        Args:
            library: Material library for looking up materials
        """
        self.library = library

    def build_prompt(
        self,
        room: Room,
        assignments: List[MaterialAssignment],
        config: RenderConfig,
    ) -> str:
        """
        Build a DALL-E prompt for rendering a room.

        Args:
            room: Room to render
            assignments: Material assignments for the room
            config: Render configuration

        Returns:
            Complete prompt string for DALL-E
        """
        # Get materials for each surface type
        materials_by_surface = self._get_materials_for_room(room.id, assignments)

        # Build the prompt sections
        room_description = self._build_room_description(room, config.style_preset)
        materials_section = self._build_materials_section(materials_by_surface)
        lighting_section = self._build_lighting_section(config)
        additional_section = self._build_additional_section(config.additional_prompt)

        # Combine into final prompt
        prompt_parts = [
            "Professional architectural interior visualization, photorealistic:",
            "",
            room_description,
            "",
            materials_section,
            "",
            lighting_section,
        ]

        if additional_section:
            prompt_parts.extend(["", additional_section])

        prompt_parts.extend([
            "",
            "Interior design magazine quality, realistic textures, 8K detail.",
        ])

        return "\n".join(prompt_parts)

    def _get_materials_for_room(
        self,
        room_id: str,
        assignments: List[MaterialAssignment],
    ) -> Dict[str, Material]:
        """Get materials assigned to a room, organized by surface type."""
        materials_by_surface: Dict[str, Material] = {}

        for assignment in assignments:
            # Match by room_id or by surface_id containing room_id
            if assignment.room_id == room_id or assignment.surface_id.startswith(f"{room_id}_"):
                material = self.library.get(assignment.material_id)
                if material:
                    materials_by_surface[assignment.surface_type] = material

        return materials_by_surface

    def _build_room_description(self, room: Room, style: str) -> str:
        """Build the room description section."""
        room_type = room.room_type if room.room_type != "generic" else room.name or "room"
        area = round(room.area, 1)
        return f"{room_type.title()} ({area} sq m), {style} style"

    def _build_materials_section(self, materials: Dict[str, Material]) -> str:
        """Build the materials section of the prompt."""
        if not materials:
            return "Materials: Contemporary finishes"

        lines = ["Materials:"]

        # Order: floor, walls, ceiling, then others
        surface_order = ["floor", "wall", "ceiling", "trim", "accent"]

        for surface in surface_order:
            if surface in materials:
                mat = materials[surface]
                lines.append(f"- {surface.title()}: {mat.name}")

        # Add any remaining surfaces not in the order
        for surface, mat in materials.items():
            if surface not in surface_order:
                lines.append(f"- {surface.title()}: {mat.name}")

        return "\n".join(lines)

    def _build_lighting_section(self, config: RenderConfig) -> str:
        """Build the lighting section of the prompt."""
        lighting_desc = self.LIGHTING_DESCRIPTIONS.get(config.lighting, config.lighting)
        time_desc = self.TIME_DESCRIPTIONS.get(config.time_of_day, config.time_of_day)
        return f"Lighting: {lighting_desc}, {time_desc}"

    def _build_additional_section(self, additional_prompt: str) -> str:
        """Build the additional user prompt section."""
        if not additional_prompt:
            return ""
        return additional_prompt.strip()

    def build_custom_prompt(
        self,
        room: Room,
        custom_prompt: str,
        config: RenderConfig,
    ) -> str:
        """
        Build a prompt using custom user text with room context.

        Args:
            room: Room context
            custom_prompt: User's custom prompt
            config: Render configuration

        Returns:
            Complete prompt string for DALL-E
        """
        room_type = room.room_type if room.room_type != "generic" else room.name or "room"
        area = round(room.area, 1)

        prompt_parts = [
            "Professional architectural interior visualization, photorealistic:",
            "",
            f"{room_type.title()} ({area} sq m):",
            "",
            custom_prompt.strip(),
            "",
            self._build_lighting_section(config),
            "",
            "Interior design magazine quality, realistic textures, 8K detail.",
        ]

        return "\n".join(prompt_parts)

    def build_minimal_prompt(
        self,
        room_type: str,
        style: str,
        materials_description: Optional[str] = None,
    ) -> str:
        """
        Build a minimal prompt without Room object.

        Args:
            room_type: Type of room (e.g., "living room", "bedroom")
            style: Design style (e.g., "modern", "rustic")
            materials_description: Optional materials description

        Returns:
            Complete prompt string for DALL-E
        """
        prompt_parts = [
            "Professional architectural interior visualization, photorealistic:",
            "",
            f"{room_type.title()}, {style} style",
            "",
        ]

        if materials_description:
            prompt_parts.append(materials_description)
            prompt_parts.append("")

        prompt_parts.extend([
            "Natural daylight, midday sun",
            "",
            "Interior design magazine quality, realistic textures, 8K detail.",
        ])

        return "\n".join(prompt_parts)
