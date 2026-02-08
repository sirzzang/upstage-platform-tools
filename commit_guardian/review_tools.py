def parse_diff_stats(diff_text: str) -> str:
    """diff 통계 요약: 파일 수, 추가/삭제 줄."""
    additions = 0
    deletions = 0
    files = set()

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            parts = line.split(" b/")
            if len(parts) > 1:
                files.add(parts[-1])
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    return (
        f"변경 파일 수: {len(files)}\n"
        f"추가된 줄: +{additions}\n"
        f"삭제된 줄: -{deletions}\n"
        f"변경 파일:\n" + "\n".join(f"  - {f}" for f in sorted(files))
    )


def format_review_context(diff_text: str, changed_files: str) -> str:
    """리뷰 컨텍스트를 하나의 문자열로 조합."""
    stats = parse_diff_stats(diff_text)

    # diff가 너무 길면 잘라내기 (LLM 컨텍스트 보호)
    max_diff_len = 8000
    truncated = ""
    if len(diff_text) > max_diff_len:
        diff_text = diff_text[:max_diff_len]
        truncated = f"\n(diff가 {max_diff_len}자로 잘렸습니다. 전체 diff는 더 깁니다.)"

    return (
        f"[변경 통계]\n{stats}\n\n"
        f"[변경 파일 목록]\n{changed_files}\n\n"
        f"[전체 Diff]\n{diff_text}{truncated}"
    )
