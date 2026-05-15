import uuid
from urllib.request import Request

from fastapi import FastAPI

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.core.context import request_id_context_var

app = FastAPI(lifespan=lifespan)

app.include_router(query_router)

# 中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # 在每一个请求被处理之前（但是前端已经将请求发送过来了），添加一个id
    request_id = uuid.uuid4()
    # 这里需要定义一个contextvar，它是python的协程本地变量，它的作用就在于每一次创建一个异步的协程任务的时候，都会维持一个全局变量
    # 它有两个方法，一个是set，存入变量，一个是get，取出变量，而且是整个协程执行之间都会保存这个变量的副本
    request_id_context_var.set(request_id)
    response = await call_next(request)

    return response