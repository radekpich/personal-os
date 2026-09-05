import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.challenge import Challenge
from app.models.user import User
from app.schemas.challenge import (
    ChallengeCreate,
    ChallengeList,
    ChallengePauseCreate,
    ChallengePauseRead,
    ChallengeRead,
    ChallengeUpdate,
    CheckInCreate,
    CheckInResult,
)
from app.services import challenge_service

router = APIRouter(prefix="/challenges", tags=["challenges"])


@router.get("", response_model=ChallengeList)
async def list_challenges(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChallengeList:
    challenges = await challenge_service.list_challenges(db, current_user)
    return ChallengeList(
        items=[ChallengeRead.model_validate(challenge) for challenge in challenges]
    )


@router.post(
    "",
    response_model=ChallengeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_challenge(
    payload: ChallengeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Challenge:
    return await challenge_service.create_challenge(db, current_user, payload)


@router.get("/{challenge_id}", response_model=ChallengeRead)
async def get_challenge(
    challenge_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Challenge:
    return await challenge_service.get_challenge(db, current_user, challenge_id)


@router.patch("/{challenge_id}", response_model=ChallengeRead, dependencies=[Depends(verify_csrf)])
async def update_challenge(
    challenge_id: uuid.UUID,
    payload: ChallengeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Challenge:
    return await challenge_service.update_challenge(db, current_user, challenge_id, payload)


@router.delete(
    "/{challenge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def delete_challenge(
    challenge_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await challenge_service.delete_challenge(db, current_user, challenge_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{challenge_id}/check-in", response_model=CheckInResult, dependencies=[Depends(verify_csrf)]
)
async def check_in_challenge(
    challenge_id: uuid.UUID,
    payload: CheckInCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CheckInResult:
    check_in, created, challenge = await challenge_service.check_in_challenge(
        db, current_user, challenge_id, payload
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return CheckInResult(
        check_in=check_in,
        current_streak=challenge.current_streak,
        longest_streak=challenge.longest_streak,
    )


@router.post(
    "/{challenge_id}/pauses",
    response_model=ChallengePauseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_pause(
    challenge_id: uuid.UUID,
    payload: ChallengePauseCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChallengePauseRead:
    pause = await challenge_service.create_pause(
        db, current_user, challenge_id, payload.start_date, payload.end_date, payload.note
    )
    return ChallengePauseRead.model_validate(pause)
