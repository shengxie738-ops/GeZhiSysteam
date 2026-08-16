from fastapi import APIRouter, Depends, Form, Header, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage
import json
import asyncio
import time
import uuid
import re
import openai
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import get_db
from app.core.miniprogram_response import api_response, is_miniprogram_client, page_items
from app.core.security import decode_access_token
from app.models.user_rag import UserRagMapping
from app.models.code_diagnosis import CodeDiagnosis
from app.schemas.chat import ChatRequest
from app.services.rag_service import (
    build_repository_metadata_condition,
    get_public_dataset_ids,
    retrieve_from_datasets,
)
from app.services.user_knowledge_service import upload_document_to_default_repository
from app.services.chat_history import (
    build_agent_thread_id,
    clear_chat_history,
    delete_chat_message,
    list_chat_history,
    normalize_agent_mode,
    normalize_user_id,
    save_chat_message,
)
from app.services.agent_workflow import agent_graph, resolve_runtime_model_id
from app.services.model_registry import build_chat_model, has_model, list_public_models
from app.tools.ragflow_tool import query_data_structure_knowledge

router = APIRouter()


def resolve_agent_mode(request: ChatRequest) -> str:
    if request.agent_mode:
        return normalize_agent_mode(request.agent_mode)
    return "rag" if request.force_rag else "tutor"


def resolve_user_id(request: ChatRequest) -> str:
    return normalize_user_id(request.sessionId or request.thread_id)


def resolve_thread_id(request: ChatRequest, user_id: str, agent_mode: str) -> str:
    if request.thread_id:
        return build_agent_thread_id(request.thread_id, agent_mode)
    return build_agent_thread_id(user_id, agent_mode)


def resolve_request_agent_id(request: ChatRequest, agent_mode: str) -> str:
    if request.agent_id:
        return request.agent_id
    if request.is_diagnosis or "【用户当前代码】" in (request.message or ""):
        return "agent_coder"
    return "agent_researcher" if agent_mode == "rag" else "agent_tutor"


def build_agent_runtime_config(request: ChatRequest, *, thread_id: str, agent_mode: str, message: str) -> dict:
    configurable = {
        "thread_id": thread_id,
        "agent_id": resolve_request_agent_id(request, agent_mode),
        "agent_model": request.agent_model,
        "agent_prompt": request.agent_prompt,
    }
    selected_model = resolve_runtime_model_id({"configurable": configurable}, message)
    configurable["agent_model"] = selected_model
    return {"configurable": configurable}


def get_request_chat_model(config: dict, *, temperature: float = 0.1):
    model_id = config.get("configurable", {}).get("agent_model")
    return build_chat_model(model_id, temperature=temperature)


def get_runtime_agent_id(config: dict, fallback: str = "agent_tutor") -> str:
    agent_id = config.get("configurable", {}).get("agent_id")
    return agent_id or fallback


MODEL_UNAVAILABLE_MESSAGE = "当前模型不可用，请更换模型"


def is_model_invocation_error(exc: BaseException) -> bool:
    return isinstance(exc, openai.OpenAIError)


def is_configured_model_unavailable(request) -> bool:
    requested_model = getattr(request, "agent_model", None)
    return bool(requested_model) and not has_model(requested_model, category="text")


def build_model_unavailable_notice(model_id: str) -> str:
    return f"⚠️ 模型 {model_id} {MODEL_UNAVAILABLE_MESSAGE}"


def build_model_unavailable_event(model_id: str) -> str:
    return f"data: {json.dumps({'type': 'model_unavailable', 'model': model_id, 'message': MODEL_UNAVAILABLE_MESSAGE})}\n\n"


@router.get("/ai/models")
async def list_ai_models():
    return {
        "status": "success",
        "data": list_public_models(),
    }

REFERENCE_SOURCE_PATTERN = re.compile(
    r"\n{0,2}【(?:数据结构)?知识库引用来源】[:：][ \t]*(?:\n[ \t]*[-•][ \t]*[^\n]+)*",
    re.MULTILINE,
)


def strip_reference_source_block(text: str) -> str:
    if not text:
        return ""
    return REFERENCE_SOURCE_PATTERN.sub("", text).strip()


def should_emit_reference_sources(agent_mode: str | None) -> bool:
    return normalize_agent_mode(agent_mode) == "rag"


def build_reference_source_block(ref_docs, agent_mode: str | None) -> str:
    docs = sorted(doc for doc in ref_docs if doc)
    if not docs or not should_emit_reference_sources(agent_mode):
        return ""
    return "\n\n【知识库引用来源】:\n" + "\n".join([f"- {doc}" for doc in docs])


def build_verified_reference_reply(answer: str, ref_docs, agent_mode: str | None) -> str:
    cleaned_answer = strip_reference_source_block(answer)
    return cleaned_answer + build_reference_source_block(ref_docs, agent_mode)


def clean_message_content(text: str) -> str:
    if not text:
        return ""
    # 匹配带方括号的时间戳，如 [2026-06-20 21:31:00]
    pattern_bracket = r"\[\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}(?::\d{1,2})?\]"
    # 匹配不带方括号的时间戳，如 2026-06-20 21:31:00
    pattern_nobracket = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}(?::\d{1,2})?"
    
    cleaned = re.sub(pattern_bracket, "", text)
    cleaned = re.sub(pattern_nobracket, "", cleaned)
    
    cleaned = cleaned.strip()
    if cleaned.startswith(":") or cleaned.startswith("："):
        cleaned = cleaned[1:].strip()
        
    return cleaned

def is_greeting(text: str) -> bool:
    if not text:
        return True
    text_clean = text.strip().lower()
    greetings = {
        "你好", "在吗", "早上好", "中午好", "下午好", "晚上好", "哈喽", "嗨", "hello", "hi", "hey", 
        "你是谁", "你叫什么", "再见", "谢谢", "谢谢你", "88", "拜拜", "你真棒", "你是谁？", "你是谁?",
        "你叫什么名字", "你叫什么名字？", "你叫什么名字?", "你是机器人吗", "你是机器人吗？", "你是机器人吗?"
    }
    if text_clean in greetings:
        return True
    
    professional_keywords = ["表", "树", "图", "栈", "队", "链", "哈希", "查找", "排序", "算法", "堆", "二叉", "存储", "结构", "物理", "逻辑"]
    if len(text_clean) <= 3:
        has_kw = any(kw in text_clean for kw in professional_keywords)
        if not has_kw:
            return True
            
    return False

def get_dataset_id(db: Session, user_id: str) -> str:
    record = db.query(UserRagMapping).filter(UserRagMapping.user_id == user_id).first()
    return record.dataset_id if record else None


def retrieve_chunks_for_user(
    db: Session,
    *,
    user_id: str,
    query: str,
    repository_id: str | None = None,
    top_k_per_dataset: int = 4,
    course_dataset_ids: list[str] | None = None,
) -> list:
    chunks = []
    if course_dataset_ids:
        public_dataset_ids = course_dataset_ids
    else:
        public_dataset_ids = get_public_dataset_ids()
    user_dataset_id = get_dataset_id(db, user_id)

    if public_dataset_ids:
        chunks.extend(retrieve_from_datasets(public_dataset_ids, query, top_k_per_dataset=top_k_per_dataset))

    if user_dataset_id:
        metadata_condition = build_repository_metadata_condition(repository_id)
        chunks.extend(
            retrieve_from_datasets(
                [user_dataset_id],
                query,
                top_k_per_dataset=top_k_per_dataset,
                metadata_condition=metadata_condition,
            )
        )

    return chunks

def save_dataset_mapping(db: Session, user_id: str, dataset_id: str):
    record = db.query(UserRagMapping).filter(UserRagMapping.user_id == user_id).first()
    if record:
        record.dataset_id = dataset_id
    else:
        record = UserRagMapping(user_id=user_id, dataset_id=dataset_id)
        db.add(record)
    db.commit()

@router.post("/user/upload")
async def upload_user_doc(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        file_bytes = await file.read()
        document = upload_document_to_default_repository(
            db,
            user_id=user_id,
            file_bytes=file_bytes,
            filename=file.filename,
            file_size=len(file_bytes),
        )
        
        return {
            "status": "success",
            "dataset_id": document["dataset_id"],
            "document_id": document["rag_document_id"],
            "data": document,
            "message": f"文件 {file.filename} 上传成功，已触发向量化解析。"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    agent_mode = resolve_agent_mode(request)
    user_id = resolve_user_id(request)
    thread_id = resolve_thread_id(request, user_id, agent_mode)
    
    combined_context = ""
    ref_docs = set()
    
    cleaned_msg = clean_message_content(request.message)
    save_chat_message(db, user_id=user_id, agent_mode=agent_mode, role="user", content=cleaned_msg)
    
    # 寒暄检测：如果是寒暄，则不检索知识库
    if not is_greeting(cleaned_msg):
        try:
            all_chunks = retrieve_chunks_for_user(
                db,
                user_id=user_id,
                query=cleaned_msg,
                repository_id=request.repository_id,
                top_k_per_dataset=4,
                course_dataset_ids=request.course_dataset_ids,
            )
            if all_chunks:
                context_parts = []
                for chunk in all_chunks:
                    doc_name = chunk.get('document_keyword') or chunk.get('document_name') or '未知文档'
                    content = chunk.get('content', '')
                    context_parts.append(f"【{doc_name}】\n{content}")
                    ref_docs.add(doc_name)
                combined_context = "\n\n".join(context_parts)
        except Exception as e:
            print(f"[RAG] Multi-dataset retrieval error: {e}")

    user_content = cleaned_msg
    if combined_context:
        user_content = (
            f"以下是从知识库中检索到的相关参考资料：\n"
            f"{combined_context}\n\n"
            f"请结合以上资料，直接且专业地回答用户的问题：{cleaned_msg}"
        )

    config = build_agent_runtime_config(request, thread_id=thread_id, agent_mode=agent_mode, message=user_content)
    model_unavailable_notice = ""
    if is_configured_model_unavailable(request):
        model_unavailable_notice = build_model_unavailable_notice(request.agent_model) + "\n\n"

    if agent_mode == "rag":
        try:
            if not combined_context:
                rag_result = "知识库中未找到相关内容，请尝试换一种问法。"
            else:
                response = get_request_chat_model(config, temperature=0.1).invoke(user_content)
                rag_result = build_verified_reference_reply(response.content, ref_docs, agent_mode)
            final_reply = f"【✨ 强制开启专属知识库检索 (RAG模式)】\n\n{rag_result}"
        except Exception as e:
            final_reply = f"【✨ 强制 RAG 检索失败】\n\n发生错误: {str(e)}"
            if is_model_invocation_error(e):
                final_reply = build_model_unavailable_notice(config["configurable"]["agent_model"]) + "\n\n" + final_reply
        
        from app.services.profile_extractor import extract_and_update_profile
        save_chat_message(db, user_id=user_id, agent_mode=agent_mode, role="assistant", content=final_reply, sender_id="agent_researcher")
        asyncio.create_task(extract_and_update_profile(user_id, cleaned_msg, final_reply))
        return {"reply": final_reply, "history": []}

    initial_state = {"messages": [HumanMessage(content=user_content)]}
    
    try:
        result = await agent_graph.ainvoke(initial_state, config=config)
        final_reply = result["messages"][-1].content
        final_reply = strip_reference_source_block(final_reply)
            
        history_list = []
        for msg in result["messages"]:
            if isinstance(msg, HumanMessage):
                history_list.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage) and msg.content:
                history_list.append(f"AI: {msg.content}")
    except Exception as e:
        rag_result = query_data_structure_knowledge.invoke({"query": request.message})
        final_reply = f"【系统提示：大模型连接失败 ({type(e).__name__})，已直接为您调用本地 RAGFlow 检索】\n\n{rag_result}"
        if is_model_invocation_error(e):
            final_reply = build_model_unavailable_notice(config["configurable"]["agent_model"]) + "\n\n" + final_reply
        final_reply = strip_reference_source_block(final_reply)
        history_list = []
    
    if request.is_diagnosis:
        try:
            diagnosis_record = CodeDiagnosis(
                user_id=user_id,
                problem_id=request.problem_id or "unknown",
                problem_title=request.problem_title or "未知题目",
                user_code=request.user_code or "",
                diagnosis_result=final_reply
            )
            db.add(diagnosis_record)
            db.commit()
        except Exception as db_err:
            print(f"[DB Error] Failed to save code diagnosis: {db_err}")

    from app.services.profile_extractor import extract_and_update_profile
    save_chat_message(db, user_id=user_id, agent_mode=agent_mode, role="assistant", content=final_reply, sender_id=get_runtime_agent_id(config))
    asyncio.create_task(extract_and_update_profile(user_id, request.message, final_reply))
    return {
        "reply": model_unavailable_notice + final_reply,
        "history": history_list
    }


@router.get("/diagnosis/history")
async def get_diagnosis_history(user_id: str, db: Session = Depends(get_db)):
    try:
        records = db.query(CodeDiagnosis)\
            .filter(CodeDiagnosis.user_id == user_id)\
            .order_by(CodeDiagnosis.created_at.desc())\
            .limit(50)\
            .all()
        return {
            "status": "success",
            "data": [
                {
                    "id": r.id,
                    "problem_id": r.problem_id,
                    "problem_title": r.problem_title,
                    "user_code": r.user_code,
                    "diagnosis_result": r.diagnosis_result,
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None
                }
                for r in records
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/chat/history")
async def get_chat_history(
    session_id: str,
    agent_mode: str = "tutor",
    limit: int = 200,
    db: Session = Depends(get_db),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
):
    try:
        history = list_chat_history(
            db,
            user_id=session_id,
            agent_mode=agent_mode,
            limit=limit,
        )
        if is_miniprogram_client(x_gezhi_client):
            return api_response(page_items(history, limit=limit))
        return {
            "status": "success",
            "data": history,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/chat/history/{message_id}")
async def remove_chat_history_message(
    message_id: int,
    session_id: str,
    db: Session = Depends(get_db),
):
    try:
        deleted = delete_chat_message(db, user_id=session_id, message_id=message_id)
        if not deleted:
            return {"status": "error", "message": "历史记录不存在或无权删除"}
        return {"status": "success", "message": "历史记录已删除", "data": {"id": message_id}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/chat/history")
async def clear_chat_history_endpoint(
    session_id: str,
    agent_mode: str = "tutor",
    db: Session = Depends(get_db),
):
    try:
        deleted_count = clear_chat_history(db, user_id=session_id, agent_mode=agent_mode)
        return {
            "status": "success",
            "message": "历史记录已清空",
            "data": {"deleted_count": deleted_count},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def stream_chat_events(request: ChatRequest, db: Session):
    agent_mode = resolve_agent_mode(request)
    user_id = resolve_user_id(request)
    thread_id = resolve_thread_id(request, user_id, agent_mode)
    
    combined_context = ""
    ref_docs = set()
    
    cleaned_msg = clean_message_content(request.message)
    save_chat_message(db, user_id=user_id, agent_mode=agent_mode, role="user", content=cleaned_msg)
    
    # 寒暄检测：如果是寒暄，则不检索知识库
    if not is_greeting(cleaned_msg):
        try:
            yield f"data: {json.dumps({'type': 'progress', 'agent': 'DataBot', 'status': '正在检索本地课件知识库...'})}\n\n"
            await asyncio.sleep(0.05)
            all_chunks = retrieve_chunks_for_user(
                db,
                user_id=user_id,
                query=cleaned_msg,
                repository_id=request.repository_id,
                top_k_per_dataset=4,
                course_dataset_ids=request.course_dataset_ids,
            )
            if all_chunks:
                context_parts = []
                for chunk in all_chunks:
                    doc_name = chunk.get('document_keyword') or chunk.get('document_name') or '未知文档'
                    content = chunk.get('content', '')
                    context_parts.append(f"【{doc_name}】\n{content}")
                    ref_docs.add(doc_name)
                combined_context = "\n\n".join(context_parts)
        except Exception as e:
            print(f"[RAG] Multi-dataset retrieval error: {e}")

    user_content = cleaned_msg
    if combined_context:
        user_content = (
            f"以下是从知识库中检索到的相关参考资料：\n"
            f"{combined_context}\n\n"
            f"请结合以上资料，直接且专业地回答用户的问题：{cleaned_msg}"
        )

    ref_list = build_reference_source_block(ref_docs, agent_mode)

    full_reply = ""
    config = build_agent_runtime_config(request, thread_id=thread_id, agent_mode=agent_mode, message=user_content)
    if is_configured_model_unavailable(request):
        yield build_model_unavailable_event(request.agent_model)

    if agent_mode == "rag":
        try:
            if not combined_context:
                error_msg = "知识库中未找到相关内容，请尝试换一种问法。"
                full_reply = f"【✨ 强制开启专属知识库检索 (RAG模式)】\n\n{error_msg}"
                yield f"data: {json.dumps({'type': 'token', 'content': full_reply})}\n\n"
            else:
                prefix = "【✨ 强制开启专属知识库检索 (RAG模式)】\n\n"
                full_reply += prefix
                yield f"data: {json.dumps({'type': 'token', 'content': prefix})}\n\n"
                model_answer = ""
                async for chunk in get_request_chat_model(config, temperature=0.1).astream(user_content):
                    if chunk.content:
                        model_answer += chunk.content
                verified_answer = build_verified_reference_reply(model_answer, ref_docs, agent_mode)
                full_reply += verified_answer
                if verified_answer:
                    yield f"data: {json.dumps({'type': 'token', 'content': verified_answer})}\n\n"
        except Exception as e:
            if is_model_invocation_error(e):
                yield build_model_unavailable_event(config["configurable"]["agent_model"])
            err_msg = f"【✨ 强制 RAG 检索失败】\n\n发生错误: {str(e)}"
            full_reply = err_msg
            yield f"data: {json.dumps({'type': 'error', 'message': err_msg})}\n\n"
        
        from app.services.profile_extractor import extract_and_update_profile
        save_chat_message(db, user_id=user_id, agent_mode=agent_mode, role="assistant", content=full_reply, sender_id="agent_researcher")
        asyncio.create_task(extract_and_update_profile(user_id, cleaned_msg, full_reply))
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
        return

    # Normal Agent flow: LangGraph
    yield f"data: {json.dumps({'type': 'progress', 'agent': 'Alina', 'status': 'Alina 正在规划您的学习路径并协同导师...'})}\n\n"
    await asyncio.sleep(0.05)
    initial_state = {"messages": [HumanMessage(content=user_content)]}
    
    # Track whether any tokens were streamed
    tokens_streamed = False

    try:
        async for event in agent_graph.astream_events(initial_state, config=config, version="v1"):
            kind = event.get("event")
            if kind in ("on_chat_model_stream", "on_llm_stream"):
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    full_reply += chunk.content
                    tokens_streamed = True
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
            elif kind == "on_tool_start":
                tool_name = event.get("name")
                agent_name = "DataBot"
                status_text = f"正在调用工具 {tool_name}..."
                if tool_name == "execute_python_code":
                    status_text = "CodeNinja 正在沙箱中安全执行 Python 代码..."
                    agent_name = "CodeNinja"
                elif tool_name == "query_data_structure_knowledge":
                    status_text = "DataBot 正在检索《数据结构》核心课件..."
                    agent_name = "DataBot"
                yield f"data: {json.dumps({'type': 'progress', 'agent': agent_name, 'status': status_text})}\n\n"
            elif kind == "on_tool_end":
                tool_name = event.get("name")
                agent_name = "DataBot"
                if tool_name == "execute_python_code":
                    agent_name = "CodeNinja"
                yield f"data: {json.dumps({'type': 'progress_end', 'agent': agent_name, 'status': f'{tool_name} 执行完毕'})}\n\n"
        
        if ref_list:
            full_reply += ref_list
            yield f"data: {json.dumps({'type': 'token', 'content': ref_list})}\n\n"
        
        # Fallback: if no tokens were streamed but we have a response, send it as a single token
        if not tokens_streamed and full_reply:
            yield f"data: {json.dumps({'type': 'token', 'content': full_reply})}\n\n"
            
        from app.services.profile_extractor import extract_and_update_profile
        full_reply = strip_reference_source_block(full_reply)
        save_chat_message(db, user_id=user_id, agent_mode=agent_mode, role="assistant", content=full_reply, sender_id=get_runtime_agent_id(config))
        asyncio.create_task(extract_and_update_profile(user_id, request.message, full_reply))
            
    except Exception as e:
        print(f"[Agent Stream] Error: {e}")
        if is_model_invocation_error(e):
            yield build_model_unavailable_event(config["configurable"]["agent_model"])
        # Fallback to direct local RAG
        yield f"data: {json.dumps({'type': 'progress', 'agent': 'DataBot', 'status': '系统响应略有延迟，正在直连本地 RAGFlow 检索...' })}\n\n"
        try:
            rag_result = query_data_structure_knowledge.invoke({"query": request.message})
            fallback_reply = f"【系统提示：大模型连接失败 ({type(e).__name__})，已直接为您调用本地 RAGFlow 检索】\n\n" + rag_result
            fallback_reply = strip_reference_source_block(fallback_reply)
            yield f"data: {json.dumps({'type': 'token', 'content': fallback_reply})}\n\n"
            from app.services.profile_extractor import extract_and_update_profile
            save_chat_message(db, user_id=user_id, agent_mode=agent_mode, role="assistant", content=fallback_reply, sender_id="agent_researcher")
            asyncio.create_task(extract_and_update_profile(user_id, request.message, fallback_reply))
        except Exception as ex:
            yield f"data: {json.dumps({'type': 'error', 'message': f'系统出错: {str(ex)}'})}\n\n"

    yield f"data: {json.dumps({'type': 'complete'})}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    # Require authentication
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    token_payload = decode_access_token(authorization.split(" ", 1)[1])
    if not token_payload:
        raise HTTPException(status_code=401, detail="invalid token")
    auth_username = token_payload.get("sub")
    if not auth_username:
        raise HTTPException(status_code=401, detail="invalid token payload")
    # Use authenticated user's ID instead of client-provided one
    request.sessionId = auth_username
    request.thread_id = auth_username
    return StreamingResponse(stream_chat_events(request, db), media_type="text/event-stream")


# ==================== OpenAI 兼容接口 ====================

class OpenAIChatMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None


def build_openai_runtime_config(request: OpenAIChatRequest, *, thread_id: str, message: str) -> dict:
    configurable = {
        "thread_id": thread_id,
        "agent_id": "agent_tutor",
        "agent_model": request.model,
    }
    selected_model = resolve_runtime_model_id({"configurable": configurable}, message)
    configurable["agent_model"] = selected_model
    return {"configurable": configurable}

@router.get("/v1/models")
@router.get("/models")
async def list_openai_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "agent_tutor",
                "object": "model",
                "created": 1677610602,
                "owned_by": "格至智能协同教育"
            }
        ]
    }

async def stream_openai_chat_events(request: OpenAIChatRequest, db: Session):
    chat_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())
    model_name = request.model
    
    last_msg = request.messages[-1].content if request.messages else ""
    print(f"=== [OpenAI API Request last_msg] ===\n{last_msg}\n====================================")
    cleaned_last_msg = clean_message_content(last_msg)
    thread_id = f"openai-{uuid.uuid4()}"
    
    combined_context = ""
    ref_docs = set()
    
    is_greet = is_greeting(cleaned_last_msg)
    
    if not is_greet:
        try:
            initial_payload = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": "🤔 正在分析课件知识库...\n\n"},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(initial_payload)}\n\n"
            await asyncio.sleep(0.01)

            all_chunks = retrieve_chunks_for_user(
                db,
                user_id="default-thread",
                query=cleaned_last_msg,
                top_k_per_dataset=4,
            )
            if all_chunks:
                context_parts = []
                for chunk in all_chunks:
                    doc_name = chunk.get('document_keyword') or chunk.get('document_name') or '未知文档'
                    content = chunk.get('content', '')
                    context_parts.append(f"【{doc_name}】\n{content}")
                    ref_docs.add(doc_name)
                combined_context = "\n\n".join(context_parts)
        except Exception as e:
            print(f"[RAG] OpenAI multi-dataset retrieval error: {e}")
    else:
        initial_payload = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(initial_payload)}\n\n"

    user_content = cleaned_last_msg
    if combined_context:
        user_content = (
            f"以下是从知识库中检索到的相关参考资料：\n"
            f"{combined_context}\n\n"
            f"请结合以上资料，直接且专业地回答用户的问题：{cleaned_last_msg}"
        )

    ref_list = ""
    if ref_docs:
        ref_list = "\n\n【知识库引用来源】:\n" + "\n".join([f"- {doc}" for doc in sorted(ref_docs)])

    langchain_messages = []
    for msg in request.messages[:-1]:
        cleaned_hist_content = clean_message_content(msg.content)
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=cleaned_hist_content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=cleaned_hist_content))
    langchain_messages.append(HumanMessage(content=user_content))

    initial_state = {"messages": langchain_messages}
    config = build_openai_runtime_config(request, thread_id=thread_id, message=user_content)

    full_reply = ""
    try:
        async for event in agent_graph.astream_events(initial_state, config=config, version="v2"):
            kind = event.get("event")
            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    full_reply += chunk.content
                    payload = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk.content},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
            elif kind == "on_tool_start":
                tool_name = event.get("name")
                status_text = f"\n*（智能助教正在调用工具 {tool_name}...）*\n"
                payload = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": status_text},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(payload)}\n\n"
        
        if ref_list:
            full_reply += ref_list
            payload = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"content": ref_list},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(payload)}\n\n"
            
        from app.services.profile_extractor import extract_and_update_profile
        asyncio.create_task(extract_and_update_profile(thread_id, last_msg, full_reply))
            
    except Exception as e:
        print(f"[OpenAI Agent Stream] Error: {e}")
        try:
            rag_result = query_data_structure_knowledge.invoke({"query": last_msg})
            fallback_reply = f"\n【系统提示：大模型连接失败，已直接为您调用本地 RAGFlow 检索】\n\n" + rag_result
            payload = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"content": fallback_reply},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(payload)}\n\n"
            from app.services.profile_extractor import extract_and_update_profile
            asyncio.create_task(extract_and_update_profile(thread_id, last_msg, fallback_reply))
        except Exception as ex:
            error_payload = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"\n【系统错误：{str(ex)}】\n"},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    stop_payload = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created_time,
        "model": model_name,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(stop_payload)}\n\n"
    yield "data: [DONE]\n\n"

@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def openai_chat_completions(request: OpenAIChatRequest, db: Session = Depends(get_db)):
    if request.stream:
        return StreamingResponse(stream_openai_chat_events(request, db), media_type="text/event-stream")
        
    last_msg = request.messages[-1].content if request.messages else ""
    print(f"=== [OpenAI API Request last_msg] ===\n{last_msg}\n====================================")
    cleaned_last_msg = clean_message_content(last_msg)
    thread_id = f"openai-{uuid.uuid4()}"
    
    combined_context = ""
    ref_docs = set()
    
    if not is_greeting(cleaned_last_msg):
        try:
            all_chunks = retrieve_chunks_for_user(
                db,
                user_id="default-thread",
                query=cleaned_last_msg,
                top_k_per_dataset=4,
            )
            if all_chunks:
                context_parts = []
                for chunk in all_chunks:
                    doc_name = chunk.get('document_keyword') or chunk.get('document_name') or '未知文档'
                    content = chunk.get('content', '')
                    context_parts.append(f"【{doc_name}】\n{content}")
                    ref_docs.add(doc_name)
                combined_context = "\n\n".join(context_parts)
        except Exception as e:
            print(f"[RAG] OpenAI retrieval error: {e}")

    user_content = cleaned_last_msg
    if combined_context:
        user_content = (
            f"以下是从知识库中检索到的相关参考资料：\n"
            f"{combined_context}\n\n"
            f"请结合以上资料，直接且专业地回答用户的问题：{cleaned_last_msg}"
        )

    langchain_messages = []
    for msg in request.messages[:-1]:
        cleaned_hist_content = clean_message_content(msg.content)
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=cleaned_hist_content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=cleaned_hist_content))
    langchain_messages.append(HumanMessage(content=user_content))

    initial_state = {"messages": langchain_messages}
    config = build_openai_runtime_config(request, thread_id=thread_id, message=user_content)
    
    try:
        result = await agent_graph.ainvoke(initial_state, config=config)
        final_reply = result["messages"][-1].content
        
        if ref_docs:
            ref_list = "\n\n【知识库引用来源】:\n" + "\n".join([f"- {doc}" for doc in sorted(ref_docs)])
            final_reply += ref_list
    except Exception as e:
        print(f"[OpenAI Agent Non-stream] Error: {e}")
        try:
            rag_result = query_data_structure_knowledge.invoke({"query": last_msg})
            final_reply = f"【系统提示：大模型连接失败，已直接为您调用本地 RAGFlow 检索】\n\n" + rag_result
        except Exception as ex:
            final_reply = f"【系统错误：{str(ex)}】"
            
    from app.services.profile_extractor import extract_and_update_profile
    asyncio.create_task(extract_and_update_profile(thread_id, last_msg, final_reply))
    
    chat_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())
    return {
        "id": chat_id,
        "object": "chat.completion",
        "created": created_time,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": final_reply
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
# Reload Trigger: Aliyun API Key configured in backend .env
