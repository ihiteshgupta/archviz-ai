"""Chat routes for LLM-powered design assistant."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.azure import AzureConfig, AzureOpenAIService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Azure OpenAI service
config = AzureConfig.from_env()
openai_service = AzureOpenAIService(config) if config.is_openai_configured() else None


class ChatMessage(BaseModel):
    """Chat message."""

    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Chat request."""

    message: str
    conversation_history: list[ChatMessage] = []
    project_id: Optional[str] = None
    project_context: Optional[dict] = None


class ChatResponse(BaseModel):
    """Chat response."""

    message: str
    conversation_history: list[ChatMessage]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the AI design assistant."""
    if not openai_service:
        raise HTTPException(
            status_code=503,
            detail="Azure OpenAI not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.",
        )

    try:
        # Convert history to dict format
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

        # Get response from Azure OpenAI
        response = await openai_service.chat_with_context(
            user_message=request.message,
            conversation_history=history,
            project_context=request.project_context,
        )

        # Build updated history
        updated_history = request.conversation_history + [
            ChatMessage(role="user", content=request.message),
            ChatMessage(role="assistant", content=response),
        ]

        return ChatResponse(
            message=response,
            conversation_history=updated_history,
        )

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class FloorPlanAnalysisRequest(BaseModel):
    """Floor plan analysis request."""

    image_path: str


@router.post("/analyze-floor-plan")
async def analyze_floor_plan(request: FloorPlanAnalysisRequest):
    """Analyze a floor plan image using GPT-4 Vision."""
    if not openai_service:
        raise HTTPException(
            status_code=503,
            detail="Azure OpenAI not configured.",
        )

    try:
        analysis = await openai_service.analyze_floor_plan_image(request.image_path)
        return {"analysis": analysis}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image file not found")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_chat_status():
    """Check if chat service is available."""
    return {
        "available": openai_service is not None,
        "provider": "azure_openai" if openai_service else None,
        "models": {
            "chat": config.gpt4_deployment if config.is_openai_configured() else None,
            "vision": config.gpt4_vision_deployment if config.is_openai_configured() else None,
        },
    }
