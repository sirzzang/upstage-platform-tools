import os
import re

from k8s_assistant.templates import TEMPLATES, VALIDATION_RULES

# analyze_repo에서 탐색할 파일 목록 (우선순위 순)
_REPO_FILES = [
    # 컨테이너 빌드
    ("Dockerfile", "Dockerfile"),
    ("docker-compose.yml", "Docker Compose"),
    ("docker-compose.yaml", "Docker Compose"),
    # 환경변수
    (".env.example", "환경변수 예시"),
    (".env.sample", "환경변수 예시"),
    (".env.template", "환경변수 예시"),
    # 언어별 의존성
    ("go.mod", "Go 모듈"),
    ("package.json", "Node.js 패키지"),
    ("requirements.txt", "Python 의존성"),
    ("pom.xml", "Maven (Java)"),
    ("build.gradle", "Gradle (Java)"),
    ("Cargo.toml", "Rust 패키지"),
    # 기존 K8s 매니페스트
    ("k8s/", "K8s 매니페스트 디렉토리"),
    ("deploy/", "배포 디렉토리"),
    ("manifests/", "매니페스트 디렉토리"),
    ("helm/", "Helm 차트 디렉토리"),
]

# 언어별 엔트리포인트 파일 탐색 패턴
_ENTRYPOINTS = [
    ("cmd/*/main.go", "Go 엔트리포인트"),
    ("main.go", "Go 엔트리포인트"),
    ("cmd/app/main.go", "Go 엔트리포인트"),
    ("main.py", "Python 엔트리포인트"),
    ("app.py", "Python 엔트리포인트"),
    ("manage.py", "Django 엔트리포인트"),
    ("src/main.ts", "TypeScript 엔트리포인트"),
    ("src/index.ts", "TypeScript 엔트리포인트"),
    ("src/main.js", "Node.js 엔트리포인트"),
    ("index.js", "Node.js 엔트리포인트"),
    ("app.js", "Node.js 엔트리포인트"),
    ("server.js", "Node.js 엔트리포인트"),
    ("src/main/java/**/Application.java", "Spring Boot 엔트리포인트"),
    ("src/main.rs", "Rust 엔트리포인트"),
]


def analyze_repo(repo_path: str) -> str:
    """레포지토리의 주요 파일을 읽어 K8s 배포에 필요한 정보를 추출."""
    repo_path = os.path.expanduser(repo_path.strip())
    if not os.path.isdir(repo_path):
        return f"[오류] 디렉토리를 찾을 수 없습니다: {repo_path}"

    sections = []

    # 1. 디렉토리 구조 (1단계)
    try:
        entries = sorted(os.listdir(repo_path))
        tree = [e for e in entries if not e.startswith(".")]
        sections.append(f"[디렉토리 구조]\n{', '.join(tree)}")
    except OSError:
        pass

    # 2. 주요 파일 읽기
    for filename, label in _REPO_FILES:
        filepath = os.path.join(repo_path, filename)
        if filename.endswith("/"):
            # 디렉토리인 경우 존재 여부만 확인하고 내부 파일 목록 제공
            if os.path.isdir(filepath):
                try:
                    dir_files = _list_dir_recursive(filepath, max_depth=2)
                    sections.append(f"[{label}] {filename}\n{dir_files}")
                except OSError:
                    sections.append(f"[{label}] {filename} (디렉토리 존재)")
        elif os.path.isfile(filepath):
            content = _read_file_safe(filepath)
            if content:
                sections.append(f"[{label}] {filename}\n{content}")

    # 3. 엔트리포인트 탐색
    for pattern, label in _ENTRYPOINTS:
        found_files = _glob_simple(repo_path, pattern)
        for fpath in found_files:
            rel_path = os.path.relpath(fpath, repo_path)
            content = _read_file_safe(fpath)
            if content:
                sections.append(f"[{label}] {rel_path}\n{content}")

    if not sections:
        return f"[결과] {repo_path} 에서 K8s 배포에 관련된 파일을 찾지 못했습니다."

    header = f"[레포지토리] {repo_path}\n"
    return header + "\n\n---\n\n".join(sections)


def _read_file_safe(filepath: str, max_lines: int = 200) -> str | None:
    """파일을 안전하게 읽되, 너무 긴 파일은 잘라서 반환."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            truncated = lines[:max_lines]
            truncated.append(f"\n... ({len(lines) - max_lines}줄 생략)\n")
            return "".join(truncated)
        return "".join(lines)
    except (OSError, UnicodeDecodeError):
        return None


def _list_dir_recursive(dirpath: str, max_depth: int = 2, _depth: int = 0) -> str:
    """디렉토리 내부 파일 목록을 재귀적으로 반환."""
    if _depth >= max_depth:
        return ""
    result = []
    try:
        for entry in sorted(os.listdir(dirpath)):
            if entry.startswith("."):
                continue
            full = os.path.join(dirpath, entry)
            indent = "  " * _depth
            if os.path.isdir(full):
                result.append(f"{indent}{entry}/")
                result.append(_list_dir_recursive(full, max_depth, _depth + 1))
            else:
                result.append(f"{indent}{entry}")
    except OSError:
        pass
    return "\n".join(r for r in result if r)


def _glob_simple(base: str, pattern: str) -> list[str]:
    """간단한 glob 패턴 매칭 (** 미지원, * 는 단일 디렉토리 매칭)."""
    parts = pattern.split("/")
    candidates = [base]

    for part in parts:
        next_candidates = []
        for cand in candidates:
            if not os.path.isdir(cand):
                continue
            if part == "*" or part == "**":
                # * → 현재 디렉토리의 모든 항목
                try:
                    for entry in os.listdir(cand):
                        if not entry.startswith("."):
                            next_candidates.append(os.path.join(cand, entry))
                except OSError:
                    pass
            elif "*" in part:
                # 와일드카드 포함 (예: *.java)
                import fnmatch

                try:
                    for entry in os.listdir(cand):
                        if fnmatch.fnmatch(entry, part):
                            next_candidates.append(os.path.join(cand, entry))
                except OSError:
                    pass
            else:
                # 정확한 파일/디렉토리명
                full = os.path.join(cand, part)
                if os.path.exists(full):
                    next_candidates.append(full)
        candidates = next_candidates

    return [c for c in candidates if os.path.isfile(c)]


def analyze_yaml(yaml_content: str) -> str:
    """YAML에서 핵심 필드를 추출하고 원본과 함께 반환."""
    info_parts = []
    lines = yaml_content.strip().split("\n")

    extractors = {
        "apiVersion:": "API 버전",
        "kind:": "리소스 종류",
        "replicas:": "레플리카",
        "image:": "이미지",
        "containerPort:": "컨테이너 포트",
        "namespace:": "네임스페이스",
        "serviceName:": "서비스 이름",
        "type:": "타입",
    }

    name_found = False
    for line in lines:
        stripped = line.strip()

        # name은 첫 번째만 추출 (metadata.name)
        if not name_found and stripped.startswith("name:") and "  name:" in line:
            info_parts.append(f"이름: {stripped.split(':', 1)[1].strip()}")
            name_found = True
            continue

        for prefix, label in extractors.items():
            if stripped.startswith(prefix):
                value = stripped.split(":", 1)[1].strip()
                if value:
                    info_parts.append(f"{label}: {value}")
                break

    summary = "\n".join(info_parts) if info_parts else "구조 정보를 추출하지 못했습니다."
    return f"[추출된 정보]\n{summary}\n\n[원본 YAML]\n{yaml_content}"


def generate_yaml(requirement: str, resource_types: list | None = None) -> str:
    """요구사항과 관련 템플릿을 함께 반환."""
    if not resource_types:
        resource_types = ["Deployment"]

    template_parts = []
    for rt in resource_types:
        tmpl = TEMPLATES.get(rt)
        if tmpl:
            template_parts.append(f"# {rt} 템플릿 참고:\n{tmpl}")
        else:
            template_parts.append(f"# {rt}: 템플릿 없음 (직접 생성 필요)")

    templates_text = "\n---\n".join(template_parts)
    return (
        f"[요구사항] {requirement}\n"
        f"[요청 리소스] {', '.join(resource_types)}\n\n"
        f"[참고 템플릿]\n{templates_text}"
    )


def validate_yaml(yaml_content: str, check_categories: list | None = None) -> str:
    """문자열 기반 휴리스틱 검증."""
    if not check_categories or "all" in check_categories:
        check_categories = ["security", "resources", "reliability", "networking"]

    findings = []
    content_lower = yaml_content.lower()

    # SEC001: latest 태그
    if ":latest" in content_lower or "image: latest" in content_lower:
        rule = _get_rule("SEC001")
        if rule and rule["category"] in check_categories:
            findings.append(f"[{rule['severity']}] {rule['message']}")

    # SEC002: securityContext 미설정
    if "securitycontext" not in content_lower:
        rule = _get_rule("SEC002")
        if rule and rule["category"] in check_categories:
            findings.append(f"[{rule['severity']}] {rule['message']}")

    # SEC003: allowPrivilegeEscalation
    if "allowprivilegeescalation" not in content_lower and "security" in check_categories:
        rule = _get_rule("SEC003")
        if rule:
            findings.append(f"[{rule['severity']}] {rule['message']}")

    # RES001: resources 미설정
    if "resources:" not in content_lower:
        rule = _get_rule("RES001")
        if rule and rule["category"] in check_categories:
            findings.append(f"[{rule['severity']}] {rule['message']}")

    # REL001: livenessProbe
    if "livenessprobe" not in content_lower:
        rule = _get_rule("REL001")
        if rule and rule["category"] in check_categories:
            findings.append(f"[{rule['severity']}] {rule['message']}")

    # REL002: readinessProbe
    if "readinessprobe" not in content_lower:
        rule = _get_rule("REL002")
        if rule and rule["category"] in check_categories:
            findings.append(f"[{rule['severity']}] {rule['message']}")

    # REL003: replicas < 2
    replicas_match = re.search(r"replicas:\s*(\d+)", yaml_content)
    if replicas_match and int(replicas_match.group(1)) < 2:
        rule = _get_rule("REL003")
        if rule and rule["category"] in check_categories:
            findings.append(f"[{rule['severity']}] {rule['message']}")

    # NET001: namespace 미지정
    if "namespace:" not in content_lower:
        rule = _get_rule("NET001")
        if rule and rule["category"] in check_categories:
            findings.append(f"[{rule['severity']}] {rule['message']}")

    if not findings:
        findings.append("[OK] 주요 검증 항목을 모두 통과했습니다.")

    return f"[검증 결과]\n" + "\n".join(findings) + f"\n\n[원본 YAML]\n{yaml_content}"


def generate_multi_resource(requirement: str, resource_types: list) -> str:
    """여러 리소스 템플릿을 함께 반환."""
    return generate_yaml(requirement, resource_types)


def diff_yaml(yaml_before: str, yaml_after: str) -> str:
    """두 YAML을 나란히 반환."""
    return f"[변경 전 YAML]\n{yaml_before}\n\n[변경 후 YAML]\n{yaml_after}"


def _get_rule(rule_id: str) -> dict | None:
    """규칙 ID로 검증 규칙 조회."""
    return next((r for r in VALIDATION_RULES if r["id"] == rule_id), None)
