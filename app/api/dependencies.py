from typing import Annotated

from fastapi import Depends
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.sql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repositories import DWMysqlRepository
from app.repositories.mysql.meta.meta_mysql_repositories import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.query_service import QueryService

async def get_meta_session() :
    # 当会话session被其他节点拿去使用过后，会返回到当前函数中继续执行close session操作
    async with meta_mysql_client_manager.session_factory() as meta_session:
        yield meta_session

async def get_meta_mysql_repository(session: Annotated[AsyncSession,Depends(get_meta_session)]) -> MetaMySQLRepository:
    return MetaMySQLRepository(session)


async def get_embedding_client() -> HuggingFaceEndpointEmbeddings:
    return embedding_client_manager.client

async def get_dw_session():
    # 当会话session被其他节点拿去使用过后，会返回到当前函数中继续执行close session操作
    async with dw_mysql_client_manager.session_factory() as dw_session:
        yield dw_session

async def get_dw_mysql_repository(session: Annotated[AsyncSession,Depends(get_dw_session)]) -> DWMysqlRepository:
    return DWMysqlRepository(session)

async def get_column_qdrant_repository() -> ColumnQdrantRepository:
    return ColumnQdrantRepository(qdrant_client_manager.client)

async def get_metric_qdrant_repository() -> MetricQdrantRepository:
    return MetricQdrantRepository(qdrant_client_manager.client)

async def get_value_es_repository() -> ValueEsRepository:
    return ValueEsRepository(es_client_manager.client)

async def get_query_service(meta_mysql_repository: Annotated[MetaMySQLRepository,Depends(get_meta_mysql_repository)],
                 embedding_client: Annotated[HuggingFaceEndpointEmbeddings,Depends(get_embedding_client)],
                 dw_mysql_repository: Annotated[DWMysqlRepository,Depends(get_dw_mysql_repository)],
                 column_qdrant_repository:Annotated[ColumnQdrantRepository,Depends(get_column_qdrant_repository)],
                 metric_qdrant_repository:Annotated[MetricQdrantRepository,Depends(get_metric_qdrant_repository)],
                 value_es_repository:Annotated[ValueEsRepository,Depends(get_value_es_repository)]
            ) -> QueryService:
    # 需要返回一个具体的对象作为依赖，才可以去调用方法
    # 这里需要注意的是，QueryService需要很多参数，很多是repository层的参数，其实也表明了QueryService需要这些依赖项
    # api层需要service层的依赖项，service需要repository层的依赖项
    return QueryService(meta_mysql_repository=meta_mysql_repository,
                        embedding_client=embedding_client,
                        dw_mysql_repository=dw_mysql_repository,
                        column_qdrant_repository=column_qdrant_repository,
                        metric_qdrant_repository=metric_qdrant_repository,
                        value_es_repository=value_es_repository)