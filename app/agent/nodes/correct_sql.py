import asyncio

import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger

async def correct_sql(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "校正sql语句","status": "running"})
    try:
        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]
        query = state["query"]
        # 进入了这个节点，代表sql有问题，因此需要给LLM输入待纠正的sql语句
        sql = state["sql"]
        error = state["error"]

        prompt = PromptTemplate(template=load_prompt("correct_sql"),
                                input_variables=["table_infos", "metric_infos", "date_info", "db_info", "query"])
        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
                                      "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
                                      "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
                                      "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
                                      "query": query})

        writer({"type": "progress","step": "校正sql语句","status": "success"})

        logger.info(f"纠正后的sql语句：{result}")
        return {"sql": result}

    except Exception as e:
        # 这个是执行进度
        logger.error(f"校正sql语句失败：{e}")
        writer({"type": "progress","step": "校正sql语句","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise