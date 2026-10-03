# simple_agent 需求文档 v1.0

> 出处：方向6 阶段1（harness 预习）+ Astra R4 计划 2026.09 双出口里程碑
> 日期：2026-10-03 | 时间盒：今天半天（约 4-5h），之后扩展
> 铁律：无工件不计完成。今天的"完成"= 第 4 节验收用例全过 + 第 6 节交付物齐全。

---

## 0. 目标与定位

**手写一个约 200 行的最小 coding agent**：终端里多轮对话，模型可以调用工具
（读文件 / 执行命令 / 搜索），拿到结果后继续思考，直到给出最终回答。

**为什么手写、不用框架**：这个项目的产物不是"一个能用的 agent"，而是
"你能讲清楚 agent loop 每一步发生了什么"。LangChain 之类框架会把最值得
学的部分（消息序列、工具回填、终止条件）全部藏掉。**禁止使用任何 agent 框架**，
只用 `openai` SDK（或 `requests`）+ 标准库。

完成后你将能回答（也是面试考点）：
- Agent 和普通 RAG Chain 的本质区别是什么？（循环 + 自主决定下一步）
- 一次工具调用的完整消息序列长什么样？
- 为什么必须有 max iterations 这种硬停止条件？

---

## 1. 总体规格

- **形态**：终端 REPL。`python agent.py` 启动，显示提示符，用户输入 → 模型思考 →
  （可能）调工具 → 最终回答，然后等待下一轮输入。
- **模型**：GLM（open.bigmodel.cn）或 DeepSeek（api.deepseek.com），二选一。
  两者都兼容 OpenAI Chat Completions 协议，用 `openai` SDK 时只需改 `base_url`
  和模型名（具体模型名查官方文档，如 `deepseek-chat`）。
- **密钥**：从环境变量读（如 `SIMPLE_AGENT_API_KEY`），**绝不硬编码在代码里**，
  不提交到任何仓库。
- **结构**：单文件 `agent.py` 为主（可以拆 `tools.py`），核心逻辑（去掉注释和空行）
  **≤ 250 行**。明显超过说明过度设计了，回来砍。

---

## 2. 功能需求

| # | 需求 | 具体行为 |
|---|---|---|
| FR1 | LLM 接入 | OpenAI 兼容接口，API key 从环境变量读；API 报错时打印友好错误并**回到输入提示符，不崩溃**（可加 1 次重试） |
| FR2 | 工具注册 | 工具用 JSON Schema 声明（见 2.1 示例），集中放在一个 `TOOLS` 列表；新增工具 = 加一个 schema + 一个 Python 函数 |
| FR3 | Agent 主循环 | 发送全部历史 → 若返回 `tool_calls` 则执行工具、把结果按协议回填、再次发送，**循环**；若无 `tool_calls` 则本轮结束，输出回答 |
| FR4 | 工具 `read_file` | 参数 `path`（必填）、`max_chars`（可选，默认 8000）。读本地文本文件；超过 max_chars 截断并在结果里注明"已截断"；文件不存在返回错误信息（给模型看，不是抛异常） |
| FR5 | 工具 `run_command` | 参数 `command`。执行 shell 命令，30s 超时；**执行前终端里 y/N 人工确认**（显示完整命令）；输出超 4000 字符截断；返回退出码 + stdout/stderr |
| FR6 | 工具 `web_search` | 参数 `query`，返回前 5 条结果的标题+摘要+链接。实现方案三选一（见 2.2） |
| FR7 | 基本拒答 | 系统提示词里声明能力边界（只有这 3 个工具）。用户要求工具做不到的事（如"帮我订机票"）时，模型**不乱调工具**，直接说明做不到、能做什么。这是验收场景，不是可选项 |
| FR8 | 会话管理 | 多轮对话（历史跨轮保留，含工具中间消息）；`/exit` 退出；`/clear` 清空历史重新开始；Ctrl+C 不留垃圾栈追踪 |

### 2.1 工具 schema 示例（照这个形状写，另两个自己推）

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "读取本地文本文件内容。路径相对于当前目录或使用绝对路径。",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "文件路径"},
        "max_chars": {"type": "integer", "description": "最多返回的字符数，默认 8000"}
      },
      "required": ["path"]
    }
  }
}
```

### 2.2 搜索工具三选一

| 方案 | 做法 | 优缺点 |
|---|---|---|
| A. DuckDuckGo | `pip install ddgs`，免 key | 最贴"web 搜索"字面；国内网络可能不稳，失败换 B |
| B. 本地文件搜索 | 自写：遍历目录，返回包含关键词的文件名+行号 | 无网络依赖、100% 可控；也算合法的"搜索工具" |
| C. 付费搜索 API | 博查 / Serper 等（有 key 才用） | 结果质量最好 |

A/B 任一通过验收即算满足 FR6。

---

## 3. 非功能需求

- **NFR1** 不使用任何 agent 框架（LangChain / LlamaIndex / smolagents 等）。
- **NFR2** 依赖 ≤ 3 个第三方包（`openai` + `ddgs` 顶多再加一个）。
- **NFR3** Windows 兼容：subprocess 输出中文不乱码（提示：`subprocess.run(..., encoding="utf-8", errors="replace")`；git-bash 存在，`shell=True` 即可用 bash 语法）。
- **NFR4** 消息历史是 append-only：**绝不修改或删除已存在的消息**，只追加。
  （这是真实 harness 的铁律，也是 prompt caching 的前提——面试会问）
- **NFR5** 每一步在终端可见：发起调用前打印 `[tool] read_file {"path": "..."}`，
  拿到结果打印一行摘要。你今天要能亲眼看见循环在转。

---

## 4. 验收用例（今天"完成"的客观定义）

准备：在项目目录放一个 `sample.txt`（随便写几行中文+英文）。

| # | 用户输入 | 必须发生 |
|---|---|---|
| T1 | "用一句话解释 agent loop 和普通 RAG chain 的区别" | 直接回答，**0 次工具调用** |
| T2 | "读一下 sample.txt 并用两点总结" | 调 `read_file` → 给出两点总结 |
| T3 | "这个目录下有几个 .py 文件？" | 调 `run_command`（有 y/N 确认）→ 给出正确数字 |
| T4 | "搜一下 Python 3.13 有什么新特性" | 调 `web_search` → 归纳出至少 2 条特性（附来源） |
| T5 | "把今天的日期写入 date.txt，然后读出来确认写对了" | **连续 ≥2 次工具调用**（模型自己拆步骤），最终确认写入成功。这是本项目最核心的一条 |
| T6 | "帮我订一张明天去北京的机票" | 不调任何工具，直接说明做不到 + 列出自己能做什么（FR7 拒答） |
| T7 | 构造一个会死循环的任务（如让模型反复搜索同一个词）| `max_iterations=8` 触发后优雅停止并提示，不崩溃、不烧钱 |

T1–T7 全过 = 今天完成。

---

## 5. 半天时间盒（3 块，每块结束有检查点）

| 块 | 时长 | 内容 | 检查点 |
|---|---|---|---|
| 块1 | ~1.5h | 打通 API：单轮对话 → 手写一个工具 schema，让模型**单次**调用 `read_file` 并把结果回填拿到回答（还没有循环，while 循环最后加） | T2 的简化版跑通：请求里有 tool_calls，你能解析 arguments，能拼出 role="tool" 的回填消息 |
| 块2 | ~1.5h | 加 while 主循环 + `run_command`（含 y/N 确认）+ max_iterations + `/exit` `/clear` + 错误不崩溃 | T1 T2 T3 T5 T7 过 |
| 块3 | ~1h | `web_search` + T4 T6 + 录运行记录 + 写 DESIGN.md | 全部过，交付物齐 |

**卡住 20 分钟以上就回来问我，不要自己硬磨**——今天的目标是理解 loop，不是练调试。

---

## 6. 交付物清单（缺一不可）

```
simple_agent/
├── REQUIREMENTS.md      # 本文档
├── agent.py             # 主程序（可拆 tools.py）
├── requirements.txt     # 依赖
├── sample.txt           # 测试用文件
├── DESIGN.md            # 设计说明，回答第 9 节的问题
└── runs/                # 5 条运行记录
    ├── run1.md ... run5.md
```

**运行记录格式**（每条一档，对应验收用例至少 5 条，T5 必录）：
```markdown
# run3：统计 .py 文件
- 用户：这个目录下有几个 .py 文件？
- 工具调用：run_command("ls *.py | wc -l") → 输出 "3"
- 最终回答：当前目录有 3 个 .py 文件。
- 观察：模型一步到位 / 先 ls 再数了两步。
```

---

## 7. 已知坑（先读一遍，能省你 2 小时）

1. **`tool_calls[0].function.arguments` 是 JSON 字符串，不是 dict**——必须 `json.loads()`。
2. **消息顺序**：模型返回 tool_calls 后，必须先把这条带 `tool_calls` 的 assistant
   消息 append 进历史，**再** append 每个工具的 `{"role": "tool", "tool_call_id": ..., "content": ...}`。
   顺序或字段错了 API 直接 400——这是所有人第一个卡住的坑。
3. 一次回复可能带**多个** tool_calls（并行调用），要全部执行、全部回填。
4. 每个工具结果必须带对应的 `tool_call_id`，模型靠它对号入座。
5. 工具执行出错（文件不存在等）**不要抛异常**，把错误文本作为 tool 消息返回——
   让模型自己决定重试还是换路。这才是 agent。
6. Windows 中文乱码：subprocess 加 `encoding="utf-8", errors="replace"`。
7. 大文件/长输出必须截断（FR4/FR5 已给数值），否则一轮就把上下文撑爆。
8. API key 放环境变量；`setx` 或当前终端 `export` 都行，别写进代码。

---

## 8. 扩展路线（今天不做，做完回来挑）

按 harness 六维度排的优先级：
1. **上下文管理**：历史超长时裁剪/压缩旧的工具结果（真实 harness 的核心难题）
2. **安全**：run_command 白名单/黑名单，替代每条 y/N
3. **评估**：固定 10 个任务的测试脚本，统计成功率和平均轮数（对应 evals 维度）
4. 流式输出（stream=True 打字机效果）
5. 第四个工具：write_file / edit_file，让它能真正改代码
6. token 用量统计与成本显示

---

## 9. DESIGN.md 必答问题（写设计说明 = 把知识固化）

1. 画出（文字版即可）一轮带工具调用的完整消息序列，标出每条消息的 role。
2. 为什么 max_iterations 是必需的？没有它会出什么事？
3. 你的拒答（T6）是靠什么实现的——模型能力还是 prompt 工程？证据是什么？
4. T5 里模型自己拆了两步。这个"拆步骤"的决定是谁做的、在哪个环节？
5. 如果把工具从 3 个加到 20 个，调用准确率会发生什么？为什么？
   （对应 D6 路线图"工具数量 vs 调用准确率"问题）

---

## 10. 面试考点映射（功利版速记）

| 本项目踩过的点 | 面试怎么问 |
|---|---|
| FR3 主循环 | "讲一下 agent loop 的消息流转" |
| 7.2 消息顺序 | "tool calling 的消息格式是什么，顺序有要求吗" |
| FR7 拒答 | "怎么防止 agent 幻觉调用不存在的工具/乱调工具" |
| NFR4 append-only | "为什么消息历史不能改？prompt caching 原理" |
| FR5 人工确认 | "生产环境 agent 执行命令的安全设计" |
| T5 多步 | "ReAct 和 function calling 循环的关系" |
