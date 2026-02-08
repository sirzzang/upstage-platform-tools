import re

from k8s_assistant.templates import TEMPLATES, VALIDATION_RULES


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
