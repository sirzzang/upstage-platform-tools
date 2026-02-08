import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mlops_dashboard.db_manager import DB_PATH
from mlops_dashboard.setup_db import create_sample_db
from mlops_dashboard.sql_agent import SQLAgent


def main():
    usage_enabled = "--usage" in sys.argv

    if not os.path.exists(DB_PATH):
        print("샘플 DB가 없습니다. 생성합니다...")
        create_sample_db()

    print(f"DB 연결 완료 ({DB_PATH})")
    if usage_enabled:
        print("📊 사용량 추적 활성화 (비용은 추정치이며, 정확한 차감량은 console.upstage.ai/billing 에서 확인하세요)")
    print("질문을 입력하세요 (quit 또는 exit로 종료)\n")

    agent = SQLAgent(usage_enabled=usage_enabled)

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit"):
            print("종료합니다.")
            break

        try:
            answer = agent.ask(question)
            print(f"\n[설명] {answer}\n")
        except Exception as e:
            print(f"\n[오류] {e}\n")


if __name__ == "__main__":
    main()
