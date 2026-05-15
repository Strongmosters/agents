import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, TableInfoState
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger

async def filter_table(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "过滤表格信息","status": "running"})
    try:
        query = state["query"]
        table_infos: list[TableInfoState] = state["table_infos"]

        # 通过大模型来过滤表格和字段信息
        prompt = PromptTemplate(template=load_prompt("filter_table_info"), input_variables=["query","table_infos"])
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        # 返回的JSON格式为：
        # {{
        #     "表名1":["字段1", "字段2", "..."],
        #     "表名2":["字段1", "字段2", "..."]
        # }}
        # 这里需要注意的是，这里的"表名1"和"字段1"都是各自的名字，比如表名和字段名
        results = await chain.ainvoke({"query": query,
                                       "table_infos": yaml.dump(table_infos,allow_unicode=True,sort_keys=False)})


        # 其实这里就是印证了大模型只负责做出决策，而不是自动调用工具或者执行代码，执行这些的是自己定义的代码
        filtered_table_infos: list[TableInfoState] = []
        for table_info in table_infos:
            if table_info["name"] in results:
                # 这里确定了这张表在过滤表集合内后，然后还需要过滤这张表里面的字段信息
                table_info["columns"] = [column for column in table_info["columns"] if column["name"] in results[table_info["name"]]]
                # 这才算将表和字段信息都过滤了一遍，就可以添加了
                filtered_table_infos.append(table_info)

        writer({"type": "progress","step": "过滤表格信息","status": "success"})

        logger.info(f"过滤后的表信息：{[filtered_table_info["name"] for filtered_table_info in filtered_table_infos]}")
        return {"table_infos":filtered_table_infos}

    except Exception as e:
        # 这个是执行进度
        logger.error(f"过滤表格信息失败：{e}")
        writer({"type": "progress","step": "过滤表格信息","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise