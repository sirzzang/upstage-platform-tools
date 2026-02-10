# Runbook: Kubernetes Pod CrashLoopBackOff Troubleshooting

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
