from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from wdl_shared.schemas.engine.models.realms import (
    RealmCreateModel,
    RealmResponseModel,
    RealmUpdateModel,
)

from wdl_be_core.application.services.realm import (
    CreateRealm,
    CreateRealmRequest,
    DeleteRealm,
    DeleteRealmRequest,
    GetRealm,
    ListRealms,
    UpdateRealm,
    UpdateRealmRequest,
)
from wdl_be_core.domain.entities.realm import Realm, RealmStatus, RealmVisibility
from wdl_be_core.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
from wdl_be_core.presentation.api.dependencies.realm import get_realm_uow

router = APIRouter(prefix="/realms", tags=["realms"])
RealmUow = Annotated[SQLAlchemyUnitOfWork, Depends(get_realm_uow)]


def to_response(realm: Realm) -> RealmResponseModel:
    return RealmResponseModel(
        id=realm.id,
        name=realm.name.value,
        slug=realm.slug,
        status=realm.status.value,
        visibility=realm.visibility.value,
        settings=realm.settings,
        notice=realm.notice,
        author_id=realm.author_id,
        created_at=realm.created_at,
        updated_at=realm.updated_at,
        deleted_at=realm.deleted_at,
        updated_by=realm.updated_by,
    )


@router.get("/", response_model=list[RealmResponseModel])
async def get_realms(uow: RealmUow) -> list[RealmResponseModel]:
    realms = await ListRealms(uow).execute()
    return [to_response(realm) for realm in realms]


@router.get("/{realm_id}", response_model=RealmResponseModel)
async def get_realm(realm_id: UUID, uow: RealmUow) -> RealmResponseModel:
    return to_response(await GetRealm(uow).execute(realm_id))


@router.post("/", response_model=RealmResponseModel, status_code=status.HTTP_201_CREATED)
async def create_realm(body: RealmCreateModel, uow: RealmUow) -> RealmResponseModel:
    realm = await CreateRealm(uow).execute(
        CreateRealmRequest(
            name=body.name,
            slug=body.slug,
            status=RealmStatus(body.status),
            visibility=RealmVisibility(body.visibility),
            settings=body.settings,
            notice=body.notice,
            author_id=body.author_id,
        )
    )
    return to_response(realm)


@router.put("/{realm_id}", response_model=RealmResponseModel)
async def update_realm(realm_id: UUID, body: RealmUpdateModel, uow: RealmUow) -> RealmResponseModel:
    realm = await UpdateRealm(uow).execute(
        UpdateRealmRequest(
            realm_id=realm_id,
            name=body.name,
            slug=body.slug,
            status=RealmStatus(body.status),
            visibility=RealmVisibility(body.visibility),
            settings=body.settings,
            notice=body.notice,
            updated_by=body.updated_by,
        )
    )
    return to_response(realm)


@router.delete("/{realm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_realm(realm_id: UUID, updated_by: UUID, uow: RealmUow) -> Response:
    await DeleteRealm(uow).execute(DeleteRealmRequest(realm_id=realm_id, updated_by=updated_by))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
