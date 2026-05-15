from typing import TypedDict

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repositories import DWMysqlRepository
from app.repositories.mysql.meta.meta_mysql_repositories import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class DataAgentContext(TypedDict):
    column_qdrant_repository : ColumnQdrantRepository
    metric_qdrant_repository : MetricQdrantRepository
    value_es_repository : ValueEsRepository
    embedding_client : HuggingFaceEndpointEmbeddings
    meta_mysql_repository : MetaMySQLRepository
    dw_mysql_repository : DWMysqlRepository

