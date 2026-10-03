import json
import os
from typing import cast

from openai import APIStatusError, AuthenticationError, OpenAI, RateLimitError
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
)
from tools import TOOLS, IMPLEMENTATIONS


def get_client(test: bool = True):
    client = OpenAI(
        api_key=os.getenv("GLM_API_KEY"),
        base_url="https://open.bigmodel.cn/api/coding/paas/v4",  # 关键：Coding Plan 专属端点
    )

    if test:
        try:
            resp = client.chat.completions.create(
                model="glm-4.6",
                messages=[{"role": "user", "content": "你好，介绍一下你自己"}],
            )
            print(resp.choices[0].message.content)
        except Exception as e:
            print(friendly_error(e))
    return client

def friendly_error(exc: Exception) -> str:
    if isinstance(exc, AuthenticationError):
        return "api key error"      # 填：key 错了该干嘛
    if isinstance(exc, RateLimitError):
        return "wait a minute"      # 填：稍后再试之类
    # 继续补 Timeout / Connection / NotFound
    if isinstance(exc, APIStatusError):
        return f"API 返回错误 （HTTP{exc.status_code}): {exc.message}"     # 父类兜底：把 exc.status_code 和 exc.message 放进去
    return f"未知错误：{exc!r}"

def chat(client: OpenAI, messages: list[ChatCompletionMessageParam]) -> ChatCompletionMessage | None:
    # 测试通过不代表以后每次运行都能通过，因此做一个简易chat用于示例
    try:
        resp = client.chat.completions.create(
            model="glm-4.6",
            messages=messages,
            tools=TOOLS,  # TOOLS 已在 tools.py 用 ChatCompletionToolParam 注解，类型天然对齐
        )
        return resp.choices[0].message
    except Exception as e:
        print(friendly_error(e))
        return None

def build_system_prompt() -> str:
    tool_lines = "\n".join(
        f"- {t['function']['name']}：{t['function'].get('description', '')}"
        for t in TOOLS
    )
    return f"""你是 simple_agent，一个终端编程助手。

    你可用且仅可用以下工具：
    {tool_lines}

    规则：
    - 上述工具做不到的请求（如订机票、发邮件）：不要调用任何工具，直接说明做不到，并说明你能做什么。
    - 禁止编造或调用清单之外的工具名。
    """


def main():
    MAX_ITERATIONS = 8
    try:
        client = get_client(test=False)
        # history 用 SDK 的输入消息类型注解：system/user/assistant/tool 四种形状的合法集合
        history: list[ChatCompletionMessageParam] = [{"role": "system", "content": build_system_prompt()}]
        while True:
            input_text = input()
            if input_text == "/exit":
                break
            if input_text == "/clear":
                history = [{"role": "system", "content": build_system_prompt()}]
                print("[info] 历史已清空")
                continue
            history.append({"role": "user", "content": input_text})
            # 计数器
            iter_count = 0
            while True:
                iter_count += 1
                if iter_count >= MAX_ITERATIONS:
                    print("[info] 本轮调用失败，回到输入")
                    break
                message = chat(client, history)
                if message is None:                      # 失败：回到输入提示符，不崩溃（FR1）
                    print("[info] 本轮调用失败，回到输入")
                    break
                if not message.tool_calls:               # 最终回答
                    print(message.content)
                    # content 类型是 str | None（带 tool_calls 时为 None），or "" 收敛为 str
                    history.append({"role": "assistant", "content": message.content or ""})
                    break                                # 只退内层循环，回到 input()
                history.append(cast(ChatCompletionAssistantMessageParam, cast(object, message.model_dump())))  # 带 tool_calls 的消息转 dict 进历史（坑7.2：必须先于 tool 消息）
                for tc in message.tool_calls:
                    # 新版 SDK 的 tool_calls 可能含 custom 等类型，本项目只支持 function；
                    # 协议要求每个 tool_call_id 都必须有 tool 消息应答，否则 API 400
                    if tc.type != "function":
                        history.append({"role": "tool", "tool_call_id": tc.id, "content": "[不支持的工具调用类型]"})
                        continue
                    print(f"[tool] {tc.function.name} {tc.function.arguments}")
                    retult = IMPLEMENTATIONS[tc.function.name](**json.loads(tc.function.arguments))
                    history.append({"role":"tool", "tool_call_id":tc.id, "content":str(retult)})
    except KeyboardInterrupt:
        print("[info] 已退出")


if __name__ == "__main__":
    main()
