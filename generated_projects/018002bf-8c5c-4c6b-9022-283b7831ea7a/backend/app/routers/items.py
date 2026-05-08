from fastapi import APIRouter

from app.schemas.item import Item
from app.services.item_service import list_items

router = APIRouter()


@router.get("/", response_model=list[Item])
def get_items() -> list[Item]:
    return list_items()
