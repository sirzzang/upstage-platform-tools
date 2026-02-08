# K8s YAML Assistant 실제 사용 사례

`k8s_assistant`의 실제 사용 사례를 정리했습니다.

## 실제 사용 사례

### 사례 1: 프로덕션 수준 YAML 생성

```bash
> nginx Deployment 만들어줘

[YAML 생성] generate_yaml 호출됨

아래는 nginx 를 프로덕션 환경에서 안전하게 운영하기 위한 Deployment 와 Service 매니페스트 예시입니다.

apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      securityContext:
        runAsNonRoot: true
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: false
        runAsUser: 101
      containers:
        - name: nginx
          image: nginx:1.25.3
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "200m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
```

"nginx Deployment 만들어줘"라는 한 줄의 요청에 대해, 시스템 프롬프트의 규칙대로 프로덕션 수준의 매니페스트를 생성했습니다.

- `replicas: 2`, `securityContext`, `resources`, `livenessProbe`/`readinessProbe`까지 모두 포함되어 있습니다.
- 요청하지 않은 Service까지 자동으로 함께 생성해주는 점도 실용적입니다.

### 사례 2: 맥락을 반영한 간결한 생성

```bash
> CKA 시험 대비를 위해 간단한 수준의 실습으로만 필요 해. nginx deployment를 생성해줘 # 띄어쓰기 오타 자동 감지

[YAML 생성] generate_yaml 호출됨

apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.25.3
          ports:
            - containerPort: 80
```

같은 "nginx deployment 생성" 요청이지만, "CKA 시험 대비", "간단한 수준의 실습"이라는 맥락을 정확히 반영했습니다.

- `securityContext`, `resources`, probe 같은 프로덕션 요소를 과감히 생략하고, `replicas: 1`로 최소 구성만 제공합니다.
- 사례 1과 비교하면 동일한 LLM이 요청 맥락에 따라 출력 수준을 조절하는 것을 확인할 수 있습니다.
- 시스템 프롬프트의 "프로덕션 품질" 규칙을 무조건 따르는 게 아니라, 사용자 의도를 우선시합니다.

### 사례 3: 실무 YAML 분석 및 개선 제안

```bash
> (멀티라인으로 YAML 입력)
---
# PostgreSQL 외부 서비스 정의
apiVersion: v1
kind: Service
metadata:
  name: postgres-external
  namespace: team-mlops
spec:
  ports:
  - name: postgres
    protocol: TCP
    port: 5432
    targetPort: 54320
---
# PostgreSQL 외부 엔드포인트 매핑
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: postgres-external
  namespace: team-mlops
  labels:
    kubernetes.io/service-name: postgres-external
addressType: IPv4
ports:
- name: postgres
  protocol: TCP
  port: 54320
endpoints:
- addresses:
  - "10.0.1.100"

[YAML 분석] analyze_yaml 호출됨
[추출된 정보]
API 버전: v1
리소스 종류: Service
이름: postgres-external
네임스페이스: team-mlops
API 버전: discovery.k8s.io/v1
리소스 종류: EndpointSlice

[설명]
- Service가 포트 5432로 노출되고, 실제 DB 포트 54320으로 라우팅
- EndpointSlice에 외부 PostgreSQL 서버 IP가 등록되어 있음
- kube-proxy가 Service → EndpointSlice → 외부 DB IP로 트래픽 전달

[개선 권장 사항]
| 항목             | 권장 설정                           | 이유                              |
|-----------------|-------------------------------------|----------------------------------|
| Service 타입     | type: ExternalName                  | DNS 기반 연결로 IP 관리 부담 제거   |
| metadata.labels | app: postgres, env: production 등   | 운영 시 식별·관리 용이              |
| selector        | {} 혹은 빈 객체                      | EndpointSlice와 명시적 연결        |
| 다중 엔드포인트   | 여러 DB 서버를 endpoints에 추가       | 고가용성/로드밸런싱                 |
```

실제 운영 중인 외부 DB 연결 매니페스트(Service + EndpointSlice)를 입력하니, 단순 구조 분석에 그치지 않고 각 리소스의 역할과 트래픽 흐름을 설명한 뒤 개선 방향까지 제시했습니다.

- `type` 필드가 명시되지 않아 기본값 ClusterIP가 적용된다는 점, `selector`를 비워야 EndpointSlice와 연결된다는 점 등 놓치기 쉬운 부분을 짚어줍니다.
- `templates.py`에 EndpointSlice 템플릿이 정의되어 있지 않고, `analyze_yaml`의 extractors에도 `addressType`, `endpoints` 같은 고유 필드가 없습니다.
- 그런데도 분석 품질에는 문제가 없었습니다. `analyze_yaml`이 원본 YAML 전문을 LLM에 넘기는 구조이기 때문에, extractors의 필드 추출은 보조 힌트일 뿐이고 실제 분석은 LLM이 원본을 직접 읽고 수행합니다.
- 이는 템플릿을 코드 생성기가 아닌 LLM 컨텍스트로 사용하는 설계의 강점입니다.

### 사례 4: 분석 결과를 바탕으로 개선된 매니페스트 생성

```bash
> 더 나은 방향으로 수정해줘

[YAML 생성] generate_yaml 호출됨
[멀티 리소스 생성] generate_multi_resource 호출됨

# 1. ExternalName Service (외부 DB를 DNS 이름으로 연결)
apiVersion: v1
kind: Service
metadata:
  name: postgres-external
  namespace: team-mlops
  labels:
    app: postgres
    tier: external
  annotations:
    description: "External PostgreSQL service via DNS name"
spec:
  type: ExternalName
  externalName: postgres.external.example.com
  ports:
    - name: postgres
      protocol: TCP
      port: 5432
---
# 2. EndpointSlice (IP fallback, 선택 사항)
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: postgres-external
  namespace: team-mlops
  labels:
    kubernetes.io/service-name: postgres-external
addressType: IPv4
ports:
  - name: postgres
    protocol: TCP
    port: 54320
endpoints:
  - addresses:
      - "10.0.1.100"
---
# 3. Client Deployment (DB 접속용 파드)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-client
  namespace: team-mlops
  labels:
    app: postgres-client
spec:
  replicas: 2
  ...
  env:
    - name: PGPASSWORD
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
  ...
---
# 4. Secret (DB 인증 정보)
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: team-mlops
type: Opaque
data:
  password: cGFzc3dvcmQ=
```

이전 대화에서 분석한 내용을 기억하고, 제안했던 개선 방향을 그대로 반영한 매니페스트를 생성했습니다.

- 원본 2개 리소스(Service + EndpointSlice)에서 4개 리소스(ExternalName Service + EndpointSlice fallback + Client Deployment + Secret)로 확장되었습니다.
- `generate_yaml`과 `generate_multi_resource`를 연속 호출하여 연관 리소스를 한번에 생성하는 Function Calling 체이닝이 잘 작동합니다.
- DB 비밀번호를 환경변수 평문이 아닌 `Secret` + `secretKeyRef`로 분리한 점, EndpointSlice를 DNS 장애 시 IP fallback 용도로 남겨둔 점 등 실무적으로 의미 있는 개선입니다.

사례 3 → 사례 4의 흐름이 이 어시스턴트의 핵심 사용 패턴입니다.

- 분석 결과 끝에 "추가로 수정이 필요하거나 다른 옵션(예: ExternalName 사용)을 적용하고 싶으시면 알려 주세요!"라는 후속 조치 유도가 붙습니다.
- 사용자가 "더 나은 방향으로 수정해줘"로 응답하면 이전 맥락을 기반으로 개선된 결과를 만들어 줍니다.
- 별도의 UI 없이 자연어로 예/아니오 의사결정을 이어갈 수 있어, 대화 자체가 점진적 리팩토링 워크플로우가 됩니다.

### 사례 5: 템플릿 미정의 리소스 검증 — 도구의 오탐을 LLM이 교정

```bash
> (PodDisruptionBudget YAML 입력)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-backend-prod-pdb
  namespace: team-mlops
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: app-backend-prod

[YAML 검증] validate_yaml 호출됨
[검증 결과]
[CRITICAL] securityContext 미설정. runAsNonRoot: true를 설정하세요.
[WARNING] allowPrivilegeEscalation: false를 설정하세요.
[CRITICAL] resources.requests/limits 미설정. OOM Kill 위험이 있습니다.
[WARNING] livenessProbe 미설정...

(LLM 응답)
## 검증 결과 (수정된 피드백)

### 1. 전체 평가
- **문제점 없음** – PodDisruptionBudget(PDB)은 운영 중단 시 최소 가용 파드 수를
  보장하는 정책 리소스이며, 현재 매니페스트는 핵심 필드만 정확히 포함하고 있습니다.
- **보안, 리소스, 헬스체크 항목**은 PDB에 적용되지 않으므로,
  검증 도구의 초기 경고는 **오탐**입니다.

### 2. 현재 매니페스트 분석
| 항목                | 설명                            | 비고 |
|--------------------|--------------------------------|------|
| apiVersion / kind  | policy/v1 → PDB                | ✅   |
| spec.minAvailable  | 최소 가용 파드 수 2              | ✅   |
| spec.selector      | matchLabels로 대상 파드 선택     | ✅   |

### 3. 개선 제안
1. labels/annotations 추가로 운영 시 식별성 향상
2. minAvailable: 2를 만족하려면 워크로드의 replicas ≥ 2 필요
3. apiVersion: policy/v1은 현재(2026년 기준) 최신이며 정상

### 4. 최종 권고
필요하시면 해당 워크로드 매니페스트도 함께 검증해 드릴 수 있습니다.
```

이 사례가 특히 흥미로운 이유는, `validate_yaml` 도구가 예상대로 오탐을 쏟아냈다는 점입니다.

- PDB에는 `securityContext`도 `resources`도 `livenessProbe`도 존재하지 않으므로, Pod 워크로드 기반의 하드코딩된 검증 규칙이 전부 CRITICAL/WARNING을 발생시켰습니다.
- 그런데 LLM이 이 도구 결과를 받아서 **"검증 도구의 초기 경고는 오탐입니다"**라고 스스로 판단하고, PDB에 맞는 진짜 검증을 직접 수행했습니다.
- `minAvailable`과 replicas의 관계, `policy/v1` 버전의 적절성, labels 추가 권장 등 도구가 제공하지 못하는 리소스별 맥락 검증을 LLM이 보완한 것입니다.

결국 이 시스템에서 **도구는 틀려도 최종 응답은 맞습니다**.

- 도구가 제공하는 데이터는 LLM의 판단 재료일 뿐이고, LLM이 해당 리소스의 특성을 이해하고 있으면 잘못된 도구 결과를 걸러냅니다.
- 이는 Function Calling 에이전트의 강점이 도구의 정확도가 아니라 **LLM의 판단력과 도구 결과의 조합**에 있다는 것을 보여주는 좋은 사례입니다.

끝에 "해당 워크로드 매니페스트도 함께 검증해 드릴 수 있습니다"라는 후속 조치 유도도 자연스럽게 붙어 있어, Deployment의 replicas가 정말 2 이상인지 이어서 확인할 수 있습니다.

### 사례 6: 후속 조치를 예/아니오로 이어가기

```bash
> (사례 3의 분석 결과 끝에)
추가로 수정이 필요하거나 다른 옵션(예: ExternalName 사용)을 적용하고 싶으시면 알려 주세요!

> 더 나은 방향으로 수정해줘

(→ 사례 4: ExternalName Service + EndpointSlice fallback + Client Deployment + Secret 생성)

> (사례 4의 생성 결과 끝에)
필요에 따라 EndpointSlice를 제거해도 무방합니다(ExternalName만 사용 시).

> EndpointSlice 빼고 ExternalName만 사용하는 버전으로 줄여줘

(→ ExternalName Service + Secret만 남긴 간소화 버전 생성)
```

이 흐름이 이 어시스턴트의 가장 인상적인 부분입니다. 매 응답 끝에 다음 선택지를 자연어로 제안하고, 사용자는 그 중 하나를 골라 응답하거나 자신의 의도를 덧붙이면 됩니다.

- "수정해 드릴까요?" → "응, 해줘" → 개선된 매니페스트 생성
- "다른 옵션도 있어요" → "그걸로 바꿔줘" → 대안 적용
- "추가 리소스가 필요할 수 있어요" → "필요 없어" → 현재 상태 유지

명시적인 "예/아니오" 버튼이 없어도, 대화 자체가 의사결정 트리처럼 작동합니다. 시스템 프롬프트에 명시적으로 지시한 동작이 아니라, LLM이 대화 맥락에서 자연스럽게 만들어내는 패턴이라는 점에서, Function Calling 에이전트가 단순한 도구 실행기를 넘어 대화형 컨설턴트처럼 동작하는 좋은 사례입니다.

### 사례 7: 레포지토리 경로 기반 매니페스트 생성 — analyze_repo 도구 없을 때

```bash
> /path/to/my-admin-backend 레포 배포에 필요한 프로덕션 레벨 매니페스트 작성

[YAML 생성] generate_yaml 호출됨 (4회 연속)

apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-admin-back           # ← 실제 바이너리명은 my-admin-backend
  ...
spec:
  containers:
  - name: my-admin-back
    image: my-admin-back:1.0.0  # ← 이미지명도 잘림
    ports:
    - containerPort: 8080       # ← 맞음 (일반적인 백엔드 포트 추정)
    livenessProbe:
      httpGet:
        path: /healthz          # ← 존재하지 않는 엔드포인트
        port: 8080
    readinessProbe:
      httpGet:
        path: /                 # ← 맞음 (실제 존재)
        port: 8080
    # 환경변수: 없음            # ← 실제로는 13개 필수
---
apiVersion: v1
kind: Service
  ...
```

레포 경로를 주고 매니페스트를 요청했지만, `analyze_repo` 같은 도구가 없으므로 **LLM이 실제 레포를 읽지 않았습니다**.

- 경로 문자열에서 앱 이름을 추론하고, "백엔드 앱이니까 8080 포트, `/healthz` 프로브"라는 일반 패턴을 적용했을 뿐입니다.

실제 레포의 Dockerfile과 소스를 확인해보면:

| 항목 | LLM 생성 | 실제 레포 | 판정 |
|------|---------|----------|------|
| 이미지 이름 | `my-admin-back:1.0.0` | `my-admin-backend` (Dockerfile 빌드 바이너리명) | 틀림 |
| 컨테이너 포트 | 8080 | 8080 (`EXPOSE 8080`) | 맞음 |
| livenessProbe | `/healthz` | 존재하지 않음 (`/`만 존재) | 틀림 |
| readinessProbe | `/` | `/` (Gin 라우터에 정의) | 맞음 |
| 환경변수 | 없음 | 13개 필수 (DB, AWS S3, 앱 설정) | 누락 |
| Secret/ConfigMap | 없음 | DB 비밀번호, AWS 키 필요 | 누락 |
| 외부 의존성 | 없음 | PostgreSQL, AWS S3 | 누락 |

**이 매니페스트를 apply하면 파드가 즉시 CrashLoopBackOff에 빠집니다.** 13개 필수 환경변수가 없으므로 Go 바이너리가 시작 직후 `log.Fatal`로 종료됩니다.

프로덕션 "형식"은 완벽하지만(securityContext, resources, probe, replicas: 2 등), **이 앱에 맞는 프로덕션 매니페스트는 아닙니다**.

- K8s 리소스 스펙은 LLM의 학습 데이터에 충분히 있지만, 특정 앱의 환경변수와 엔드포인트는 학습 데이터에 없습니다.

### 사례 8: analyze_repo 도구 추가 후 — 같은 레포, 다른 결과

`analyze_repo` 도구를 추가한 뒤 프로그램을 재시작하고, 동일한 요청을 다시 보냈습니다.

```bash
> /path/to/my-admin-backend 레포 배포에 필요한 프로덕션 레벨 매니페스트 작성

[레포 분석] analyze_repo 호출됨
[결과 미리보기]
[레포지토리] /path/to/my-admin-backend
[디렉토리 구조]
Dockerfile, README.md, cmd, go.mod, go.sum, internal
---
[Dockerfile] Dockerfile
FROM golang:1.23.7-alpine AS builder
WORKDIR /ap...

[멀티 리소스 생성] generate_multi_resource 호출됨
[요구사항] 프로덕션 레벨 배포를 위해 my-admin-backend 애플리케이션을 배포합니다.
Dockerfile은 EXPOSE 8080이며, 환경 변수는 APP_PORT, DB_HOST, DB_PORT, DB_NAME,
DB_USER, DB_PASSWORD, AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, A...

[YAML 검증] validate_yaml 호출됨
[검증 결과]
[INFO] namespace 미지정. default 네임스페이스에 배포됩니다.

# 1. ConfigMap (비밀이 아닌 일반 환경 변수)
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-admin-backend-config
data:
  APP_PORT: "8080"
  DB_HOST: "postgres-db.default.svc.cluster.local"
  DB_PORT: "5432"
  DB_NAME: "my_admin"
  DB_USER: "my_user"
  AWS_REGION: "ap-northeast-2"
  AWS_S3_LAB_TEST_BUCKET_NAME: "my-lab-test"
  AWS_S3_MONTHLY_REPORT_BUCKET_NAME: "my-monthly-report"
  AWS_S3_ROUTINE_BUCKET_NAME: "my-routine"
  BACKEND_ENV: "prod"
---
# 2. Secret (민감 환경 변수)
apiVersion: v1
kind: Secret
metadata:
  name: my-admin-backend-secret
type: Opaque
data:
  DB_PASSWORD: "<BASE64_ENCODED_DB_PASSWORD>"
  AWS_S3_SECRET_ACCESS_KEY: "<BASE64_ENCODED_S3_SECRET>"
---
# 3. Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-admin-backend
spec:
  replicas: 3
  ...
  containers:
    - name: my-admin-backend
      image: my-admin-backend:v1.0.0
      ports:
        - containerPort: 8080
      livenessProbe:
        httpGet:
          path: /              # ← 실제 Gin 라우터에 정의된 엔드포인트
          port: 8080
      envFrom:
        - configMapRef:
            name: my-admin-backend-config
        - secretRef:
            name: my-admin-backend-secret
---
# 4. Service
apiVersion: v1
kind: Service
  ...
```

사례 7과 동일한 레포에 동일한 요청이지만, 결과가 완전히 달라졌습니다.

| 항목 | 사례 7 (도구 없음) | 사례 8 (analyze_repo) |
|------|-------------------|----------------------|
| 이미지 이름 | `my-admin-back:1.0.0` (잘림) | `my-admin-backend:v1.0.0` (정확) |
| livenessProbe | `/healthz` (미존재) | `/` (실제 Gin 라우터) |
| 환경변수 | 없음 | 13개 전부 반영 |
| ConfigMap/Secret | 없음 | ConfigMap 10개 + Secret 2개 분리 |
| envFrom 연결 | 없음 | `configMapRef` + `secretRef` |
| Tool 호출 | `generate_yaml` x4 (중복) | `analyze_repo` → `generate_multi_resource` → `validate_yaml` |
| apply 시 | CrashLoopBackOff | 정상 동작 가능 |

Tool 호출 흐름도 깔끔해졌습니다.

- 사례 7에서는 `generate_yaml`이 4번 중복 호출됐지만, 사례 8에서는 `analyze_repo` → `generate_multi_resource` → `validate_yaml` 순서로 정확히 한 번씩 체이닝됐습니다.
- 레포 분석 결과가 명확한 컨텍스트를 제공하니 LLM의 Function Calling 판단도 안정적이 된 것입니다.

프로그램을 재시작했으므로 이전 세션의 대화 기록은 전혀 없습니다.

- Chat Completions API는 stateless이고, 매 세션마다 `self.messages`가 시스템 프롬프트만으로 초기화됩니다.
- 사례 8의 품질 향상은 이전 기억이 아니라, **`analyze_repo`가 실제 파일을 읽어서 LLM에 전달한 컨텍스트** 덕분입니다.
- 도구 하나가 "그럴듯하지만 동작하지 않는 YAML"과 "실제 동작 가능한 YAML"의 차이를 만들었습니다.

## 강점

1. **요청 맥락에 따른 출력 수준 조절**
   - 같은 "nginx Deployment 생성" 요청도 프로덕션용 vs CKA 실습용을 구분하여 적절한 복잡도의 매니페스트를 생성합니다.
   - 시스템 프롬프트의 베스트 프랙티스 규칙을 일괄 적용하지 않고, 사용자 의도를 우선시합니다.

2. **분석 → 개선 제안 → 반영의 워크플로우**
   - 기존 YAML을 분석하면서 개선 방향을 제시하고, 이어지는 요청에서 이를 반영한 매니페스트를 생성하는 대화형 워크플로우가 자연스럽습니다.
   - 단발성 생성 도구가 아니라 점진적 개선을 함께 해나가는 어시스턴트에 가깝습니다.

3. **템플릿에 없는 리소스에 대한 graceful degradation**
   - EndpointSlice, PodDisruptionBudget처럼 `templates.py`에 정의되지 않은 리소스도 분석/생성/검증 모두 잘 동작합니다.
   - 이는 "template-as-context" 설계의 강점입니다. 템플릿을 직접 치환하는 코드 생성기였다면 템플릿 없는 리소스는 아예 불가능했을 것입니다.
   - 이 구조에서 템플릿은 팀 컨벤션을 강제하는 보조 수단이고, 실제 분석/생성/검증의 주체는 LLM의 사전 학습 지식입니다.
   - 검증의 경우 도구 레벨에서 오탐이 발생하지만, LLM이 이를 인식하고 교정하여 최종 응답에서는 정확한 결과를 제공합니다(사례 5 참조).

4. **연관 리소스 자동 확장**
   - Deployment만 요청해도 Service를 함께 생성하고, 외부 DB 연결 개선 시 Secret과 Client Deployment까지 자동으로 포함합니다.
   - Function Calling을 여러 번 체이닝하여 연관 리소스를 빠짐없이 구성합니다.

5. **자연어 후속 조치 유도**
   - 매 응답 끝에 "수정해 드릴까요?", "다른 옵션도 적용하고 싶으시면 알려 주세요!" 같은 후속 선택지를 제시합니다.
   - 사용자는 "예"/"아니오" 수준의 간단한 응답으로 워크플로우를 이어갈 수 있어, 대화 자체가 의사결정 트리처럼 작동합니다.
   - 시스템 프롬프트에 명시적으로 지시한 동작이 아니라 LLM이 자연스럽게 만들어내는 패턴이라는 점에서, Function Calling 에이전트가 단순한 도구 실행기를 넘어 대화형 컨설턴트로 동작하는 사례입니다.

6. **한국어 응답의 자연스러움**
   - 시스템 프롬프트에 "모든 응답은 한국어로 작성" 규칙이 있고, YAML 주석과 설명 모두 한국어로 일관되게 제공됩니다.
   - K8s 용어와 한국어 설명이 적절히 섞여 가독성이 좋습니다.

7. **레포 분석을 통한 "동작 가능한" 매니페스트 생성**
   - `analyze_repo` 도구가 Dockerfile, 소스 코드, 환경변수 파일을 읽어 실제 앱 정보를 추출합니다.
   - 사례 7 → 8 비교에서 보듯, 동일한 요청이라도 레포 컨텍스트 유무에 따라 "형식만 맞는 YAML"과 "apply 즉시 동작하는 YAML"로 갈립니다.
   - 특히 환경변수를 ConfigMap/Secret으로 자동 분리하고, 실제 존재하는 엔드포인트를 프로브에 반영하는 점이 실용적입니다.

## 개선 가능한 점

- **`validate_yaml` 도구 자체는 오탐을 냅니다.**
  - 검증 규칙이 Deployment/Pod 워크로드에 하드코딩되어 있어, PDB를 넣으면 securityContext·resources·probe 미설정으로 CRITICAL이 뜹니다.
  - 사례 5에서 보듯 LLM이 이를 "오탐"으로 교정하여 최종 응답은 정확하지만, 도구 레벨에서 `kind`별 규칙 분기가 있으면 LLM의 판단 부담이 줄고 응답 일관성이 높아질 것입니다.
- **`analyze_yaml`의 extractors가 뽑아주는 필드는 제한적입니다.**
  - 원본 YAML이 그대로 LLM에 전달되므로 실질적인 분석 품질에는 큰 영향이 없습니다.
  - 다만 extractors를 개선하면 LLM에 구조화된 힌트를 더 줄 수 있어 응답 일관성이 높아질 수 있습니다.
- **같은 요청에 `generate_yaml`이 2~4회 중복 호출되는 경우가 있었습니다.**
  - LLM의 Function Calling 판단이 중복될 때 이를 제어하는 로직이 없습니다.
- **사례 7 → 8이 도구 하나의 차이를 보여줍니다.**
  - 동일 레포에 동일 요청이지만, `analyze_repo` 유무에 따라 CrashLoopBackOff(사례 7) vs 정상 동작(사례 8)으로 갈렸습니다.
  - 다만 클러스터 적용(`kubectl_apply`)이나 정책 검증(`check_opa_policy`) 도구는 아직 없으므로, 생성된 매니페스트의 실제 적용과 정책 준수 확인은 수동으로 해야 합니다.

## 활용 방향

- **CKA/CKAD 시험 준비**: 자연어로 리소스를 빠르게 생성하여 시험 환경에서의 YAML 작성 감각을 익힐 수 있습니다. "간단하게"라는 맥락만 추가하면 시험에 적합한 최소 구성을 만들어 줍니다.
- **코드 리뷰 보조**: 팀원이 작성한 매니페스트를 붙여넣으면 보안, 리소스 제한, 프로브 설정 등을 자동으로 체크하고 개선안을 제시합니다.
- **운영 매니페스트 리팩토링**: 레거시 YAML을 분석한 뒤 "더 나은 방향으로 수정해줘"로 베스트 프랙티스를 반영한 버전을 얻을 수 있습니다.
- **학습 도구**: 생성된 YAML의 각 필드에 대한 설명과 이유를 함께 제공하므로, K8s를 배우는 과정에서 참고 자료로 활용할 수 있습니다.
- **셀프 서비스 플랫폼 프로토타입**: `analyze_repo`(레포 분석)가 추가되어 레포지토리 기반 매니페스트 생성이 가능해졌습니다. 여기에 `kubectl_apply`(클러스터 적용), `check_opa_policy`(정책 검증) 같은 도구를 더하면, 개발자가 인프라를 안전하게 프로비저닝하는 셀프 서비스 플랫폼으로 확장할 수 있습니다. Function Calling Agent 패턴이 도구 확장에 유리한 구조이므로, 기존 코드를 거의 건드리지 않고 도구만 추가하면 됩니다.

## 사용 팁

1. **맥락을 함께 전달**: "nginx Deployment"보다 "프로덕션용 nginx Deployment" 또는 "CKA 실습용 nginx Deployment"가 더 적절한 결과를 만들어 줍니다.
2. **분석 후 개선 요청**: YAML을 먼저 붙여넣어 분석한 뒤, "더 나은 방향으로 수정해줘"로 이어가면 맥락이 유지된 채 개선된 매니페스트를 받을 수 있습니다.
3. **멀티 리소스 한번에 요청**: "nginx Deployment + Service + Ingress 만들어줘"처럼 연관 리소스를 함께 요청하면 일관된 라벨링과 포트 매핑을 보장합니다.
4. **사용량 추적**: `--usage` 플래그로 API 비용을 확인하면서 사용합니다.
   ```bash
   python3 k8s_assistant/main.py --usage
   ```

## 예시 세션

```bash
> nginx Deployment 만들어줘
> CKA 실습용으로 간단하게 다시 만들어줘
> (기존 YAML 붙여넣기)
> 보안 관점에서 검증해줘
> 더 나은 방향으로 수정해줘
> Redis StatefulSet + Service + PVC 만들어줘
```
