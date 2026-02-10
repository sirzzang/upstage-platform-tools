"""근거 검증(Groundedness Check) 모듈.

RAG 시스템에서 LLM이 생성한 답변이 실제 검색된 문서에 근거하는지
별도의 LLM 호출로 검증한다. 이를 통해:
  - 환각(hallucination) 탐지: LLM이 문서에 없는 내용을 지어냈는지 확인
  - 답변 신뢰도 표시: grounded / notGrounded / notSure 배지로 사용자에게 투명 공개
  - RAG 품질 보증: 검색 결과가 부족하거나 무관할 때 이를 감지

프로덕션에서는 Upstage의 전용 Groundedness Check API를 사용할 수도 있으나,
여기서는 solar-pro3 채팅 모델을 활용한 프롬프트 기반 검증을 구현한다.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.client import client


def check_groundedness(context: str, answer: str) -> str:
    """
    RAG 답변이 검색된 문서에 근거하는지 검증.

    Args:
        context: 검색된 문서 청크들을 하나로 합친 텍스트 (근거 자료)
        answer: AI가 생성한 답변 (검증 대상)

    Returns:
        "grounded"    — 답변이 문서 내용에 의해 뒷받침됨
        "notGrounded" — 답변이 문서에 없는 내용을 포함함 (환각 가능성)
        "notSure"     — 근거 여부를 판단하기 어려움
    """
    # 컨텍스트가 너무 길면 LLM 토큰 한도를 초과할 수 있으므로 4000자로 제한.
    # 잘린 부분은 검증 대상에서 제외되므로,
    # 긴 문서의 후반부에만 근거가 있는 경우 "notSure"가 나올 수 있다.
    max_ctx = 4000
    if len(context) > max_ctx:
        context = context[:max_ctx] + "\n...(truncated)"

    try:
        # [Upstage API] Chat Completions (solar-pro3) — Groundedness Check 용도
        # 별도의 system prompt로 "근거 검증 전문가" 역할을 부여.
        # 검색된 문서(context)와 AI 답변(answer)을 함께 전달하여
        # 답변이 문서에 직접적으로 뒷받침되는지 판정을 요청한다.
        response = client.chat.completions.create(
            model="solar-pro3",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a groundedness checker. "
                        "Given retrieved documents (context) and an AI-generated answer, "
                        "determine if the answer is directly supported by the documents. "
                        "Respond with exactly one word: grounded, notGrounded, or notSure."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"[Context - Retrieved Documents]\n{context}\n\n"
                        f"[Answer - AI Response]\n{answer}\n\n"
                        "Is this answer grounded in the retrieved documents? "
                        "Respond with: grounded, notGrounded, or notSure"
                    ),
                },
            ],
        )
        # LLM 응답에서 판정 결과 추출 (contains 방식으로 유연하게 매칭)
        # "notgrounded"을 먼저 체크해야 "grounded"에 잘못 매칭되지 않음
        result = response.choices[0].message.content.strip().lower()
        if "notgrounded" in result:
            return "notGrounded"
        elif "grounded" in result:
            return "grounded"
        else:
            return "notSure"
    except Exception as e:
        return f"[Groundedness 오류] {e}"
