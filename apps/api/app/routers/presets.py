from fastapi import APIRouter, HTTPException

from app import presets
from app.schemas import PresetOut

router = APIRouter(prefix="/v1/presets", tags=["presets"])


def _to_out(p: dict) -> PresetOut:
    return PresetOut(
        id=p["id"],
        label=p["label"],
        category=p["category"],
        capability=p["capability"],
        credit_cost=p["credit_cost"],
    )


@router.get("", response_model=list[PresetOut])
async def list_presets() -> list[PresetOut]:
    return [_to_out(p) for p in presets.list_presets()]


@router.get("/{preset_id}", response_model=PresetOut)
async def get_preset(preset_id: str) -> PresetOut:
    p = presets.get_preset(preset_id)
    if p is None:
        raise HTTPException(404, "preset not found")
    return _to_out(p)
