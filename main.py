"""
위키독스 블로그 자동 포스팅 - LangGraph 구현
n8n 워크플로우를 Python LangGraph로 변환

필요한 패키지:
pip install langgraph langchain langchain-anthropic langchain-community httpx python-dotenv
"""

import os
import json
import time
import httpx
from typing import TypedDict, Literal
from dataclasses import dataclass

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic

# .env 파일 로드 (현재 파일 기준 경로)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


# ============================================================
# 1. 상태 정의 (State Schema)
# ============================================================
class BlogState(TypedDict):
    # 입력
    topic: str
    contents: str
    
    # LLM 생성 결과
    title: str
    content: str
    tags: str
    image_prompt: str
    
    # 블로그 생성 결과
    blog_id: int
    
    # 이미지 생성 결과
    freepik_task_id: str
    image_status: str
    image_url: str
    image_markdown_url: str
    
    # 폴링 카운터
    poll_count: int
    
    # 최종 결과
    result_message: str
    error: str


# ============================================================
# 2. 설정 클래스
# ============================================================
@dataclass
class Config:
    """API 키 및 설정"""
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    wikidocs_api_key: str = f'Token {os.getenv("WIKIDOCS_API_KEY", "")}'
    freepik_api_key: str = os.getenv("FREEPIK_API_KEY", "")
    
    wikidocs_base_url: str = "https://wikidocs.net/napi/blog"
    freepik_base_url: str = "https://api.freepik.com/v1/ai/mystic"
    
    max_poll_attempts: int = 30
    poll_interval: int = 2  # seconds


config = Config()


# ============================================================
# 3. 노드 함수들 (Node Functions)
# ============================================================

def generate_poem(state: BlogState) -> BlogState:
    """
    Claude API를 사용해 시 생성
    n8n의 "Message a model" 노드에 해당
    """
    print("📝 시 생성 중...")

    prompt = f"""당신은 전문 시인입니다. 주어진 주제에 대해 자유형태의 시를 작성해주세요.
- 주제: {state['topic']}
- 내용: {state['contents']}를 기반으로 여기에 내용을 덧붙여서 작성해 주세요.

반드시 다음 JSON 형식으로만 응답해주세요 (다른 텍스트 없이 순수 JSON만)
태그는 지정된 태그만 사용해 주세요. 변경하지 않습니다.
{{
  "title": "매력적인 제목",
  "content": "마크다운 형식의 시 모양의 본문 (50자 이상 150자 이하), [1], [2]와 같은 출처 표시를 하지 말아 주세요.",
  "tags": "AI시집,n8n",
  "image_prompt": "이 글에 어울리는 썸네일 이미지를 위한 영문 프롬프트"
}}
"""

    try:
        # Claude 모델 사용
        llm = ChatAnthropic(
            model="claude-opus-4-5-20251101",
            api_key=config.anthropic_api_key,
            temperature=0.7
        )

        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # 디버깅: 응답 내용 출력
        # print(f"[DEBUG] Claude 응답:\n{content}\n")

        # 마크다운 코드 블록 제거 (```json ... ``` 형식)
        if content.startswith("```"):
            # 첫 번째 줄과 마지막 줄 제거
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        result = json.loads(content)

        return {
            **state,
            "title": result["title"],
            "content": result["content"],
            "tags": result["tags"],
            "image_prompt": result["image_prompt"]
        }
    except Exception as e:
        return {**state, "error": f"시 생성 실패: {str(e)}"}


def create_blog(state: BlogState) -> BlogState:
    """
    위키독스에 빈 블로그 생성
    n8n의 "블로그 생성" 노드에 해당
    """
    if state.get("error"):
        return state
    
    print("📄 블로그 생성 중...")
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{config.wikidocs_base_url}/create/",
                headers={
                    "Authorization": config.wikidocs_api_key,
                    "Content-Type": "application/json"
                },
                json={}
            )
            response.raise_for_status()
            data = response.json()
            
            return {**state, "blog_id": data["id"]}
    except Exception as e:
        return {**state, "error": f"블로그 생성 실패: {str(e)}"}


def request_image_generation(state: BlogState) -> BlogState:
    """
    Freepik API로 이미지 생성 요청
    n8n의 "freepik" 노드에 해당
    """
    if state.get("error"):
        return state
    
    print("🎨 이미지 생성 요청 중...")
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                config.freepik_base_url,
                headers={"x-freepik-api-key": config.freepik_api_key},
                json={
                    "prompt": state["image_prompt"],
                    "resolution": "1k",
                    "aspect_ratio": "widescreen_16_9",
                    "model": "realism"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                **state,
                "freepik_task_id": data["data"]["task_id"],
                "image_status": "PENDING",
                "poll_count": 0
            }
    except Exception as e:
        return {**state, "error": f"이미지 생성 요청 실패: {str(e)}"}


def check_image_status(state: BlogState) -> BlogState:
    """
    이미지 생성 상태 확인
    n8n의 "생성확인" 노드에 해당
    """
    if state.get("error"):
        return state
    
    print(f"🔍 이미지 상태 확인 중... (시도 {state['poll_count'] + 1})")
    
    # 폴링 전 대기
    time.sleep(config.poll_interval)
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{config.freepik_base_url}/{state['freepik_task_id']}",
                headers={"x-freepik-api-key": config.freepik_api_key}
            )
            response.raise_for_status()
            data = response.json()
            
            status = data["data"]["status"]
            image_url = ""
            
            if status == "COMPLETED":
                image_url = data["data"]["generated"][0]
                print("✅ 이미지 생성 완료!")
            
            return {
                **state,
                "image_status": status,
                "image_url": image_url,
                "poll_count": state["poll_count"] + 1
            }
    except Exception as e:
        return {**state, "error": f"이미지 상태 확인 실패: {str(e)}"}


def download_and_upload_image(state: BlogState) -> BlogState:
    """
    이미지 다운로드 후 위키독스에 업로드
    n8n의 "이미지다운로드" + "이미지 업로드" 노드에 해당
    """
    if state.get("error"):
        return state
    
    print("📥 이미지 다운로드 및 업로드 중...")
    
    try:
        with httpx.Client(timeout=60) as client:
            # 1. 이미지 다운로드
            image_response = client.get(state["image_url"])
            image_response.raise_for_status()
            image_data = image_response.content
            
            # 2. 위키독스에 업로드
            files = {"file": ("image.png", image_data, "image/png")}
            data = {"blog_id": str(state["blog_id"])}
            
            upload_response = client.post(
                f"{config.wikidocs_base_url}/images/upload/",
                headers={"Authorization": config.wikidocs_api_key},
                files=files,
                data=data
            )
            upload_response.raise_for_status()
            upload_result = upload_response.json()
            
            # 마크다운 이미지 URL 추출
            image_markdown = upload_result.get("image_markdown_url", "")
            
            return {**state, "image_markdown_url": image_markdown}
    except Exception as e:
        return {**state, "error": f"이미지 업로드 실패: {str(e)}"}


def update_blog(state: BlogState) -> BlogState:
    """
    블로그 내용 업데이트
    n8n의 "블로그 수정" 노드에 해당
    """
    if state.get("error"):
        return state
    
    print("✏️ 블로그 내용 업데이트 중...")
    
    try:
        # 이미지 마크다운 + 본문 조합
        full_content = ""
        if state.get("image_markdown_url"):
            full_content = state["image_markdown_url"] + "\n\n"
        full_content += state["content"]
        
        with httpx.Client(timeout=30) as client:
            response = client.put(
                f"{config.wikidocs_base_url}/{state['blog_id']}/",
                headers={
                    "Authorization": config.wikidocs_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "title": state["title"],
                    "content": full_content,
                    "is_public": False,
                    "tags": state["tags"]
                }
            )
            response.raise_for_status()
            
            result_message = f"""
✅ 블로그가 성공적으로 작성되었습니다!

- 블로그 ID: {state['blog_id']}
- 제목: {state['title']}
- URL: https://wikidocs.net/blog/{state['blog_id']}
"""
            return {**state, "result_message": result_message}
    except Exception as e:
        return {**state, "error": f"블로그 수정 실패: {str(e)}"}


def handle_error(state: BlogState) -> BlogState:
    """에러 처리 노드"""
    print(f"❌ 에러 발생: {state.get('error', 'Unknown error')}")
    return state


# ============================================================
# 4. 조건부 라우팅 함수 (Conditional Edges)
# ============================================================

def should_continue_polling(state: BlogState) -> Literal["check_status", "download_upload", "error", "timeout"]:
    """
    이미지 생성 상태에 따른 분기
    n8n의 "If" 노드에 해당
    """
    if state.get("error"):
        return "error"
    
    if state["image_status"] == "COMPLETED":
        return "download_upload"
    
    if state["poll_count"] >= config.max_poll_attempts:
        return "timeout"
    
    return "check_status"


def check_error(state: BlogState) -> Literal["continue", "error"]:
    """에러 체크"""
    if state.get("error"):
        return "error"
    return "continue"


# ============================================================
# 5. 그래프 구성 (Graph Construction)
# ============================================================

def create_blog_workflow() -> StateGraph:
    """LangGraph 워크플로우 생성"""
    
    # 그래프 초기화
    workflow = StateGraph(BlogState)
    
    # 노드 추가
    workflow.add_node("generate_poem", generate_poem)
    workflow.add_node("create_blog", create_blog)
    workflow.add_node("request_image", request_image_generation)
    workflow.add_node("check_status", check_image_status)
    workflow.add_node("download_upload", download_and_upload_image)
    workflow.add_node("update_blog", update_blog)
    workflow.add_node("handle_error", handle_error)
    
    # 엣지 연결 (순차적 흐름)
    workflow.set_entry_point("generate_poem")
    
    workflow.add_conditional_edges(
        "generate_poem",
        check_error,
        {"continue": "create_blog", "error": "handle_error"}
    )
    
    workflow.add_conditional_edges(
        "create_blog",
        check_error,
        {"continue": "request_image", "error": "handle_error"}
    )
    
    workflow.add_conditional_edges(
        "request_image",
        check_error,
        {"continue": "check_status", "error": "handle_error"}
    )
    
    # 폴링 루프 (이미지 생성 완료 대기)
    workflow.add_conditional_edges(
        "check_status",
        should_continue_polling,
        {
            "check_status": "check_status",  # 재시도
            "download_upload": "download_upload",  # 완료
            "error": "handle_error",
            "timeout": "handle_error"
        }
    )
    
    workflow.add_conditional_edges(
        "download_upload",
        check_error,
        {"continue": "update_blog", "error": "handle_error"}
    )
    
    workflow.add_edge("update_blog", END)
    workflow.add_edge("handle_error", END)
    
    return workflow.compile()


# ============================================================
# 6. 실행 함수
# ============================================================

def run_blog_posting(topic: str, contents: str) -> dict:
    """
    블로그 포스팅 워크플로우 실행
    
    Args:
        topic: 블로그 주제/제목
        contents: 블로그 내용 아이디어
    
    Returns:
        최종 상태 딕셔너리
    """
    # 워크플로우 생성
    app = create_blog_workflow()
    
    # 초기 상태
    initial_state: BlogState = {
        "topic": topic,
        "contents": contents,
        "title": "",
        "content": "",
        "tags": "",
        "image_prompt": "",
        "blog_id": 0,
        "freepik_task_id": "",
        "image_status": "",
        "image_url": "",
        "image_markdown_url": "",
        "poll_count": 0,
        "result_message": "",
        "error": ""
    }
    
    print("=" * 50)
    print("🚀 블로그 자동 포스팅 시작")
    print("=" * 50)
    print(f"주제: {topic}")
    print(f"내용: {contents}")
    print("=" * 50)
    
    # 워크플로우 실행
    final_state = app.invoke(initial_state)
    
    print("=" * 50)
    if final_state.get("error"):
        print(f"❌ 실패: {final_state['error']}")
    else:
        print(final_state.get("result_message", "완료"))
    print("=" * 50)
    
    return final_state


# ============================================================
# 7. 메인 실행
# ============================================================

if __name__ == "__main__":
    # 환경변수 또는 직접 설정 필요:
    # - PERPLEXITY_API_KEY
    # - WIKIDOCS_API_KEY
    # - FREEPIK_API_KEY
    
    # 테스트 실행
    result = run_blog_posting(
        topic="봄날의 산책",
        contents="따뜻한 봄 햇살 아래 공원을 걷는 평화로운 순간"
    )