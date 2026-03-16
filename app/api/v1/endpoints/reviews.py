from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DBSession
from app.models.user import Place, Review
from app.schemas.schemas import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(body: ReviewCreate, current_user: CurrentUser, db: DBSession):
    # Verify place exists
    place = await db.get(Place, body.place_id)
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")

    # Prevent duplicate reviews
    existing = await db.execute(
        select(Review).where(
            Review.user_id == current_user.id,
            Review.place_id == body.place_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already reviewed")

    review = Review(
        user_id=current_user.id,
        place_id=body.place_id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return review


@router.get("/places/{place_id}", response_model=list[ReviewOut])
async def get_place_reviews(
    place_id: UUID,
    db: DBSession,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    result = await db.execute(
        select(Review)
        .where(Review.place_id == place_id)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(review_id: UUID, current_user: CurrentUser, db: DBSession):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your review")

    await db.delete(review)