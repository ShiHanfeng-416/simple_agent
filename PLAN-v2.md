# simple_agent → 工业级 harness 升级课程（v2 总纲）

> **本文档是课程的唯一进度真相源。对话窗口有限、可随时新开对话：续课时先读本文档 +
> `notes/` 最新一篇，即可无缝继续。每完成一步必须更新第 5 节进度表和第 6 节决策记录。**
>
> 开课：2026-11-22 | 学员进度基线：v1.0 已完成（235 行 agent loop，T1-T7 全过，10-03 抽查暴露协议层弱项）

---

## 0. 课程定位与运作规则（宪法，不可随意改）

**定位**：把"只有 agent loop 的简易 harness"一步步提升为 **dsh 那种考虑周全的工业级 harness**。
交付物是"我的 mini-harness 及其演进过程"，**不是**"本地跑通一个 dsh"。

| # | 规则 | 说明 |
|---|---|---|
| R1 | 每模块先原理教学 | 讲清机制 + 各家做法（dsh/pi/Claude Code/Codex），**讨论后才开始拟写**。不讨论不写码 |
| R2 | 教学为主，AI 落地 | 不再手抄。分模块设计 → 逐步让 agent 写代码落地。模块拆分足够细，每次只动一块 |
| R3 | 资料归档 | 复习资料、中途试错的坑，全部进 `notes/`（面试素材库："你遇到什么困难、如何解决"） |
| R4 | 参照系外置 | dsh 源码 clone 在 `d:/code/AI/deepseek-harness`（**项目主干之外**），只读参照，不依赖 |
| R5 | 对比常态化 | 每个设计决策都要问一遍：dsh / pi / Claude Code / Codex 各怎么做？允许混搭或替换 |
| R6 | 半成品教学法 | 允许先做半成品 → 后续假设业务场景 → 被坑 → 补救（剧本见第 4 节，提前预埋） |
| R7 | 进度落盘 | 任何设计定稿/阶段完成/剧本触发，当场更新本文档，不依赖对话记忆 |

**延续 v1.0 铁律**：不用任何 agent 框架；密钥只从环境变量读；消息历史 append-only（除 M6 明确讨论的 compaction 场景）。

---

## 1. 参照系

| 对象 | 语言/许可 | 角色 | 核心主张 |
|---|---|---|---|
| **DeepSeek Harness (dsh)** | TS / MIT | **主线地图**（模块怎么拆） | Everything is a Plugin：模型、工具、会话、沙箱、存储、**主循环本身**皆可替换；基于 Cordis（服务+类型化事件+可撤销副作用） |
| **pi** (badlogic/pi-mono) | TS / MIT | 极简对照样本 | 强模型只需极简 scaffolding：膨胀的系统提示词和框架开销是弱模型时代的遗产。与 dsh 光谱两端，每次取舍两头看 |
| **Claude Code** | 闭源 | 功能设计清单（该做什么） | 权限分级、CLAUDE.md 记忆、auto-compact、Edit 唯一匹配约束；只能学设计，学不到实现 |
| **Codex CLI** | Rust / 开源 | 安全专题（沙箱与审批） | OS 级沙箱（Seatbelt/Landlock，Windows 不可用）+ approval 分级；M7 精读 |

其他 agent CLI（Gemini CLI / opencode / Qwen Code 等）随课程按需引入，引入时更新此表。

---

## 2. 目标形态（结课时 mini-harness 长什么样）

```
simple_agent/                     # 逐步长成多模块包
├── agent.py                      # 入口（REPL 保持可用）
├── loop.py                       # M4：主循环（可替换的驱动）
├── model_adapter.py              # M4：模型适配器（GLM/DeepSeek 可切）
├── tools/
│   ├── registry.py               # M3：注册表 + 结构化错误协议
│   ├── files.py                  # M2：read/write/edit
│   ├── shell.py                  # M7：命令执行 + 权限
│   └── search.py
├── context.py                    # M6：token 预算 + compaction
├── sessions.py                   # M8：JSONL 持久化 + /resume
├── permissions.py                # M7：allow/ask/deny 规则
├── PLAN-v2.md                    # 本文档
├── REQUIREMENTS.md               # v1.0（存档）
├── notes/                        # R3：复习 + 试错档案
└── evals/                        # M10：任务集 + 统计脚本
```

---

## 3. 模块拆分（每模块固定流程：①原理教学 → ②讨论定稿 → ③AI 落地 → ④验收 → ⑤剧本打脸 → ⑥补救 → ⑦复习卡入 notes/）

### M0 课程准备（本次）
- [x] GitHub 同步 v1.0 收尾改动
- [x] `notes/` 建立，复习资料归档
- [ ] dsh clone 到项目外（depth 1）
- [ ] 本文档 + memory 固化
- 验收：新开对话能凭本文档续课

### M1 现状审计 + dsh 地图
- 原理：harness 六维度；dsh 插件域全览（models/tools/skills/sessions/sandboxes/storage/loops/scheduling/UI）
- 落地：`notes/AUDIT-m1.md` —— dsh 每个域 ↔ simple_agent 现状（对应哪几行 / 缺失）→ 差距清单即后续课程表
- 对比：pi 的最小工具面 vs 我们的 3 工具；两家"什么才算 harness 必需件"的分歧
- 验收：能回答"dsh 认为主循环为什么要可替换"

### M2 文件写入三件套：write_file / edit_file（+read 强化）
- 原理：为什么 Edit 用 old_str/new_str 全字面替换（Claude Code 实证）而非 diff 补丁；read-before-write 协议；唯一匹配约束；绝对路径约定；Windows 编码与 CRLF
- 落地：`tools/files.py`，通过验收用例
- 对比：Claude Code Read/Write/Edit 约束、pi 的文件工具、dsh 工具插件接口
- 剧本：A（多匹配改错处）、B（未读就改，幻觉编辑）→ 见第 4 节
- 验收：模型能"修复一个带 bug 的 .py 文件并跑测试确认"

### M3 工具注册表 + 结构化错误协议
- 原理：schema 从函数签名/声明生成；注册表模块化（加工具不再改 agent.py 主干）；工具结果的结构（content + is_error）——为什么纯字符串分不清"命令失败"和"输出恰好像错误"
- 落地：`tools/registry.py`，三个旧工具迁移
- 剧本：C（错误无标志 → 模型把报错当正常输出继续推理）
- 对比：dsh 工具插件、Codex 工具定义、pi 的 thin tool surface

### M4 主循环拆包 + 模型适配器（"default driver"思想）
- 原理：loop 即接口（dsh：主循环只是默认实现）；为什么可替换（审批钩子、并行工具调用、恢复执行）；适配器模式隔离 OpenAI 协议细节
- 落地：`loop.py` + `model_adapter.py`，agent.py 瘦身为入口
- 剧本：D（适配器只测非流式 → 切流式 tool_calls 分片乱序，arguments JSON 拼不完整）
- 对比：dsh core/agent-loop、pi 的循环、Codex 会话模型
- 机动：流式输出（SSE、index 聚合）可作为本模块加餐

### M5 ~~流式输出~~（并入 M4 机动项）

### M6 上下文管理（重头戏一）
- 原理：token 预算感知；截断 vs 摘要压缩（compaction）；append-only 铁律与压缩的表面矛盾（答案：压缩=开新段注入摘要，不改写历史 → prompt caching 兼容）；大工具结果的占坑问题
- 落地：`context.py`：预算统计 + compaction
- 剧本：E（长会话滑窗裁掉关键决策 → agent 推翻重来重复犯错烧钱）
- 对比：Claude Code auto-compact、dsh sessions/storage、pi 的极简立场（它认为该问题被高估？课堂辩论）
- 验收：构造超长会话，压缩后 agent 仍记得早期关键决策；能讲清与 prompt caching 的关系

### M7 安全与权限（重头戏二）
- 原理：权限三态（allow/ask/deny）；命令白名单的解析陷阱（shell 语法：`;` `&&` 管道绕过、参数级匹配）；沙箱思想（OS 级为何强、Windows 为何缺位）；工作区边界（路径逃逸 `../`）
- 落地：`permissions.py` + `tools/shell.py` 改造，y/N 升级为规则表
- 剧本：F（前缀白名单放行 `git push --force`；`echo ok && rm` 绕过）
- 对比：Claude Code permission modes、Codex sandbox/approval 精读、dsh sandbox 插件、pi 的 YOLO mode 与 podman 沙箱（光谱两端再次对照）
- 验收：攻击用例集全被拦截，正常用例不被误伤

### M8 会话持久化 + /resume
- 原理：JSONL append-only 日志；崩溃恢复；resume 时上下文重建
- 落地：`sessions.py`
- 剧本：G（写日志中途崩溃 → 末行残缺 → resume 解析炸）
- 对比：dsh sessions、Claude Code --resume、Codex resume

### M9 项目记忆 + 系统提示词组装
- 原理：AGENTS.md/CLAUDE.md 惯例；系统提示词的组装顺序（身份/工具/项目记忆/安全声明）；pi 的反方观点（提示词膨胀是问题）
- 落地：启动时读 AGENTS.md 注入；工具说明自动生成进系统提示词
- 验收：AGENTS.md 里写一条项目约定，agent 行为随之改变

### M10 评估（evals）
- 原理：任务集设计（难度梯度、可判定性）；指标（成功率/平均轮数/成本）；回归意义
- 落地：`evals/` 10 任务 + 统计脚本；跑一次全量出报告
- 对比：各家 evals 公开做法
- 结课验收：mini-harness 全量 eval 报告 + 面试叙事线（notes/ 里的坑按"困难→解决"结构整理成文）

---

## 4. 业务场景剧本（R6 预埋打脸点，触发时在 notes/ 立档）

| # | 挂载模块 | 半成品缺陷 | 业务场景（假想） | 预期被打脸 | 补救方向 |
|---|---|---|---|---|---|
| A | M2 | edit_file 直接改第一个匹配 | 重构项目中改一处重复代码 | old_str 命中 3 处，改错位置，测试挂 | 唯一匹配强制，多匹配报错附行号 |
| B | M2 | 无 read-before-write 约束 | 模型凭记忆改没读过的文件 | 幻觉编辑：改动落在想象中的内容上 | 工具层强制先读（或 edit 前校验文件已读） |
| C | M3 | 错误以纯字符串返回 | 命令超时 vs 正常输出难分辨 | 模型把报错当成功继续推理 | 结构化结果 + is_error 标志 |
| D | M4 | 适配器只测非流式 | 业务要求打字机效果切流式 | tool_calls 增量分片，arguments 拼不完整 | 按 index 聚合增量，收齐再执行 |
| E | M6 | 简单滑窗截断旧历史 | 跨 20 轮的调试长会话 | 关键决策被裁，agent 推翻重来、重复犯错烧钱 | compaction：摘要注入 + 最近 K 轮保留 |
| F | M7 | 白名单按命令前缀匹配 | "允许 git 命令" 日常场景 | `git push --force`、`echo ok && rm -rf` 绕过 | shell 语法解析 + 参数级规则 |
| G | M8 | JSONL 直接追加写 | 会话中途进程被杀 | 末行残缺，/resume 解析崩溃 | 末行容错跳过 + 原子写入 |

> 剧本执行仪式：触发时先让缺陷真实发作（截图/记录入 notes/），再讨论补救方案，最后 AI 落地修复。
> **不许跳过"先发作"直接写防御代码——没见过坏事发生的教育不完整。**

---

## 5. 进度跟踪

| 模块 | 状态 | 完成日 | 备注 |
|---|---|---|---|
| M0 | 🔄 进行中 | — | 待：dsh clone、memory 固化 |
| M1-M10 | ⬜ 未开始 | — | 顺序执行，允许按讨论微调（改了要记第 6 节） |

**当前下一步**：M0 收尾 → M1 原理教学开讲。

## 6. 决策记录（ADR 摘要）

| # | 日期 | 决策 | 理由 |
|---|---|---|---|
| D1 | 11-22 | 主对标 dsh；Claude Code=功能清单；Codex=安全专题；pi=极简对照 | 唯一全开源可读且模块主张清晰；闭源只能学设计 |
| D2 | 11-22 | 教学模式改为"原理→讨论→AI 落地"，不再手抄 | 用户明确要求；重心从打字移到设计与原理 |
| D3 | 11-22 | 复习/试错资料统一入 `notes/` | 面试素材库："遇到的困难与解决" |
| D4 | 11-22 | dsh clone 放项目外，只读参照 | 交付物是自己的 harness，不是跑通 dsh |
| D5 | 11-22 | 半成品+剧本打脸教学法 | 缺陷要先真实发作再补救，工程直觉靠踩坑养成 |
| D6 | 11-22 | v1.0 铁律延续：无框架、env 密钥、append-only | 课程灵魂是"每一步都讲得清" |
