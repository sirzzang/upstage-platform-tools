# K8s YAML Assistant 활용 질문 가이드

`k8s_assistant`를 최대한 활용하기 위한 질문 예시들을 카테고리별로 정리했다.

## 더 알아보기

실제 사용 사례와 활용 방향은 [EXAMPLES.md](./EXAMPLES.md)를 참고한다.

## YAML 생성

### 기본 워크로드
- "nginx Deployment 만들어줘"
- "Redis StatefulSet 만들어줘"
- "매일 자정에 실행되는 CronJob 만들어줘"
- "PostgreSQL용 PersistentVolumeClaim 만들어줘"

### 맥락을 포함한 생성
- "CKA 시험 대비용으로 간단한 nginx Deployment 만들어줘"
- "프로덕션용 nginx Deployment를 보안 설정 포함해서 만들어줘"
- "개발 환경용이라 리소스 제한 낮게 해서 만들어줘"
- "high availability가 중요한 서비스 Deployment 만들어줘"

### 네트워킹 리소스
- "nginx Service 만들어줘"
- "외부 트래픽을 nginx로 라우팅하는 Ingress 만들어줘"
- "특정 파드 간 통신만 허용하는 NetworkPolicy 만들어줘"
- "외부 DB를 클러스터 내부에서 접근할 수 있게 ExternalName Service 만들어줘"

### 설정 및 보안 리소스
- "환경변수용 ConfigMap 만들어줘"
- "DB 비밀번호를 저장할 Secret 만들어줘"
- "CPU 사용률 70%에서 오토스케일링하는 HPA 만들어줘"

### 템플릿 미정의 리소스
- "nginx Deployment에 대한 PodDisruptionBudget 만들어줘"
- "ServiceAccount 만들어줘"
- "ClusterRole과 ClusterRoleBinding 만들어줘"
- "ResourceQuota 만들어줘"

## 멀티 리소스 생성

### 애플리케이션 배포 세트
- "nginx Deployment + Service + Ingress 한번에 만들어줘"
- "Redis StatefulSet + Service + PVC 만들어줘"
- "백엔드 API용 Deployment + Service + ConfigMap + Secret 만들어줘"
- "Prometheus 모니터링용 Deployment + Service + ConfigMap 만들어줘"

### 연관 리소스 조합
- "nginx Deployment에 PDB랑 HPA도 같이 만들어줘"
- "앱 Deployment + DB Service + Ingress + TLS Secret 한번에 만들어줘"

## YAML 분석

### 기존 매니페스트 분석
- (YAML 붙여넣기 후 자동 분석)
- "이 YAML이 뭐 하는 건지 설명해줘"
- "이 매니페스트의 트래픽 흐름을 설명해줘"

### 분석 후 후속 질문
- "더 나은 방향으로 수정해줘"
- "보안 관점에서 부족한 점이 있어?"
- "프로덕션에 배포해도 괜찮을까?"
- "이 Deployment에 맞는 Service도 만들어줘"

## YAML 검증

### 카테고리별 검증
- "이 YAML 보안 검사해줘"
- "리소스 설정이 적절한지 확인해줘"
- "프로덕션 배포 전에 전체 검증해줘"
- "베스트 프랙티스에 맞는지 체크해줘"

### 검증 후 후속 질문
- "지적한 문제 수정한 버전 만들어줘"
- "CRITICAL 항목만 수정해줘, WARNING은 괜찮아"
- "securityContext를 추가한 버전으로 수정해줘"

## YAML 비교

### 버전 비교
- "이 두 Deployment의 차이점 알려줘"
- "수정 전후 YAML 비교해줘"
- "v1과 v2의 변경 사항 설명해줘"

## 대화형 워크플로우

한 번의 질문이 아니라 대화를 이어가면서 점진적으로 결과를 개선할 수 있다.

### 생성 → 검증 → 개선
```
> nginx Deployment 만들어줘
> 방금 만든 거 검증해줘
> 지적한 문제 수정해줘
```

### 분석 → 개선 → 확장
```
> (기존 YAML 붙여넣기)
> 더 나은 방향으로 수정해줘
> 여기에 HPA도 추가해줘
```

### 프로덕션 → 시험용 전환
```
> 프로덕션용 Redis StatefulSet 만들어줘
> CKA 시험용으로 간단하게 다시 만들어줘
```

### 후속 조치 유도 활용
```
> (YAML 분석 결과에서)
  "ExternalName 사용을 적용하고 싶으시면 알려 주세요!"
> 응, 그렇게 해줘
```

## 실무 시나리오 기반 질문

### 배포 준비
- "이 Deployment, 프로덕션에 올려도 되는 수준이야?"
- "보안 감사 통과할 수 있는 수준으로 만들어줘"
- "namespace 격리된 환경에서 쓸 매니페스트 만들어줘"

### 운영 안정성
- "노드 업그레이드 시에도 서비스 중단 없도록 PDB 만들어줘"
- "트래픽 증가에 자동 대응할 수 있게 HPA 추가해줘"
- "장애 복구 속도를 높이려면 이 YAML에 뭘 추가해야 해?"

### 외부 서비스 연동
- "클러스터 외부에 있는 DB를 Service로 연결하려면?"
- "외부 API 엔드포인트를 ExternalName Service로 만들어줘"

### CKA/CKAD 시험 준비
- "CKA 실습용 nginx Deployment 만들어줘"
- "시험에서 빠르게 작성할 수 있는 최소 구성의 Pod 만들어줘"
- "NetworkPolicy 기본 형태 보여줘"
- "RBAC 설정 예시 만들어줘"
