import asyncio

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
from app.conf.app_config import QdrantConfig, app_config
from qdrant_client.models import Distance, VectorParams

class QdrantClientManager:
    def __init__(self,config:QdrantConfig):
        self.client: AsyncQdrantClient | None= None
        self.config: QdrantConfig = config

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"
    # 初始化Qdrant客户端,在init初始化的时候赋值
    def init(self):
        self.client =  AsyncQdrantClient(url=self._get_url())
    async def close(self):
        await self.client.close()

# 单例的实例对象，全局的
qdrant_client_manager = QdrantClientManager(config = app_config.qdrant)

if __name__ == "__main__":
    # 需要注意的是本地是docker run qdrant，因此qdrant默认是HTTP only (port 6333)，是HTTP服务，而不是HTTPS
    qdrant_client_manager.init()
    client=qdrant_client_manager.client

    async def test():
        # 创建一个集合（表），表名叫做test_collection
        await client.create_collection(
            collection_name="test_collection_async",
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )

        # 更新或者插入向量数据（id，向量，还有payload额外属性（自定义））
        await client.upsert(
            collection_name="test_collection_async",
            wait=True,
            points=[
                PointStruct(id=1, vector=[0.05, 0.61, 0.76, 0.74], payload={"city": "Berlin"}),
                PointStruct(id=2, vector=[0.19, 0.81, 0.75, 0.11], payload={"city": "London"}),
                PointStruct(id=3, vector=[0.36, 0.55, 0.47, 0.94], payload={"city": "Moscow"}),
                PointStruct(id=4, vector=[0.18, 0.01, 0.85, 0.80], payload={"city": "New York"}),
                PointStruct(id=5, vector=[0.24, 0.18, 0.22, 0.44], payload={"city": "Beijing"}),
                PointStruct(id=6, vector=[0.35, 0.08, 0.11, 0.44], payload={"city": "Mumbai"}),
            ],
        )

        # 查询数据，这可以通过异步创建任务，但不是立即执行，因此points先执行，但是由于任务没执行，就会报错，因为任务是没有"points"这个属性的，所以要加括号
        # 因此要加括号，表示先让await执行后再去找points
        search_result = await client.query_points(
            collection_name="test_collection_async",
            query=[0.2, 0.1, 0.9, 0.7],
            with_payload=False,
            limit=3
        )

        print(search_result.points)

        await qdrant_client_manager.close()

    # 启动异步程序
    asyncio.run(test())