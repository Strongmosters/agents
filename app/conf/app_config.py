from dataclasses import dataclass

from omegaconf import OmegaConf
from pathlib import Path


@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str

@dataclass
class Console:
    enable: bool
    level: str

@dataclass
class LoggingConfig:
    file: File
    console: Console

# 数据库配置
@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int

@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str

@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str

@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str

@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig



config_file = Path(__file__).parents[2]/ 'conf'/ 'app_config.yaml'
# 具体的文件路径
context = OmegaConf.load(config_file)
# print(type(context))
# 具体的对应类型格式
schema = OmegaConf.structured(AppConfig)
# 把它变成具体的实体类，这样你要调用实例里面的属性就可以有提示，更好的操作
# to_object 就是将合并后的conf转成一个对象，变成一个实例对象
app_config : AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))


if __name__ == "__main__":
    print(app_config.logging.file.path)