from dataclasses import dataclass
from typing import Optional

@dataclass
class ColumnConfig:
    name: str
    role: str
    description: str
    alias: list[str]
    sync: bool

@dataclass
class TableConfig:
    name: str
    role: str
    description: str
    columns: list[ColumnConfig]

@dataclass
class MetricConfig:
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]

@dataclass
class MetaConfig:
    # 这里因为由于后续业务可能要增加其他表和指标，有可能只增加表，也有可能只增加指标，因此添加Optional，表示这些属性是可选性
    # 这里表示tables是一个list，list的每一个元素都是TableConfig
    tables: Optional[list[TableConfig]] = None
    metrics: Optional[list[MetricConfig]] = None