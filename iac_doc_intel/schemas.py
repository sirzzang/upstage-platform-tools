# Document Classification 스키마
CLASSIFICATION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "doc-classify",
        "schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "terraform",
                        "kubernetes",
                        "ansible",
                        "runbook",
                        "architecture_diagram",
                        "unknown",
                    ],
                    "description": "The document classification category",
                }
            },
            "required": ["category"],
        },
    },
}

# Terraform 추출 스키마
TERRAFORM_EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "terraform_extract",
        "schema": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "Cloud provider (aws, gcp, azure, etc.)",
                },
                "region": {
                    "type": "string",
                    "description": "Deployment region",
                },
                "resources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Resource type (e.g. aws_instance)",
                            },
                            "name": {
                                "type": "string",
                                "description": "Resource name",
                            },
                        },
                    },
                    "description": "List of defined resources",
                },
                "variables": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "default": {"type": "string"},
                        },
                    },
                    "description": "Input variables",
                },
                "instance_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Instance types used",
                },
                "outputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "string"},
                        },
                    },
                    "description": "Output values",
                },
            },
        },
    },
}

# Kubernetes 추출 스키마
KUBERNETES_EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "kubernetes_extract",
        "schema": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "description": "Resource kind (Deployment, Service, etc.)",
                },
                "api_version": {
                    "type": "string",
                    "description": "API version",
                },
                "name": {
                    "type": "string",
                    "description": "Resource name",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace",
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Container images used",
                },
                "replicas": {
                    "type": "integer",
                    "description": "Number of replicas",
                },
                "ports": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "container_port": {"type": "integer"},
                            "service_port": {"type": "integer"},
                            "protocol": {"type": "string"},
                        },
                    },
                    "description": "Port configurations",
                },
                "labels": {
                    "type": "object",
                    "description": "Labels",
                },
            },
        },
    },
}

# Ansible 추출 스키마
ANSIBLE_EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "ansible_extract",
        "schema": {
            "type": "object",
            "properties": {
                "playbook_name": {
                    "type": "string",
                    "description": "Playbook name or description",
                },
                "hosts": {
                    "type": "string",
                    "description": "Target hosts",
                },
                "become": {
                    "type": "boolean",
                    "description": "Whether privilege escalation is used",
                },
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "module": {"type": "string"},
                        },
                    },
                    "description": "List of tasks",
                },
                "variables": {
                    "type": "object",
                    "description": "Defined variables",
                },
                "roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Roles used",
                },
            },
        },
    },
}

# 분류 라벨 → 추출 스키마 매핑
EXTRACTION_SCHEMAS = {
    "terraform": TERRAFORM_EXTRACTION_SCHEMA,
    "kubernetes": KUBERNETES_EXTRACTION_SCHEMA,
    "ansible": ANSIBLE_EXTRACTION_SCHEMA,
}
