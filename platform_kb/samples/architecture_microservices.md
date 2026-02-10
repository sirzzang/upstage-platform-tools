# Architecture Document: E-Commerce Microservices Platform

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
