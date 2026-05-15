from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.models.column_info import ColumnInfoMySQL
from app.models.table_info import TableInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper


# 这里表示的是对meta数据库的读写操作
class MetaMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def save_table_infos(self, table_infos):
        # 由于这里的table_info是业务实体，我们需要先把它们转化为ORM实体才可以读写到数据库里面
        # 通过mapper方法就可以转化成ORM实体的列表，就可以用session.add_all方法来写入，这里就将数据写入数据库里面了
        # add_all方法并不是直接将数据存储到数据库中，而是存储到程序本地的session对象里面了，并没有发生实际的网络IO操作，如果需要传入数据到数据库中，还需要flush或者commit方法才可以写入
        self.session.add_all([TableInfoMapper.to_model(table_info) for table_info in table_infos])

    def save_column_infos(self, column_infos):
        self.session.add_all([ColumnInfoMapper.to_model(column_info) for column_info in column_infos])

    async def save_metric_infos(self, metric_infos):
        self.session.add_all([MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos])

    async def save_column_metrics(self, column_metrics):
        self.session.add_all([ColumnMetricMapper.to_model(column_metric) for column_metric in column_metrics])

    async def get_column_info_by_id(self, id: str) -> ColumnInfo | None:
        column_info_mysql:ColumnInfoMySQL | None = await self.session.get(ColumnInfoMySQL,id)
        if column_info_mysql:
            return ColumnInfoMapper.to_entity(column_info_mysql)
        else:
            return None

    async def get_table_info_by_id(self, id: str) -> TableInfo | None:
        table_info_mysql: TableInfoMySQL | None = await self.session.get(TableInfoMySQL, id)
        if table_info_mysql:
            return TableInfoMapper.to_entity(table_info_mysql)
        else:
            return None

    async def get_key_columns_by_id(self, table_id: str) -> list[ColumnInfo] | None:
        sql = "select * from column_info where table_id = :table_id and role in ('primary_key','foreign_key')"
        result = await self.session.execute(text(sql), {'table_id': table_id})
        return [ColumnInfo(**dict(row)) for row in result.mappings().fetchall()]
