import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from k8s_assistant.k8s_agent import K8sAgent


HELP_TEXT = """
사용 가능한 기능:
  1. YAML 분석   - K8s YAML을 붙여넣으면 분석합니다
  2. YAML 생성   - 자연어로 요구사항을 입력하면 YAML을 생성합니다
  3. YAML 검증   - 보안/베스트 프랙티스를 검사합니다
  4. 멀티 리소스  - Deployment+Service+Ingress 등을 한번에 생성합니다
  5. YAML 비교   - 두 YAML의 차이점을 설명합니다

명령어:
  help  - 도움말 표시
  clear - 대화 초기화
  quit  - 종료

YAML 입력 방법:
  apiVersion: 또는 kind: 또는 --- 로 시작하면
  멀티라인 모드가 활성화됩니다.
  빈 줄을 2번 입력하면 입력이 완료됩니다.
"""


def read_multiline_yaml(first_line: str) -> str:
    """YAML 멀티라인 입력을 처리."""
    print("  (YAML 입력 중... 빈 줄 2번 입력으로 완료)")
    lines = [first_line]
    empty_count = 0

    while True:
        try:
            extra = input("  ")
        except (EOFError, KeyboardInterrupt):
            break

        if extra.strip() == "":
            empty_count += 1
            if empty_count >= 2:
                break
            lines.append("")
        else:
            empty_count = 0
            lines.append(extra)

    return "\n".join(lines)


def is_yaml_start(line: str) -> bool:
    """YAML 시작 여부를 판단."""
    return line.startswith(("apiVersion:", "kind:", "---"))


def main():
    usage_enabled = "--usage" in sys.argv

    print("=== Kubernetes YAML Assistant ===")
    print("K8s 매니페스트 분석/생성/검증을 도와드립니다.")
    if usage_enabled:
        print("📊 사용량 추적 활성화 (비용은 추정치이며, 정확한 차감량은 console.upstage.ai/billing 에서 확인하세요)")
    print("'help'로 사용법을 확인하세요. (quit 또는 exit로 종료)\n")

    agent = K8sAgent(usage_enabled=usage_enabled)

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
            agent = K8sAgent(usage_enabled=usage_enabled)
            print("대화가 초기화되었습니다.\n")
            continue

        # 멀티라인 YAML 입력 처리
        if is_yaml_start(line):
            question = read_multiline_yaml(line)
        else:
            question = line

        try:
            answer = agent.ask(question)
            print(f"\n{answer}\n")
        except Exception as e:
            print(f"\n[오류] {e}\n")


if __name__ == "__main__":
    main()
