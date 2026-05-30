"""Prompt utilities backed by the LLM layer (OpenRouter)."""
from fastapi import APIRouter

from app import llm
from app.schemas import PromptEnhanceRequest, PromptEnhanceResponse

router = APIRouter(prefix="/v1/prompt", tags=["prompt"])


@router.post("/enhance", response_model=PromptEnhanceResponse)
async def enhance(body: PromptEnhanceRequest) -> PromptEnhanceResponse:
    enriched = await llm.enhance_prompt(body.prompt, body.capability)
    return PromptEnhanceResponse(prompt=enriched)
