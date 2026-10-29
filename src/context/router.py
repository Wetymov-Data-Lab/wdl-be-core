from fastapi import APIRouter

from context.interface.controllers.canvas import router as canvas_router
from context.interface.controllers.database import router as database_router
from context.interface.controllers.enums import router as enums_router
from context.interface.controllers.history import router as history_router
from context.interface.controllers.project import router as projects_router
from context.interface.controllers.realm import router as realm_router
from context.interface.controllers.relationship import router as relationships_router
from context.interface.controllers.sql_export import router as sql_export_router

api_router = APIRouter()

api_router.include_router(realm_router)
api_router.include_router(projects_router)
api_router.include_router(database_router)
api_router.include_router(sql_export_router)
api_router.include_router(enums_router)
api_router.include_router(relationships_router)
api_router.include_router(canvas_router)
api_router.include_router(history_router)
