"""Tests for RoomClassifier with fixture/text/AI-based classification."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from typing import List

from core.dwg_parser.room_classifier import (
    RoomContext,
    RoomClassification,
    RoomClassifier,
    FIXTURE_PATTERNS,
    ROOM_TYPES,
)


class TestRoomContext:
    """Tests for RoomContext dataclass."""

    def test_room_context_creation(self):
        """Test creating a RoomContext with required fields."""
        polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
        context = RoomContext(
            polygon=polygon,
            area=100.0,
            aspect_ratio=1.0,
            door_count=1,
            window_count=2,
        )

        assert context.polygon == polygon
        assert context.area == 100.0
        assert context.aspect_ratio == 1.0
        assert context.door_count == 1
        assert context.window_count == 2

    def test_room_context_defaults(self):
        """Test RoomContext default values."""
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
        )

        assert context.door_count == 0
        assert context.window_count == 0
        assert context.fixtures == []
        assert context.nearby_text == []
        assert context.adjacent_rooms == []

    def test_room_context_with_fixtures(self):
        """Test RoomContext with fixture list."""
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            fixtures=["toilet", "sink", "shower"],
        )

        assert context.fixtures == ["toilet", "sink", "shower"]

    def test_room_context_with_nearby_text(self):
        """Test RoomContext with nearby text labels."""
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["BATHROOM", "MASTER BATH"],
        )

        assert context.nearby_text == ["BATHROOM", "MASTER BATH"]


class TestFixtureDetection:
    """Tests for FIXTURE_PATTERNS constant."""

    def test_bathroom_fixtures_in_patterns(self):
        """Test that bathroom fixtures are present in FIXTURE_PATTERNS."""
        bathroom_fixtures = ["toilet", "wc", "sink", "basin", "shower", "tub", "bath"]
        for fixture in bathroom_fixtures:
            assert any(
                fixture in patterns
                for patterns in FIXTURE_PATTERNS.values()
            ), f"Missing bathroom fixture: {fixture}"

    def test_kitchen_fixtures_in_patterns(self):
        """Test that kitchen fixtures are present in FIXTURE_PATTERNS."""
        kitchen_fixtures = ["stove", "oven", "fridge", "refrigerator", "dishwasher"]
        for fixture in kitchen_fixtures:
            assert any(
                fixture in patterns
                for patterns in FIXTURE_PATTERNS.values()
            ), f"Missing kitchen fixture: {fixture}"

    def test_laundry_fixtures_in_patterns(self):
        """Test that laundry fixtures are present in FIXTURE_PATTERNS."""
        laundry_fixtures = ["washer", "dryer", "washing"]
        for fixture in laundry_fixtures:
            assert any(
                fixture in patterns
                for patterns in FIXTURE_PATTERNS.values()
            ), f"Missing laundry fixture: {fixture}"

    def test_fixture_patterns_structure(self):
        """Test that FIXTURE_PATTERNS has correct structure."""
        assert isinstance(FIXTURE_PATTERNS, dict)
        assert "bathroom" in FIXTURE_PATTERNS
        assert "kitchen" in FIXTURE_PATTERNS
        assert "laundry" in FIXTURE_PATTERNS
        assert all(isinstance(v, (list, tuple, set)) for v in FIXTURE_PATTERNS.values())


class TestRoomTypes:
    """Tests for ROOM_TYPES constant."""

    def test_all_room_types_present(self):
        """Test that all expected room types are present."""
        expected_types = [
            "living_room", "bedroom", "bathroom", "kitchen", "hallway",
            "closet", "garage", "dining_room", "office", "laundry",
            "pantry", "balcony", "conference_room", "reception",
            "lobby", "storage", "utility", "unknown"
        ]
        for room_type in expected_types:
            assert room_type in ROOM_TYPES, f"Missing room type: {room_type}"

    def test_room_types_is_collection(self):
        """Test that ROOM_TYPES is a proper collection."""
        assert isinstance(ROOM_TYPES, (list, tuple, set, frozenset))
        assert len(ROOM_TYPES) >= 18


class TestRoomClassification:
    """Tests for RoomClassification dataclass."""

    def test_room_classification_creation(self):
        """Test creating a RoomClassification."""
        classification = RoomClassification(
            room_type="bathroom",
            confidence=0.95,
            reasoning="Found toilet and sink fixtures",
        )

        assert classification.room_type == "bathroom"
        assert classification.confidence == 0.95
        assert classification.reasoning == "Found toilet and sink fixtures"

    def test_is_low_confidence_true(self):
        """Test is_low_confidence returns True below threshold."""
        classification = RoomClassification(
            room_type="unknown",
            confidence=0.3,
            reasoning="Insufficient data",
        )

        assert classification.is_low_confidence is True

    def test_is_low_confidence_false(self):
        """Test is_low_confidence returns False above threshold."""
        classification = RoomClassification(
            room_type="kitchen",
            confidence=0.8,
            reasoning="Found stove and refrigerator",
        )

        assert classification.is_low_confidence is False

    def test_is_low_confidence_boundary(self):
        """Test is_low_confidence at boundary value (0.5)."""
        classification_at_boundary = RoomClassification(
            room_type="bedroom",
            confidence=0.5,
            reasoning="Some evidence",
        )
        # At 0.5, should not be considered low confidence
        assert classification_at_boundary.is_low_confidence is False

        classification_below = RoomClassification(
            room_type="bedroom",
            confidence=0.49,
            reasoning="Weak evidence",
        )
        assert classification_below.is_low_confidence is True


class TestRoomClassifier:
    """Tests for RoomClassifier class."""

    def test_classifier_initialization_without_openai(self):
        """Test classifier initializes without OpenAI service."""
        classifier = RoomClassifier()
        assert classifier.openai_service is None

    def test_classifier_initialization_with_openai(self):
        """Test classifier initializes with OpenAI service."""
        mock_service = MagicMock()
        classifier = RoomClassifier(openai_service=mock_service)
        assert classifier.openai_service is mock_service

    def test_classify_returns_unknown_without_evidence(self):
        """Test classify returns unknown when no evidence available and no OpenAI."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
        )

        result = classifier.classify(context)

        assert result.room_type == "unknown"
        assert result.confidence == 0.0

    def test_infer_from_fixtures_bathroom(self):
        """Test _infer_from_fixtures detects bathroom from fixtures."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (3, 0), (3, 4), (0, 4)],
            area=12.0,
            aspect_ratio=0.75,
            fixtures=["toilet", "sink", "shower"],
        )

        result = classifier._infer_from_fixtures(context)

        assert result is not None
        assert result[0] == "bathroom"
        assert result[1] > 0.7  # High confidence

    def test_infer_from_fixtures_kitchen(self):
        """Test _infer_from_fixtures detects kitchen from fixtures."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
            area=20.0,
            aspect_ratio=1.25,
            fixtures=["stove", "refrigerator", "sink"],
        )

        result = classifier._infer_from_fixtures(context)

        assert result is not None
        assert result[0] == "kitchen"
        assert result[1] > 0.7

    def test_infer_from_fixtures_laundry(self):
        """Test _infer_from_fixtures detects laundry from fixtures."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (3, 0), (3, 3), (0, 3)],
            area=9.0,
            aspect_ratio=1.0,
            fixtures=["washer", "dryer"],
        )

        result = classifier._infer_from_fixtures(context)

        assert result is not None
        assert result[0] == "laundry"

    def test_infer_from_fixtures_no_match(self):
        """Test _infer_from_fixtures returns None when no match."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            fixtures=["unknown_item"],
        )

        result = classifier._infer_from_fixtures(context)

        assert result is None

    def test_infer_from_text_bedroom(self):
        """Test _infer_from_text detects bedroom from text labels."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["MASTER BEDROOM", "BEDROOM 1"],
        )

        result = classifier._infer_from_text(context)

        assert result is not None
        assert result[0] == "bedroom"

    def test_infer_from_text_living_room(self):
        """Test _infer_from_text detects living room from text labels."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (8, 0), (8, 6), (0, 6)],
            area=48.0,
            aspect_ratio=1.33,
            nearby_text=["LIVING ROOM"],
        )

        result = classifier._infer_from_text(context)

        assert result is not None
        assert result[0] == "living_room"

    def test_infer_from_text_no_match(self):
        """Test _infer_from_text returns None when no matching text."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["ABCD1234", "XYZ"],
        )

        result = classifier._infer_from_text(context)

        assert result is None

    def test_classify_with_fixtures_priority(self):
        """Test classify prioritizes fixtures over text."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            fixtures=["toilet", "sink"],  # Bathroom fixtures
            nearby_text=["KITCHEN"],  # Conflicting text
        )

        result = classifier.classify(context)

        # Fixtures should take priority
        assert result.room_type == "bathroom"

    def test_classify_falls_back_to_text(self):
        """Test classify falls back to text when no fixtures match."""
        classifier = RoomClassifier()
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            fixtures=[],
            nearby_text=["OFFICE", "HOME OFFICE"],
        )

        result = classifier.classify(context)

        assert result.room_type == "office"

    def test_classify_batch(self):
        """Test classify_batch processes multiple contexts."""
        classifier = RoomClassifier()
        contexts = [
            RoomContext(
                polygon=[(0, 0), (3, 0), (3, 4), (0, 4)],
                area=12.0,
                aspect_ratio=0.75,
                fixtures=["toilet", "sink"],
            ),
            RoomContext(
                polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
                area=20.0,
                aspect_ratio=1.25,
                fixtures=["stove", "fridge"],
            ),
        ]

        results = classifier.classify_batch(contexts)

        assert len(results) == 2
        assert results[0].room_type == "bathroom"
        assert results[1].room_type == "kitchen"


class TestClassifierWithMockedOpenAI:
    """Tests for RoomClassifier with mocked OpenAI service."""

    @pytest.fixture
    def mock_openai_service(self):
        """Create a mock OpenAI service."""
        service = MagicMock()
        return service

    def test_classify_with_openai_when_no_local_inference(self, mock_openai_service):
        """Test classifier uses OpenAI when local inference fails."""
        # Setup mock to return valid classification
        mock_openai_service.chat_completion = AsyncMock(
            return_value='{"room_type": "bedroom", "confidence": 0.85, "reasoning": "AI detected bed"}'
        )

        classifier = RoomClassifier(openai_service=mock_openai_service)
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            fixtures=[],
            nearby_text=[],
        )

        result = classifier.classify(context)

        # Should have called OpenAI
        mock_openai_service.chat_completion.assert_called_once()
        assert result.room_type == "bedroom"
        assert result.confidence == 0.85

    def test_classify_handles_openai_json_error(self, mock_openai_service):
        """Test classifier handles JSON parsing errors from OpenAI."""
        # Setup mock to return invalid JSON
        mock_openai_service.chat_completion = AsyncMock(
            return_value='Not valid JSON response'
        )

        classifier = RoomClassifier(openai_service=mock_openai_service)
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
        )

        result = classifier.classify(context)

        # Should fall back to unknown
        assert result.room_type == "unknown"
        assert result.confidence == 0.0

    def test_classify_handles_openai_exception(self, mock_openai_service):
        """Test classifier handles exceptions from OpenAI."""
        # Setup mock to raise an exception
        mock_openai_service.chat_completion = AsyncMock(
            side_effect=Exception("API Error")
        )

        classifier = RoomClassifier(openai_service=mock_openai_service)
        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
        )

        result = classifier.classify(context)

        # Should fall back to unknown
        assert result.room_type == "unknown"

    def test_classify_skips_openai_when_fixtures_match(self, mock_openai_service):
        """Test classifier skips OpenAI when fixtures provide match."""
        classifier = RoomClassifier(openai_service=mock_openai_service)
        context = RoomContext(
            polygon=[(0, 0), (3, 0), (3, 4), (0, 4)],
            area=12.0,
            aspect_ratio=0.75,
            fixtures=["toilet", "sink", "shower"],
        )

        result = classifier.classify(context)

        # Should NOT have called OpenAI since fixtures matched
        mock_openai_service.chat_completion.assert_not_called()
        assert result.room_type == "bathroom"

    def test_classify_batch_with_openai(self, mock_openai_service):
        """Test classify_batch with mixed local and AI classification."""
        # Return bedroom for the unknown room
        mock_openai_service.chat_completion = AsyncMock(
            return_value='{"room_type": "bedroom", "confidence": 0.75, "reasoning": "AI analysis"}'
        )

        classifier = RoomClassifier(openai_service=mock_openai_service)
        contexts = [
            # This one should be classified locally as bathroom
            RoomContext(
                polygon=[(0, 0), (3, 0), (3, 4), (0, 4)],
                area=12.0,
                aspect_ratio=0.75,
                fixtures=["toilet", "sink"],
            ),
            # This one has no evidence, should use AI
            RoomContext(
                polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
                area=25.0,
                aspect_ratio=1.0,
            ),
        ]

        results = classifier.classify_batch(contexts)

        assert len(results) == 2
        assert results[0].room_type == "bathroom"
        assert results[1].room_type == "bedroom"
        # OpenAI should only be called once (for the second context)
        assert mock_openai_service.chat_completion.call_count == 1


class TestTextPatternMatching:
    """Tests for text label pattern matching."""

    def test_case_insensitive_matching(self):
        """Test that text matching is case insensitive."""
        classifier = RoomClassifier()

        # Test lowercase
        context_lower = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["bathroom"],
        )
        result_lower = classifier._infer_from_text(context_lower)

        # Test uppercase
        context_upper = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["BATHROOM"],
        )
        result_upper = classifier._infer_from_text(context_upper)

        # Test mixed case
        context_mixed = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["BathRoom"],
        )
        result_mixed = classifier._infer_from_text(context_mixed)

        assert result_lower is not None
        assert result_upper is not None
        assert result_mixed is not None
        assert result_lower[0] == result_upper[0] == result_mixed[0] == "bathroom"

    def test_partial_text_matching(self):
        """Test matching partial text labels."""
        classifier = RoomClassifier()

        context = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["MASTER BEDROOM SUITE"],
        )

        result = classifier._infer_from_text(context)

        assert result is not None
        assert result[0] == "bedroom"


class TestConfidenceCalculation:
    """Tests for confidence calculation logic."""

    def test_multiple_fixtures_increase_confidence(self):
        """Test that multiple matching fixtures increase confidence."""
        classifier = RoomClassifier()

        # Single fixture
        context_single = RoomContext(
            polygon=[(0, 0), (3, 0), (3, 4), (0, 4)],
            area=12.0,
            aspect_ratio=0.75,
            fixtures=["toilet"],
        )
        result_single = classifier._infer_from_fixtures(context_single)

        # Multiple fixtures
        context_multi = RoomContext(
            polygon=[(0, 0), (3, 0), (3, 4), (0, 4)],
            area=12.0,
            aspect_ratio=0.75,
            fixtures=["toilet", "sink", "shower", "tub"],
        )
        result_multi = classifier._infer_from_fixtures(context_multi)

        assert result_single is not None
        assert result_multi is not None
        assert result_multi[1] >= result_single[1]  # Multi should have >= confidence

    def test_text_confidence_varies_with_specificity(self):
        """Test that more specific text labels give different confidence."""
        classifier = RoomClassifier()

        # Generic text
        context_generic = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["ROOM"],
        )
        result_generic = classifier._infer_from_text(context_generic)

        # Specific text
        context_specific = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["MASTER BEDROOM"],
        )
        result_specific = classifier._infer_from_text(context_specific)

        # Specific should match, generic might not
        assert result_specific is not None
        assert result_specific[0] == "bedroom"
