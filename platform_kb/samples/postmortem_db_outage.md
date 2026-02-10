# Post-Mortem: Production Database Outage (2024-11-15)

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
