import uuid
from dataclasses import asdict

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf
from qdrant_client.http.models import PointStruct

from app.conf.meta_config import MetaConfig
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.models.column_info import ColumnInfoMySQL
from app.models.table_info import TableInfoMySQL
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repositories import DWMysqlRepository
from app.repositories.mysql.meta.meta_mysql_repositories import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.core.log import logger

class MetaKnowledgeService:
    # 写业务逻辑
    # 数据库具体的读写操作是repository层，因此不要将具体的读写操作写到service层
    # 要构建service对象的时候，再传入repository
    def __init__(self,meta_mysql_repository :MetaMySQLRepository,
                 dw_mysql_repository : DWMysqlRepository,
                 column_qdrant_repository :ColumnQdrantRepository,
                 embedding_client :HuggingFaceEndpointEmbeddings,
                 value_es_repository :ValueEsRepository,
                 metric_qdrant_repository :MetricQdrantRepository):
        self.meta_mysql_repository :MetaMySQLRepository = meta_mysql_repository
        self.dw_mysql_repository : DWMysqlRepository =dw_mysql_repository
        self.column_qdrant_repository :ColumnQdrantRepository = column_qdrant_repository
        self.embedding_client :HuggingFaceEndpointEmbeddings = embedding_client
        self.value_es_repository :ValueEsRepository = value_es_repository
        self.metric_qdrant_repository :MetricQdrantRepository = metric_qdrant_repository

    async def _save_tables_to_meta_db(self,meta_config:MetaConfig)-> list[ColumnInfo]:
        # 建立sql数据库table_info和column_info表的实体类，以便写进meta数据库，但是这里要注意的是，尽量不要把repository层的操作写到service层里面
        # 建立业务实体是为了让后面如果不用sqlalchemy的架构存储sql数据库的时候，可以不改变service层的逻辑
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []
        for table in meta_config.tables:
            # 将table -> table_info，将table的配置格式写入table_info中
            table_info = TableInfo(id=table.name,
                                   name=table.name,
                                   description=table.description,
                                   role=table.role,
                                   )
            table_infos.append(table_info)

            # 查询字段类型：一表一查，整个表的所有字段的类型可以直接查出来
            columns_type = await self.dw_mysql_repository.get_columns_type(table.name)

            for column in table.columns:
                # 查询字段取值示例：需要精确到每一个字段，然后取值
                column_values = await self.dw_mysql_repository.get_column_values(table.name, column.name)
                # column -> column_info
                # 由于字段的id如果用字段名，可能不唯一，因为可能在不同的表里面有相同的字段名
                # 数仓里面所有的column字段都会在column_info这个表里面
                column_info = ColumnInfo(id=f"{table.name}.{column.name}",
                                         name=column.name,
                                         type=columns_type[column.name],
                                         role=column.role,
                                         examples=column_values,
                                         description=column.description,
                                         alias=column.alias,
                                         table_id=table.name
                                         )
                column_infos.append(column_info)

        # 将所有指定的表信息和字段信息都存放到两个list里面后，就可以调用读写操作写入mata数据库
        # 这里因为是读写进meta的数据库里面，对meta数据库进行操作，那就要用到meta_mysql_repository
        # 这里表示的是session事务的开启，自动维护生命周期，如果后续读写操作没有问题，自动提交，如果有问题，就自动回滚
        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_table_infos(table_infos)
            self.meta_mysql_repository.save_column_infos(column_infos)
        return column_infos

    async def _save_columns_to_qdrant(self,column_infos:list[ColumnInfo]):
        # 有了qdrant的读写client，就可以开始写了
        await self.column_qdrant_repository.ensure_collection()
        # 由于每一个字段有多个信息需要被向量存储
        points = []
        for column_info in column_infos:
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": column_info.name,
                "payload": asdict(column_info)
            })
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": column_info.description,
                "payload": asdict(column_info)
            })
            for alia in column_info.alias:
                points.append({
                    "id": uuid.uuid4(),
                    "embedding_text": alia,
                    "payload": asdict(column_info)
                })

        # 向量化
        # 整体的向量化列表是一个二维的数组，数组里面每一个元素是一个向量化数组
        embeddings: list[list[float]] = []
        embedding_texts = [point["embedding_text"] for point in points]
        embedding_batch_size = 20
        # 将每次进行向量化的数据进行分批向量化，保证并行达到高效率
        for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i:i + embedding_batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding_texts)
            # 将每次向量化的子元素扩展到整个向量化数组embeddings里面
            embeddings.extend(batch_embeddings)
        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]

        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)

    async def _save_values_to_es(self,meta_config:MetaConfig):
        await self.value_es_repository.ensure_index()
        value_infos: list[ValueInfo] = []
        # 需要先判断到底是哪些维度字段需要建立全文索引
        for table in meta_config.tables:
            for column in table.columns:
                # 需要建立全文索引
                if column.sync:
                    # 求出字段所属的所有去重的值
                    current_column_values = await self.dw_mysql_repository.get_column_values(table.name, column.name,
                                                                                             limit=100000)
                    current_values_infos = [
                        ValueInfo(id=f"{table.name}.{column.name}.{current_column_value}", value=current_column_value,
                                  column_id=f"{table.name}.{column.name}")
                        for current_column_value in current_column_values]
                    value_infos.extend(current_values_infos)
        # 将指定的维度字段取值建立全文索引
        await self.value_es_repository.index(value_infos)

    async def _save_metrics_to_meta_db(self,meta_config:MetaConfig)-> list[MetricInfo]:
        metric_infos: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []
        for metric in meta_config.metrics:
            metric_info = MetricInfo(id=f"{metric.name}",
                                     name=metric.name,
                                     description=metric.description,
                                     relevant_columns=metric.relevant_columns,
                                     alias=metric.alias, )
            metric_infos.append(metric_info)
            # 对每一个metric相关的字段进行遍历
            for column in metric.relevant_columns:
                column_metric = ColumnMetric(column_id=column,
                                             metric_id=metric.name)
                column_metrics.append(column_metric)
        # 事务自动提交和回滚
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_metric_infos(metric_infos)
            await self.meta_mysql_repository.save_column_metrics(column_metrics)
        return metric_infos

    async def _save_metrics_to_qdrant(self,metric_infos: list[MetricInfo]):
        await self.metric_qdrant_repository.ensure_collection()
        # 由于每一个metric有多个信息需要被向量存储
        points = []
        for metric_info in metric_infos:
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": metric_info.name,
                "payload": asdict(metric_info)
            })
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": metric_info.description,
                "payload": asdict(metric_info)
            })
            for alia in metric_info.alias:
                points.append({
                    "id": uuid.uuid4(),
                    "embedding_text": alia,
                    "payload": asdict(metric_info)
                })

        # 向量化
        # 整体的向量化列表是一个二维的数组，数组里面每一个元素是一个向量化数组
        embeddings: list[list[float]] = []
        embedding_texts = [point["embedding_text"] for point in points]
        embedding_batch_size = 20
        # 将每次进行向量化的数据进行分批向量化，保证并行达到高效率
        for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i:i + embedding_batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding_texts)
            # 将每次向量化的子元素扩展到整个向量化数组embeddings里面
            embeddings.extend(batch_embeddings)
        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]

        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)

    # build需要调用很多异步的读写方法，因此外面要加async
    async def build(self,config_file):
        # 1.读取配置文件
        context = OmegaConf.load(config_file)
        # print(type(context))
        # 具体的对应类型格式
        schema = OmegaConf.structured(MetaConfig)
        # 把它变成具体的实体类，这样你要调用实例里面的属性就可以有提示，更好的操作
        # to_object 就是将合并后的conf转成一个对象，变成一个实例对象
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
        logger.info("加载配置文件成功")

        # 2.根据配置文件同步指定的表信息
        if meta_config.tables:
            # 2.1 将表信息和字段信息保存到meta数据库中
            column_infos = await self._save_tables_to_meta_db(meta_config)
            logger.info("保存表信息和字段信息到数据库成功")

            # 2.2 对字段信息建立向量索引（qdrant）
            await self._save_columns_to_qdrant(column_infos)
            logger.info("为字段信息建立向量索引成功")

            # 2.3 对指定的维度字段取值建立全文索引
            await self._save_values_to_es(meta_config)
            logger.info("为指定的维度字段取值建立全文索引成功")

        # 3.根据配置文件同步指定的指标信息
        if meta_config.metrics:
            # 3.1 将指标保存到meta数据库中
            metric_infos = await self._save_metrics_to_meta_db(meta_config)
            logger.info("保存指标信息到数据库成功")

            # 3.2 对指标信息建立向量索引
            await self._save_metrics_to_qdrant(metric_infos)
            logger.info("为指标信息建立向量索引成功")