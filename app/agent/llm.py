from langchain.chat_models import init_chat_model
import os
llm = init_chat_model(
    model = "GLM-5.1",
    model_provider= "openai",
    api_key = os.getenv("ZHIPU_API_KEY"),
    base_url = "https://open.bigmodel.cn/api/paas/v4/",
    temperature = 0
)

if __name__ == "__main__":
    print(llm.invoke("你好").content)

