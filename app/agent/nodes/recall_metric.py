from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger

async def recall_metric(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "召回指标信息","status": "running"})
    try:
        query = state["query"]
        keywords = state["keywords"]
        # 取到读写qdrant的客户端，就可以进行读写操作，这里的任务是去召回qdrant的字段信息，这里需要注意的是召回指标信息的时候，也是在qdrant的指标数据库召回
        metric_qdrant_repository = runtime.context["metric_qdrant_repository"]
        embedding_client = runtime.context["embedding_client"]

        # 借助LLM扩展关键词
        # chain = prompt | llm | output_parser
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_metric_recall"), input_variables=["query"])
        # 将LLM的输出被解析成合法的 JSON 对象: 比如这里得到的Json数组通过输出器生成list
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser
        results = await chain.ainvoke({"query": query})

        keywords = set(keywords + results)

        # 从qdrant中检索指标信息
        metric_info_map: dict[str, MetricInfo] = {}
        for keyword in keywords:
            # 对每一个keyword进行embedding
            embedding = await embedding_client.aembed_query(keyword)
            # 对这个keyword对应的embedding向量进行召回，这里需要注意的是召回需要去qdrant数据库进行召回，embedding只是一个向量化的工具
            current_metric_infos: list[MetricInfo] = await metric_qdrant_repository.search(embedding,score_threshold = 0.6,limit = 10)
            # 由于每一个关键字可能都会召回同一个payload，即同一个字段的信息，会导致冗余，因此需要去重，去重不能直接用set，要用哈希表的方式来去重
            for metric_info in current_metric_infos:
                if metric_info.id not in metric_info_map:
                    metric_info_map[metric_info.id] = metric_info
        retrieved_metric_infos = list(metric_info_map.values())

        writer({"type": "progress","step": "召回指标信息","status": "success"})

        logger.info(f"检索的指标信息：{list(metric_info_map.keys())}")
        return {"retrieved_metric_infos": retrieved_metric_infos}

    except Exception as e:
        # 这个是执行进度
        logger.error(f"召回指标信息失败：{e}")
        writer({"type": "progress","step": "召回指标信息","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise