"""Material and texture routes."""

import logging
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class MaterialCategory(str, Enum):
    """Material categories."""

    WOOD = "wood"
    STONE = "stone"
    METAL = "metal"
    FABRIC = "fabric"
    CERAMIC = "ceramic"
    CONCRETE = "concrete"
    PAINT = "paint"


class Material(BaseModel):
    """Material definition."""

    id: str
    name: str
    category: MaterialCategory
    subcategory: str
    color_hex: str
    roughness: float
    metallic: float
    description: str
    style_tags: list[str]
    preview_url: Optional[str] = None


# Predefined material library
MATERIALS: list[Material] = [
    # Wood
    Material(
        id="white_oak_light",
        name="White Oak (Light)",
        category=MaterialCategory.WOOD,
        subcategory="Oak",
        color_hex="#D4B896",
        roughness=0.7,
        metallic=0.0,
        description="Light white oak with subtle grain pattern",
        style_tags=["modern", "scandinavian", "minimalist"],
    ),
    Material(
        id="white_oak_medium",
        name="White Oak (Medium)",
        category=MaterialCategory.WOOD,
        subcategory="Oak",
        color_hex="#B8956E",
        roughness=0.65,
        metallic=0.0,
        description="Medium-toned white oak, natural finish",
        style_tags=["traditional", "modern", "transitional"],
    ),
    Material(
        id="walnut_dark",
        name="Walnut (Dark)",
        category=MaterialCategory.WOOD,
        subcategory="Walnut",
        color_hex="#5C4033",
        roughness=0.6,
        metallic=0.0,
        description="Rich dark walnut with pronounced grain",
        style_tags=["traditional", "luxury", "art_deco"],
    ),
    Material(
        id="maple_natural",
        name="Maple (Natural)",
        category=MaterialCategory.WOOD,
        subcategory="Maple",
        color_hex="#E8D4B8",
        roughness=0.55,
        metallic=0.0,
        description="Light blonde maple, uniform grain",
        style_tags=["scandinavian", "modern", "minimalist"],
    ),
    # Stone
    Material(
        id="carrara_marble",
        name="Carrara Marble",
        category=MaterialCategory.STONE,
        subcategory="Marble",
        color_hex="#F5F5F5",
        roughness=0.3,
        metallic=0.0,
        description="Classic Italian marble with grey veining",
        style_tags=["luxury", "traditional", "modern"],
    ),
    Material(
        id="nero_marquina",
        name="Nero Marquina Marble",
        category=MaterialCategory.STONE,
        subcategory="Marble",
        color_hex="#1C1C1C",
        roughness=0.25,
        metallic=0.0,
        description="Black Spanish marble with white veins",
        style_tags=["luxury", "modern", "dramatic"],
    ),
    Material(
        id="slate_grey",
        name="Grey Slate",
        category=MaterialCategory.STONE,
        subcategory="Slate",
        color_hex="#708090",
        roughness=0.8,
        metallic=0.0,
        description="Natural grey slate, matte finish",
        style_tags=["industrial", "modern", "rustic"],
    ),
    # Metal
    Material(
        id="brushed_brass",
        name="Brushed Brass",
        category=MaterialCategory.METAL,
        subcategory="Brass",
        color_hex="#B5A642",
        roughness=0.4,
        metallic=0.9,
        description="Warm brushed brass finish",
        style_tags=["modern", "luxury", "art_deco"],
    ),
    Material(
        id="black_steel",
        name="Black Steel",
        category=MaterialCategory.METAL,
        subcategory="Steel",
        color_hex="#1A1A1A",
        roughness=0.35,
        metallic=0.85,
        description="Matte black powder-coated steel",
        style_tags=["industrial", "modern", "minimalist"],
    ),
    Material(
        id="brushed_nickel",
        name="Brushed Nickel",
        category=MaterialCategory.METAL,
        subcategory="Nickel",
        color_hex="#C0C0C0",
        roughness=0.35,
        metallic=0.9,
        description="Satin brushed nickel finish",
        style_tags=["modern", "transitional", "contemporary"],
    ),
    # Concrete
    Material(
        id="polished_concrete",
        name="Polished Concrete",
        category=MaterialCategory.CONCRETE,
        subcategory="Polished",
        color_hex="#A9A9A9",
        roughness=0.25,
        metallic=0.0,
        description="Smooth polished concrete, industrial look",
        style_tags=["industrial", "modern", "minimalist"],
    ),
    Material(
        id="raw_concrete",
        name="Raw Concrete",
        category=MaterialCategory.CONCRETE,
        subcategory="Raw",
        color_hex="#808080",
        roughness=0.85,
        metallic=0.0,
        description="Textured raw concrete finish",
        style_tags=["industrial", "brutalist", "modern"],
    ),
    # Paint
    Material(
        id="white_matte",
        name="White (Matte)",
        category=MaterialCategory.PAINT,
        subcategory="Wall Paint",
        color_hex="#FAFAFA",
        roughness=0.9,
        metallic=0.0,
        description="Clean white matte wall paint",
        style_tags=["minimalist", "scandinavian", "modern", "traditional"],
    ),
    Material(
        id="warm_grey",
        name="Warm Grey",
        category=MaterialCategory.PAINT,
        subcategory="Wall Paint",
        color_hex="#D3D0CB",
        roughness=0.85,
        metallic=0.0,
        description="Soft warm grey paint",
        style_tags=["modern", "transitional", "scandinavian"],
    ),
    # Ceramic
    Material(
        id="white_porcelain",
        name="White Porcelain",
        category=MaterialCategory.CERAMIC,
        subcategory="Porcelain",
        color_hex="#F8F8F8",
        roughness=0.2,
        metallic=0.0,
        description="Clean white porcelain tile",
        style_tags=["modern", "minimalist", "contemporary"],
    ),
    Material(
        id="terracotta",
        name="Terracotta",
        category=MaterialCategory.CERAMIC,
        subcategory="Terracotta",
        color_hex="#C75B39",
        roughness=0.75,
        metallic=0.0,
        description="Natural terracotta tile",
        style_tags=["mediterranean", "rustic", "traditional"],
    ),
]


class StylePreset(BaseModel):
    """Style preset with material recommendations."""

    id: str
    name: str
    description: str
    materials: dict[str, str]  # surface -> material_id


# Style presets
STYLE_PRESETS: list[StylePreset] = [
    StylePreset(
        id="modern_minimalist",
        name="Modern Minimalist",
        description="Clean lines, neutral palette, minimal decoration",
        materials={
            "floor": "white_oak_light",
            "walls": "white_matte",
            "ceiling": "white_matte",
            "accents": "black_steel",
        },
    ),
    StylePreset(
        id="scandinavian",
        name="Scandinavian",
        description="Light woods, white walls, cozy and functional",
        materials={
            "floor": "maple_natural",
            "walls": "white_matte",
            "ceiling": "white_matte",
            "accents": "white_oak_light",
        },
    ),
    StylePreset(
        id="industrial",
        name="Industrial",
        description="Raw materials, exposed elements, urban feel",
        materials={
            "floor": "polished_concrete",
            "walls": "raw_concrete",
            "ceiling": "raw_concrete",
            "accents": "black_steel",
        },
    ),
    StylePreset(
        id="luxury_modern",
        name="Luxury Modern",
        description="High-end materials, sophisticated palette",
        materials={
            "floor": "nero_marquina",
            "walls": "warm_grey",
            "ceiling": "white_matte",
            "accents": "brushed_brass",
        },
    ),
    StylePreset(
        id="mediterranean",
        name="Mediterranean",
        description="Warm tones, natural textures, relaxed elegance",
        materials={
            "floor": "terracotta",
            "walls": "white_matte",
            "ceiling": "white_matte",
            "accents": "walnut_dark",
        },
    ),
]


@router.get("/library")
async def get_material_library():
    """Get all available materials."""
    return {"materials": [m.model_dump() for m in MATERIALS]}


@router.get("/library/{material_id}")
async def get_material(material_id: str):
    """Get a specific material."""
    for material in MATERIALS:
        if material.id == material_id:
            return material.model_dump()
    raise HTTPException(status_code=404, detail="Material not found")


@router.get("/categories")
async def get_categories():
    """Get all material categories."""
    return {
        "categories": [
            {"id": cat.value, "name": cat.name.replace("_", " ").title()}
            for cat in MaterialCategory
        ]
    }


@router.get("/category/{category}")
async def get_materials_by_category(category: str):
    """Get materials by category."""
    try:
        cat = MaterialCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")

    materials = [m.model_dump() for m in MATERIALS if m.category == cat]
    return {"category": category, "materials": materials}


@router.get("/presets")
async def get_style_presets():
    """Get all style presets."""
    return {"presets": [p.model_dump() for p in STYLE_PRESETS]}


@router.get("/presets/{preset_id}")
async def get_style_preset(preset_id: str):
    """Get a specific style preset."""
    for preset in STYLE_PRESETS:
        if preset.id == preset_id:
            # Include full material details
            materials_detail = {}
            for surface, material_id in preset.materials.items():
                for m in MATERIALS:
                    if m.id == material_id:
                        materials_detail[surface] = m.model_dump()
                        break
            return {
                **preset.model_dump(),
                "materials_detail": materials_detail,
            }
    raise HTTPException(status_code=404, detail="Preset not found")


class MaterialRecommendationRequest(BaseModel):
    """Request for material recommendations."""

    style: str
    room_type: str
    preferences: Optional[str] = None
    floor_plan_context: Optional[dict] = None
    use_ai: bool = True  # Whether to use Azure OpenAI


# Initialize Azure OpenAI service (lazy loading)
_openai_service = None


def get_openai_service():
    """Get or create Azure OpenAI service."""
    global _openai_service
    if _openai_service is None:
        try:
            from core.azure import AzureConfig, AzureOpenAIService
            config = AzureConfig.from_env()
            if config.is_openai_configured():
                _openai_service = AzureOpenAIService(config)
        except Exception as e:
            logger.warning(f"Azure OpenAI not available: {e}")
    return _openai_service


@router.post("/recommend")
async def get_material_recommendations(request: MaterialRecommendationRequest):
    """Get AI-powered material recommendations using Azure OpenAI."""

    # Try AI recommendations first if enabled
    if request.use_ai:
        openai_service = get_openai_service()
        if openai_service:
            try:
                ai_response = await openai_service.get_material_recommendations(
                    room_type=request.room_type,
                    style=request.style,
                    preferences=request.preferences,
                    floor_plan_context=request.floor_plan_context,
                )

                return {
                    "style": request.style,
                    "room_type": request.room_type,
                    "recommendations": ai_response.get("recommendations", {}),
                    "style_notes": ai_response.get("style_notes", ""),
                    "alternatives": ai_response.get("alternatives", []),
                    "source": "azure_openai",
                }
            except Exception as e:
                logger.warning(f"AI recommendation failed, falling back to presets: {e}")

    # Fallback to style presets
    for preset in STYLE_PRESETS:
        if preset.id == request.style or request.style.lower() in preset.name.lower():
            return {
                "style": request.style,
                "room_type": request.room_type,
                "recommendations": {
                    "floor": {"material": preset.materials.get("floor", ""), "color": None, "reasoning": "Style preset"},
                    "walls": {"material": preset.materials.get("walls", ""), "color": None, "reasoning": "Style preset"},
                    "ceiling": {"material": preset.materials.get("ceiling", ""), "color": None, "reasoning": "Style preset"},
                    "accents": {"material": preset.materials.get("accents", ""), "color": None, "reasoning": "Style preset"},
                },
                "source": "preset",
                "note": "Based on style preset. Enable Azure OpenAI for AI-powered recommendations.",
            }

    # Default recommendations
    return {
        "style": request.style,
        "room_type": request.room_type,
        "recommendations": {
            "floor": {"material": "white_oak_light", "color": "#D4B896", "reasoning": "Default"},
            "walls": {"material": "white_matte", "color": "#FAFAFA", "reasoning": "Default"},
            "ceiling": {"material": "white_matte", "color": "#FFFFFF", "reasoning": "Default"},
            "accents": {"material": "brushed_nickel", "color": "#C0C0C0", "reasoning": "Default"},
        },
        "source": "default",
        "note": "Default recommendations. Configure Azure OpenAI for personalized suggestions.",
    }
