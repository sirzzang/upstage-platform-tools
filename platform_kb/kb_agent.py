"""플랫폼 지식 베이스 에이전트 모듈.

OpenAI-호환 Function Calling 패턴을 사용하여
사용자의 의도를 파악하고 적절한 도구를 자동 선택하는 에이전트를 구현한다.

전체 아키텍처:
  사용자 질문 → LLM(solar-pro3)이 도구 선택 → 도구 실행 → 결과 반영 → 최종 응답
  (도구 호출이 없을 때까지 루프 반복)

사용하는 Upstage API:
  - Chat Completions + Function Calling (solar-pro3): 에이전트 루프, RAG 답변 생성
  - Embeddings (embedding-passage / embedding-query): 문서/쿼리 임베딩
  - Groundedness Check (solar-pro3 프롬프트): 답변 근거 검증
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.client import client
from common.usage import UsageTracker, print_usage
from platform_kb.embedding_tools import chunk_document, embed_chunks, embed_query
from platform_kb.vector_store import VectorStore
from platform_kb.groundedness import check_groundedness

# 벡터 스토어 싱글턴 — 모든 도구 핸들러가 공유하는 단일 인스턴스
_store = VectorStore()

# ── Function Calling 도구 정의 ──────────────────────────────
# OpenAI-호환 형식의 도구(함수) 스키마 리스트.
# LLM(solar-pro3)이 사용자 의도를 파악하여 적절한 도구를 자동 선택한다.
# 예: "CrashLoopBackOff 대응법 알려줘" → rag_query 자동 호출
#     "이 문서 추가해줘" → add_document 자동 호출
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_document",
            "description": "텍스트/마크다운 파일을 청킹하고 임베딩하여 지식 베이스에 추가합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "추가할 문서 파일 경로 (.md, .txt 등)",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "쿼리와 유사한 문서 청크를 벡터 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색 쿼리",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "반환할 결과 수 (기본: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": "지식 베이스에 저장된 문서 목록과 청크 수를 표시합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_document",
            "description": "지식 베이스에서 특정 문서를 삭제합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_name": {
                        "type": "string",
                        "description": "삭제할 문서 이름",
                    }
                },
                "required": ["doc_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rag_query",
            "description": "지식 베이스에서 관련 문서를 검색한 후 LLM이 답변을 생성하고, 근거를 검증합니다. 사용자 질문에 답변할 때 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "사용자의 질문",
                    }
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reset_knowledge_base",
            "description": "지식 베이스의 모든 데이터를 초기화합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

# 도구명 → 한글 라벨 매핑 (콘솔 출력 시 사용자 친화적 표시용)
TOOL_LABELS = {
    "add_document": "문서 추가",
    "search_documents": "문서 검색",
    "list_documents": "문서 목록",
    "delete_document": "문서 삭제",
    "rag_query": "RAG 답변",
    "reset_knowledge_base": "KB 초기화",
}

SYSTEM_PROMPT = """당신은 플랫폼 엔지니어링 지식 베이스 전문가입니다. 내부 문서 (Runbook, 포스트모템, 아키텍처 문서)를 기반으로 질문에 답변합니다.

역할:
- 문서 관리: 문서를 지식 베이스에 추가/삭제/조회
- RAG Q&A: 관련 문서를 검색하여 근거 기반 답변 생성
- 근거 검증: 답변이 실제 문서에 근거하는지 자동 검증

규칙:
- 사용자의 질문에는 항상 rag_query 도구를 사용하여 답변하세요.
- 문서 추가 요청 시 add_document를 사용하세요.
- 문서 검색만 요청 시 search_documents를 사용하세요.
- 모든 응답은 한국어로 작성하세요.
- 답변에 출처 (파일명, 섹션)를 반드시 포함하세요.
- 검색 결과가 없으면 "관련 문서가 지식 베이스에 없습니다"라고 안내하세요.
- 근거 검증 결과를 답변에 포함하세요.
"""


# ── 도구 핸들러 함수들 ──────────────────────────────────────


def _handle_add_document(args: dict) -> str:
    """문서 추가 파이프라인: 파일 읽기 → 청킹 → 임베딩 → 벡터 DB 저장.

    전체 흐름:
    1. 파일 시스템에서 텍스트 읽기
    2. chunk_document(): ## 헤딩 기준 섹션 분할 + 메타데이터 부착
    3. embed_chunks(): Upstage embedding-passage API로 4096차원 벡터 변환
    4. VectorStore.add_documents(): JSON 파일에 청크+벡터+메타 저장
    """
    file_path = args["file_path"]
    if not os.path.isfile(file_path):
        return f"[오류] 파일이 존재하지 않습니다: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        file_name = os.path.basename(file_path)

        # 1. 청킹: 마크다운 ## 헤딩 기준 섹션 분할, 500자 초과 시 단락 재분할
        chunks = chunk_document(text, file_name)
        if not chunks:
            return f"[오류] 문서에서 청크를 추출할 수 없습니다: {file_path}"

        # 2. 임베딩: Upstage embedding-passage API로 각 청크를 4096차원 벡터로 변환
        embeddings = embed_chunks(chunks)

        # 3. 벡터 DB 저장: 청크 텍스트 + 벡터 + 메타데이터를 JSON 파일에 영속화
        count = _store.add_documents(chunks, embeddings, file_name)

        return (
            f"[문서 추가 완료]\n"
            f"파일: {file_name}\n"
            f"청크 수: {count}\n"
            f"각 청크 섹션: {', '.join(c['metadata']['section'] for c in chunks)}"
        )
    except Exception as e:
        return f"[문서 추가 오류] {e}"


def _handle_search_documents(args: dict) -> str:
    """쿼리와 유사한 문서 청크를 벡터 검색한다.

    흐름: 쿼리 임베딩(embedding-query) → 벡터 스토어에서 cosine 유사도 검색
    """
    query = args["query"]
    n_results = args.get("n_results", 5)

    try:
        # 검색 쿼리를 embedding-query 모델로 4096차원 벡터 변환
        query_emb = embed_query(query)
        # 벡터 스토어에서 cosine 유사도 기반 상위 N개 청크 검색
        results = _store.search(query_emb, n_results=n_results)

        if not results:
            return "[검색 결과 없음] 지식 베이스에 문서가 없습니다."

        parts = [f"[검색 결과] 쿼리: '{query}' (상위 {len(results)}건)"]
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            # cosine distance → cosine similarity 변환 (1 - distance)
            similarity = 1 - r["distance"]
            parts.append(
                f"\n--- 결과 {i} (유사도: {similarity:.3f}) ---\n"
                f"출처: {meta.get('doc_name', '?')} > {meta.get('section', '?')}\n"
                f"내용:\n{r['text'][:300]}{'...' if len(r['text']) > 300 else ''}"
            )
        return "\n".join(parts)
    except Exception as e:
        return f"[검색 오류] {e}"


def _handle_list_documents(_args: dict) -> str:
    docs = _store.list_documents()
    if not docs:
        return "[문서 목록] 지식 베이스가 비어있습니다."

    parts = ["[저장된 문서 목록]"]
    total_chunks = 0
    for name, count in sorted(docs.items()):
        parts.append(f"  - {name} ({count} chunks)")
        total_chunks += count
    parts.append(f"\n총 {len(docs)}개 문서, {total_chunks}개 청크")
    return "\n".join(parts)


def _handle_delete_document(args: dict) -> str:
    doc_name = args["doc_name"]
    count = _store.delete_document(doc_name)
    if count == 0:
        return f"[삭제] '{doc_name}' 문서를 찾을 수 없습니다."
    return f"[삭제 완료] '{doc_name}' ({count}개 청크 삭제됨)"


def _handle_rag_query(args: dict) -> str:
    """RAG (Retrieval-Augmented Generation) 파이프라인의 핵심 함수.

    전체 6단계:
    1. 쿼리 임베딩: 사용자 질문을 embedding-query 모델로 벡터 변환
    2. 유사 청크 검색: 벡터 스토어에서 cosine 유사도 기반 top-5 검색
    3. 컨텍스트 조합: 검색된 청크들을 출처 정보와 함께 하나의 문자열로 조합
    4. LLM 답변 생성: 컨텍스트 + 질문을 solar-pro3에 전달하여 근거 기반 답변 생성
    5. 근거 검증: 생성된 답변이 실제 문서에 근거하는지 별도 LLM 호출로 검증
    6. 결과 조합: 답변 + 출처 + 근거 검증 배지를 최종 응답으로 조합
    """
    question = args["question"]

    try:
        # ── 1단계: 쿼리 임베딩 ──
        # 사용자 질문을 embedding-query 모델로 4096차원 벡터 변환
        query_emb = embed_query(question)

        # ── 2단계: 유사 청크 검색 ──
        # 벡터 스토어에서 cosine 유사도가 높은 상위 5개 청크를 검색
        results = _store.search(query_emb, n_results=5)

        if not results:
            return "[RAG] 관련 문서가 지식 베이스에 없습니다. 먼저 문서를 추가해주세요."

        # ── 3단계: 컨텍스트 조합 ──
        # 검색된 청크들을 [출처: 파일명 > 섹션] 형식의 출처와 함께 하나로 합침
        context_parts = []
        sources = []
        for r in results:
            meta = r["metadata"]
            source = f"{meta.get('doc_name', '?')} > {meta.get('section', '?')}"
            context_parts.append(f"[출처: {source}]\n{r['text']}")
            sources.append(source)

        context = "\n\n---\n\n".join(context_parts)

        # ── 4단계: LLM 답변 생성 ──
        # [Upstage API] Chat Completions (solar-pro3)
        # 에이전트 루프의 system prompt와는 별개로, RAG 전용 system prompt를 사용한다.
        # "제공된 컨텍스트 문서에만 기반하여 답변"하도록 제한하여
        # LLM이 자체 지식(학습 데이터)으로 환각(hallucination)하는 것을 방지.
        rag_response = client.chat.completions.create(
            model="solar-pro3",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a platform engineering knowledge base assistant. "
                        "Answer the user's question based ONLY on the provided context documents. "
                        "If the context doesn't contain enough information, say so. "
                        "Always cite the source document and section. "
                        "Respond in Korean."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"[검색된 문서]\n{context}\n\n"
                        f"[질문]\n{question}"
                    ),
                },
            ],
        )
        answer = rag_response.choices[0].message.content

        # ── 5단계: 근거 검증 (Groundedness Check) ──
        # 생성된 답변이 실제로 검색된 문서에 근거하는지 별도의 LLM 호출로 검증.
        # 이 단계가 없으면 LLM이 컨텍스트에 없는 내용을 지어낼(hallucinate) 수 있다.
        # 결과: "grounded" | "notGrounded" | "notSure"
        groundedness = check_groundedness(context, answer)

        if groundedness == "grounded":
            badge = "grounded"
        elif groundedness == "notGrounded":
            badge = "notGrounded"
        else:
            badge = "notSure"

        # ── 6단계: 결과 조합 ──
        unique_sources = list(dict.fromkeys(sources))  # 중복 제거, 순서 유지
        source_list = "\n".join(f"  - {s}" for s in unique_sources)

        return (
            f"[RAG 답변]\n{answer}\n\n"
            f"[출처]\n{source_list}\n\n"
            f"[근거 검증] {badge}"
        )
    except Exception as e:
        return f"[RAG 오류] {e}"


def _handle_reset(_args: dict) -> str:
    _store.reset()
    return "[초기화 완료] 지식 베이스의 모든 데이터가 삭제되었습니다."


# ── 도구 핸들러 디스패치 테이블 ────────────────────────────
# 도구 이름(문자열) → 핸들러 함수 매핑.
# LLM이 반환한 tool_call.function.name 으로 해당 핸들러를 찾아 실행한다.
TOOL_HANDLERS = {
    "add_document": _handle_add_document,
    "search_documents": _handle_search_documents,
    "list_documents": _handle_list_documents,
    "delete_document": _handle_delete_document,
    "rag_query": _handle_rag_query,
    "reset_knowledge_base": _handle_reset,
}


def handle_tool_call(tool_call) -> str:
    """LLM이 반환한 tool_call 객체를 파싱하여 해당 핸들러를 실행한다."""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)  # JSON 문자열 → dict 파싱
    handler = TOOL_HANDLERS.get(name)
    if handler:
        return handler(args)
    return "[오류] 알 수 없는 도구입니다."


# ── 에이전트 클래스 ──────────────────────────────────────────


class KBAgent:
    """Function Calling 기반 지식 베이스 에이전트.

    동작 원리:
    1. 사용자 메시지를 대화 히스토리에 추가
    2. solar-pro3에 도구 스키마(TOOLS)와 함께 호출
    3. 모델이 tool_calls를 반환하면 → 해당 핸들러 실행 → 결과를 히스토리에 추가
    4. tool_calls가 없을 때까지 2-3을 반복 (while 루프)
    5. 최종 텍스트 응답 반환

    이 루프 덕분에 LLM이 여러 도구를 순차적으로 호출할 수도 있다.
    예: list_documents → rag_query 등 다단계 작업 가능
    """

    def __init__(self, usage_enabled: bool = False):
        # 대화 히스토리: system prompt로 초기화. 이후 user/assistant/tool 메시지 누적.
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tracker = UsageTracker(enabled=usage_enabled)

    def ask(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})

        # [Upstage API] Chat Completions + Function Calling
        # solar-pro3 모델에 6개 도구 스키마(TOOLS)를 함께 전달.
        # 모델이 사용자 의도를 파악하여 도구 호출 여부를 결정한다.
        # 도구가 필요 없으면 바로 텍스트 응답을, 필요하면 tool_calls를 반환.
        response = client.chat.completions.create(
            model="solar-pro3",
            messages=self.messages,
            tools=TOOLS,
        )
        self.tracker.track_chat(response)

        message = response.choices[0].message
        self.messages.append(message)

        # ── 에이전트 루프: 도구 호출이 없을 때까지 반복 ──
        while message.tool_calls:
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                label = TOOL_LABELS.get(name, name)
                print(f"\n[{label}] {name} 호출됨")

                # 도구 핸들러 실행 (add_document, rag_query 등)
                result = handle_tool_call(tool_call)
                preview = result[:200] + "..." if len(result) > 200 else result
                print(f"[결과 미리보기]\n{preview}")

                # 도구 실행 결과를 role:"tool" 메시지로 대화 히스토리에 추가
                # tool_call_id로 어떤 호출의 결과인지 매핑
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

            # [Upstage API] Chat Completions + Function Calling (tool 결과 반영 후 재호출)
            # 도구 결과가 추가된 히스토리로 다시 모델 호출 →
            # 추가 도구가 필요하면 다시 tool_calls 반환, 아니면 최종 텍스트 응답
            response = client.chat.completions.create(
                model="solar-pro3",
                messages=self.messages,
                tools=TOOLS,
            )
            self.tracker.track_chat(response)
            message = response.choices[0].message
            self.messages.append(message)

        print_usage(self.tracker, None)
        return message.content
