"""Platform Knowledge Base CLI 진입점.

사용자와의 대화형(REPL) 인터페이스를 제공한다.
- 단축 명령(add, docs, search, reset 등)을 자연어로 변환하여 에이전트에 전달
- 자연어 질문은 그대로 KBAgent.ask()에 전달 → Function Calling으로 자동 처리
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from platform_kb.kb_agent import KBAgent


HELP_TEXT = """
=== Platform Knowledge Base - 사용법 ===

명령어:
  add <file>             - 문서를 지식 베이스에 추가
  docs                   - 저장된 문서 목록 표시
  search <query>         - 유사 문서 검색
  reset                  - 지식 베이스 초기화
  generate-samples       - 테스트용 샘플 문서 생성
  samples                - 샘플 파일 목록 표시
  help                   - 도움말 표시
  clear                  - 대화 초기화
  quit                   - 종료

자연어 입력도 가능합니다:
  "CrashLoopBackOff 대응 방법 알려줘"
  "DB 장애 포스트모템 요약해줘"
  "마이크로서비스 아키텍처 구성이 어떻게 돼?"
"""

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")


def resolve_file_path(path_str: str) -> str | None:
    """파일 경로를 해석하고 존재 여부 확인."""
    abs_path = os.path.abspath(path_str)
    if os.path.isfile(abs_path):
        return abs_path
    # samples 디렉토리에서도 찾기
    sample_path = os.path.join(SAMPLES_DIR, path_str)
    if os.path.isfile(sample_path):
        return sample_path
    print(f"[오류] 파일을 찾을 수 없습니다: {path_str}")
    return None


def list_samples():
    """샘플 디렉토리의 파일 목록 표시."""
    if not os.path.isdir(SAMPLES_DIR):
        print("샘플 디렉토리가 없습니다. 'generate-samples'로 생성하세요.\n")
        return
    files = os.listdir(SAMPLES_DIR)
    if not files:
        print("샘플 파일이 없습니다. 'generate-samples'로 생성하세요.\n")
        return
    print("샘플 파일 목록:")
    for f in sorted(files):
        full_path = os.path.join(SAMPLES_DIR, f)
        size = os.path.getsize(full_path)
        print(f"  - {f} ({size} bytes)")
    print()


def main():
    """메인 REPL(Read-Eval-Print Loop) 함수.

    실행: python -m platform_kb.main [--usage]
    --usage 플래그를 붙이면 API 호출 비용 추정치를 표시한다.
    """
    usage_enabled = "--usage" in sys.argv

    print("=== Platform Knowledge Base ===")
    print("플랫폼 엔지니어링 문서를 임베딩하고, RAG 기반 Q&A를 제공합니다.")
    if usage_enabled:
        print("📊 사용량 추적 활성화 (비용은 추정치이며, 정확한 차감량은 console.upstage.ai/billing 에서 확인하세요)")
    print("'help'로 사용법을 확인하세요. (quit 또는 exit로 종료)\n")

    agent = KBAgent(usage_enabled=usage_enabled)

    # ── REPL 루프 ──
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if not line:
            continue
        if line.lower() in ("quit", "exit"):
            print("종료합니다.")
            break
        if line.lower() == "help":
            print(HELP_TEXT)
            continue
        if line.lower() == "clear":
            agent = KBAgent(usage_enabled=usage_enabled)
            print("대화가 초기화되었습니다.\n")
            continue

        # generate-samples 명령
        if line.lower() == "generate-samples":
            try:
                from platform_kb.sample_docs import generate_all_samples

                print("샘플 문서 생성 중...")
                generate_all_samples()
                print("샘플 생성 완료!\n")
            except ImportError as e:
                print(f"[오류] 샘플 생성 모듈 로드 실패: {e}\n")
            continue

        # samples 명령
        if line.lower() == "samples":
            list_samples()
            continue

        # reset 명령
        if line.lower() == "reset":
            from platform_kb.vector_store import VectorStore

            store = VectorStore()
            store.reset()
            print("지식 베이스가 초기화되었습니다.\n")
            continue

        # docs 명령
        if line.lower() == "docs":
            from platform_kb.vector_store import VectorStore

            store = VectorStore()
            docs = store.list_documents()
            if not docs:
                print("지식 베이스가 비어있습니다. 'add <file>'로 문서를 추가하세요.\n")
            else:
                print("저장된 문서:")
                total = 0
                for name, count in sorted(docs.items()):
                    print(f"  - {name} ({count} chunks)")
                    total += count
                print(f"\n총 {len(docs)}개 문서, {total}개 청크\n")
            continue

        # ── 단축 명령 → 자연어 변환 ──
        # 단축 명령을 자연어 문장으로 변환하여 에이전트에 전달.
        # 에이전트가 Function Calling으로 적절한 도구를 자동 선택한다.
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd == "add" and len(parts) > 1:
            file_path = resolve_file_path(parts[1].strip())
            if not file_path:
                continue
            # "add runbook.md" → "/.../runbook.md 문서를 지식 베이스에 추가해주세요."
            question = f"{file_path} 문서를 지식 베이스에 추가해주세요."
        elif cmd == "search" and len(parts) > 1:
            query = parts[1].strip()
            question = f"'{query}'로 유사 문서를 검색해주세요."
        else:
            # 단축 명령이 아닌 자연어 입력은 그대로 에이전트에 전달
            question = line

        try:
            answer = agent.ask(question)
            print(f"\n{answer}\n")
        except Exception as e:
            print(f"\n[오류] {e}\n")


if __name__ == "__main__":
    main()
