import json

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repositories import DWMysqlRepository
from app.repositories.mysql.meta.meta_mysql_repositories import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class QueryService:
    def __init__(self,meta_mysql_repository:MetaMySQLRepository,
                 embedding_client: HuggingFaceEndpointEmbeddings,
                 dw_mysql_repository:DWMysqlRepository,
                 column_qdrant_repository:ColumnQdrantRepository,
                 metric_qdrant_repository:MetricQdrantRepository,
                 value_es_repository:ValueEsRepository):

        self.meta_mysql_repository = meta_mysql_repository
        self.embedding_client = embedding_client
        self.dw_mysql_repository = dw_mysql_repository

        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self,query:str):
        state = DataAgentState(query=query)
        context = DataAgentContext(column_qdrant_repository=self.column_qdrant_repository,
                                   metric_qdrant_repository=self.metric_qdrant_repository,
                                   embedding_client=self.embedding_client,
                                   value_es_repository=self.value_es_repository,
                                   meta_mysql_repository=self.meta_mysql_repository,
                                   dw_mysql_repository=self.dw_mysql_repository)
        try:
            async for chunk in graph.astream(input=state, context=context, stream_mode="custom"):
                # 每次输出一个chunk，就给前端yield一个返回数据值，然后流式输出到前端上
                # 这里每次流式输出的是用户自定义的字典类型消息，需要先将字典转化为json字符串，然后转化为SSE协议的格式
                yield f"data: {json.dumps(chunk,ensure_ascii=False,default=str)}\n\n"

        # 通过捕获某个节点错误抛出来的异常,然后把错误信息发送给前端
        except Exception as e:
            error = {"type": "error","message": str(e)}
            yield f"data: {json.dumps(error,ensure_ascii=False,default=str)}\n\n"


