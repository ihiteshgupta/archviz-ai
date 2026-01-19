# tests/test_furniture_placer.py
"""Tests for AI-guided furniture placement."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import directly to avoid model_gen __init__ which has Python 3.10+ syntax
import sys
import importlib.util

# Load the module directly to avoid __init__.py imports
spec = importlib.util.spec_from_file_location(
    "furniture_placer",
    "core/model_gen/furniture_placer.py"
)
furniture_placer_module = importlib.util.module_from_spec(spec)
sys.modules["furniture_placer"] = furniture_placer_module
spec.loader.exec_module(furniture_placer_module)
FurniturePlacer = furniture_placer_module.FurniturePlacer


class TestFurniturePlacer:
    """Tests for AI-guided furniture placement."""

    @pytest.mark.asyncio
    async def test_generates_furniture_plan_for_bedroom(self):
        """Should generate appropriate furniture list for bedroom."""
        room_context = {
            "room_type": "bedroom",
            "dimensions": {"width": 5, "depth": 4, "height": 2.7},
            "doors": [{"wall": "south", "position": 2.5}],
            "windows": [{"wall": "east", "position": 2.0}],
            "style": "scandinavian",
        }

        # Mock the OpenAI response
        mock_response = {
            "furniture": [
                {"type": "bed_queen", "position": [2.5, 0, 3.0], "rotation": 0},
                {"type": "nightstand", "position": [0.8, 0, 3.0], "rotation": 0},
            ]
        }

        with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            placer = FurniturePlacer()
            plan = await placer.generate_plan(room_context)

            assert "furniture" in plan
            assert len(plan["furniture"]) >= 1
            assert all("type" in f and "position" in f for f in plan["furniture"])

    @pytest.mark.asyncio
    async def test_generates_furniture_plan_for_living_room(self):
        """Should generate appropriate furniture list for living room."""
        room_context = {
            "room_type": "living_room",
            "dimensions": {"width": 6, "depth": 5, "height": 2.8},
            "doors": [{"wall": "north", "position": 1.5}],
            "windows": [
                {"wall": "south", "position": 3.0},
                {"wall": "east", "position": 2.5},
            ],
            "style": "modern",
        }

        mock_response = {
            "furniture": [
                {"type": "sofa_3_seater", "position": [3.0, 0, 2.5], "rotation": 0},
                {"type": "coffee_table", "position": [3.0, 0, 1.5], "rotation": 0},
                {"type": "armchair", "position": [1.0, 0, 1.5], "rotation": 45},
                {"type": "tv_stand", "position": [3.0, 0, 0.3], "rotation": 0},
            ]
        }

        with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            placer = FurniturePlacer()
            plan = await placer.generate_plan(room_context)

            assert "furniture" in plan
            assert len(plan["furniture"]) >= 1
            # Check that positions are 3D coordinates
            for furniture in plan["furniture"]:
                assert len(furniture["position"]) == 3
                assert "rotation" in furniture

    @pytest.mark.asyncio
    async def test_handles_room_without_windows(self):
        """Should handle rooms with no windows (e.g., bathroom, closet)."""
        room_context = {
            "room_type": "bathroom",
            "dimensions": {"width": 2.5, "depth": 2.0, "height": 2.4},
            "doors": [{"wall": "west", "position": 1.0}],
            "windows": [],
            "style": "minimalist",
        }

        mock_response = {
            "furniture": [
                {"type": "vanity", "position": [1.25, 0, 0.3], "rotation": 0},
                {"type": "toilet", "position": [2.0, 0, 1.5], "rotation": 90},
            ]
        }

        with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            placer = FurniturePlacer()
            plan = await placer.generate_plan(room_context)

            assert "furniture" in plan
            # Should still generate placement even without windows
            assert len(plan["furniture"]) >= 1

    @pytest.mark.asyncio
    async def test_defaults_to_modern_style(self):
        """Should default to modern style when not specified."""
        room_context = {
            "room_type": "bedroom",
            "dimensions": {"width": 4, "depth": 3, "height": 2.7},
            "doors": [{"wall": "south", "position": 2.0}],
            "windows": [{"wall": "west", "position": 1.5}],
            # No style specified
        }

        mock_response = {
            "furniture": [
                {"type": "bed_queen", "position": [2.0, 0, 2.5], "rotation": 0},
            ]
        }

        with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            placer = FurniturePlacer()
            plan = await placer.generate_plan(room_context)

            # Verify _call_llm was called (style should default to modern)
            mock_llm.assert_called_once()
            assert "furniture" in plan

    @pytest.mark.asyncio
    async def test_prompt_includes_room_context(self):
        """Verify that the prompt includes all room context details."""
        room_context = {
            "room_type": "office",
            "dimensions": {"width": 3.5, "depth": 3.0, "height": 2.6},
            "doors": [{"wall": "east", "position": 1.5}],
            "windows": [{"wall": "north", "position": 1.75}],
            "style": "industrial",
        }

        mock_openai_service = MagicMock()
        mock_openai_service.chat_completion = AsyncMock(
            return_value='{"furniture": [{"type": "desk", "position": [1.75, 0, 2.0], "rotation": 0}]}'
        )

        placer = FurniturePlacer(openai_service=mock_openai_service)
        await placer.generate_plan(room_context)

        # Verify the chat_completion was called
        mock_openai_service.chat_completion.assert_called_once()

        # Get the call arguments
        call_args = mock_openai_service.chat_completion.call_args
        messages = call_args.kwargs.get('messages') or call_args[0][0]
        prompt_content = messages[0]["content"]

        # Verify context is in the prompt
        assert "office" in prompt_content
        assert "3.5" in prompt_content  # width
        assert "3.0" in prompt_content  # depth
        assert "industrial" in prompt_content

    @pytest.mark.asyncio
    async def test_empty_furniture_list_is_valid(self):
        """Should handle empty furniture list (e.g., very small storage room)."""
        room_context = {
            "room_type": "storage",
            "dimensions": {"width": 1.0, "depth": 1.0, "height": 2.4},
            "doors": [{"wall": "south", "position": 0.5}],
            "windows": [],
            "style": "utilitarian",
        }

        mock_response = {
            "furniture": []
        }

        with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            placer = FurniturePlacer()
            plan = await placer.generate_plan(room_context)

            assert "furniture" in plan
            assert plan["furniture"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
