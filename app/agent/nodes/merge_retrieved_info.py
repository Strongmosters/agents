import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState, MetricInfoState, ColumnInfoState
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.mysql.meta.meta_mysql_repositories import MetaMySQLRepository
from app.core.log import logger

async def merge_retrieved_info(state: DataAgentState,runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress","step": "合并召回信息","status": "running"})
    try:
        # 将三个召回的值全部指明
        retrieved_column_infos :list[ColumnInfo] = state["retrieved_column_infos"]
        retrieved_metric_infos :list[MetricInfo] = state["retrieved_metric_infos"]
        retrieved_value_infos :list[ValueInfo] = state["retrieved_value_infos"]

        meta_mysql_repository: MetaMySQLRepository = runtime.context["meta_mysql_repository"]

        # 处理表信息
        # 将指标信息的相关字段信息添加到字段信息中
        retrieved_column_info_map : dict[str, ColumnInfo] = {retrieved_column_info.id: retrieved_column_info
                                                   for retrieved_column_info in retrieved_column_infos}
        for metric_info in retrieved_metric_infos:
            for relevant_column in metric_info.relevant_columns:
                if relevant_column not in retrieved_column_info_map:
                    # 这里得到的是相关字段的id，我们需要将整个字段信息都放入column_info_map里面，因此需要通过这个字段的id去查整个字段信息（meta库）
                    column_info :ColumnInfo =  await meta_mysql_repository.get_column_info_by_id(relevant_column)
                    # 如果直接将整个column_info的信息全部丢到里面，然后用if判断，只会判断地址信息，因此我们需要做一个字典，用id来判断是否存在于这个map当中
                    retrieved_column_info_map[relevant_column] = column_info

        # 字段取值加入到所属字段的examples中
        for value_info in retrieved_value_infos:
            value = value_info.value
            column_id = value_info.column_id
            if column_id not in retrieved_column_info_map:
                column_info :ColumnInfo = await meta_mysql_repository.get_column_info_by_id(column_id)
                retrieved_column_info_map[column_id] = column_info
            # 如果所属字段的示例没有该取值，那么就在字段的example里面加上字段取值
            if value not in retrieved_column_info_map[column_id].examples:
                retrieved_column_info_map[column_id].examples.append(value)


        # 按照表对字段信息进行分组，整理成目标格式
        table_to_column_map : dict[str,list[ColumnInfo]] = {}
        for retrieved_column_info in retrieved_column_info_map.values():
            table_id = retrieved_column_info.table_id
            # 初始化，第一个有table_id的字段，建立一个空list，方便后面添加属于相同表的字段
            if table_id not in table_to_column_map:
                table_to_column_map[table_id] = []
            table_to_column_map[table_id].append(retrieved_column_info)


        # 首先得知道有哪些表，才知道如何去查这个表下面的主外键字段
        # 这里需要操作的是，通过表的id去查字段
        for table_id in table_to_column_map.keys():
            key_columns:list[ColumnInfo] = await meta_mysql_repository.get_key_columns_by_id(table_id)
            column_ids = [column_info.id for column_info in table_to_column_map[table_id]]
            for key_column in key_columns:
                if key_column.id not in column_ids:
                    table_to_column_map[table_id].append(key_column)


        # 将表信息整理成目标格式
        table_infos: list[TableInfoState]=[]
        for table_id,column_infos in table_to_column_map.items():
            table_info: TableInfo = await meta_mysql_repository.get_table_info_by_id(table_id)
            # 将这个表下面的Column_info实体转换成需要的形式ColumnInfoState
            column_infos_state = [ColumnInfoState(name=column_info.name,
                                                  type=column_info.type,
                                                  role=column_info.role,
                                                  examples=column_info.examples,
                                                  description=column_info.description,
                                                  alias=column_info.alias) for column_info in column_infos]
            table_info_state = TableInfoState(name=table_info.name,
                                              role=table_info.role,
                                              description=table_info.description,
                                              columns= column_infos_state)

            table_infos.append(table_info_state)

        # 处理指标信息
        metric_infos :list[MetricInfoState] = [MetricInfoState(
            name=retrieved_metric_info.name,
            description=retrieved_metric_info.description,
            relevant_columns=retrieved_metric_info.relevant_columns,
            alias=retrieved_metric_info.alias) for retrieved_metric_info in retrieved_metric_infos]

        writer({"type": "progress","step": "合并召回信息","status": "success"})

        logger.info("合并召回信息成功")
        # 包括召回的表信息的所有主外键id字段，都存放到相应的表所属的字段中，保证后续写sql语句的时候可以关联主外键字段，生成正确的sql语句
        return {"table_infos": table_infos, "metric_infos": metric_infos}

    except Exception as e:
        # 这个是执行进度
        logger.error(f"合并召回信息失败：{e}")
        writer({"type": "progress","step": "合并召回信息","status": "error"})
        # 这个是抛出异常给上一层，让整个graph停止下来
        raise