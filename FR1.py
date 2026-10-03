import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GLM_API_KEY"),
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",  # 关键：Coding Plan 专属端点
)
resp = client.chat.completions.create(
    model="glm-4.6",
    messages=[{"role": "user", "content": "你好，介绍一下你自己"}],
)
print(resp.choices[0].message.content)
