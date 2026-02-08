# 플랫폼 엔지니어링 활용 시나리오

5개 도구를 플랫폼 엔지니어링 실무 관점에서 어떻게 활용할 수 있는지 정리한 문서입니다.
개별 도구의 사용 사례는 각 프로젝트 디렉토리의 `EXAMPLES.md`를 참고하세요.

## 도구 요약

| 도구 | 역할 | 핵심 Upstage API |
|---|---|---|
| `iac_doc_intel` | IaC 문서 분류/파싱/보안 분석 | Document AI + Chat |
| `k8s_assistant` | K8s 매니페스트 생성/검증 | Chat + Function Calling |
| `commit_guardian` | 코드 변경사항 리뷰 | Chat + Groundedness Check |
| `platform_kb` | 인프라 지식 검색 (런북/아키텍처, 예정) | Embedding + Chat |
| `mlops_dashboard` | ML 파이프라인/메트릭 조회 | Chat + Function Calling |

---

## 시나리오 1: 새로운 서비스 배포 (생성 → 검증 → 커밋)

새로운 마이크로서비스를 K8s에 배포할 때의 워크플로우입니다.

### 사용 도구: `k8s_assistant` → `iac_doc_intel` → `commit_guardian`

**Step 1 — K8s 매니페스트 생성 및 1차 검증**

```bash
python3 k8s_assistant/main.py

> Redis StatefulSet + Service + PVC 만들어줘. 프로덕션 환경 기준으로.
# → 리소스 제한, securityContext, probe 등이 포함된 YAML 생성

> 보안 관점에서 검증해줘
# → SEC001~NET001 규칙 기반 검증 + LLM 보정
# → 생성된 YAML을 redis.yaml로 저장
```

**Step 2 — IaC 관점 심층 분석**

```bash
python3 iac_doc_intel/main.py

> 이 파일 분석해줘 /path/to/redis.yaml
# → Document AI가 구조화 데이터 추출 (kind, images, replicas, ports 등)

> 리소스 제한이 Redis 워크로드에 적절한지 봐줘
# → memory limits vs Redis maxmemory 설정 정합성 분석

> 이 구성에서 단일 장애 지점은 없어?
# → replicas, PVC 바인딩, anti-affinity 관점 분석
```

**Step 3 — 커밋 및 코드 리뷰**

```bash
python3 commit_guardian/main.py /path/to/project

> staged
# → YAML 변경사항 리뷰 + Groundedness Check로 환각 필터링
# → "CRITICAL: PDB가 정의되지 않음" 등의 근거 기반 피드백
```

### 이 시나리오의 가치

- K8s 전문가가 아니어도 프로덕션급 매니페스트를 작성할 수 있음
- **2중 검증**: k8s_assistant(규칙 기반) + iac_doc_intel(LLM 분석)으로 누락 방지
- 커밋 전 최종 리뷰까지 자동화

---

## 시나리오 2: IaC PR 리뷰 자동화

팀원이 Terraform PR을 올렸는데, 인프라 전문 리뷰어가 부족한 경우입니다.

### 사용 도구: `commit_guardian` → `iac_doc_intel`

**Step 1 — diff 기반 변경사항 리뷰**

```bash
python3 commit_guardian/main.py /path/to/infra-repo

> commit abc1234
# → Terraform 파일 변경사항에 대한 코드 리뷰
# → "WARNING: 보안그룹 인바운드 규칙이 변경됨" 등

> 보안 관점에서만 더 자세히 봐줘
# → 보안 집중 리뷰 (실제 diff에 근거한 발견사항만 제시)
```

**Step 2 — 변경된 파일 심층 분석**

```bash
python3 iac_doc_intel/main.py

> 이 파일 분석해줘 /path/to/infra-repo/modules/ecs/main.tf
# → 파일 전체에 대한 보안/베스트 프랙티스 분석
# → [CRITICAL] SSH 포트가 0.0.0.0/0으로 열려있음
# → [WARNING] 태그가 일부 리소스에 누락됨
# → [SUGGESTION] t3.medium → t3.small 검토 (비용 최적화)
```

### 이 시나리오의 가치

- commit_guardian: **변경된 부분**에 집중한 리뷰 (diff 기반)
- iac_doc_intel: **파일 전체**에 대한 인프라 관점 분석
- 두 도구의 관점이 다르므로 상호 보완적

---

## 시나리오 3: 레거시 인프라 문서 현행화 (platform_kb 추가 시)

인수인계받은 프로젝트에 PDF로만 남아있는 인프라 문서를 구조화하는 경우입니다.

### 사용 도구: `iac_doc_intel` → `platform_kb`

**Step 1 — PDF 문서에서 정보 추출**

```bash
python3 iac_doc_intel/main.py

> classify /docs/legacy-infra.pdf
# → "terraform" 유형으로 분류

> analyze /docs/legacy-infra.pdf
# → 3단계 파이프라인: 분류 → 파싱(OCR) → 구조화 추출
# → provider: aws, region: ap-northeast-2
# → resources: [aws_vpc, aws_subnet x3, aws_rds_cluster, ...]
# → variables: [db_password (sensitive), environment, ...]

> 이 문서에서 파악된 인프라 구성을 마크다운으로 정리해줘
# → 정리된 내용을 infra-summary.md로 저장
```

**Step 2 — 지식 베이스에 등록 및 검색**

```bash
python3 platform_kb/main.py

> add /docs/infra-summary.md
# → 청킹 → 임베딩 → 벡터 스토어 저장

> 우리 프로덕션 VPC의 CIDR 범위가 뭐야?
# → RAG 검색으로 "10.0.0.0/16" 등 정확한 답변

> DB 접근은 어떤 보안그룹으로 제어되고 있어?
# → Groundedness Check로 근거 기반 답변 보장
```

### 이 시나리오의 가치

- "이전 담당자가 퇴사해서 아무도 모르는" 인프라 정보를 검색 가능한 지식으로 변환
- PDF → 구조화 데이터 → 벡터 임베딩의 파이프라인으로 레거시 문서를 활용 가능하게 만듦

---

## 시나리오 4: 장애 대응 시 인프라 빠른 파악 (platform_kb 추가 시)

새벽 온콜 중 장애가 발생하여 해당 서비스의 구성을 빠르게 파악해야 하는 경우입니다.

### 사용 도구: `platform_kb` → `iac_doc_intel` → `mlops_dashboard`

**Step 1 — 런북에서 초기 대응 절차 확인**

```bash
python3 platform_kb/main.py

> Pod CrashLoopBackOff 대응 절차 알려줘
# → 런북 검색: 진단 단계, 일반적인 원인, 에스컬레이션 기준

> 이전에 비슷한 DB 연결 장애 사례 있었어?
# → 포스트모템 검색: 원인, 해결 방법, 재발 방지 조치
```

**Step 2 — 해당 서비스 인프라 구성 확인**

```bash
python3 iac_doc_intel/main.py

> /infra/services/payment/main.tf 분석해줘
# → 현재 서비스의 리소스 구성, 오토스케일링 설정 파악

> 이 서비스의 DB 연결 설정이 충분해 보여?
# → Aurora 커넥션 수, 타임아웃 설정 등 분석
```

**Step 3 — (ML 서비스 장애라면) 최근 배포 확인**

```bash
python3 mlops_dashboard/main.py

> 최근 24시간 내 배포된 모델 있어?
# → 장애 시점과 배포 시점 상관관계 확인

> payment-fraud 모델의 최근 메트릭 변화 추이는?
# → 성능 저하 여부 확인
```

### 이 시나리오의 가치

- 코드를 직접 읽지 않고도 인프라 구성을 파악하여 MTTR 단축
- 런북/포스트모템 검색으로 이전 경험을 빠르게 참조

---

## 시나리오 5: 인프라 마이그레이션 사전 분석

기존 EC2 기반 구성을 ECS Fargate로 마이그레이션하려는 경우입니다.

### 사용 도구: `iac_doc_intel` (단독 활용)

```bash
python3 iac_doc_intel/main.py

# ---- 현행 분석 ----
> /infra/ec2/main.tf 분석해줘
# → 현재 인스턴스 타입, 보안그룹 규칙, 네트워크 구성 파악

> 현재 보안 관점에서 개선이 필요한 부분은?
# → [CRITICAL] SSH 0.0.0.0/0, [WARNING] 태그 누락 등

# ---- 레퍼런스 확인 ----
> analyze terraform_fargate_sample.pdf
# → Fargate 구성 예시의 구조 분석 (VPC, ECS, Aurora, EFS, Auto Scaling)

# ---- 마이그레이션 갭 분석 ----
> 현재 EC2 구성에서 Fargate로 전환할 때 추가해야 할 리소스는?
# → ECS 클러스터, 태스크 정의, ALB, 서비스 디스커버리 등

> Fargate 전환 시 보안 관점에서 달라지는 점은?
# → EC2 SSH 접근 제거, 태스크 IAM 역할 분리, 네트워크 모드 변경 등
```

### 이 시나리오의 가치

- 마이그레이션 전후 인프라를 분석하여 누락 사항 사전 파악
- 샘플 PDF를 레퍼런스 아키텍처로 활용

---

## 시나리오 6: ML 모델 릴리스 의사결정

모델 성능 메트릭을 비교하고, 배포 결정을 내리는 경우입니다.

### 사용 도구: `mlops_dashboard` → `commit_guardian`

**Step 1 — 모델 메트릭 비교**

```bash
python3 mlops_dashboard/main.py

> wafer-defect v2.0과 v2.1의 메트릭 비교해줘
# → mAP50, F1, precision, recall, inference_ms 비교

> 오탐이 적은 모델 추천해줘
# → precision/recall 트레이드오프 기반 추천

> production 스테이지에 배포된 모델 목록 보여줘
# → 현재 운영 중인 모델 현황 확인
```

**Step 2 — 모델 코드 변경사항 리뷰**

```bash
python3 commit_guardian/main.py /path/to/ml-project

> commit def5678
# → 모델 학습 코드 변경사항 리뷰
# → "INFO: 하이퍼파라미터 변경 - learning_rate 0.001 → 0.0005"

> 이 변경이 성능에 어떤 영향을 줄 수 있을지 분석해줘
```

### 이 시나리오의 가치

- SQL 없이 자연어로 메트릭을 비교하여 배포 의사결정
- 코드 변경과 성능 변화를 연결하여 분석

---

## 빠르게 시작하기

위 시나리오를 시작하기 위한 최소 준비:

```bash
# 1. 의존성 설치 및 API 키 설정
pip install -r requirements.txt
cp .env.example .env  # UPSTAGE_API_KEY 입력

# 2. 샘플 데이터 준비
python3 iac_doc_intel/main.py        # > generate-samples
python3 platform_kb/main.py          # > generate-samples → add 명령으로 등록 (platform_kb 추가 시)
python3 mlops_dashboard/setup_db.py  # SQLite 샘플 DB 생성

# 3. 시나리오 5부터 시작 (iac_doc_intel 단독, 즉시 체험 가능)
python3 iac_doc_intel/main.py --usage
> samples                                    # 샘플 목록 확인
> analyze terraform_fargate_sample.pdf       # 종합 분석 실행
> 이 구성에서 보안 이슈가 있어?               # 자연어 후속 질문
```
