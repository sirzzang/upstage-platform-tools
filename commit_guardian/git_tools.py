import os
import subprocess


def _run_git(repo_path: str, args: list[str]) -> str:
    """Git 명령어를 실행하고 stdout을 반환."""
    if not os.path.isdir(repo_path):
        return f"[오류] 경로가 존재하지 않습니다: {repo_path}"
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return f"[오류] Git 저장소가 아닙니다: {repo_path}"

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return f"[Git 오류] {result.stderr.strip()}"
        return result.stdout.strip() if result.stdout.strip() else "(변경 사항 없음)"
    except subprocess.TimeoutExpired:
        return "[오류] Git 명령어 실행 시간이 초과되었습니다."
    except FileNotFoundError:
        return "[오류] git이 설치되어 있지 않습니다."


def get_diff(
    repo_path: str, mode: str = "unstaged", commit_hash: str | None = None
) -> str:
    """diff 조회. mode: unstaged, staged, commit"""
    if mode == "staged":
        return _run_git(repo_path, ["diff", "--cached"])
    elif mode == "commit" and commit_hash:
        return _run_git(repo_path, ["show", "--format=", commit_hash])
    else:
        return _run_git(repo_path, ["diff"])


def get_commit_log(repo_path: str, count: int = 5) -> str:
    """최근 커밋 로그 조회."""
    return _run_git(repo_path, ["log", f"-{count}", "--oneline", "--no-decorate"])


def get_changed_files(
    repo_path: str, mode: str = "unstaged", commit_hash: str | None = None
) -> str:
    """변경된 파일 목록 조회."""
    if mode == "staged":
        return _run_git(repo_path, ["diff", "--cached", "--name-status"])
    elif mode == "commit" and commit_hash:
        return _run_git(
            repo_path, ["show", "--name-status", "--format=", commit_hash]
        )
    else:
        return _run_git(repo_path, ["diff", "--name-status"])


def get_commit_info(repo_path: str, commit_hash: str) -> str:
    """커밋 상세 정보 조회."""
    return _run_git(
        repo_path,
        [
            "show",
            "--no-patch",
            "--format=커밋: %H%n작성자: %an <%ae>%n날짜: %ai%n%n%s%n%n%b",
            commit_hash,
        ],
    )
