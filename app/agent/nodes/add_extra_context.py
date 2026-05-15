from langgraph.runtime import Runtime
from datetime import date
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState, DBInfoState
from app.core.log import logger

async def add_extra_context(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "添加额外上下文","status": "running"})
    try:
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")
        weekday = today.strftime("%A")
        quarter = f"Q{(today.month-1)//3 + 1}"

        date_info = DateInfoState(date=date_str,weekday=weekday,quarter=quarter)

        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        db = await dw_mysql_repository.get_db_info()
        db_info = DBInfoState(**db)

        writer({"type": "progress","step": "添加额外上下文","status": "success"})

        logger.info(f"日期信息：{date_info}")
        logger.info(f"数据库信息：{db_info}")
        return {"date_info": date_info, "db_info": db_info}

    except Exception as e:
        # 这个是执行进度
        logger.error(f"添加额外上下文失败：{e}")
        writer({"type": "progress","step": "添加额外上下文","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise