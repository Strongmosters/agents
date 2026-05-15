import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger

async def run_sql(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "执行sql语句","status": "running"})
    try:
        sql = state["sql"]

        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        result = await dw_mysql_repository.run(sql)

        writer({"type": "progress","step": "执行sql语句","status": "success"})
        logger.info(f"执行sql语句的结果：{result}")
        writer({"type": "result","data": result})

    except Exception as e:
        # 这个是执行进度
        logger.error(f"执行sql语句失败：{e}")
        writer({"type": "progress","step": "执行sql语句","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise