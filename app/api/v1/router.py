"""
V1 API router – aggregates all endpoint modules.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import ai, auth, diary, pomodoro, sleep

router = APIRouter()
router.add_api_route("/users/me", auth.get_me, methods=["GET"], response_model=auth.UserResponse, summary="Alias for /auth/me")

router.include_router(auth.router)
router.include_router(diary.router)
router.include_router(pomodoro.router)
router.include_router(sleep.router)
router.include_router(ai.router)
