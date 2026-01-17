"""Azure OpenAI service for LLM and DALL-E integration."""

import base64
import logging
from typing import Optional
from pathlib import Path

from openai import AzureOpenAI

from .config import AzureConfig

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """Azure OpenAI service for chat, vision, and image generation."""

    def __init__(self, config: AzureConfig):
        self.config = config
        self._client: Optional[AzureOpenAI] = None

    @property
    def client(self) -> AzureOpenAI:
        """Get or create Azure OpenAI client."""
        if self._client is None:
            if not self.config.is_openai_configured():
                raise ValueError("Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.")

            self._client = AzureOpenAI(
                azure_endpoint=self.config.openai_endpoint,
                api_key=self.config.openai_api_key,
                api_version=self.config.openai_api_version,
            )
        return self._client

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Get chat completion from GPT-4."""
        try:
            response = self.client.chat.completions.create(
                model=self.config.gpt4_deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise

    async def get_material_recommendations(
        self,
        room_type: str,
        style: str,
        preferences: Optional[str] = None,
        floor_plan_context: Optional[dict] = None,
    ) -> dict:
        """Get AI-powered material recommendations for a room."""

        system_prompt = """You are an expert interior designer and architect specializing in material selection.

Given a room type and style preference, recommend appropriate materials for:
- Floor (flooring material)
- Walls (wall finish/paint)
- Ceiling (ceiling treatment)
- Accents (trim, fixtures, hardware)

Consider:
- Style coherence and authenticity
- Practical durability for the room type
- Color harmony and visual flow
- Material textures and how they interact with light

Respond in JSON format with this structure:
{
    "recommendations": {
        "floor": {"material": "name", "color": "#hex", "reasoning": "why"},
        "walls": {"material": "name", "color": "#hex", "reasoning": "why"},
        "ceiling": {"material": "name", "color": "#hex", "reasoning": "why"},
        "accents": {"material": "name", "color": "#hex", "reasoning": "why"}
    },
    "style_notes": "brief explanation of the overall design direction",
    "alternatives": [{"surface": "floor", "alternative": "name", "reasoning": "why"}]
}"""

        user_prompt = f"""Please recommend materials for:
- Room Type: {room_type}
- Style: {style}
"""
        if preferences:
            user_prompt += f"- Additional Preferences: {preferences}\n"

        if floor_plan_context:
            user_prompt += f"""
- Room Size: {floor_plan_context.get('area', 'unknown')} sq meters
- Windows: {floor_plan_context.get('window_count', 0)}
- Natural Light: {floor_plan_context.get('light_level', 'moderate')}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self.chat_completion(messages, temperature=0.7)

            # Parse JSON response
            import json
            # Clean response if wrapped in markdown code block
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Material recommendation failed: {e}")
            # Return fallback recommendations
            return {
                "recommendations": {
                    "floor": {"material": "White Oak", "color": "#D4B896", "reasoning": "Classic choice"},
                    "walls": {"material": "Matte White", "color": "#FAFAFA", "reasoning": "Clean backdrop"},
                    "ceiling": {"material": "Matte White", "color": "#FFFFFF", "reasoning": "Maximizes light"},
                    "accents": {"material": "Brushed Nickel", "color": "#C0C0C0", "reasoning": "Modern touch"},
                },
                "style_notes": "Fallback recommendations due to service error",
                "alternatives": [],
                "error": str(e),
            }

    async def analyze_floor_plan_image(
        self,
        image_path: str,
    ) -> dict:
        """Analyze a floor plan image using GPT-4 Vision."""

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Determine media type
        ext = Path(image_path).suffix.lower()
        media_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "image/png")

        messages = [
            {
                "role": "system",
                "content": """You are an expert architect analyzing floor plans.
Identify and describe:
1. Room types and their approximate sizes
2. Traffic flow and spatial relationships
3. Natural light sources (windows)
4. Architectural features (columns, built-ins, etc.)

Respond in JSON format:
{
    "rooms": [{"name": "Living Room", "approx_size": "large", "features": ["bay window"]}],
    "flow_analysis": "description of circulation",
    "natural_light": "assessment of light",
    "suggestions": ["improvement ideas"]
}"""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please analyze this floor plan image and provide insights.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}",
                        },
                    },
                ],
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.config.gpt4_vision_deployment,
                messages=messages,
                max_tokens=2000,
            )

            content = response.choices[0].message.content or "{}"

            # Parse JSON
            import json
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"Floor plan analysis failed: {e}")
            raise

    async def generate_concept_render(
        self,
        prompt: str,
        style: str = "photorealistic",
        size: str = "1024x1024",
        quality: str = "hd",
    ) -> dict:
        """Generate a concept render using DALL-E 3."""

        # Enhance prompt for architectural visualization
        enhanced_prompt = f"""Professional architectural interior visualization, {style} style:
{prompt}

Photography style: Interior design magazine quality, natural lighting,
high-end finishes, realistic materials and textures, subtle ambient occlusion,
architectural photography composition, 8K resolution quality."""

        try:
            response = self.client.images.generate(
                model=self.config.dalle_deployment,
                prompt=enhanced_prompt,
                size=size,
                quality=quality,
                n=1,
            )

            return {
                "url": response.data[0].url,
                "revised_prompt": response.data[0].revised_prompt,
                "size": size,
                "quality": quality,
            }
        except Exception as e:
            logger.error(f"DALL-E generation failed: {e}")
            raise

    async def generate_room_render(
        self,
        room_type: str,
        style: str,
        materials: dict,
        additional_details: Optional[str] = None,
        size: str = "1024x1024",
    ) -> dict:
        """Generate a room render with specific materials."""

        # Build detailed prompt from materials
        material_desc = []
        for surface, mat in materials.items():
            if isinstance(mat, dict):
                material_desc.append(f"{surface}: {mat.get('material', mat)}")
            else:
                material_desc.append(f"{surface}: {mat}")

        prompt = f"""{style} style {room_type} interior:
Materials:
{chr(10).join('- ' + m for m in material_desc)}

{additional_details or ''}

Spacious, well-lit room with cohesive design, attention to material textures and reflections."""

        return await self.generate_concept_render(
            prompt=prompt,
            style="photorealistic architectural",
            size=size,
            quality="hd",
        )

    async def chat_with_context(
        self,
        user_message: str,
        conversation_history: list[dict],
        project_context: Optional[dict] = None,
    ) -> str:
        """Have a contextual conversation about the project."""

        system_prompt = """You are an AI interior design assistant for ArchViz AI,
an architectural visualization platform.

You help architects and designers:
- Select materials and finishes
- Recommend color palettes
- Suggest furniture layouts
- Explain design principles
- Answer questions about the project

Be concise, professional, and helpful. When recommending materials,
consider durability, aesthetics, cost, and sustainability."""

        if project_context:
            system_prompt += f"""

Current project context:
- Rooms: {project_context.get('room_count', 'unknown')}
- Total Area: {project_context.get('total_area', 'unknown')} sq meters
- Style: {project_context.get('style', 'not specified')}
"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        return await self.chat_completion(messages, temperature=0.7, max_tokens=1000)
