"""테스트용 샘플 마크다운 문서 모듈.

플랫폼 엔지니어링 시나리오에 맞는 3종의 마크다운 문서를 제공한다:
  1. Runbook — K8s CrashLoopBackOff 트러블슈팅 절차
  2. Post-Mortem — 프로덕션 DB 장애 사후 분석 보고서
  3. Architecture — 이커머스 마이크로서비스 아키텍처 설계 문서

이 문서들은 embedding_tools.py의 청킹 로직이 ## 헤딩 기준으로
섹션을 분할하도록 설계되어 있으므로, 모두 ## 헤딩을 포함하는
마크다운 구조로 작성되어 있다.
"""

import os

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")

# ── 샘플 1: Kubernetes Runbook ──────────────────────────────
# CrashLoopBackOff 상태의 Pod를 진단하고 해결하는 절차서.
# 섹션: Overview, Symptoms, Diagnosis Steps, Common Causes, Escalation, Post-Resolution
RUNBOOK_K8S = """# Runbook: Kubernetes Pod CrashLoopBackOff Troubleshooting

## Overview

This runbook covers the diagnosis and resolution of Kubernetes Pods stuck in CrashLoopBackOff state. CrashLoopBackOff means the container is starting, crashing, and being restarted repeatedly by kubelet with exponential backoff delay.

Severity: P2 (High)
On-call team: Platform Engineering
Escalation: SRE Lead after 30 minutes

## Symptoms

- Pod status shows CrashLoopBackOff in kubectl get pods output
- Container restart count is increasing continuously
- Application logs show repeated startup and crash patterns
- Alerts fired from monitoring system (Prometheus/Grafana)
- Service health checks failing for the affected deployment

## Diagnosis Steps

Step 1: Check pod status and events
```
kubectl describe pod <pod-name> -n <namespace>
```
Look for: Exit codes, OOMKilled events, image pull errors, mount failures.

Step 2: Check container logs
```
kubectl logs <pod-name> -n <namespace> --previous
```
The --previous flag shows logs from the last crashed container instance.

Step 3: Check resource limits
```
kubectl top pod <pod-name> -n <namespace>
```
Compare actual usage against resource requests and limits in the deployment spec.

Step 4: Check ConfigMap and Secret mounts
```
kubectl get configmap,secret -n <namespace>
```
Verify all referenced ConfigMaps and Secrets exist and have correct data.

## Common Causes and Solutions

### Exit Code 1: Application Error
- Check application logs for stack traces or configuration errors
- Verify environment variables are set correctly
- Check database connection strings and credentials
- Solution: Fix application code or configuration, redeploy

### Exit Code 137: OOMKilled
- Container exceeded memory limits
- Check actual memory usage vs limits
- Solution: Increase memory limits in deployment spec or fix memory leak
```yaml
resources:
  limits:
    memory: "512Mi"  # Increase if needed
```

### Exit Code 0 with Restart: Missing CMD
- Container exits successfully but has no long-running process
- Solution: Ensure Dockerfile CMD or deployment command keeps process running

### Image Pull Error
- Wrong image tag or private registry auth failure
- Solution: Verify image exists, check imagePullSecrets configuration

## Escalation Criteria

Escalate to SRE Lead if:
- Issue persists after 30 minutes of troubleshooting
- Multiple pods across different deployments are affected
- Root cause is infrastructure-related (node issues, network)
- Data loss or corruption is suspected

## Post-Resolution

- Update deployment spec if resource limits were changed
- Add monitoring alert if new failure mode discovered
- Document root cause in incident channel
- Schedule post-mortem if customer impact exceeded 15 minutes
"""

# ── 샘플 2: DB 장애 포스트모템 ──────────────────────────────
# 프로덕션 PostgreSQL 장애(84분) 사후 분석 보고서.
# 섹션: Incident Summary, Timeline, Root Cause Analysis, Impact, Action Items, Lessons Learned
POSTMORTEM_DB = """# Post-Mortem: Production Database Outage (2024-11-15)

## Incident Summary

Duration: 2024-11-15 14:23 KST ~ 15:47 KST (84 minutes)
Severity: P1 (Critical)
Impact: All write operations to the order-service database failed. Read operations degraded to 30% success rate. Approximately 2,300 orders were delayed.

## Timeline

- 14:23 - Automated alert: order-service database connection pool exhaustion
- 14:25 - On-call engineer acknowledged alert, began investigation
- 14:30 - Identified: PostgreSQL primary node CPU at 100%, replication lag >60s
- 14:35 - Root cause identified: Long-running analytical query from batch job
- 14:38 - Attempted to kill the problematic query, but it respawned from cron
- 14:42 - Disabled the batch cron job in Kubernetes CronJob
- 14:45 - Killed all long-running analytical queries manually
- 14:50 - Database CPU started recovering, replication lag decreasing
- 15:10 - Connection pool recovered, write operations resumed
- 15:30 - Replication lag cleared, read operations fully restored
- 15:47 - All metrics nominal, incident resolved

## Root Cause Analysis

The batch analytics job (report-generator CronJob) was deployed without resource constraints and ran a full table scan query on the orders table (47M rows) without proper indexing.

Contributing factors:
1. No query timeout configured on the database connection
2. No resource quota for the analytics namespace
3. The batch job was scheduled during peak traffic hours (14:00 KST)
4. No read replica routing for analytical queries
5. Missing database connection pool limits per service

## Impact Assessment

- 2,300 orders delayed by average 45 minutes
- 150 orders failed and required manual retry by customer support
- 12 partner API webhook deliveries failed (retried successfully)
- Customer-facing error rate peaked at 67% for order placement
- Estimated revenue impact: approximately $15,000 in delayed processing

## Action Items

### Immediate (completed)
- [x] Kill problematic queries and disable batch cron
- [x] Add pg_stat_statements monitoring for query duration
- [x] Set statement_timeout=30s on application database connections

### Short-term (1 week)
- [ ] Add read replica for all analytical and reporting queries
- [ ] Implement per-namespace resource quotas in Kubernetes
- [ ] Reschedule batch jobs to off-peak hours (03:00 KST)
- [ ] Add query cost estimation before execution in batch framework

### Long-term (1 month)
- [ ] Implement database connection pool per service with limits
- [ ] Deploy PgBouncer as connection pooler
- [ ] Create dedicated analytics database with CDC replication
- [ ] Add circuit breaker pattern for database connections
- [ ] Implement automated query killer for queries exceeding threshold

## Lessons Learned

1. Analytical queries must never run against production primary database
2. All database connections must have statement_timeout configured
3. Batch jobs need resource limits and should run during off-peak hours
4. Connection pool exhaustion cascades quickly across all services
5. Need automated runbook for database connection pool alerts
"""

# ── 샘플 3: 마이크로서비스 아키텍처 문서 ─────────────────────
# 이커머스 플랫폼의 12개 서비스 구성, 통신 패턴, DB 전략, 모니터링 스택, 배포 전략.
# 섹션: System Overview, Service Catalog, Communication Patterns, Database Strategy,
#        Monitoring Stack, Deployment Strategy
ARCHITECTURE_MICROSERVICES = """# Architecture Document: E-Commerce Microservices Platform

## System Overview

Our e-commerce platform follows a microservices architecture with 12 core services, deployed on Kubernetes (EKS) across 3 availability zones in ap-northeast-2 region.

Total services: 12
Communication: gRPC (internal), REST (external)
Message broker: Apache Kafka (3 brokers, 3 ZooKeeper)
Service mesh: Istio 1.20

## Service Catalog

### Core Services
| Service | Language | Replicas | Database | Owner Team |
|---------|----------|----------|----------|------------|
| api-gateway | Go | 4 | - | Platform |
| user-service | Java | 3 | PostgreSQL | Identity |
| order-service | Java | 5 | PostgreSQL | Commerce |
| product-service | Go | 3 | PostgreSQL | Catalog |
| payment-service | Java | 3 | PostgreSQL | Payment |
| inventory-service | Go | 3 | Redis + PostgreSQL | Supply |
| notification-service | Python | 2 | MongoDB | Platform |
| search-service | Python | 3 | Elasticsearch | Search |
| recommendation-service | Python | 2 | Redis | ML |
| analytics-service | Python | 2 | ClickHouse | Data |
| auth-service | Go | 3 | Redis + PostgreSQL | Identity |
| cdn-service | Go | 2 | S3 | Platform |

## Communication Patterns

### Synchronous (gRPC)
- api-gateway -> all backend services (request routing)
- order-service -> payment-service (payment processing)
- order-service -> inventory-service (stock check and reservation)
- user-service -> auth-service (token validation)

### Asynchronous (Kafka Topics)
| Topic | Producer | Consumers | Purpose |
|-------|----------|-----------|---------|
| order.created | order-service | inventory, notification, analytics | New order events |
| order.completed | payment-service | order, notification, analytics | Payment confirmation |
| user.registered | user-service | notification, recommendation | New user events |
| inventory.low | inventory-service | notification, analytics | Low stock alerts |
| product.updated | product-service | search, recommendation, cdn | Product catalog changes |

## Database Strategy

### Database per Service Pattern
Each service owns its database. No direct cross-service database access.

- PostgreSQL 15: user, order, product, payment, inventory (relational data)
- Redis 7: auth (sessions/tokens), inventory (cache), recommendation (feature store)
- MongoDB 7: notification (flexible schema for multi-channel)
- Elasticsearch 8: search (full-text product search)
- ClickHouse: analytics (OLAP for event data)

### Data Consistency
- Saga pattern for distributed transactions (order -> payment -> inventory)
- Outbox pattern for reliable Kafka event publishing
- Eventually consistent reads via CDC (Change Data Capture)

## Monitoring Stack

### Observability
- Metrics: Prometheus + Grafana (per-service dashboards)
- Logging: Fluentd -> Elasticsearch -> Kibana (EFK stack)
- Tracing: Jaeger with OpenTelemetry instrumentation
- Alerting: Prometheus AlertManager -> Slack + PagerDuty

### SLO Targets
| Service | Availability | Latency (p99) | Error Rate |
|---------|-------------|----------------|------------|
| api-gateway | 99.95% | 200ms | < 0.1% |
| order-service | 99.9% | 500ms | < 0.5% |
| payment-service | 99.9% | 1000ms | < 0.1% |
| search-service | 99.5% | 300ms | < 1% |

## Deployment Strategy

- GitOps with ArgoCD for all service deployments
- Canary deployment for critical services (order, payment)
- Blue-green deployment for api-gateway
- Rolling update for all other services
- Helm charts stored in central chart repository
- Environment promotion: dev -> staging -> production
"""


def generate_all_samples() -> list[str]:
    """모든 샘플 마크다운 문서를 samples/ 디렉토리에 파일로 생성한다.

    Returns:
        생성된 파일들의 절대 경로 리스트
    """
    os.makedirs(SAMPLES_DIR, exist_ok=True)

    # (파일명, 문서 내용) 튜플 리스트
    samples = [
        ("runbook_k8s_troubleshoot.md", RUNBOOK_K8S),
        ("postmortem_db_outage.md", POSTMORTEM_DB),
        ("architecture_microservices.md", ARCHITECTURE_MICROSERVICES),
    ]

    paths = []
    for filename, content in samples:
        path = os.path.join(SAMPLES_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"  {filename} 생성: {path}")
        paths.append(path)

    return paths


if __name__ == "__main__":
    print("샘플 문서 생성 중...")
    results = generate_all_samples()
    print(f"\n총 {len(results)}개 샘플 생성 완료")
