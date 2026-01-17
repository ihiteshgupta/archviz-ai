"""Room classification using fixtures, text labels, and optionally GPT-4.

This module provides intelligent room type classification based on:
1. Fixture detection (toilets, stoves, etc.)
2. Text label analysis (room names in floor plan)
3. AI-based classification via GPT-4 (optional fallback)
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Type alias for polygon points
Point2D = Tuple[float, float]


# Fixture patterns for detecting room types from block names
FIXTURE_PATTERNS: dict[str, list[str]] = {
    "bathroom": [
        "toilet", "wc", "sink", "basin", "shower", "tub", "bath",
        "bidet", "vanity", "lavatory",
    ],
    "kitchen": [
        "stove", "oven", "fridge", "refrigerator", "sink", "dishwasher",
        "range", "cooktop", "microwave", "counter",
    ],
    "laundry": [
        "washer", "dryer", "washing", "laundry", "iron",
    ],
    "bedroom": [
        "bed", "mattress", "wardrobe", "closet", "nightstand",
    ],
    "living_room": [
        "sofa", "couch", "tv", "television", "fireplace", "coffee_table",
    ],
    "dining_room": [
        "dining", "table", "chairs",
    ],
    "office": [
        "desk", "computer", "bookshelf", "filing",
    ],
    "garage": [
        "car", "vehicle", "garage_door",
    ],
}


# Text patterns for detecting room types from labels
TEXT_PATTERNS: dict[str, list[str]] = {
    "living_room": [
        "living", "lounge", "family room", "great room", "sitting",
    ],
    "bedroom": [
        "bedroom", "bed room", "master bed", "guest room", "sleeping",
    ],
    "bathroom": [
        "bathroom", "bath room", "restroom", "toilet", "wc", "lavatory",
        "powder room", "half bath", "full bath",
    ],
    "kitchen": [
        "kitchen", "kitchenette", "cook",
    ],
    "hallway": [
        "hallway", "hall", "corridor", "passage", "entry", "foyer",
    ],
    "closet": [
        "closet", "wardrobe", "storage", "pantry",
    ],
    "garage": [
        "garage", "carport", "parking",
    ],
    "dining_room": [
        "dining", "breakfast", "eat-in",
    ],
    "office": [
        "office", "study", "den", "library", "work room",
    ],
    "laundry": [
        "laundry", "utility", "mud room",
    ],
    "pantry": [
        "pantry", "larder",
    ],
    "balcony": [
        "balcony", "terrace", "patio", "deck", "porch",
    ],
    "conference_room": [
        "conference", "meeting", "board room",
    ],
    "reception": [
        "reception", "lobby", "waiting",
    ],
    "lobby": [
        "lobby", "entrance", "vestibule",
    ],
    "storage": [
        "storage", "store", "attic", "basement",
    ],
    "utility": [
        "utility", "mechanical", "hvac", "electrical",
    ],
}


# All recognized room types
ROOM_TYPES: frozenset[str] = frozenset([
    "living_room",
    "bedroom",
    "bathroom",
    "kitchen",
    "hallway",
    "closet",
    "garage",
    "dining_room",
    "office",
    "laundry",
    "pantry",
    "balcony",
    "conference_room",
    "reception",
    "lobby",
    "storage",
    "utility",
    "unknown",
])


@dataclass
class RoomContext:
    """Context information about a room for classification.

    Attributes:
        polygon: List of points defining room boundary
        area: Room area in square meters
        aspect_ratio: Width/height ratio of bounding box
        door_count: Number of doors
        window_count: Number of windows
        fixtures: List of fixture/block names found in room
        nearby_text: List of text labels near or inside room
        adjacent_rooms: List of adjacent room types (if known)
    """

    polygon: List[Point2D]
    area: float
    aspect_ratio: float
    door_count: int = 0
    window_count: int = 0
    fixtures: List[str] = field(default_factory=list)
    nearby_text: List[str] = field(default_factory=list)
    adjacent_rooms: List[str] = field(default_factory=list)


@dataclass
class RoomClassification:
    """Result of room classification.

    Attributes:
        room_type: The classified room type
        confidence: Confidence score between 0.0 and 1.0
        reasoning: Explanation for the classification
    """

    room_type: str
    confidence: float
    reasoning: str

    @property
    def is_low_confidence(self) -> bool:
        """Return True if confidence is below threshold (0.5)."""
        return self.confidence < 0.5


class RoomClassifier:
    """Classifies rooms based on fixtures, text labels, and AI.

    Classification priority:
    1. Infer from fixtures (if present)
    2. Infer from nearby text labels
    3. Use GPT-4 API (if openai_service provided)
    4. Return "unknown" with confidence 0.0
    """

    def __init__(self, openai_service: Optional[Any] = None):
        """Initialize the classifier.

        Args:
            openai_service: Optional Azure OpenAI service for AI classification.
                           Expected to have an async chat_completion method.
        """
        self.openai_service = openai_service

    def classify(self, context: RoomContext) -> RoomClassification:
        """Classify a room based on available context.

        Args:
            context: RoomContext with room information

        Returns:
            RoomClassification with room type, confidence, and reasoning
        """
        # Priority 1: Infer from fixtures
        fixture_result = self._infer_from_fixtures(context)
        if fixture_result is not None:
            room_type, confidence = fixture_result
            return RoomClassification(
                room_type=room_type,
                confidence=confidence,
                reasoning=f"Detected from fixtures: {', '.join(context.fixtures)}",
            )

        # Priority 2: Infer from text labels
        text_result = self._infer_from_text(context)
        if text_result is not None:
            room_type, confidence = text_result
            return RoomClassification(
                room_type=room_type,
                confidence=confidence,
                reasoning=f"Detected from text labels: {', '.join(context.nearby_text)}",
            )

        # Priority 3: Use AI classification
        if self.openai_service is not None:
            ai_result = self._classify_with_ai(context)
            if ai_result is not None:
                return ai_result

        # Fallback: Unknown
        return RoomClassification(
            room_type="unknown",
            confidence=0.0,
            reasoning="No fixtures, text labels, or AI classification available",
        )

    def classify_batch(
        self, contexts: List[RoomContext]
    ) -> List[RoomClassification]:
        """Classify multiple rooms.

        Args:
            contexts: List of RoomContext objects

        Returns:
            List of RoomClassification results
        """
        return [self.classify(context) for context in contexts]

    def _infer_from_fixtures(
        self, context: RoomContext
    ) -> Optional[Tuple[str, float]]:
        """Infer room type from fixture names.

        Args:
            context: RoomContext with fixtures list

        Returns:
            Tuple of (room_type, confidence) or None if no match
        """
        if not context.fixtures:
            return None

        # Count matches for each room type
        room_scores: dict[str, int] = {}

        for fixture in context.fixtures:
            fixture_lower = fixture.lower()
            for room_type, patterns in FIXTURE_PATTERNS.items():
                for pattern in patterns:
                    if pattern in fixture_lower:
                        room_scores[room_type] = room_scores.get(room_type, 0) + 1
                        break  # Count each fixture only once per room type

        if not room_scores:
            return None

        # Find best match
        best_room = max(room_scores, key=room_scores.get)  # type: ignore
        match_count = room_scores[best_room]

        # Calculate confidence based on number of matches
        # 1 match: 0.6, 2 matches: 0.75, 3+ matches: 0.85+
        if match_count == 1:
            confidence = 0.6
        elif match_count == 2:
            confidence = 0.75
        else:
            confidence = min(0.95, 0.75 + (match_count - 2) * 0.05)

        return (best_room, confidence)

    def _infer_from_text(
        self, context: RoomContext
    ) -> Optional[Tuple[str, float]]:
        """Infer room type from nearby text labels.

        Args:
            context: RoomContext with nearby_text list

        Returns:
            Tuple of (room_type, confidence) or None if no match
        """
        if not context.nearby_text:
            return None

        # Check each text label against patterns
        room_scores: dict[str, float] = {}

        for text in context.nearby_text:
            text_lower = text.lower()
            for room_type, patterns in TEXT_PATTERNS.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        # More specific patterns get higher scores
                        score = len(pattern) / 10.0  # Longer patterns = more specific
                        room_scores[room_type] = max(
                            room_scores.get(room_type, 0), score
                        )

        if not room_scores:
            return None

        # Find best match
        best_room = max(room_scores, key=room_scores.get)  # type: ignore
        score = room_scores[best_room]

        # Calculate confidence (0.5 - 0.85 based on pattern specificity)
        confidence = min(0.85, 0.5 + score)

        return (best_room, confidence)

    def _classify_with_ai(
        self, context: RoomContext
    ) -> Optional[RoomClassification]:
        """Classify room using GPT-4 AI.

        Args:
            context: RoomContext with room information

        Returns:
            RoomClassification or None if AI classification fails
        """
        if self.openai_service is None:
            return None

        try:
            # Run async call in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, self._async_classify_with_ai(context)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self._async_classify_with_ai(context)
                )
        except Exception as e:
            logger.warning(f"AI classification failed: {e}")
            return None

    async def _async_classify_with_ai(
        self, context: RoomContext
    ) -> Optional[RoomClassification]:
        """Async implementation of AI classification.

        Args:
            context: RoomContext with room information

        Returns:
            RoomClassification or None if AI classification fails
        """
        system_prompt = """You are an expert architect analyzing floor plans.
Given information about a room, classify its type and explain your reasoning.

Available room types:
- living_room, bedroom, bathroom, kitchen, hallway, closet, garage
- dining_room, office, laundry, pantry, balcony
- conference_room, reception, lobby, storage, utility, unknown

Respond ONLY with valid JSON in this exact format:
{
    "room_type": "the_room_type",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}"""

        user_prompt = f"""Classify this room:
- Area: {context.area:.1f} sq meters
- Aspect ratio: {context.aspect_ratio:.2f}
- Doors: {context.door_count}
- Windows: {context.window_count}
- Adjacent rooms: {', '.join(context.adjacent_rooms) if context.adjacent_rooms else 'unknown'}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self.openai_service.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=200,
            )

            # Parse JSON response
            response_text = response.strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            data = json.loads(response_text)

            room_type = data.get("room_type", "unknown")
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning", "AI classification")

            # Validate room type
            if room_type not in ROOM_TYPES:
                room_type = "unknown"
                confidence = 0.0

            return RoomClassification(
                room_type=room_type,
                confidence=confidence,
                reasoning=reasoning,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.warning(f"AI classification error: {e}")
            return None
