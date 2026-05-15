from dataclasses import asdict

from app.entities.table_info import TableInfo
from app.models.table_info import TableInfoMySQL


class TableInfoMapper:
    # ORM到业务实体
    @staticmethod
    def to_entity(table_info_mysql : TableInfoMySQL) -> TableInfo:
        # 直接返回业务实体
        return TableInfo(id = table_info_mysql.id,
                         name= table_info_mysql.name,
                         role= table_info_mysql.role,
                         description= table_info_mysql.description,
        )

    # 业务实体到ORM
    @staticmethod
    def to_model(table_info: TableInfo) -> TableInfoMySQL:
        # 直接返回ORM实体
        # 由于table_info是一个dataclass的业务实体对象，可以用方法
        return TableInfoMySQL(**asdict(table_info))


