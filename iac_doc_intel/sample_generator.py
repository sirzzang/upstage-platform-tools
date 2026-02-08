import os

from fpdf import FPDF

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")

TERRAFORM_CODE = """# Terraform Configuration - AWS Infrastructure

provider "aws" {
  region = "ap-northeast-2"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "main-vpc"
    Environment = "production"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-northeast-2a"
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet"
  }
}

resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Security group for web servers"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "web" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.medium"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]

  tags = {
    Name = "web-server"
  }
}

output "instance_public_ip" {
  value = aws_instance.web.public_ip
}
"""

KUBERNETES_CODE = """# Kubernetes Deployment - Web Application

apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
  labels:
    app: web-app
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
        tier: frontend
    spec:
      containers:
      - name: web-app
        image: nginx:1.25.3
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: web-app-svc
  namespace: production
spec:
  type: ClusterIP
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
"""

ANSIBLE_CODE = """# Ansible Playbook - Web Server Setup

---
- name: Configure Web Servers
  hosts: webservers
  become: true
  vars:
    nginx_port: 80
    app_user: deploy

  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present
        update_cache: yes

    - name: Copy nginx config
      template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      notify: Restart nginx

    - name: Enable UFW firewall
      ufw:
        rule: allow
        port: "{{ nginx_port }}"
        proto: tcp

    - name: Create app directory
      file:
        path: /var/www/app
        state: directory
        owner: "{{ app_user }}"
        mode: "0755"

    - name: Deploy application
      copy:
        src: files/app/
        dest: /var/www/app/
        owner: "{{ app_user }}"

    - name: Start nginx
      service:
        name: nginx
        state: started
        enabled: yes

  handlers:
    - name: Restart nginx
      service:
        name: nginx
        state: restarted
"""

# 출처: https://github.com/futurice/terraform-examples
# 참고: aws/wordpress_fargate (ECS Fargate + Aurora Serverless + EFS 구성)
TERRAFORM_ADVANCED_CODE = """# Terraform - ECS Fargate + Aurora Serverless + EFS
# Source: github.com/futurice/terraform-examples
#         aws/wordpress_fargate

provider "aws" {
  region = "ap-northeast-2"
}

locals {
  name = "webapp"
  env  = "production"
  tags = {
    Environment = local.env
    ManagedBy   = "terraform"
    Project     = "webapp-fargate"
  }
}

data "aws_availability_zones" "az" {
  state = "available"
}

# ========== VPC & Networking ==========

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = merge(local.tags, { Name = "${local.name}-vpc" })
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet("10.0.0.0/16", 8, count.index)
  availability_zone = data.aws_availability_zones.az.names[count.index]
  map_public_ip_on_launch = true
  tags = merge(local.tags, {
    Name = "${local.name}-pub-${count.index}"
  })
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet("10.0.0.0/16", 8, count.index + 10)
  availability_zone = data.aws_availability_zones.az.names[count.index]
  tags = merge(local.tags, {
    Name = "${local.name}-priv-${count.index}"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.tags, { Name = "${local.name}-igw" })
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(local.tags, { Name = "${local.name}-eip" })
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  tags = merge(local.tags, { Name = "${local.name}-nat" })
}

# ========== Security Groups ==========

resource "aws_security_group" "alb" {
  name   = "${local.name}-alb-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.tags
}

resource "aws_security_group" "ecs" {
  name   = "${local.name}-ecs-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.tags
}

resource "aws_security_group" "db" {
  name   = "${local.name}-db-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
  tags = local.tags
}

resource "aws_security_group" "efs" {
  name   = "${local.name}-efs-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
  tags = local.tags
}

# ========== EFS ==========

resource "aws_efs_file_system" "app" {
  creation_token = "${local.name}-efs"
  encrypted      = true
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
  tags = merge(local.tags, { Name = "${local.name}-efs" })
}

resource "aws_efs_mount_target" "app" {
  count           = 2
  file_system_id  = aws_efs_file_system.app.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs.id]
}

# ========== Aurora Serverless ==========

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
  tags       = local.tags
}

resource "aws_rds_cluster" "main" {
  cluster_identifier      = "${local.name}-aurora"
  engine                  = "aurora-mysql"
  engine_mode             = "serverless"
  database_name           = "webapp"
  master_username         = var.db_username
  master_password         = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  skip_final_snapshot     = false
  backup_retention_period = 7
  deletion_protection     = true

  scaling_configuration {
    auto_pause               = true
    min_capacity             = 1
    max_capacity             = 4
    seconds_until_auto_pause = 300
  }
  tags = local.tags
}

# ========== ECS Fargate ==========

resource "aws_ecs_cluster" "main" {
  name = "${local.name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = local.tags
}

resource "aws_iam_role" "ecs_exec" {
  name = "${local.name}-ecs-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ecs_exec" {
  role       = aws_iam_role.ecs_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonECSTaskExecRolePolicy"
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name}"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name}-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_exec.arn

  container_definitions = jsonencode([{
    name  = "app"
    image = "wordpress:6.4-php8.2-fpm"
    portMappings = [{ containerPort = 8080 }]
    environment = [
      { name = "DB_HOST",
        value = aws_rds_cluster.main.endpoint },
      { name = "DB_NAME", value = "webapp" },
    ]
    secrets = [
      { name      = "DB_USER"
        valueFrom = aws_ssm_parameter.db_user.arn },
      { name      = "DB_PASS"
        valueFrom = aws_ssm_parameter.db_pass.arn },
    ]
    mountPoints = [{
      sourceVolume  = "efs-vol"
      containerPath = "/var/www/html"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"  = "/ecs/${local.name}"
        "awslogs-region" = "ap-northeast-2"
        "awslogs-stream-prefix" = "ecs"
      }
    }
    healthCheck = {
      command  = ["CMD-SHELL",
        "curl -f http://localhost:8080/ || exit 1"]
      interval = 30
      timeout  = 5
      retries  = 3
    }
  }])

  volume {
    name = "efs-vol"
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.app.id
    }
  }
  tags = local.tags
}

resource "aws_ecs_service" "app" {
  name            = "${local.name}-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  tags = local.tags
}

# ========== Auto Scaling ==========

resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 6
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${local.name}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = "ecs"

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# ========== Secrets (SSM) ==========

resource "aws_ssm_parameter" "db_user" {
  name  = "/${local.name}/db/username"
  type  = "SecureString"
  value = var.db_username
  tags  = local.tags
}

resource "aws_ssm_parameter" "db_pass" {
  name  = "/${local.name}/db/password"
  type  = "SecureString"
  value = var.db_password
  tags  = local.tags
}

# ========== Monitoring ==========

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${local.name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "ECS CPU > 85%"
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "rds_endpoint" {
  value     = aws_rds_cluster.main.endpoint
  sensitive = true
}

output "efs_id" {
  value = aws_efs_file_system.app.id
}
"""

# 출처: https://github.com/ansible/ansible-examples
# 참고: lamp_haproxy (LAMP Stack + HAProxy 로드밸런서 구성)
ANSIBLE_ADVANCED_CODE = """# Ansible - LAMP Stack + HAProxy Load Balancer
# Source: github.com/ansible/ansible-examples
#         lamp_haproxy

---
- name: Apply common configuration to all nodes
  hosts: all
  become: true
  vars:
    ntp_server: time.google.com
    security_updates: true

  tasks:
    - name: Install common packages
      package:
        name:
          - ntp
          - wget
          - curl
          - firewalld
          - python3-pip
        state: present

    - name: Configure NTP
      template:
        src: templates/ntp.conf.j2
        dest: /etc/ntp.conf
      notify: Restart NTP

    - name: Start firewalld
      service:
        name: firewalld
        state: started
        enabled: yes

    - name: Apply security updates
      yum:
        name: '*'
        state: latest
        security: yes
      when: security_updates | bool
      tags: [security]

  handlers:
    - name: Restart NTP
      service:
        name: ntpd
        state: restarted

---
- name: Configure Database Servers
  hosts: dbservers
  become: true
  vars:
    mysql_root_pw: "{{ vault_mysql_root_pw }}"
    mysql_databases:
      - name: webapp
        encoding: utf8mb4
        collation: utf8mb4_unicode_ci
    mysql_users:
      - name: webapp_user
        password: "{{ vault_webapp_db_pw }}"
        priv: "webapp.*:ALL"
        host: "10.0.%"
    mysql_max_connections: 200
    mysql_innodb_buffer_pool: "1G"

  tasks:
    - name: Install MariaDB
      yum:
        name:
          - mariadb-server
          - mariadb
          - MySQL-python
        state: present

    - name: Deploy MariaDB config
      template:
        src: templates/my.cnf.j2
        dest: /etc/my.cnf
      notify: Restart MariaDB

    - name: Start MariaDB
      service:
        name: mariadb
        state: started
        enabled: yes

    - name: Set root password
      mysql_user:
        name: root
        password: "{{ mysql_root_pw }}"
        login_unix_socket: /var/lib/mysql/mysql.sock
      no_log: true

    - name: Create databases
      mysql_db:
        name: "{{ item.name }}"
        encoding: "{{ item.encoding }}"
        collation: "{{ item.collation }}"
        state: present
        login_user: root
        login_password: "{{ mysql_root_pw }}"
      loop: "{{ mysql_databases }}"

    - name: Create database users
      mysql_user:
        name: "{{ item.name }}"
        password: "{{ item.password }}"
        priv: "{{ item.priv }}"
        host: "{{ item.host }}"
        state: present
        login_user: root
        login_password: "{{ mysql_root_pw }}"
      loop: "{{ mysql_users }}"
      no_log: true

    - name: Open MySQL port
      firewalld:
        port: 3306/tcp
        permanent: yes
        state: enabled
        source: "10.0.0.0/24"
      notify: Reload firewalld

  handlers:
    - name: Restart MariaDB
      service:
        name: mariadb
        state: restarted

    - name: Reload firewalld
      service:
        name: firewalld
        state: reloaded

---
- name: Configure Web Servers
  hosts: webservers
  become: true
  vars:
    http_port: 80
    app_root: /var/www/webapp
    php_packages:
      - php
      - php-fpm
      - php-mysql
      - php-gd
      - php-mbstring
    max_children: 50

  tasks:
    - name: Install Apache and PHP
      yum:
        name: "{{ ['httpd'] + php_packages }}"
        state: present

    - name: Deploy Apache vhost
      template:
        src: templates/vhost.conf.j2
        dest: /etc/httpd/conf.d/webapp.conf
      notify: Restart Apache

    - name: Configure PHP-FPM pool
      template:
        src: templates/www.conf.j2
        dest: /etc/php-fpm.d/www.conf
      notify: Restart PHP-FPM

    - name: Create app directory
      file:
        path: "{{ app_root }}"
        state: directory
        owner: apache
        group: apache
        mode: "0755"

    - name: Deploy application
      git:
        repo: "https://github.com/example/webapp.git"
        dest: "{{ app_root }}"
        version: "{{ app_version | default('main') }}"
      notify: Restart Apache
      tags: [deploy]

    - name: Set app config
      template:
        src: templates/app-config.php.j2
        dest: "{{ app_root }}/config.php"
        owner: apache
        mode: "0640"
      tags: [deploy, config]

    - name: Start services
      service:
        name: "{{ item }}"
        state: started
        enabled: yes
      loop:
        - httpd
        - php-fpm

    - name: Open HTTP port
      firewalld:
        port: "{{ http_port }}/tcp"
        permanent: yes
        state: enabled
      notify: Reload firewalld

  handlers:
    - name: Restart Apache
      service:
        name: httpd
        state: restarted

    - name: Restart PHP-FPM
      service:
        name: php-fpm
        state: restarted

    - name: Reload firewalld
      service:
        name: firewalld
        state: reloaded

---
- name: Configure HAProxy Load Balancer
  hosts: lbservers
  become: true
  vars:
    haproxy_stats_port: 8404
    haproxy_stats_user: admin
    haproxy_stats_pw: "{{ vault_haproxy_stats_pw }}"
    backend_servers: "{{ groups['webservers'] }}"

  tasks:
    - name: Install HAProxy
      yum:
        name: haproxy
        state: present

    - name: Deploy HAProxy config
      template:
        src: templates/haproxy.cfg.j2
        dest: /etc/haproxy/haproxy.cfg
        validate: haproxy -c -f %s
      notify: Reload HAProxy

    - name: Configure HAProxy logging
      copy:
        content: |
          $ModLoad imudp
          $UDPServerAddress 127.0.0.1
          $UDPServerRun 514
          local2.* /var/log/haproxy.log
        dest: /etc/rsyslog.d/haproxy.conf
      notify: Restart rsyslog

    - name: Enable SELinux boolean
      seboolean:
        name: haproxy_connect_any
        state: yes
        persistent: yes
      when: ansible_selinux.status == "enabled"

    - name: Start HAProxy
      service:
        name: haproxy
        state: started
        enabled: yes

    - name: Open LB ports
      firewalld:
        port: "{{ item }}/tcp"
        permanent: yes
        state: enabled
      loop:
        - "80"
        - "443"
        - "{{ haproxy_stats_port }}"
      notify: Reload firewalld

  handlers:
    - name: Reload HAProxy
      service:
        name: haproxy
        state: reloaded

    - name: Restart rsyslog
      service:
        name: rsyslog
        state: restarted

    - name: Reload firewalld
      service:
        name: firewalld
        state: reloaded
"""


def _create_code_pdf(title: str, code: str, output_path: str) -> str:
    """코드 내용을 PDF로 생성."""
    pdf = FPDF()
    pdf.add_page()

    # 제목
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 코드 본문
    pdf.set_font("Courier", size=8)
    for line in code.strip().split("\n"):
        # 긴 줄 처리
        if len(line) > 95:
            line = line[:95] + "..."
        pdf.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    return output_path


def generate_terraform_sample() -> str:
    """Terraform 샘플 PDF 생성."""
    path = os.path.join(SAMPLES_DIR, "terraform_sample.pdf")
    return _create_code_pdf("Terraform Configuration - AWS Infrastructure", TERRAFORM_CODE, path)


def generate_kubernetes_sample() -> str:
    """Kubernetes 샘플 PDF 생성."""
    path = os.path.join(SAMPLES_DIR, "kubernetes_sample.pdf")
    return _create_code_pdf("Kubernetes Deployment - Web Application", KUBERNETES_CODE, path)


def generate_ansible_sample() -> str:
    """Ansible 샘플 PDF 생성."""
    path = os.path.join(SAMPLES_DIR, "ansible_sample.pdf")
    return _create_code_pdf("Ansible Playbook - Web Server Setup", ANSIBLE_CODE, path)


def generate_terraform_advanced_sample() -> str:
    """Terraform (Advanced) 샘플 PDF 생성."""
    path = os.path.join(SAMPLES_DIR, "terraform_fargate_sample.pdf")
    return _create_code_pdf(
        "Terraform - ECS Fargate + Aurora Serverless + EFS",
        TERRAFORM_ADVANCED_CODE,
        path,
    )


def generate_ansible_advanced_sample() -> str:
    """Ansible (Advanced) 샘플 PDF 생성."""
    path = os.path.join(SAMPLES_DIR, "ansible_lamp_haproxy_sample.pdf")
    return _create_code_pdf(
        "Ansible - LAMP Stack + HAProxy Load Balancer",
        ANSIBLE_ADVANCED_CODE,
        path,
    )


def generate_all_samples() -> list[str]:
    """모든 샘플 PDF를 생성."""
    os.makedirs(SAMPLES_DIR, exist_ok=True)

    paths = []
    for name, gen_func in [
        ("Terraform (Basic)", generate_terraform_sample),
        ("Terraform (Advanced)", generate_terraform_advanced_sample),
        ("Kubernetes", generate_kubernetes_sample),
        ("Ansible (Basic)", generate_ansible_sample),
        ("Ansible (Advanced)", generate_ansible_advanced_sample),
    ]:
        path = gen_func()
        print(f"  {name} 샘플 생성: {path}")
        paths.append(path)

    return paths


if __name__ == "__main__":
    print("샘플 PDF 생성 중...")
    results = generate_all_samples()
    print(f"\n총 {len(results)}개 샘플 생성 완료")
