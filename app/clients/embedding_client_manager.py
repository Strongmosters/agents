import asyncio

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self,config:EmbeddingConfig):
        # 这个Embedding client 不区分同步和异步
        self.client : HuggingFaceEndpointEmbeddings | None = None
        self.config : EmbeddingConfig = config

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        self.client = HuggingFaceEndpointEmbeddings(model = self._get_url())

    # 由于不是长连接，因此不需要再用close来关闭client，是无状态的客户端
    # async def close(self):
    #     await self.client.close()

# 全局的embedding对象，而且是一个单例
embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__ == "__main__":
    embedding_client_manager.init()
    client = embedding_client_manager.client

    async def test():
        text = "What is deep learning?"
        query_result = await client.aembed_query(text)
        print(query_result[:3])

    asyncio.run(test())