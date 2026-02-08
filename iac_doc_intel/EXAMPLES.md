# IaC Doc Intelligence 실제 사용 사례

`iac_doc_intel`의 실제 사용 사례를 정리했습니다.

## 실제 사용 사례

### 사례 1: Basic Terraform PDF 분류 및 분석

Basic 샘플 PDF(`terraform_sample.pdf`)에 `classify` 명령을 실행한 사례입니다.

```bash
> classify terraform_sample.pdf

[문서 분류] classify_document 호출됨
[결과 미리보기]
[분류 오류] Error code: 400 - {'error': {'message': 'The requested model is invalid or no longer supported...

[문서 파싱] parse_document 호출됨
[결과 미리보기]
[파싱 완료] 2 페이지 처리됨

[텍스트]
Terraform Configuration - AWS Infrastructure
# Terraform Configuration - AWS Infrastructure
provider "aws" {
region = "ap-northeast-2"
}
resource "aws_vpc" "main" {
cidr_block...

[정보 추출] extract_information 호출됨
[결과 미리보기]
[오류] 'unknown' 유형에 대한 추출 스키마가 없습니다. 지원: ['terraform', 'kubernetes', 'ansible']

[정보 추출] extract_information 호출됨
[결과 미리보기]
[추출 오류] Error code: 400 - ...

📈 세션 누적: 7회 호출 | 총 26,038 토큰 | 2 페이지 | 총 비용: $0.027030

📂 문서 분류 결과
업로드하신 파일은 Terraform 구성 파일(Infrastructure as Code)임을 확인했습니다.

📄 주요 내용 요약 (파싱된 텍스트 기준)
| 항목 | 내용 |
|------|------|
| 프로바이더 | aws – 리전 ap-northeast-2 |
| VPC | CIDR: 10.0.0.0/16, 태그: Name=main-vpc, Environment=production |
| 퍼블릭 서브넷 | CIDR: 10.0.1.0/24, AZ: ap-northeast-2a |
| 보안 그룹 | SSH(22), HTTP(80), HTTPS(443) → 0.0.0.0/0 |
| EC2 인스턴스 | t3.medium, AMI: ami-0c55b159cbfafe1f0 |
| 출력 | instance_public_ip |

※ OCR 오류
- "10 0 · 0 .0/16" → 실제는 10.0.0.0/16
- "t3 .medium" → t3.medium
- 공백이 잘못 삽입된 부분이 있습니다.

🔍 IaC 체크리스트 기반 분석

| 카테고리 | 평가 | 상세 내용 |
|----------|------|-----------|
| 보안 | CRITICAL | 보안그룹 0.0.0.0/0으로 모든 포트(22,80,443) 및 egress 전면 개방 |
| 베스트 프랙티스 | WARNING | provider 버전 고정 없음, 상태 파일 관리가 로컬로 가정 |
| 네트워킹 | WARNING | 보안그룹이 과도하게 열려 있어 외부 공격에 취약 |
| 비용 | INFO | t3.medium은 워크로드에 따라 다운사이징 가능, 단일 인스턴스 구성 |
| 안정성 | INFO | 멀티 AZ 배포 없음, 백업(EBS 스냅샷) 및 모니터링 설정 없음 |
```

`classify`만 요청했지만, LLM이 자율적으로 `parse_document` → `extract_information`까지 도구를 연속 호출(Function Calling 체이닝)하여 종합 분석 결과를 제공했습니다.

이 사례에서 주목할 점:

- **Document Classify API 오류 발생**: `document-classify` 모델이 400 에러를 반환했지만, LLM은 이를 무시하고 `parse_document`로 fallback하여 텍스트를 직접 읽고 분류를 수행했습니다. 즉, Document AI API가 실패해도 LLM이 파싱된 텍스트만으로 문서 유형을 정확히 판단합니다.
- **Information Extract API도 오류 발생**: `document-classify` 실패로 `doc_type`이 `unknown`이 되어 추출 스키마를 찾지 못했고, 수동으로 `terraform` 유형을 지정한 재시도에서도 `information-extract` 모델 자체가 400 에러를 반환했습니다. 그런데도 최종 응답에는 리소스 목록, 설정값, 보안 분석이 모두 포함되어 있습니다.
- **도구 실패를 LLM이 보완**: 3개 도구 중 2개(`classify`, `extract`)가 API 오류로 실패했지만, `parse_document`가 성공적으로 추출한 텍스트를 LLM이 직접 분석하여 분류/요약/보안 체크리스트까지 완성했습니다. 이는 에이전트 패턴에서 **도구는 보조 수단이고 LLM이 최종 판단의 주체**라는 점을 보여줍니다.

### 사례 2: Advanced Terraform PDF 파싱 — OCR 품질과 LLM 보정

Advanced 샘플 PDF(`terraform_fargate_sample.pdf`, 6페이지)를 `parse` 명령으로 파싱한 사례입니다.

```bash
> parse terraform_fargate_sample.pdf

[문서 파싱] parse_document 호출됨
[결과 미리보기]
[파싱 완료] 6 페이지 처리됨

[텍스트]
Terraform - ECS Fargate + Aurora Serverless + EFS
# Terraform - ECS Fargate + Aurora Serverless + EFS
# Source: github.com/futurice/terraform-examples
# aws/wordpress_fargate
...

📈 세션 누적: 10회 호출 | 총 49,648 토큰 | 8 페이지 | 총 비용: $0.093742

📌 주요 구성 요소 요약

| 구분 | 주요 리소스 | 비고 |
|------|-------------|------|
| 프로바이더 | aws (region: ap-northeast-2) | |
| 변수 | db_username, db_password (민감) | SSM 파라미터로 관리 |
| 출력 | cluster_name, rds_endpoint, efs_id | |
| 네트워크 | VPC, Public/Private Subnet, NAT GW, IGW, ALB SG | 퍼블릭 2개, 프라이빗 2개 |
| 보안 | ALB SG(22,80), ECS SG(8080), DB SG(3306), EFS SG(2049) | 대부분 0.0.0.0/0으로 열려 있어 보안 강화 필요 |
| 스토리지 | EFS 파일시스템 + 2개 마운트 타깃 | |
| 데이터베이스 | Aurora Serverless (MySQL) | deletion_protection=true, scaling 적용 |
| 컴퓨팅 | ECS Fargate (desired_count=2, cpu=512, mem=1024) | Auto Scaling (CPU>70%) 적용 |
| 모니터링 | CloudWatch 알람 cpu_high (CPU>85%) | |
| 시크릿 관리 | SSM db_user, db_pass (SecureString) | |
| 자동 스케일링 | appautoscaling_target (2~6) & policy (CPU) | |

🛠️ 권장 개선 사항 (SUGGESTION)

1. 보안 강화 — ALB SG, ECS SG, DB SG 모두 0.0.0.0/0 대신 최소 CIDR 적용. 특히 SSH(22)와 DB(3306)는 반드시 제한.
2. 상태 파일 관리 — terraform 상태 파일을 S3 백엔드에 저장하도록 backend 설정 추가.
3. 버전 고정 — required_providers 및 required_version 명시.
4. 고비용 리소스 검토 — Aurora max_capacity=4 축소 검토, Fargate cpu=512/mem=1024 적정성 확인.
5. 멀티 AZ 고가용성 — NAT Gateway가 1개만 사용 중. 다중 AZ에 배포 또는 Route 53 failover 구성 고려.
6. 코드 가독성 개선 — policy_arn 오타 수정 필요, assume_role_policy JSON 들여쓰기 오류 검토.
```

`parse`만 요청했지만, LLM이 파싱된 텍스트를 분석하여 구성 요소 요약 테이블과 6개 개선사항까지 제시했습니다.

이 사례에서 주목할 점:

- **OCR 노이즈에 대한 LLM의 강건성**: Document Parse API의 OCR 결과에는 상당한 노이즈가 포함되어 있었습니다. `"10 · 0 0 0/16"` (실제: `10.0.0.0/16`), `"${local.name }-vpc"` (공백 삽입), `"${local.name)-alb-sg"` (괄호 오류), `"$(local.name)-db-sg"` (`${}` → `$()`) 등. 그런데도 LLM은 이런 OCR 오류를 자연스럽게 무시하고, 원래 의도된 코드를 정확히 이해하여 20개 이상의 리소스를 올바르게 식별하고 분류했습니다.
- **PDF에서 코드를 읽는 한계와 가치**: 6페이지 분량의 복잡한 Terraform 코드를 PDF로 만들면 OCR 품질이 떨어지는 것은 불가피합니다. 하지만 "PDF로만 남아있는 인프라 문서"를 분석해야 하는 실무 상황에서는 이 정도의 노이즈 허용 범위 내에서도 핵심 구성을 파악할 수 있다는 점이 의미 있습니다.
- **`parse`만 호출했는데 분석까지 수행**: 사용자는 텍스트 추출만 요청했지만, LLM이 추출된 텍스트를 읽고 "이것은 Terraform 코드이므로 구성 요약과 개선사항을 제시하는 것이 유용하겠다"고 자율 판단했습니다. 시스템 프롬프트의 "IaC 분석 체크리스트"가 LLM의 행동 방향을 가이드한 결과입니다.

### 사례 2에서 발견된 OCR 오류 패턴

PDF 코드에서 반복적으로 나타나는 OCR 오류 유형을 정리하면:

| OCR 결과 | 실제 코드 | 오류 유형 |
|---|---|---|
| `"10 · 0 0 0/16"` | `"10.0.0.0/16"` | 마침표(`.`)가 중점(`·`)이나 공백으로 치환 |
| `"0.0 . 0 0/0"` | `"0.0.0.0/0"` | 마침표 주변에 불필요한 공백 삽입 |
| `${local.name }-vpc` | `${local.name}-vpc` | `}` 앞에 공백 삽입 |
| `${local.name)-alb-sg` | `${local.name}-alb-sg` | `}`가 `)`로 잘못 인식 |
| `$(local.name)-db-sg` | `${local.name}-db-sg` | `${}`가 `$()`로 잘못 인식 |
| `${local.name}-pub-$ {count.index}` | `${local.name}-pub-${count.index}` | `${` 사이에 공백 삽입 |

이런 OCR 오류는 PDF의 Courier 폰트에서 `.`, `{`, `}`, `$` 같은 특수문자가 혼동되기 때문에 발생합니다. Terraform 코드에서 `${...}` 보간 구문이 빈번하므로, 이 유형의 오류가 반복적으로 나타납니다.

그럼에도 LLM은 이 패턴을 "문맥상 `${local.name}`이 의도된 것"으로 자연스럽게 해석합니다. 이는 LLM이 Terraform HCL 문법을 학습 데이터에서 충분히 학습했기 때문에 가능한 보정입니다.

### 사례 3: Advanced Terraform PDF 종합 분석 — analyze 파이프라인 전체 동작

Advanced 샘플 PDF(`terraform_fargate_sample.pdf`, 6페이지)에 `analyze` 명령을 실행한 사례입니다. `analyze`는 내부적으로 분류 → 파싱 → 추출의 3단계 파이프라인을 순차 실행하는 종합 분석 명령입니다.

```bash
> analyze terraform_fargate_sample.pdf

[IaC 종합 분석] analyze_iac_document 호출됨
[결과 미리보기]
=== 1단계: 문서 분류 ===
[분류 오류] 404 page not found

=== 2단계: 문서 파싱 ===
[파싱 완료] 6 페이지 처리됨

[텍스트]
Terraform - ECS Fargate + Aurora Serverless + EFS
# Terraform - ECS Fargate + Aurora Serverless + EFS
# Sourc...

[문서 파싱] parse_document 호출됨
[결과 미리보기]
[파싱 완료] 6 페이지 처리됨
...

📈 세션 누적: 5회 호출 | 총 25,208 토큰 | 12 페이지 | 총 비용: $0.126721

IaC 문서 종합 분석 결과
파일: terraform_fargate_sample.pdf
분류: [Terraform] (AWS provider 기반)

## 1️⃣ 전체 요약
- 목표: WordPress Fargate 서비스 + Aurora Serverless DB + EFS 파일시스템
- 구성: VPC → Public/Private Subnet → NAT GW → ALB → ECS Fargate → RDS Serverless → EFS
- 주요 문제: 과도한 공개 네트워크 허용, IAM 정책 오타, 리소스 누락, 시크릿 관리 미비

## 2️⃣ 파싱·코드 품질

| 항목 | 현황 | 심각도 |
|------|------|--------|
| 코드 포맷 | 들여쓰기·괄호·인용부호 불일관 → terraform fmt 필요 | INFO |
| 문법 오류 | logConfiguration 괄호 누락, mountPoints 불완전, aws_lb_target_group.app 미정의 | CRITICAL |
| 변수/파라미터 | var.db_username, var.db_password를 SSM에 전달하지만 출처 불명 | WARNING |

## 3️⃣ 보안 이슈

| 체크 항목 | 문제점 | 심각도 |
|----------|--------|--------|
| 시크릿 하드코딩 | var.db_password가 SSM에 그대로 전달 → state 파일 유출 위험 | CRITICAL |
| 공개 CIDR 허용 | ALB SG, ECS SG 모두 0.0.0.0/0으로 포트 개방 | CRITICAL |
| IAM 역할 정책 | policy_arn에 "AmezonECSTash" 오타, 실제는 AmazonECSTaskExecutionRole | CRITICAL |
| RDS 마스터 비밀번호 | master_password = var.db_password 직접 전달 → Secrets Manager 권장 | CRITICAL |
| 보안 그룹 egress | 모든 SG egress 0.0.0.0/0 허용 | WARNING |

## 4️⃣ 베스트 프랙티스 위반

| 항목 | 위반 내용 | 심각도 |
|------|-----------|--------|
| ALB 정의 누락 | aws_ecs_service가 aws_lb_target_group.app을 참조하지만 ALB/TG 미정의 | CRITICAL |
| EFS 마운트 포인트 | mountPoints 정의됐지만 containerPath·sourceVolume 누락 | CRITICAL |
| 태그 관리 | 일부 리소스(NAT GW, EIP, ALB)에 태그 누락 | WARNING |
| 상태 파일 관리 | 로컬 상태 파일 사용 가정, Remote Backend 미설정 | INFO |

## 5️⃣ 비용 최적화 포인트

| 항목 | 현재 설정 | 개선 제안 |
|------|-----------|-----------|
| NAT Gateway | 1개 + EIP → 월 $30-$40 | VPC Endpoint 사용 → $0-$1/월 |
| Fargate | CPU 512 / Memory 1024 | 워크로드 테스트 후 256/512 다운스케일 가능 |
| Aurora Serverless | min=1, max=4 ACU | max_capacity를 2-3으로 조정 검토 |

## 6️⃣ 안정성·고가용성

| 체크 항목 | 현황 | 평가 |
|-----------|------|------|
| 멀티 AZ | Public/Private Subnet 각 2개 | ✅ |
| RDS Serverless | deletion_protection=true, backup 7일 | ✅ |
| EFS | 2개 Mount Target (각 AZ) | ✅ |
| ECS 서비스 | desired_count=2, circuit_breaker 활성화 | ✅ |
| Auto Scaling | CPU 70% 타깃 트래킹 | ✅ |
| 모니터링 | CloudWatch Logs + CPU>85% 알람 | ✅ |

## 7️⃣ 상세 Suggestion 리스트 (15개 항목)
| 번호 | 심각도 | 내용 |
|------|--------|------|
| 1 | CRITICAL | ALB + Target Group 정의 (HTTPS 443) |
| 2 | CRITICAL | Task Execution / Task Role IAM (EFS, SSM, ECR, RDS) |
| 3 | CRITICAL | Security Group CIDR 제한 |
| 4 | CRITICAL | Secrets Manager 사용 (DB 비밀번호) |
| 5 | CRITICAL | EFS 마운트 포인트 정의 |
| 6 | WARNING | NAT Gateway → VPC Endpoint 전환 |
| 7 | WARNING | 헬스체크 성공 코드 수정 |
| 8 | WARNING | 태깅 일관성 |
| 9 | INFO | RDS Subnet Group AZ 지정 |
| 10 | INFO | Remote Backend (S3 + DynamoDB) 도입 |
| ... | ... | (이하 5개 추가 항목) |

## 8️⃣ 최종 권고
1. 문법·포맷 정리 → terraform fmt + validate
2. 보안 강화 – 공개 CIDR 제한, Secrets Manager, IAM 최소 권한
3. 누락 리소스 보완 – ALB, Target Group, EFS 마운트 포인트
4. 비용 최적화 – NAT GW → VPC Endpoint, Fargate 사이즈 다운
5. 운영 – Remote Backend, State 파일 암호화, CI/CD 파이프라인 연동
```

이 사례는 `analyze` 명령으로 3단계 파이프라인(분류 → 파싱 → 추출)을 한 번에 실행한 결과입니다. 사례 2의 `parse` 단독 실행과 비교하면 분석 깊이가 크게 달라집니다.

**파이프라인 동작 관찰:**

- **1단계 분류 실패**: `classify_document`가 404 에러를 반환했습니다. v2 API 엔드포인트에서 `document-classify` 모델의 경로가 일치하지 않는 문제로 보입니다.
- **2단계 파싱 성공**: `parse_document`가 6페이지를 성공적으로 처리하여 전체 Terraform 코드를 텍스트로 추출했습니다.
- **3단계 추출 건너뜀**: 1단계 분류가 실패하여 `doc_type`이 `unknown`이 되었고, `EXTRACTION_SCHEMAS`에 해당 키가 없어 정보 추출이 건너뛰어졌습니다.
- **LLM 보완**: 3단계 중 파싱만 성공했지만, LLM이 파싱된 텍스트를 직접 분석하여 8개 섹션의 종합 분석을 완성했습니다.

**LLM의 인프라 분석 정확도:**

`analyze` 결과에서 LLM이 실제 코드의 설정값을 정확히 참조하여 판단한 항목들입니다:

| LLM 발견사항 | 실제 코드 | 판정 |
|---|---|---|
| ALB SG에 `0.0.0.0/0`으로 22, 80 포트 개방 (CRITICAL) | `cidr_blocks = ["0.0.0.0/0"]` ingress 22, 80 | 정확 |
| `policy_arn`에 `AmezonECSTash` 오타 (CRITICAL) | `"arn:aws:iam::aws:policy/AmazonECSClusterPolicy"` | 정확 (OCR 노이즈까지 감지) |
| Aurora `deletion_protection = true` 설정 확인 (✅) | `deletion_protection = true` | 정확 |
| EFS `encrypted = true` 확인 (✅) | `encrypted = true` | 정확 |
| `backup_retention_period = 7` 확인 (✅) | `backup_retention_period = 7` | 정확 |
| `desired_count = 2` + `circuit_breaker` 활성화 (✅) | `desired_count = 2`, `deployment_circuit_breaker { enable = true }` | 정확 |
| `aws_lb_target_group.app` 참조하지만 ALB 미정의 (CRITICAL) | `target_group_arn = aws_lb_target_group.app.arn` (정의 없음) | 정확 |
| NAT Gateway 1개만 사용, 멀티 AZ 불완전 | `subnet_id = aws_subnet.public[0].id` | 정확 |
| `mountPoints` 정의 불완전 (CRITICAL) | `sourceVolume`, `containerPath` 중복 정의 | 정확 |

LLM은 OCR 노이즈가 포함된 텍스트에서도 **보안 위험(CRITICAL)과 정상 설정(✅)을 구분하여** 판단했습니다. 특히 `deletion_protection`, `encrypted`, `backup_retention_period` 같은 방어적 설정을 ✅로 평가하면서도, 같은 코드 내의 `0.0.0.0/0` 개방, IAM 오타, 리소스 미정의는 CRITICAL로 정확히 분류한 점이 주목할 만합니다.

**사례 2(parse)와 사례 3(analyze)의 비교:**

| 비교 항목 | 사례 2: `parse` | 사례 3: `analyze` |
|---|---|---|
| 도구 호출 | `parse_document` 1회 | `analyze_iac_document` (내부: classify + parse + extract) + `parse_document` |
| 분석 섹션 수 | 요약 테이블 1개 + 개선사항 6개 | 8개 섹션 (요약, 코드 품질, 보안, BP, 비용, 안정성, Suggestion, 최종 권고) |
| 보안 이슈 식별 | "대부분 0.0.0.0/0으로 열려 있어 보안 강화 필요" (1줄 요약) | CRITICAL 5건, WARNING 3건으로 구체적 분류 + 개선 방안 |
| 비용 분석 | "Fargate cpu=512/mem=1024 적정성 확인" (언급) | NAT GW 월 비용, Fargate 다운스케일, Aurora ACU 조정 등 구체적 수치 |
| 안정성 평가 | 없음 | 8개 항목별 ✅ 체크리스트 |
| 비용 | $0.067 | $0.127 |

`analyze`는 `parse`의 약 2배 비용이 들지만, 분석 깊이는 단순 요약 → 8개 섹션 종합 리포트로 크게 향상됩니다. 특히 보안 이슈의 경우, `parse`에서는 "보안 강화 필요"라는 1줄 요약이었던 것이 `analyze`에서는 5건의 CRITICAL + 3건의 WARNING으로 구체화되고, 각각에 대한 개선 방안까지 제시됩니다.

### 사례 4: 자연어 후속 질문 — 분석 결과 위에서의 대화형 심층 분석

사례 3의 `analyze` 결과를 받은 직후, 자연어로 후속 질문을 던진 사례입니다.

```bash
> 여기서 보안그룹 규칙 중 가장 위험한 건 뭐야?

📈 세션 누적: 6회 호출 | 총 42,293 토큰 | 12 페이지 | 총 비용: $0.130429

가장 위험한 보안그룹 규칙
> aws_security_group.alb – 인바운드(Ingress) 규칙

ingress {
  from_port = 443
  to_port   = 443
  protocol  = "tcp"
  cidr_blocks = ["0.0.0.0/0"]   # → 전 세계 어디서든 HTTPS 접속 가능
}
ingress {
  from_port = 80
  to_port   = 80
  protocol  = "tcp"
  cidr_blocks = ["0.0.0.0/0"]   # → 전 세계 어디서든 HTTP 접속 가능
}

### 왜 가장 위험한가?
| 위험 요소 | 설명 |
|-----------|------|
| 전 세계 공개 | 0.0.0.0/0은 모든 IPv4 주소. ALB가 외부에 노출되면 누구든 443/80으로 요청 가능. 특히 80은 비암호화 트래픽으로 MITM 공격에 취약. |
| 보호 레이어 부재 | WAF, CDN, IP Allow-list 등 추가 방어 메커니즘이 없음. |
| 시크릿·데이터 유출 위험 | ALB 뒤 ECS Fargate가 DB 비밀번호(SSM), EFS 마운트 등 민감 정보를 다룸. 공격자가 ALB로 접근하면 전체 서비스 침해 위험. |
| 비용·리소스 남용 | 악의적 트래픽 급증 시 ALB 요금 + Fargate 비용 폭등 가능. |

### 비교 – 다른 보안그룹 규칙
| SG | 주요 규칙 | 위험도 |
|----|-----------|--------|
| aws_security_group.ecs | 인바운드 8080 → ALB SG만 허용. egress → 0.0.0.0/0 | 인바운드 제한은 양호. egress가 전 세계 개방. |
| aws_security_group.db | 인바운드 3306 → ECS SG만 허용. egress → 0.0.0.0/0 | 핵심 접근 제한은 양호. egress 개방. |
| aws_security_group.efs | 인바운드 2049 → ECS SG만 허용. egress → 0.0.0.0/0 | 직접 공격 위험 낮음. egress 개방. |

> 결론: 인바운드가 전 세계 공개인 aws_security_group.alb의 443/80 포트가 가장 위험합니다.
> 다른 SG들의 egress 0.0.0.0/0도 개선 필요하지만, 첫 번째 방어선(인바운드)의 과도한 공개가 최대 위협.

## 즉시 적용 가능한 개선 방안 (10개 항목)
| # | 조치 | 기대 효과 |
|---|------|-----------|
| 1 | ALB WAF 적용 | SQL Injection, XSS 차단, 요청 속도 제한 |
| 2 | 인바운드 CIDR 제한 (IP Allow-list) | 공격 표면 감소 |
| 3 | HTTPS만 허용 (80 → 리다이렉트) | 비암호화 트래픽 차단 |
| 4 | TLS 인증서 적용 (ACM) | 암호화 보장, 자동 갱신 |
| 5 | Egress 제한 (VPC CIDR) | 무분별한 외부 연결 차단 |
| 6 | 보안그룹 태깅·명명 규칙 통일 | 가시성·운영 효율 향상 |
| 7 | terraform fmt·validate | 코드 품질 향상 |
| 8 | Remote Backend 도입 (S3+DynamoDB) | 상태 파일 암호화·버전 관리 |
| 9 | NAT Gateway → VPC Endpoint | 비용 제거, egress 내부 제한 |
| 10 | Secrets Manager 전환 | DB 비밀번호 하드코딩 방지 |

### 한줄 요약
> 가장 위험한 규칙은 ALB SG의 0.0.0.0/0 인바운드 443/80 포트
> — 즉시 WAF 적용·IP 제한·HTTPS 전용으로 전환하고, egress도 최소 범위로 축소.
```

이 사례가 `iac_doc_intel`의 핵심 활용 패턴을 보여줍니다. `classify`, `parse`, `analyze`는 도구 호출이지만, **자연어 후속 질문은 도구 없이 LLM의 대화 맥락만으로 동작**합니다.

이 사례에서 주목할 점:

- **도구 호출 없이 응답 생성**: "보안그룹 규칙 중 가장 위험한 건 뭐야?"라는 질문에 대해 추가 도구 호출이 발생하지 않았습니다. `📈 세션 누적: 6회 호출`로 사례 3의 5회에서 1회만 증가(Chat API 1회)했고, 페이지 수는 12로 동일합니다. 즉, 이미 파싱된 텍스트가 대화 히스토리(`self.messages`)에 남아있으므로 LLM이 이를 참조하여 바로 답변한 것입니다.
- **4개 보안그룹 간 위험도 비교**: 단순히 "ALB가 위험하다"고만 하지 않고, 4개 보안그룹(ALB, ECS, DB, EFS)의 인바운드/egress 규칙을 비교 테이블로 정리한 뒤, "인바운드가 전 세계 공개인 ALB가 가장 위험하고, 다른 SG들은 egress만 개방"이라는 구조적 판단을 내렸습니다.
- **"왜 위험한가"의 논리적 전개**: 전 세계 공개 → 보호 레이어 부재 → 시크릿 유출 위험 → 비용 남용으로 이어지는 4단계 위험 분석이 단순 나열이 아니라 공격 시나리오 기반입니다. 특히 "ALB 뒤 ECS Fargate가 SSM에 DB 비밀번호를 저장"한다는 점까지 이전 분석 맥락을 정확히 참조했습니다.
- **즉시 적용 가능한 Terraform 코드 수준 개선안**: 추상적인 권고가 아니라 `aws_wafv2_web_acl`, `cidr_blocks = ["203.0.113.0/24"]`, `aws_lb_listener` 리다이렉트 등 구체적인 리소스명과 설정값을 제시했습니다.

이 사례는 `iac_doc_intel`이 "분류/파싱/분석" 도구에 그치지 않고, **분석 결과 위에서 자연어 대화로 심층 탐색을 이어가는 대화형 인프라 컨설턴트**로 동작한다는 점을 보여줍니다. `k8s_assistant`의 사례 3 → 4(분석 후 개선 요청)와 유사한 패턴이지만, 여기서는 YAML 생성이 아니라 **보안 위험 분석의 심화**라는 점에서 차이가 있습니다.

### 사례 5: 자연어 후속 질문 (2) — 비용 추정 및 시나리오 시뮬레이션

사례 4에 이어, 같은 세션에서 비용 관점의 후속 질문을 던진 사례입니다.

```bash
> 이 구성의 월 예상 비용은 얼마나 될까?

📈 세션 누적: 8회 호출 | 총 103,062 토큰 | 12 페이지 | 총 비용: $0.149863

📊 이 구성의 월 예상 비용 (ap-northeast-2 서울 기준)

| 구분 | 주요 비용 항목 | 가정 | 예상 월 비용 |
|------|----------------|------|-------------|
| NAT Gateway | 시간당 + 데이터 처리 | 1 NAT GW, 0.5 GB/day | $39.5 |
| ALB | LCU + 데이터 전송 + 요청 수 | 2 LCU, 2k RPS, 5 GB/day | $49.0 |
| Aurora Serverless | ACU + 백업 스토리지 | 평균 2 ACU, 백업 10 GB | $71.6 |
| EFS | 파일시스템 + Mount Target | 250 GB GP2, IA 30일 후 전환 | $70.0 |
| Fargate | CPU + Memory + 데이터 전송 | 2 tasks, 0.5 vCPU + 1 GiB | $36.0 |
| WAF | 웹 ACL 기본 요금 | 1 ACL | $5.0 |
| CloudWatch Log | 로그 저장 | 0.5 GB/month | $0.25 |
| SSM / IAM / EIP | - | - | $0 |

총 월 예상 비용:
ALB          $49.0
NAT GW       $39.5
Aurora       $70.0
EFS          $70.0
Fargate      $36.0
WAF          $5.0
기타         $3.32
-------------------------------------------------
≈ $272 (272 USD) per month

## 비용 최적화 체크리스트 (우선순위)
| 번호 | 항목 | 현재 비용 | 최적화 방안 | 예상 절감 |
|------|------|----------|------------|-----------|
| 1 | NAT Gateway | $39.5 | VPC Endpoint 사용 → NAT GW 삭제 | $30-$35 |
| 2 | Fargate | $36 | Spot 활용 + cpu=256/mem=512 다운사이징 | 20-30% |
| 3 | Aurora | $70 | Auto-Pause 유지 + 백업 보관기간 축소 | 10-15% |
| 4 | EFS | $70 | Lifecycle AFTER_15_DAYS로 IA 전환 앞당김 | 10-20% |
| 5 | ALB | $49 | NLB 교체 또는 CloudFront 배치 | $5-$10 |

## 시나리오별 비용 시뮬레이션
| 시나리오 | 변경 내용 | 총 비용 |
|----------|----------|--------|
| A – 기본 | 위 가정 그대로 | $272 |
| B – NAT GW 제거 | VPC Endpoint 전환 | ≈ $233 (≈ $39 절감) |
| C – ALB → NLB | 데이터 전송 비용 감소 | ≈ $248 |
| D – Fargate Spot | 30% 할인 적용 | ≈ $237 |
| E – EFS IA 15일 | IA 전환 시점 앞당김 | ≈ $247 |
| F – 전체 최적화 | B+C+D+E 모두 적용 | ≈ $166 |

> 전체 최적화 적용 시 월 비용을 30-40% ($272 → $166) 절감 가능.
```

이 사례에서 주목할 점:

- **코드에서 비용을 추정하는 능력**: Terraform 코드에는 `cpu = "512"`, `memory = "1024"`, `desired_count = 2`, `min_capacity = 1`, `max_capacity = 4` 같은 설정값만 있을 뿐, 비용 정보는 어디에도 없습니다. LLM이 이 설정값에 AWS 서울 리전의 단가(`$0.04048/vCPU/hr`, `$0.00444/GB/hr`, `$0.045/NAT GW/hr` 등)를 매핑하여 리소스별 월 비용을 산출했습니다. 이는 LLM의 학습 데이터에 AWS Pricing 정보가 포함되어 있기 때문에 가능한 것입니다.
- **14개 리소스를 빠짐없이 비용 분류**: VPC/Subnet/IGW(무료)부터 NAT Gateway, ALB, Aurora, EFS, Fargate, WAF, CloudWatch, SSM, Terraform Remote State까지 코드에 정의된(또는 암시된) 모든 리소스를 비용 항목으로 분류하고, 무료인 항목도 `$0`으로 명시하여 빠진 것이 없음을 보여줍니다.
- **6개 시나리오 비교 시뮬레이션**: 단일 추정치에 그치지 않고, "NAT GW만 제거하면?", "ALB를 NLB로 바꾸면?", "Fargate Spot을 쓰면?", "전부 적용하면?"까지 6개 시나리오를 테이블로 비교했습니다. 이는 비용 최적화 의사결정에 직접 활용할 수 있는 수준입니다.
- **대화 히스토리 누적의 비용 영향**: 세션 누적 토큰이 103,062로 크게 늘어났습니다. 사례 3(25,208) → 사례 4(42,293) → 사례 5(103,062)로 이전 대화 맥락이 계속 누적되면서 Chat API 입력 토큰이 증가한 것입니다. 하지만 추가 도구 호출은 2회(Chat API만)이고 페이지 수는 12로 동일하므로, 비용 증가($0.127 → $0.150)는 토큰 증가에 따른 것입니다.

**사례 3 → 4 → 5의 대화 흐름:**

```
사례 3: analyze (종합 분석)
    → 8개 섹션 리포트, CRITICAL 5건 + WARNING 3건 식별
        ↓
사례 4: "보안그룹 중 가장 위험한 건?" (보안 심층 분석)
    → ALB SG 0.0.0.0/0 식별, 4개 SG 비교, 10개 개선 방안
        ↓
사례 5: "월 예상 비용은?" (비용 분석)
    → 14개 리소스별 비용 산출, 6개 시나리오 시뮬레이션
```

이 흐름은 하나의 `analyze` 결과 위에서 관점을 바꿔가며(보안 → 비용) 심층 탐색을 이어가는 패턴입니다. 매번 새로 파싱하거나 도구를 호출할 필요 없이, 대화 히스토리에 남아있는 파싱 결과를 LLM이 재활용합니다.

## 관찰 사항

### 도구 실패 시 LLM의 자율적 보완

사례 1에서 3개 도구 중 2개가 API 오류로 실패했지만, 최종 응답 품질에는 큰 영향이 없었습니다. 이는 에이전트의 구조적 강점입니다.

```
classify_document  → API 400 에러 (실패)
parse_document     → 성공 (텍스트 추출)
extract_information → API 400 에러 (실패)
                            ↓
        LLM이 파싱된 텍스트를 직접 읽고
        분류 + 요약 + 보안 분석 수행
                            ↓
        최종 응답: 정확한 분류, 상세 요약, 6항목 체크리스트
```

이 패턴은 Function Calling 에이전트의 **graceful degradation** 특성을 보여줍니다. 도구는 LLM에게 구조화된 데이터를 제공하는 보조 수단이지만, 도구가 실패하더라도 원본 텍스트만 있으면 LLM이 직접 분석을 수행할 수 있습니다.

다만 이것은 양날의 검이기도 합니다. 도구가 실패했다는 사실이 최종 응답에 명시적으로 드러나지 않으므로, 사용자는 Document AI API가 정상 동작했는지 아닌지를 응답만으로는 판단하기 어렵습니다. `--usage` 플래그가 켜져 있으면 콘솔의 도구 호출 로그에서 오류를 확인할 수 있지만, 이를 놓치면 "모든 API가 잘 작동하고 있다"고 오해할 수 있습니다.

### classify 요청에 대한 도구 체이닝

사례 1에서 사용자는 `classify`만 요청했지만, LLM은 자율적으로 3개 도구를 연속 호출했습니다.

```
사용자: classify terraform_sample.pdf
  ↓
LLM 판단: "분류하려면 먼저 문서 내용을 파악해야 한다"
  ↓
1. classify_document (실패)
2. parse_document (성공)
3. extract_information (실패, 2회 시도)
  ↓
LLM: 파싱된 텍스트로 분류 + 요약 + 분석까지 수행
```

이것은 시스템 프롬프트의 "파일 경로가 주어지면 먼저 classify_document로 문서 유형을 파악하세요" 규칙에 따른 동작입니다. LLM이 단순히 분류 결과만 반환하지 않고, 분류 과정에서 얻은 정보를 활용해 사용자에게 더 유용한 종합 분석까지 제공한 것입니다.

### 비용 구조

실제 세션에서 관찰된 비용:

| 명령 | API 호출 | 토큰 | 페이지 | 비용 |
|---|---|---|---|---|
| `classify terraform_sample.pdf` | Chat 7회 | 26,038 | 2 | $0.027 |
| `parse terraform_fargate_sample.pdf` | Chat 3회 + Parse 1회 | 23,610 | 6 | $0.067 |
| `analyze terraform_fargate_sample.pdf` | Chat 5회 + Parse 2회 | 25,208 | 12 | $0.127 |
| `여기서 보안그룹 규칙 중 가장 위험한 건 뭐야?` | Chat 1회 (도구 호출 없음) | 17,085 | 0 | $0.004 |
| `이 구성의 월 예상 비용은 얼마나 될까?` | Chat 2회 (도구 호출 없음) | 60,769 | 0 | $0.019 |

- `analyze`는 내부적으로 파이프라인(classify → parse → extract)을 실행한 뒤, LLM이 추가로 `parse_document`를 한 번 더 호출하여 총 12페이지를 처리했습니다. 같은 파일의 `parse` 단독($0.067)과 비교하면 약 2배 비용이지만, 분석 깊이는 1줄 요약 → 8개 섹션 종합 리포트로 크게 향상됩니다.
- 자연어 후속 질문(사례 4)은 도구 호출 없이 Chat API 1회만 사용하므로 비용이 $0.004로 매우 낮습니다. 분석 결과가 대화 히스토리에 남아있으면, 추가 비용 거의 없이 심층 탐색을 이어갈 수 있습니다.
- `classify` 명령에서 도구가 여러 번 호출/재시도되면서 Chat API 호출 횟수가 7회까지 늘어났습니다. API 오류로 인한 재시도가 비용을 높이는 요인이 됩니다.

## 활용 방향

- **레거시 인프라 문서 파악**: PDF로만 남아있는 Terraform/Ansible 문서를 파싱하여 현재 인프라 구성을 빠르게 파악할 수 있습니다. OCR 노이즈가 있어도 LLM이 보정하므로, "대략적인 구성 파악" 수준에서는 충분히 실용적입니다.
- **보안 사전 점검**: `analyze` 명령으로 IaC 파일의 보안 이슈(0.0.0.0/0, 시크릿 하드코딩 등)를 배포 전에 확인할 수 있습니다.
- **자연어 후속 질문**: 분석 결과를 받은 뒤 "보안그룹 규칙을 어떻게 수정하면 돼?", "이 구성의 월 예상 비용은?" 같은 후속 질문으로 대화를 이어갈 수 있습니다. 파싱/분석은 입구이고, 그 위에서의 자연어 대화가 실제 활용 포인트입니다.
- **k8s_assistant / commit_guardian과 연계**: 생성된 K8s YAML을 `iac_doc_intel`로 보안 분석하거나, Terraform 변경 커밋을 `commit_guardian`으로 리뷰한 뒤 `iac_doc_intel`로 파일 전체를 심층 분석하는 워크플로우가 가능합니다.

## 개선 가능한 점

- **Document Classify API 호환성**: 사례 1의 400 에러는 코드의 API base URL이 v1이었던 설정 문제로, v2(`https://api.upstage.ai/v2`)로 수정하여 해결했습니다. 다만 v2 전환 후에도 `document-classify` 모델은 404를 반환하고 있어(사례 3), 현재 지원되는 모델명이나 엔드포인트 경로에 대한 확인이 필요합니다. 분류 기능이 필요하다면 공식 문서에서 현재 사용 가능한 분류 방법을 확인하거나, `parse_document`로 텍스트를 추출한 뒤 Chat API에서 LLM이 직접 분류하는 방식으로 대체할 수 있습니다(실제로 현재 에이전트가 이 fallback을 자동으로 수행하고 있습니다).
- **OCR 후처리**: PDF 파싱 결과에 반복적인 OCR 노이즈 패턴(`.` → `·`, `${}` → `$()` 등)이 있으므로, 정규식 기반 후처리를 추가하면 LLM에 전달되는 텍스트 품질이 향상됩니다.
- **도구 실패 명시**: 현재는 도구 API 오류가 발생해도 LLM이 자연스럽게 보완하여 최종 응답에 실패 사실이 잘 드러나지 않습니다. 도구 실패 시 응답에 명시적인 경고를 포함하면 사용자가 API 상태를 인지할 수 있습니다.
