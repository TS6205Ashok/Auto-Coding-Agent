from app.schemas.item import Item


def list_items() -> list[Item]:
    return [
        Item(id=1, name="Starter task", status="ready"),
        Item(id=2, name="Next iteration", status="planned"),
    ]
