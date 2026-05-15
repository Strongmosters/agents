import asyncio

import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, TableInfoState, MetricInfoState
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger

async def filter_metric(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "过滤指标信息","status": "running"})
    try:
        query = state["query"]
        metric_infos = state["metric_infos"]

        # 通过大模型来过滤表格和字段信息
        prompt = PromptTemplate(template=load_prompt("filter_metric_info"), input_variables=["query", "metric_infos"])
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        # 返回的JSON格式为：
        # [
        #     "转正人数",
        #     "转正率"
        # ]
        results = await chain.ainvoke({"query": query,
                                       "metric_infos": yaml.dump(metric_infos,allow_unicode=True,sort_keys=False)})

        filtered_metric_infos : list[MetricInfoState] = []
        for metric_info in metric_infos:
            if metric_info["name"] in results:
                filtered_metric_infos.append(metric_info)

        writer({"type": "progress","step": "过滤指标信息","status": "success"})

        logger.info(f"过滤后的指标信息：{[filtered_metric_info["name"] for filtered_metric_info in filtered_metric_infos]}")
        return {"metric_infos": filtered_metric_infos}

    except Exception as e:
        # 这个是执行进度
        logger.error(f"过滤指标信息失败：{e}")
        writer({"type": "progress","step": "过滤指标信息","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise