import os
import subprocess
import sys
import tempfile
import uuid
from typing import Annotated, Sequence
from typing_extensions import TypedDict

# 设置 matplotlib 在无 GUI 的后台模式下工作
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from app.services.model_registry import build_chat_model, has_model
from app.tools.ragflow_tool import query_data_structure_knowledge

@tool
def execute_python_code(code: str) -> str:
    """
    在隔离的子进程中安全执行一段 Python 代码，并返回标准输出(stdout)或错误信息(stderr)。
    适用于运行 Python 算法片段、测试 Vue 数据结构原理或验证执行结果。
    """
    malicious_keywords = ["os.system", "subprocess", "rmtree", "shutil", "socket", "sys.exit"]
    for keyword in malicious_keywords:
        if keyword in code:
            return f"Error: 触发安全规则拦截。代码中禁止使用 '{keyword}'。"
            
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write(code)
        temp_path = temp_file.name
        
    try:
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        output = ""
        if result.stdout:
            output += f"[Stdout]:\n{result.stdout}\n"
        if result.stderr:
            output += f"[Stderr]:\n{result.stderr}\n"
        return output or "代码运行成功，无输出内容。"
    except subprocess.TimeoutExpired:
        return "Error: 代码执行超时 (超过 5 秒限时)，可能是由于无限循环导致。"
    except Exception as e:
        return f"Error: 执行异常: {str(e)}"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

from matplotlib.figure import Figure

@tool
def generate_algorithm_diagram(structure_type: str, nodes: str, edges: str) -> str:
    """
    智能算法图解生成器。当学生需要查看直观的数据结构图形、逻辑指向图谱，或者用户显式提出“画图”、“绘制结构图”的要求时，调用此工具。
    - structure_type: 可选 'linked_list' (链表), 'binary_tree' (二叉树), 'graph' (图/网)
    - nodes: 逗号分隔的节点名称列表，如 'A,B,C,D'
    - edges: 逗号分隔的边关系列表，格式为 '源-宿'，如 'A-B,B-C,C-D'。如果是链表且是单向，必须是 'A-B,B-C' 等。
    返回保存图片的完整 Markdown 引用链接。
    """
    try:
        node_list = [n.strip() for n in nodes.split(",") if n.strip()]
        edge_list = [e.strip().split("-") for e in edges.split(",") if len(e.strip().split("-")) == 2]
        
        # 纯面向对象接口创建 figure，不占用全局 pyplot 状态，防止并发竞态冲突
        fig = Figure(figsize=(6, 4), facecolor='none')
        ax = fig.subplots()
        
        # 动态构建拓扑
        if structure_type == 'linked_list':
            G = nx.DiGraph()
            for i in range(len(node_list) - 1):
                G.add_edge(node_list[i], node_list[i+1])
            pos = {val: (i * 2, 0) for i, val in enumerate(node_list)}
            nx.draw(G, pos, with_labels=True, node_color='#6366f1', node_size=1200, 
                    font_color='white', font_weight='bold', edge_color='#818cf8', 
                    arrowsize=18, width=2.5, font_size=10, ax=ax)
                    
        elif structure_type == 'binary_tree':
            G = nx.DiGraph()
            G.add_nodes_from(node_list)
            for u, v in edge_list:
                G.add_edge(u.strip(), v.strip())
            pos = nx.shell_layout(G)
            nx.draw(G, pos, with_labels=True, node_color='#8b5cf6', node_size=1000, 
                    font_color='white', font_weight='bold', edge_color='#c084fc', 
                    arrowsize=15, width=2.0, ax=ax)
                    
        elif structure_type == 'graph':
            G = nx.Graph()
            G.add_nodes_from(node_list)
            for u, v in edge_list:
                G.add_edge(u.strip(), v.strip())
            pos = nx.spring_layout(G)
            nx.draw(G, pos, with_labels=True, node_color='#06b6d4', node_size=1000, 
                    font_color='white', font_weight='bold', edge_color='#22d3ee', 
                    width=2.0, ax=ax)
                    
        # 静态文件夹保存路径 (backend/app/static/generated/)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_dir = os.path.join(current_dir, "static", "generated")
        os.makedirs(static_dir, exist_ok=True)
        img_filename = f"diag_{uuid.uuid4().hex[:8]}.png"
        img_path = os.path.join(static_dir, img_filename)
        
        # 导出透明背景的高清图片
        fig.savefig(img_path, bbox_inches='tight', transparent=True, dpi=180)
        
        # 返回图片 URL
        return f"![算法结构图解](http://localhost:8000/static/generated/{img_filename})"
    except Exception as e:
        return f"Error while generating diagram: {str(e)}"

DEFAULT_AGENT_MODELS = {
    "agent_planner": "qwen3.7-max",
    "agent_tutor": "qwen3.7-plus",
    "agent_researcher": "qwen3.6-plus",
    "agent_coder": "kimi-k2.7-code",
    "agent_visual_guide": "qwen-image-2.0-pro",
}

# 向下兼容引用，供画像分析和普通检索缺省调用。
llm_max = build_chat_model(DEFAULT_AGENT_MODELS["agent_planner"], temperature=0)
llm_flash = build_chat_model(DEFAULT_AGENT_MODELS["agent_researcher"], temperature=0.1)
llm = llm_max

tools = [query_data_structure_knowledge, execute_python_code, generate_algorithm_diagram]
llm_max_with_tools = llm_max.bind_tools(tools)
llm_flash_with_tools = llm_flash.bind_tools(tools)

def _get_configurable(config: RunnableConfig | dict | None) -> dict:
    if not isinstance(config, dict):
        return {}
    configurable = config.get("configurable") or {}
    return configurable if isinstance(configurable, dict) else {}


def _fallback_agent_id(last_user_message: str) -> str:
    if "【用户当前代码】" in last_user_message or "【代码AI诊断】" in last_user_message:
        return "agent_coder"
    return "agent_tutor"


def resolve_runtime_model_id(config: RunnableConfig | dict | None, last_user_message: str = "") -> str:
    configurable = _get_configurable(config)
    requested_model = configurable.get("agent_model")
    if has_model(requested_model, category="text"):
        return requested_model

    agent_id = configurable.get("agent_id") or _fallback_agent_id(last_user_message)
    fallback_model = DEFAULT_AGENT_MODELS.get(agent_id) or DEFAULT_AGENT_MODELS[_fallback_agent_id(last_user_message)]
    if has_model(fallback_model, category="text"):
        return fallback_model
    return DEFAULT_AGENT_MODELS["agent_tutor"]


def build_system_prompt(custom_prompt: str | None = None) -> SystemMessage:
    prompt = (
        "你是一个专业的《数据结构与算法》智能私教，采用严苛的“苏格拉底启发式教学法（Socratic Method）”与“支架式教学（Scaffolding）”模式引导学生。你同时协同多个智能体角色（Alina 规划师、Prof.X 启发式导师、CodeNinja 代码精灵）来与学生互动。\n\n"
        "你必须死守以下核心教学铁律，如有违反将被严厉惩罚：\n"
        "1. 【单次篇幅与步长限制】：你每次的回复必须短小精悍，分段清晰，文本总量严格控制在 200 字以内！每次只解决或讲解一个微小的算法概念、物理细节或代码行，绝对不进行长篇大论！\n"
        "2. 【苏格拉底提问律】：你绝对不可以直接给出算法的最终完整正确代码或直接说出核心结论！必须通过提问、追问来让学生自己思考并写出代码或得出推论。你每一轮回答的结尾，必须以一个具体的思考问题、逻辑选择或伪代码填空收尾，引导学生回答。\n"
        "3. 【四阶段教学脚手架】：依据用户的学习进度，严格分步走：\n"
        "   - 阶段一（概念引入）：由 Alina 明确目标，Prof. X 用通俗类比（费曼技巧）介绍概念核心，并以一个概念思考题收尾。严禁在此时提供任何代码或拓扑图解！\n"
        "   - 阶段二（直观图解）：在学生对概念作答后，你判定对错。如正确，提供直观图解（调用 `generate_algorithm_diagram` 或 Mermaid 代码块），并抛出一个涉及指针或空间流转的逻辑问题，引导学生写出关键伪代码步骤。\n"
        "   - 阶段三（代码实战）：在学生逻辑明确后，由 CodeNinja 介入，提供一个“挖空（挖去核心代码）”的不完整代码框架，让学生去右侧代码沙箱中补全并测试。严禁在此阶段给正确的完整代码！\n"
        "   - 阶段四（纠错与通关）：根据代码沙箱在后台执行的报错信息（调用 `execute_python_code`），由 CodeNinja 启发式引导学生定位 Bug（如：“看看第 5 行的 next 是否可能为空？”）。运行全部通过后，Alina 祝贺通关并更新路径。\n"
        "4. 【工具使用】：\n"
        "   - 调试/运行代码调用 `execute_python_code`。\n"
        "   - 查阅官方大纲与课件调用 `query_data_structure_knowledge`。\n"
        "   - 绘制结构图形物理逻辑调用 `generate_algorithm_diagram`。\n"
        "   - 讲解中如需对比，请用 Markdown Table 进行美化输出。\n\n"
        "请严格根据学生目前的实际反馈，分步执行上述脚手架流程，每次回复必须以引导提问或挖空收尾，控制在 200 字内。"
    )
    if custom_prompt:
        prompt += f"\n\n当前激活 Agent 的自定义系统指令如下，请在不违反教学铁律的前提下优先体现该角色设定：\n{custom_prompt}"
    return SystemMessage(content=prompt)


def call_model(state: State, config: RunnableConfig | None = None):
    configurable = _get_configurable(config)
    system_prompt = SystemMessage(
        content=build_system_prompt(configurable.get("agent_prompt")).content
    )
    messages = [system_prompt] + list(state["messages"])
    
    # 智能分流路由：根据输入内容的复杂度及特征选择大模型底座
    last_user_message = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human" or msg.__class__.__name__ == "HumanMessage":
            last_user_message = msg.content
            break
            
    model_id = resolve_runtime_model_id(config, last_user_message)
    temperature = 0 if model_id in {"qwen3.7-max", "kimi-k2.7-code"} else 0.1
    print(f"[Router] Routing to selected model: {model_id}", flush=True)
    
    # Use .stream() instead of .invoke() to enable token-level streaming
    # This allows astream_events to produce on_chat_model_stream events
    model = build_chat_model(model_id, temperature=temperature).bind_tools(tools)
    full_response = None
    for chunk in model.stream(messages):
        if full_response is None:
            full_response = chunk
        else:
            full_response = full_response + chunk
        
    return {"messages": [full_response]}

workflow = StateGraph(State)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

memory = MemorySaver()
agent_graph = workflow.compile(checkpointer=memory)
