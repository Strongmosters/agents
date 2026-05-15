from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMysqlRepository:
    def __init__(self,session:AsyncSession):
        self.session = session
        pass
    async def get_columns_type(self,table_name:str):
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        result_dict =result.mappings().fetchall()
        # [{Field:order_id,Type:varchar(30),Null:No},{Field:customer_id,Type:varchar(20),Null: YES}]
        result = {row["Field"]: row["Type"] for row in result_dict}
        #{order_id: varchar(30), customer_id: varchar(30)}
        return result

    async def get_column_values(self,table_name,column_name,limit=10):
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        # 由于取出来的数据都是一列的，所以不需要去mappings映射
        # 直接拿到值的列表，而不是row的列表
        return [row[0] for row in result.fetchall()]

    async def get_db_info(self):
        sql = "select version()"
        result = await self.session.execute(text(sql))
        # 得到了Mysql的版本
        version = result.scalar()
        dialect = self.session.bind.dialect.name

        return {"version": version, "dialect": dialect}

    async def validate(self, sql:str):
        sql = f"explain {sql}"
        await self.session.execute(text(sql))

    async def run(self, sql:str)-> list[dict]:
       result = await self.session.execute(text(sql))
       return [dict(row) for row in result.mappings().fetchall()]


