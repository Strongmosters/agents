from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger

async def validate_sql(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "校验sql语句","status": "running"})
    try:
        sql = state["sql"]

        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        try:
            await dw_mysql_repository.validate(sql)
            logger.info("SQL语句正确")
            writer({"type": "progress","step": "校验sql语句","status": "success"})
            return {"error": None}
        except Exception as e:
            # 这里是校验sql语句的时候检测到错误，需要进入校正sql节点，而不是直接抛出异常中断graph，因此这里其实也是校验sql语句成功的标志
            logger.info("SQL语句错误")
            writer({"type": "progress","step": "校验sql语句","status": "success"})
            return {"error": str(e)}

    except Exception as e:
        # 这个是执行进度
        logger.error(f"校验sql语句失败：{e}")
        writer({"type": "progress","step": "校验sql语句","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise