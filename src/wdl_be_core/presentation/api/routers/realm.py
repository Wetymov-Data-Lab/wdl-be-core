from datetime import datetime

from fastapi import APIRouter
from wdl_shared.schemas.engine.realm import RealmCreateModel, RealmResponseModel, RealmUpdateModel

router = APIRouter(prefix="/realms", tags=["realms"])


# TODO: Переписать заглушки на реальные методы работы с сервисом RealmService
@router.get("/", response_model=list[RealmResponseModel])
async def get_realms():
    return [
        RealmResponseModel(
            id="uuid1",
            name="Realm 1",
            notice=None,
            created_at=datetime.now(),
            updated_at=None,
            author_id="uuid1",
        ),
        RealmResponseModel(
            id="uuid2",
            name="Realm 2",
            notice=None,
            created_at=datetime.now(),
            updated_at=None,
            author_id="uuid2",
        ),
        RealmResponseModel(
            id="uuid3",
            name="Realm 3",
            notice=None,
            created_at=datetime.now(),
            updated_at=None,
            author_id="uuid3",
        ),
    ]


@router.get("/{realm_id}", response_model=RealmResponseModel)
async def get_realm(realm_id: str):
    return RealmResponseModel(
        id=realm_id,
        name=f"Realm {realm_id}",
        notice=None,
        created_at=datetime.now(),
        updated_at=None,
        author_id="uuid1",
    )


@router.post("/", response_model=RealmResponseModel)
async def create_realm(realm: RealmCreateModel):
    return RealmResponseModel(
        id="new_uuid",
        name=realm.name,
        notice=realm.notice,
        author_id="new_author_uuid",
        created_at=datetime.now(),
        updated_at=None,
    )


@router.put("/{realm_id}", response_model=RealmResponseModel)
async def update_realm(realm_id: str, realm: RealmUpdateModel):
    return RealmResponseModel(
        id=realm_id,
        name=realm.name,
        notice=realm.notice,
        author_id="existing_author_uuid",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@router.delete("/{realm_id}", response_model=dict)
async def delete_realm(realm_id: str):
    return {"message": f"Realm with id {realm_id} has been deleted"}
