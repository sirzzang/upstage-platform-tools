import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from iac_doc_intel.iac_agent import IaCDocAgent


HELP_TEXT = """
=== IaC Doc Intelligence - 사용법 ===

명령어:
  classify <file>          - 문서 유형 분류 (terraform/kubernetes/ansible)
  parse <file>             - 문서 파싱 (텍스트 추출)
  extract <file>           - 정보 추출 (구조화된 데이터)
  analyze <file>           - 종합 분석 (분류+파싱+추출+보안 분석)
  generate-samples         - 테스트용 샘플 PDF 생성
  samples                  - 샘플 파일 목록 표시
  help                     - 도움말 표시
  clear                    - 대화 초기화
  quit                     - 종료

자연어 입력도 가능합니다:
  "이 Terraform 파일 분석해줘"
  "보안 이슈 있는지 확인해줘"
  "어떤 리소스가 정의되어 있어?"
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
    usage_enabled = "--usage" in sys.argv

    print("=== IaC Doc Intelligence ===")
    print("IaC 문서를 분류, 파싱, 분석합니다.")
    if usage_enabled:
        print("📊 사용량 추적 활성화 (비용은 추정치이며, 정확한 차감량은 console.upstage.ai/billing 에서 확인하세요)")
    print("'help'로 사용법을 확인하세요. (quit 또는 exit로 종료)\n")

    agent = IaCDocAgent(usage_enabled=usage_enabled)

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
            agent = IaCDocAgent(usage_enabled=usage_enabled)
            print("대화가 초기화되었습니다.\n")
            continue

        # generate-samples 명령
        if line.lower() == "generate-samples":
            try:
                from iac_doc_intel.sample_generator import generate_all_samples

                print("샘플 PDF 생성 중...")
                generate_all_samples()
                print("샘플 생성 완료!\n")
            except ImportError as e:
                print(f"[오류] fpdf2 패키지가 필요합니다: pip install fpdf2\n{e}\n")
            continue

        # samples 명령
        if line.lower() == "samples":
            list_samples()
            continue

        # 단축 명령 처리
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd in ("classify", "parse", "extract", "analyze") and len(parts) > 1:
            file_path = resolve_file_path(parts[1].strip())
            if not file_path:
                continue

            if cmd == "classify":
                question = f"{file_path} 문서를 분류해주세요."
            elif cmd == "parse":
                question = f"{file_path} 문서를 파싱해서 텍스트를 추출해주세요."
            elif cmd == "extract":
                question = f"{file_path} 문서에서 IaC 정보를 추출해주세요."
            else:  # analyze
                question = f"{file_path} 문서를 종합 분석해주세요. 보안 이슈, 베스트 프랙티스 위반, 개선사항을 알려주세요."
        else:
            question = line

        try:
            answer = agent.ask(question)
            print(f"\n{answer}\n")
        except Exception as e:
            print(f"\n[오류] {e}\n")


if __name__ == "__main__":
    main()
