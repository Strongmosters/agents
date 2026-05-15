from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger

async def recall_value(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "召回字段取值","status": "running"})
    try:
        query = state["query"]
        keywords = state["keywords"]
        value_es_repository = runtime.context["value_es_repository"]

        # 借助LLM扩展关键词
        # chain = prompt | llm | output_parser
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_value_recall"), input_variables=["query"])
        # 将LLM的输出被解析成合法的 JSON 对象: 比如这里得到的Json数组通过输出器生成list
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser
        results = await chain.ainvoke({"query": query})

        keywords = set(keywords + results)

        # 从es中检索字段取值信息
        value_info_map : dict[str, ValueInfo] = {}
        for keyword in keywords:
            current_value_infos :list[ValueInfo] = await value_es_repository.search(keyword)
            # 去重，比如多个关键字可能会返回同一个value
            for current_info in current_value_infos:
                if current_info.id not in value_info_map:
                    value_info_map[current_info.id] = current_info

        retrieved_value_infos : list[ValueInfo] = list(value_info_map.values())

        writer({"type": "progress","step": "召回字段取值","status": "success"})

        logger.info(f"召回的字段取值信息：{list(value_info_map.keys())}")
        return {"retrieved_value_infos":retrieved_value_infos}

    except Exception as e:
        # 这个是执行进度
        logger.error(f"召回字段取值失败：{e}")
        writer({"type": "progress","step": "召回字段取值","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise