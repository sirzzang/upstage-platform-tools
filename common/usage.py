"""API 사용량 추적 및 비용 계산 모듈.

Upstage API 응답의 usage 필드를 누적 추적하고,
호출당 / 세션 누적 토큰 수와 예상 비용을 표시합니다.
"""

# Upstage API 가격표 (2025년 기준, USD per 1M tokens)
PRICING = {
    # Chat / Function Calling / Groundedness Check
    "solar-pro3": {"input": 0.15, "output": 0.60},
    "solar-pro2": {"input": 0.15, "output": 0.60},
    "solar-mini": {"input": 0.15, "output": 0.15},
    # Embeddings
    "embedding-passage": {"input": 0.10, "output": 0.0},
    "embedding-query": {"input": 0.10, "output": 0.0},
    "solar-embedding-1-large-passage": {"input": 0.10, "output": 0.0},
    "solar-embedding-1-large-query": {"input": 0.10, "output": 0.0},
}

# Document AI 가격표 (USD per page)
DOC_PRICING = {
    "document-parse": 0.01,
    "document-classify": 0.004,
    "information-extract": 0.04,
}


class UsageTracker:
    """API 사용량 누적 추적기."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_embedding_tokens = 0
        self.total_doc_pages = 0
        self.total_cost = 0.0
        self.call_count = 0

    def track_chat(self, response, model: str = "solar-pro3") -> dict | None:
        """Chat/Function Calling 응답의 usage를 추적합니다.

        Returns:
            {"input": int, "output": int, "cost": float} 또는 None
        """
        usage = getattr(response, "usage", None)
        if not usage:
            return None

        input_tokens = usage.prompt_tokens or 0
        output_tokens = usage.completion_tokens or 0

        price = PRICING.get(model, PRICING["solar-pro3"])
        cost = (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.call_count += 1

        return {
            "input": input_tokens,
            "output": output_tokens,
            "cost": cost,
        }

    def track_embedding(self, response, model: str = "embedding-passage") -> dict | None:
        """Embeddings 응답의 usage를 추적합니다."""
        usage = getattr(response, "usage", None)
        if not usage:
            return None

        tokens = usage.total_tokens or 0
        price = PRICING.get(model, PRICING["embedding-passage"])
        cost = tokens * price["input"] / 1_000_000

        self.total_embedding_tokens += tokens
        self.total_cost += cost
        self.call_count += 1

        return {"tokens": tokens, "cost": cost}

    def track_doc(self, model: str, pages: int = 1) -> dict:
        """Document AI 호출을 추적합니다."""
        price_per_page = DOC_PRICING.get(model, 0.01)
        cost = pages * price_per_page

        self.total_doc_pages += pages
        self.total_cost += cost
        self.call_count += 1

        return {"pages": pages, "cost": cost}

    def format_last(self, info: dict | None) -> str:
        """마지막 호출의 사용량을 포맷팅합니다."""
        if not info:
            return ""
        if "input" in info:
            return (
                f"📊 토큰: {info['input']:,} in + {info['output']:,} out"
                f" | 비용: ${info['cost']:.6f}"
            )
        if "tokens" in info:
            return f"📊 토큰: {info['tokens']:,} | 비용: ${info['cost']:.6f}"
        if "pages" in info:
            return f"📊 페이지: {info['pages']} | 비용: ${info['cost']:.4f}"
        return ""

    def format_session(self) -> str:
        """세션 누적 사용량을 포맷팅합니다."""
        parts = [f"📈 세션 누적: {self.call_count}회 호출"]
        tokens = self.total_input_tokens + self.total_output_tokens + self.total_embedding_tokens
        if tokens > 0:
            parts.append(f"총 {tokens:,} 토큰")
        if self.total_doc_pages > 0:
            parts.append(f"{self.total_doc_pages} 페이지")
        parts.append(f"총 비용: ${self.total_cost:.6f}")
        return " | ".join(parts)


def print_usage(tracker: UsageTracker, last_info: dict | None):
    """사용량을 출력합니다 (마지막 호출 + 세션 누적)."""
    last = tracker.format_last(last_info)
    session = tracker.format_session()
    if last:
        print(f"  {last}")
    print(f"  {session}")
