# 由于sqlalchemy没有client的直接引用，因此需要定义engine和session
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.conf.app_config import DBConfig, app_config


# Mysql整个类封装完毕
class MySQLClientManager:
    def __init__(self,config:DBConfig):
        # 这里需要给类型，才可以访问其他方法
        # engine会维护一个数据库连接池
        self.engine :AsyncEngine | None = None
        self.config = config
        self.session_factory = None

    def _get_url(self):
        return f"mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}?charset=utf8mb4"

    def init(self):
        # pool_size是规定连接池的个数，而pro_pre_ping是每次去调用这个客户端的连接的时候，先ping一下看是否保持连接
        self.engine = create_async_engine(self._get_url(),pool_size = 10,pool_pre_ping = True)
        self.session_factory = async_sessionmaker(self.engine,autoflush = True,expire_on_commit=False)

    # 由于Mysql具有长连接，所以需要close方法来释放连接池
    async def close(self):
        await self.engine.dispose()

# 这里是两个服务器，需要维护数据仓库dw和元数据仓库meta的client，这里需要指明的是注意db_meta和db_dw指向的配置地址和访问的sql数据库都不一样
meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)

if __name__ == "__main__":
    dw_mysql_client_manager.init()


    async def test():
        # autoflush，每次在查询的时候都会flush一下，保证每次查询的时候都能查到数据，后面这个expire_on_commit
        # 主要是查询的时候是await，其实不满足书写规范
        async with dw_mysql_client_manager.session_factory() as session:
            # 有实体类，就可以使用Sqlalchemy，就可以使用ORM，用它的语法来写Sql语句
            # 但是没有实体类，也可以使用，只需要自行写入sql语句就可以
            # 注意这里是sql语句，语法也是sql语法
            sql = "select * from fact_order limit 10"
            # 这里需要注意的是execute不能直接传入字符串，需要通过text方法来转化一下，再输入
            result = await session.execute(text(sql))

            # 将每一个row进行映射，变成dict的类型
            rows = result.mappings().fetchall()
            print(type(rows))
            print(type(rows[0]))
            print(rows[0]["order_id"])

    asyncio.run(test())