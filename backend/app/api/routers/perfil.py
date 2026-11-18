from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import AllocationItem, MethodChoiceIn, MethodsOut, ProfileIn, ProfileOut, Question, RuleConfigItem
from app.services import methods, profile

router = APIRouter(prefix="/api", tags=["perfil"])


@router.get("/perfil/questionario", response_model=list[Question])
def questionnaire() -> list[Question]:
    return profile.questionnaire()


@router.get("/perfil", response_model=ProfileOut)
def read_profile(db: Session = Depends(get_db)) -> ProfileOut:
    return profile.profile_out(profile.get_profile(db))


@router.put("/perfil", response_model=ProfileOut)
def save_profile(body: ProfileIn, db: Session = Depends(get_db)) -> ProfileOut:
    return profile.save_profile(db, body)


@router.get("/metodos", response_model=MethodsOut)
def list_methods() -> MethodsOut:
    return methods.list_methods()


@router.put("/perfil/metodos", response_model=ProfileOut)
def choose_methods(body: MethodChoiceIn, db: Session = Depends(get_db)) -> ProfileOut:
    return methods.choose_methods(db, body)


@router.get("/alocacao", response_model=list[AllocationItem])
def read_allocation(db: Session = Depends(get_db)) -> list[AllocationItem]:
    return profile.read_allocation(db)


@router.put("/alocacao", response_model=list[AllocationItem])
def save_allocation(items: list[AllocationItem], db: Session = Depends(get_db)) -> list[AllocationItem]:
    return profile.save_allocation(db, items)


@router.get("/regras", response_model=list[RuleConfigItem])
def read_rules(db: Session = Depends(get_db)) -> list[RuleConfigItem]:
    return profile.read_rules(db)


@router.put("/regras", response_model=list[RuleConfigItem])
def save_rules(items: dict[str, float], db: Session = Depends(get_db)) -> list[RuleConfigItem]:
    return profile.save_rules(db, items)
