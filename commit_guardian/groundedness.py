import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.client import client


def check_groundedness(context: str, answer: str) -> str:
    """
    리뷰 발견사항이 실제 diff에 근거하는지 검증.

    Args:
        context: 실제 코드 diff (근거 자료)
        answer: AI가 생성한 리뷰 발견사항 (검증 대상)

    Returns:
        "grounded" | "notGrounded" | "notSure"
    """
    # 컨텍스트가 너무 길면 잘라내기
    max_ctx = 4000
    if len(context) > max_ctx:
        context = context[:max_ctx] + "\n...(truncated)"

    try:
        # [Upstage API] Groundedness Check
        # 리뷰 발견사항이 실제 코드 diff에 근거하는지 검증
        # https://console.upstage.ai/api/groundedness-checking
        response = client.chat.completions.create(
            model="solar-pro3",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a groundedness checker. "
                        "Given a code diff (context) and a review finding (answer), "
                        "determine if the finding is directly supported by the code changes in the context. "
                        "Respond with exactly one word: grounded, notGrounded, or notSure."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"[Context - Code Diff]\n{context}\n\n"
                        f"[Answer - Review Finding]\n{answer}\n\n"
                        "Is this review finding grounded in the actual code diff? "
                        "Respond with: grounded, notGrounded, or notSure"
                    ),
                },
            ],
        )
        result = response.choices[0].message.content.strip().lower()
        if "notgrounded" in result:
            return "notGrounded"
        elif "grounded" in result:
            return "grounded"
        else:
            return "notSure"
    except Exception as e:
        return f"[Groundedness 오류] {e}"
