import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from commit_guardian.guardian_agent import GuardianAgent
from commit_guardian.git_tools import get_diff, get_commit_log


HELP_TEXT = """
=== Commit Guardian - 사용법 ===

명령어:
  repo <path>              - 저장소 경로 설정/변경
  review                   - 최신 unstaged 변경사항 리뷰
  staged                   - staged 변경사항 리뷰
  commit <hash>            - 특정 커밋 리뷰
  release                  - 릴리스 노트 생성 (한/영)
  test                     - 변경사항에 대한 테스트 제안 (변경 없으면 최근 커밋)
  test staged              - staged 변경사항에 대한 테스트 제안
  test <hash>              - 특정 커밋에 대한 테스트 제안
  help                     - 도움말 표시
  clear                    - 대화 초기화
  quit                     - 종료

자연어 입력도 가능합니다:
  "이 커밋 리뷰해줘"
  "보안 이슈 있는지 확인해줘"
  "릴리스 노트 만들어줘"
"""


def main():
    usage_enabled = "--usage" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--usage"]

    print("=== Commit Guardian ===")
    print("코드 변경사항을 분석하고 리뷰를 제공합니다.")
    if usage_enabled:
        print("📊 사용량 추적 활성화 (비용은 추정치이며, 정확한 차감량은 console.upstage.ai/billing 에서 확인하세요)")
    print("'help'로 사용법을 확인하세요.\n")

    # 저장소 경로 설정
    repo_path = ""
    if args:
        repo_path = os.path.abspath(args[0])
        print(f"저장소: {repo_path}\n")
    else:
        print("저장소 경로를 입력하세요 (또는 Enter로 건너뛰기):")
        try:
            path_input = input("repo> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            return
        if path_input:
            repo_path = os.path.abspath(path_input)
            print(f"저장소: {repo_path}\n")
        else:
            print("저장소 미설정. 'repo <path>' 명령어로 설정하세요.\n")

    agent = GuardianAgent(repo_path, usage_enabled=usage_enabled)

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
            agent = GuardianAgent(repo_path, usage_enabled=usage_enabled)
            print("대화가 초기화되었습니다.\n")
            continue

        # repo 명령어
        if line.lower().startswith("repo "):
            repo_path = os.path.abspath(line[5:].strip())
            agent.set_repo(repo_path)
            print(f"저장소가 변경되었습니다: {repo_path}\n")
            continue

        # 저장소 미설정 체크
        if not repo_path:
            print("[오류] 저장소가 설정되지 않았습니다. 'repo <path>'로 설정하세요.\n")
            continue

        # 단축 명령 → 자연어 변환
        # 사용자 질문을 바탕으로, LLM에게 groundedness 검증할 것을 지시하는 메시지를 추가
        if line.lower() == "review":
            question = f"{repo_path} 저장소의 unstaged 변경사항을 코드 리뷰해주세요. 발견사항은 반드시 groundedness 검증을 해주세요."
        elif line.lower() == "staged":
            question = f"{repo_path} 저장소의 staged 변경사항을 코드 리뷰해주세요. 발견사항은 반드시 groundedness 검증을 해주세요."
        elif line.lower().startswith("commit "):
            commit_hash = line[7:].strip()
            question = f"{repo_path} 저장소의 커밋 {commit_hash}을 코드 리뷰해주세요. 발견사항은 반드시 groundedness 검증을 해주세요."
        elif line.lower() == "release":
            question = f"{repo_path} 저장소의 변경사항으로 릴리스 노트를 한국어와 영어 모두 생성해주세요."
        elif line.lower().startswith("test"):
            test_arg = line[4:].strip().lower()
            if test_arg == "staged":
                mode, commit_hash = "staged", None
            elif test_arg:
                mode, commit_hash = "commit", test_arg
            else:
                mode, commit_hash = "unstaged", None

            # fallback: unstaged/staged 변경사항이 없으면 최근 커밋으로 전환
            if mode != "commit":
                diff_result = get_diff(repo_path, mode)
                if diff_result == "(변경 사항 없음)":
                    log = get_commit_log(repo_path, count=1)
                    if log and not log.startswith("["):
                        commit_hash = log.split()[0]
                        mode = "commit"
                        print(f"[{mode}] 변경사항 없음 → 최근 커밋 {commit_hash}으로 전환\n")

            if mode == "commit" and commit_hash:
                question = f"{repo_path} 저장소의 커밋 {commit_hash}의 변경사항에 대한 테스트 케이스를 제안해주세요."
            elif mode == "staged":
                question = f"{repo_path} 저장소의 staged 변경사항에 대한 테스트 케이스를 제안해주세요."
            else:
                question = f"{repo_path} 저장소의 unstaged 변경사항에 대한 테스트 케이스를 제안해주세요."
        else:
            question = line
            if repo_path not in question:
                question = f"[저장소: {repo_path}] {question}"

        try:
            answer = agent.ask(question)
            print(f"\n{answer}\n")
        except Exception as e:
            print(f"\n[오류] {e}\n")


if __name__ == "__main__":
    main()
