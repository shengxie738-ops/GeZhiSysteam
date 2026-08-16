import requests
from langchain_core.tools import tool
from app.core.config import settings

# 全局会话缓存
_session_cache: dict[str, str] = {}

def _get_or_create_chat_session(base_url: str, chat_id: str, api_key: str, thread_id: str = "default") -> str:
    if thread_id in _session_cache:
        return _session_cache[thread_id]

    url = f"{base_url}/chats/{chat_id}/sessions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, json={"name": f"rag-{thread_id}"}, headers=headers, timeout=15)
    resp.raise_for_status()
    res_json = resp.json()

    if res_json.get("code", -1) != 0:
        raise RuntimeError(f"创建 RAGFlow Chat 会话失败: {res_json.get('message', res_json)}")

    session_id = res_json["data"]["id"]
    _session_cache[thread_id] = session_id
    return session_id

@tool
def query_data_structure_knowledge(query: str) -> str:
    """
    用于查询本地《数据结构》课程知识库的工具。
    当用户询问关于数据结构、算法、树、图、链表、队列、栈、排序、查找等专业课程内容时，应该调用此工具进行检索。
    """
    api_key  = settings.RAGFLOW_API_KEY
    base_url = settings.RAGFLOW_BASE_URL.rstrip("/")
    chat_id  = settings.RAGFLOW_CHAT_ID

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        session_id = _get_or_create_chat_session(base_url, chat_id, api_key, thread_id="rag-default")

        url = f"{base_url}/chats/{chat_id}/completions"
        payload = {
            "question": query,
            "session_id": session_id,
            "stream": False
        }
        response = requests.post(url, json=payload, headers=headers, timeout=90)
        response.raise_for_status()
        res_json = response.json()

        if res_json.get("code", -1) != 0:
            error_msg = res_json.get("message", "未知错误")
            if "session" in error_msg.lower():
                _session_cache.pop("rag-default", None)
            return f"【知识库查询失败】RAGFlow 返回错误: {error_msg}"

        data = res_json.get("data", {})
        answer = data.get("answer", "")

        if not answer or "知识库中未找到" in answer:
            return f"在《数据结构》知识库中未找到关于「{query}」的相关内容，请尝试换一种问法，或该知识点尚未收录。"

        reference = data.get("reference", {})
        ref_docs = set()
        chunks = reference.get("chunks", []) if isinstance(reference, dict) else []
        for chunk in chunks:
            if isinstance(chunk, dict):
                doc_name = chunk.get("document_name") or chunk.get("doc_name")
                if doc_name:
                    ref_docs.add(doc_name)

        result_text = answer
        if ref_docs:
            ref_list = "\n".join([f"- {doc}" for doc in sorted(ref_docs)])
            result_text += f"\n\n【数据结构知识库引用来源】:\n{ref_list}"

        return result_text

    except requests.exceptions.ConnectionError:
        return f"【知识库查询失败】无法连接到 RAGFlow（{base_url}），请确认服务已启动。"
    except requests.exceptions.Timeout:
        return "【知识库查询失败】RAGFlow 请求超时（90秒），请检查服务状态。"
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        body = e.response.text[:300] if e.response else ""
        return f"【知识库查询失败】HTTP 错误 {status}: {body}"
    except RuntimeError as e:
        return f"【知识库查询失败】{str(e)}"
    except Exception as e:
        return f"【知识库查询失败】未知错误 {type(e).__name__}: {str(e)}"
