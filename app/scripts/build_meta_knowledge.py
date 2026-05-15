import argparse
import asyncio
import sys
from pathlib import Path

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.sql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
# 添加环境变量$env:PYTHONPATH = 'D:\agents\data-agent'，可以手动将根目录地址放入sys.path里面，但是是会话级，因此每次打开脚本都要配置这个环境变量，比较麻烦
# 因此，以模块化的执行方式：python -m app.scripts.build_meta_knowledge，来执行会将终端当前所在的目录添加到sys.path中:""
from app.core.log import logger
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repositories import DWMysqlRepository
from app.repositories.mysql.meta.meta_mysql_repositories import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


# 编写业务逻辑。读配置文件，根据配置文件写个Mysql，建索引。
async def build(config_path:Path):
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    # 调用__call__方法，来生成一个新的实例session，但是要调用__call__方法
    async with meta_mysql_client_manager.session_factory() as meta_session,dw_mysql_client_manager.session_factory() as dw_session:
        # 有了session，就等于有了engine，session相当于就是一个client了
        # 这里的meta和dw的repository是用谁查谁，不要搞混了
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMysqlRepository(dw_session)
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
        value_es_repository = ValueEsRepository(es_client_manager.client)
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)

        meta_knowledge_service = MetaKnowledgeService(meta_mysql_repository=meta_mysql_repository,
                                                      dw_mysql_repository=dw_mysql_repository,
                                                      column_qdrant_repository=column_qdrant_repository,
                                                      embedding_client = embedding_client_manager.client,
                                                      value_es_repository=value_es_repository,
                                                      metric_qdrant_repository=metric_qdrant_repository)
        await meta_knowledge_service.build(config_path)

    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await qdrant_client_manager.close()
    await es_client_manager.close()
# 在python的终端里面执行这个python脚本文件，需要注意的是，当前脚本所在目录D:\\agents\\data-agent\\app\\scripts会在这个sys.path里面
# 还有PYTHONPATH这个变量也会加入这个sys.path里面
# 'D:\\agents\\data-agent'，是因为"将源根添加到PYTHONPATH"这个pycharm的操作，然后添加到sys.path里面，所以直接在python脚本中右键执行会添加根目录，这样自然能找到app这个包
if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # 只解析conf这个参数就可以了
    parser.add_argument('-c', '--conf')  # option that takes a value

    args = parser.parse_args()
    config_path = args.conf

    asyncio.run(build(Path(config_path)))