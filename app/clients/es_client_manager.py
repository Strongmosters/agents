import asyncio

from elasticsearch import AsyncElasticsearch

from app.conf.app_config import QdrantConfig, app_config, ESConfig

# 这个是全文检索的异步client
# 封装好了es_client_manager
class EsClientManager:
    def __init__(self,config:ESConfig):
        self.client : AsyncElasticsearch | None = None
        self.config = config
    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"
    def init(self):
        self.client = AsyncElasticsearch(self._get_url())
    async def close(self):
        await self.client.close()


es_client_manager = EsClientManager(app_config.es)

if __name__ == "__main__":
    es_client_manager.init()
    client = es_client_manager.client

    async def test():

        # 创建索引
        # await client.indices.create(
        #     index="my_books_2",
        #     mappings={
        #         "dynamic": False,
        #         "properties": {
        #             "name": {
        #                 "type": "text"
        #             },
        #             "author": {
        #                 "type": "text"
        #             },
        #             "release_date": {
        #                 "type": "date",
        #                 "format": "yyyy-MM-dd"
        #             },
        #             "page_count": {
        #                 "type": "integer"
        #             }
        #         }
        #     },
        # )

        # 添加数据，这里的bulk（index）是动词，下面的index是名词，指的是一个列表
        await client.bulk(
            operations=[
                {
                    "index": {
                        "_index": "my_books_2"
                    }
                },
                {
                    "name": "Revelation Space",
                    "author": "Alastair Reynolds",
                    "release_date": "2000-03-15",
                    "page_count": 585
                },
                {
                    "index": {
                        "_index": "my_books_2"
                    }
                },
                {
                    "name": "1984",
                    "author": "George Orwell",
                    "release_date": "1985-06-01",
                    "page_count": 328
                },
                {
                    "index": {
                        "_index": "my_books_2"
                    }
                },
                {
                    "name": "Fahrenheit 451",
                    "author": "Ray Bradbury",
                    "release_date": "1953-10-15",
                    "page_count": 227
                },
                {
                    "index": {
                        "_index": "my_books_2"
                    }
                },
                {
                    "name": "Brave New World",
                    "author": "Aldous Huxley",
                    "release_date": "1932-06-01",
                    "page_count": 268
                },
                {
                    "index": {
                        "_index": "my_books_2"
                    }
                },
                {
                    "name": "The Handmaids Tale",
                    "author": "Margaret Atwood",
                    "release_date": "1985-06-01",
                    "page_count": 311
                }
            ],
        )
        # await asyncio.sleep(1)
        resp = await client.search(
            index="my_books_2",
            query={
                "match": {
                    "name": "brave"
                }
            },
        )
        print(resp)
        await es_client_manager.close()


    asyncio.run(test())