
from ddgs import DDGS
import subprocess

from openai.types.chat import ChatCompletionToolParam

# 用 SDK 官方类型注解：类型检查器从头到尾把关，agent.py 的 cast 桥接也不再需要
TOOLS: list[ChatCompletionToolParam] = [
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
    },
    {
    "type": "function",
        "function": {
            "name": "run_command",
            "description": "执行 shell 命令，30s 超时；执行前终端里确认；输出超 4000 字符截断返回退出码+stdout/stderr。",
            "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "终端指令"}
            },
            "required": ["command"]
            }
        }
    },
    {
    "type": "function",
        "function": {
            "name": "web_search",
            "description": "网络搜索，返回前 5 条结果的标题+摘要+链接。",
            "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索内容"}
            },
            "required": ["query"]
            }
        }
    }
]

def read_file(path: str, max_chars: int = 8000) -> str:
    # 读本地文件，超过 max_chars 截断并在结果里注明"已截断"；文件不存在返回错误信息（给模型看，不是抛异常）
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(max_chars+1)
        if len(content) > max_chars:
            # str 不可变：切片产生新对象，必须重新绑定到变量（对切片做 += 会抛 TypeError）
            content = content[:max_chars] + "\n（已截断）"
        return content
    # except FileNotFoundError:
    #     return f"文件不存在：{path}"
    except (OSError, UnicodeDecodeError) as e: 
        return f"读取失败：{e}"

# 执行 shell 命令，30s 超时；执行前终端里 y/N 人工确认（显示完整命令）；输出超 4000 字符截断；返回退出码 + stdout/stderr
def run_command(command:str) -> str:
    answer = input(f"\n 执行 shell 命令：{command}？y/N").strip().lower()
    if answer != "y":
        return "用户取消命令"
    try:
        proc = subprocess.run(
            command, 
            shell=True, 
            timeout=30, 
            encoding="utf-8", 
            errors="replace", 
            capture_output=True, # 收住 stdout/stderr，不然直接糊终端
            text=True)
        out = proc.stdout        # text=True + capture_output 下，无输出时是 ""，不会是 None，可放心用
        err = proc.stderr
        # len(out) > 4000 时切到 4000 并加"（已截断）"，err 同理
        if len(out) > 4000:
            out = out[:4000] + "（已截断）"
        if len(err) > 4000:
            err = err[:4000] + "（已截断）"
        # 把 proc.returncode、out、err 拼成一段返回
        return_str = f"退出码：{proc.returncode}\nstdout：{out}\nstderr：{err}"

        return return_str
    except subprocess.TimeoutExpired:
        return "命令超时终止"
    # except subprocess.CalledProcessError as e:
    #     return f"执行失败：{e}"

def web_search(query: str) -> str:
    try:
        results = DDGS().text(query, max_results=5)
    except Exception as e:
        return f"搜索失败：{e}"
    
    if not results:
        return "没有搜索结果"
    
    return_str = ""
    for i, result in enumerate(results, 1):
        return_str += f"{i}. {result['title']}\n摘要：{result['body']}\n链接：{result['href']}\n\n"

    
    return return_str


IMPLEMENTATIONS = {
    "read_file": read_file,
    "run_command": run_command,
    "web_search": web_search
}
