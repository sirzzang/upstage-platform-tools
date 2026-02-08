TEMPLATES = {
    "Deployment": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  labels:
    app: {name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      securityContext:
        runAsNonRoot: true
      containers:
      - name: {name}
        image: {image}
        ports:
        - containerPort: {port}
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /
            port: {port}
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 10
""",
    "Service": """apiVersion: v1
kind: Service
metadata:
  name: {name}
  labels:
    app: {name}
spec:
  type: ClusterIP
  selector:
    app: {name}
  ports:
  - port: {port}
    targetPort: {port}
    protocol: TCP
""",
    "Ingress": """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: {host}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {name}
            port:
              number: {port}
""",
    "StatefulSet": """apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {name}
  labels:
    app: {name}
spec:
  serviceName: {name}
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
      - name: {name}
        image: {image}
        ports:
        - containerPort: {port}
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: {storage}
""",
    "CronJob": """apiVersion: batch/v1
kind: CronJob
metadata:
  name: {name}
spec:
  schedule: "{schedule}"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: {name}
            image: {image}
            command: {command}
          restartPolicy: OnFailure
""",
    "ConfigMap": """apiVersion: v1
kind: ConfigMap
metadata:
  name: {name}
data:
  key: value
""",
    "Secret": """apiVersion: v1
kind: Secret
metadata:
  name: {name}
type: Opaque
data:
  key: base64-encoded-value
""",
    "PersistentVolumeClaim": """apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {name}
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: {storage}
""",
    "HorizontalPodAutoscaler": """apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {name}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {name}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
""",
    "NetworkPolicy": """apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {name}
spec:
  podSelector:
    matchLabels:
      app: {name}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: {name}
""",
}

VALIDATION_RULES = [
    {
        "id": "SEC001",
        "severity": "CRITICAL",
        "category": "security",
        "check": "image tag is 'latest'",
        "message": "image 태그 'latest' 사용 금지. 특정 버전을 지정하세요.",
    },
    {
        "id": "SEC002",
        "severity": "CRITICAL",
        "category": "security",
        "check": "no securityContext",
        "message": "securityContext 미설정. runAsNonRoot: true를 설정하세요.",
    },
    {
        "id": "SEC003",
        "severity": "WARNING",
        "category": "security",
        "check": "allowPrivilegeEscalation not set to false",
        "message": "allowPrivilegeEscalation: false를 설정하세요.",
    },
    {
        "id": "RES001",
        "severity": "CRITICAL",
        "category": "resources",
        "check": "no resources.requests or limits",
        "message": "resources.requests/limits 미설정. OOM Kill 위험이 있습니다.",
    },
    {
        "id": "REL001",
        "severity": "WARNING",
        "category": "reliability",
        "check": "no livenessProbe",
        "message": "livenessProbe 미설정. 컨테이너 장애 감지가 불가합니다.",
    },
    {
        "id": "REL002",
        "severity": "WARNING",
        "category": "reliability",
        "check": "no readinessProbe",
        "message": "readinessProbe 미설정. 무중단 배포에 문제가 발생할 수 있습니다.",
    },
    {
        "id": "REL003",
        "severity": "WARNING",
        "category": "reliability",
        "check": "replicas < 2",
        "message": "replicas가 1개입니다. 프로덕션에서는 2개 이상 권장합니다.",
    },
    {
        "id": "NET001",
        "severity": "INFO",
        "category": "networking",
        "check": "no namespace specified",
        "message": "namespace 미지정. default 네임스페이스에 배포됩니다.",
    },
]
