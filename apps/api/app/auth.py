"""Phase 0 auth stub: resolves a single dev user so the pipeline is usable
before real OIDC lands. Replace with proper auth in a later phase."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

DEV_EMAIL = "dev@lumina.local"
DEV_STARTING_CREDITS = 1000


async def get_current_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == DEV_EMAIL))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=DEV_EMAIL, credit_balance=DEV_STARTING_CREDITS)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user
