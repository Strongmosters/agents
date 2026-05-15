import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.services.query_service import QueryService

query_router = APIRouter()


@query_router.post("/api/query")
# 通过声明依赖，然后通过依赖注入，才可以调用具体的service来执行具体的代码逻辑
# 每一个请求范围内的依赖都是单例的，因为多个依赖项下面有同一个依赖项，会有缓存的操作，在同一个依赖项的情况下多次调用此依赖，不会一直去创建这个依赖，而是通过缓存获取
async def query_handler(query: QuerySchema,query_service : Annotated[QueryService,Depends(get_query_service)]):
    return StreamingResponse(query_service.query(query.query), media_type="text/event-stream")
