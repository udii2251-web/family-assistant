from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.models.family import FamilyMember
from app.schemas.schemas import FamilyMemberCreate, FamilyMemberUpdate, FamilyMemberOut

router = APIRouter(prefix="/family", tags=["family"])


@router.get("/", response_model=List[FamilyMemberOut])
def list_members(db: Session = Depends(get_db)):
    return db.query(FamilyMember).all()


@router.post("/", response_model=FamilyMemberOut)
def create_member(data: FamilyMemberCreate, db: Session = Depends(get_db)):
    member = FamilyMember(**data.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.put("/{member_id}", response_model=FamilyMemberOut)
def update_member(member_id: int, data: FamilyMemberUpdate, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise ValueError("Member not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(member, key, value)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise ValueError("Member not found")
    db.delete(member)
    db.commit()
    return {"ok": True}
