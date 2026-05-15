from dataclasses import asdict

from elasticsearch import AsyncElasticsearch

from app.entities.value_info import ValueInfo


class ValueEsRepository:
    index_name = "value_index"
    index_mappings = {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
            "column_id": {"type": "keyword"}
        }
    }

    def __init__(self,client:AsyncElasticsearch):
        self.client =client

    async def ensure_index(self):
        if not await self.client.indices.exists(index = self.index_name):
            await self.client.indices.create(
                index = self.index_name,
                mappings= self.index_mappings
            )

    async def index(self, value_infos:list[ValueInfo],es_batch_size=10):
        for i in range(0,len(value_infos),es_batch_size):
            batch_value_infos = value_infos[i:i+es_batch_size]
            batch_operations = []
            for value_info in batch_value_infos:
                batch_operations.append({
                    "index": {
                        "_index": self.index_name,
                    }
                })
                batch_operations.append(asdict(value_info))
            await self.client.bulk(operations=batch_operations)

    async def search(self, keyword) -> list[ValueInfo]:
        results = await self.client.search(
            index = self.index_name,
            query= {
                "match":{
                    "value":keyword
                }
            }
        )
        return [ValueInfo(**result["_source"]) for result in results["hits"]["hits"]]



