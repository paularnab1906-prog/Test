"""Prompt Director endpoint — preview the detailed prompt before generating."""
from fastapi import APIRouter

from app import llm
from app.schemas import PromptEnhanceRequest, PromptEnhanceResponse

router = APIRouter(prefix="/v1/prompt", tags=["prompt"])


@router.post("/enhance", response_model=PromptEnhanceResponse)
async def enhance(body: PromptEnhanceRequest) -> PromptEnhanceResponse:
    enriched = await llm.direct_prompt(
        body.prompt, body.capability, body.category, body.examples
    )
    return PromptEnhanceResponse(original=body.prompt, prompt=enriched)
