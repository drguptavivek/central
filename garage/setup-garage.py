#!/usr/bin/env python3
"""
setup-garage.py - Configure Garage S3 storage for ODK Central

This script intelligently configures Garage S3-compatible storage to work with
ODK Central's existing SSL setup (Let's Encrypt, Custom SSL, or Upstream Proxy).

Usage:
    python scripts/setup-garage.py

Requirements:
    pip install pyyaml questionary
"""

import re
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Optional imports for better UX
try:
    from questionary import select, text, confirm, Choice
    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def ok(msg: str):
        print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")

    @staticmethod
    def warn(msg: str):
        print(f"{Colors.WARNING}⚠️  {msg}{Colors.ENDC}")

    @staticmethod
    def error(msg: str):
        print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")

    @staticmethod
    def info(msg: str):
        print(f"{Colors.OKCYAN}ℹ️  {msg}{Colors.ENDC}")

    @staticmethod
    def header(msg: str):
        print(f"\n{Colors.BOLD}{msg}{Colors.ENDC}")


class SSLDetector:
    """Detect current SSL configuration from ODK Central setup"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.env_file = project_root / ".env"
        self.docker_compose = project_root / "docker-compose.yml"
        self.custom_ssl_dir = project_root / "files" / "local" / "customssl"

    def detect(self) -> Dict[str, Any]:
        """Run comprehensive SSL detection"""
        detection = {
            "ssl_type": None,
            "ssl_source": None,
            "domain": None,
            "extra_server_names": [],
            "nginx_ports": [],
            "nginx_port_mappings": [],
            "certificate_info": {},
            "confidence": "unknown",
            "warnings": [],
            "network_info": {}
        }

        # Parse .env file
        if self.env_file.exists():
            env_data = self._parse_env()
            detection.update(env_data)
        else:
            detection["warnings"].append(".env file not found")

        # Analyze docker-compose.yml
        if self.docker_compose.exists():
            port_analysis = self._analyze_docker_compose()
            detection["nginx_ports"] = port_analysis["exposed_ports"]
            detection["nginx_port_mappings"] = port_analysis["mappings"]
            detection["network_info"] = port_analysis["network_info"]
        else:
            detection["warnings"].append("docker-compose.yml not found")

        # Check for certificate files
        detection["certificate_info"] = self._check_certificates()

        # Determine SSL type with confidence
        detection["ssl_type"], detection["ssl_source"], detection["confidence"] = \
            self._determine_ssl_type(detection)

        return detection

    def _parse_env(self) -> Dict[str, Any]:
        """Parse .env file for SSL configuration"""
        result = {
            "domain": None,
            "ssl_type": None,
            "extra_server_names": [],
            "cert_domain": None
        }

        try:
            content = self.env_file.read_text()

            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.startswith("DOMAIN="):
                    result["domain"] = line.split("=", 1)[1].strip()
                elif line.startswith("SSL_TYPE="):
                    result["ssl_type"] = line.split("=", 1)[1].strip()
                elif line.startswith("EXTRA_SERVER_NAME="):
                    value = line.split("=", 1)[1].strip().strip('"\'')
                    result["extra_server_names"] = value.split()
                elif line.startswith("CERT_DOMAIN="):
                    result["cert_domain"] = line.split("=", 1)[1].strip()

        except Exception as e:
            result["parse_error"] = str(e)

        return result

    def _analyze_docker_compose(self) -> Dict[str, Any]:
        """Analyze docker-compose.yml for port and network configuration"""
        result = {
            "exposed_ports": [],
            "mappings": [],
            "network_info": {}
        }

        try:
            with open(self.docker_compose) as f:
                compose = yaml.safe_load(f)

            nginx_service = compose.get("services", {}).get("nginx", {})

            # Get port mappings
            port_mappings = nginx_service.get("ports", [])
            for mapping in port_mappings:
                if isinstance(mapping, str):
                    result["mappings"].append(mapping)
                    # Extract host port
                    if ":" in mapping:
                        host_port = mapping.split(":")[0]
                        result["exposed_ports"].append(host_port)

            # Get network info
            networks = nginx_service.get("networks", [])
            result["network_info"] = {
                "networks": networks,
                "internal_port": "80"  # ODK Nginx always listens on 80 internally
            }

        except Exception as e:
            result["parse_error"] = str(e)

        return result

    def _check_certificates(self) -> Dict[str, Any]:
        """Check for existing certificate files"""
        info = {
            "letsencrypt_exists": False,
            "customssl_exists": False,
            "customssl_files": [],
            "cert_details": {}
        }

        if self.custom_ssl_dir.exists():
            info["customssl_exists"] = True

            for cert_file in self.custom_ssl_dir.rglob("*.pem"):
                rel_path = cert_file.relative_to(self.custom_ssl_dir)
                info["customssl_files"].append(str(rel_path))

                if "fullchain" in str(cert_file) or "cert" in str(cert_file):
                    info["cert_details"] = self._get_cert_details(cert_file)

        return info

    def _get_cert_details(self, cert_path: Path) -> Dict[str, str]:
        """Extract details from certificate file using openssl"""
        details = {}

        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", str(cert_path), "-noout",
                 "-subject", "-dates", "-issuer"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith("subject="):
                        details["subject"] = line.split("=", 1)[1].strip()
                    elif line.startswith("notBefore="):
                        details["valid_from"] = line.split("=", 1)[1].strip()
                    elif line.startswith("notAfter="):
                        details["valid_until"] = line.split("=", 1)[1].strip()
                    elif line.startswith("issuer="):
                        details["issuer"] = line.split("=", 1)[1].strip()

            # Get SAN (Subject Alternative Names)
            result_san = subprocess.run(
                ["openssl", "x509", "-in", str(cert_path), "-noout",
                 "-ext", "subjectAltName"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result_san.returncode == 0:
                san_line = result_san.stdout.strip()
                if san_line.startswith("subjectAltName="):
                    san_value = san_line.split("=", 1)[1].strip()
                    details["sans"] = san_value

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        return details

    def _determine_ssl_type(self, detection: Dict) -> Tuple[str, str, str]:
        """Determine SSL type with confidence level"""
        ssl_type = detection.get("ssl_type")
        nginx_ports = detection.get("nginx_ports", [])
        cert_info = detection.get("certificate_info", {})

        # High confidence: SSL_TYPE explicitly set
        if ssl_type == "selfsign":
            return "selfsign", "ENV:SSL_TYPE=selfsign", "high"
        elif ssl_type == "letsencrypt":
            return "letsencrypt", "ENV:SSL_TYPE=letsencrypt", "high"
        elif ssl_type == "customssl":
            return "customssl", "ENV:SSL_TYPE=customssl", "high"
        elif ssl_type == "upstream":
            return "upstream", "ENV:SSL_TYPE=upstream", "high"

        # Medium confidence: Infer from other indicators
        if cert_info.get("customssl_exists"):
            if "443" not in nginx_ports:
                return "upstream", "INFERRED: Custom SSL exists but port 443 not exposed", "medium"
            return "customssl", "INFERRED: Custom SSL directory exists", "medium"

        if "443" in nginx_ports:
            domain = detection.get("domain")
            if domain:
                return "letsencrypt", f"INFERRED: Port 443 exposed for {domain}", "medium"
            return "letsencrypt", "INFERRED: Port 443 exposed (likely Let's Encrypt)", "medium"

        if nginx_ports == ["80"] or ("80" in nginx_ports and "443" not in nginx_ports):
            return "upstream", "INFERRED: Only HTTP port 80 exposed", "medium"

        return "unknown", "UNKNOWN: Could not detect SSL configuration", "low"


class PortAnalyzer:
    """Analyze current port usage and recommend configuration"""

    def __init__(self, docker_compose: Path):
        self.docker_compose = docker_compose

    def _parse_port_mapping(self, port_map: str) -> Optional[str]:
        """Parse docker-compose port mapping, handling env vars like ${HTTP_PORT:-80}:80"""
        try:
            # Match ${VAR:-default} or ${VAR} patterns
            pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
            match = re.search(pattern, port_map)
            if match:
                # Use default value if present
                default_value = match.group(2) if match.group(2) else "80"
                # Replace the entire ${...} with the default value
                resolved = re.sub(pattern, default_value, port_map)
                port_map = resolved

            # Extract host port from "host:container" or "host" format
            if ":" in port_map:
                host_port = port_map.split(":", 1)[0]
                # Filter out any remaining non-numeric characters
                if host_port.isdigit():
                    return host_port
            elif port_map.isdigit():
                return port_map

        except Exception:
            pass

        return None

    def analyze(self, ssl_type: str) -> Dict[str, Any]:
        """Analyze current port usage and recommend new configuration"""
        analysis = {
            "current_mappings": [],
            "current_exposed_ports": [],
            "recommended_upstream_port": "8080",
            "changes_needed": [],
            "docker_hostname": "nginx"
        }

        try:
            with open(self.docker_compose) as f:
                compose = yaml.safe_load(f)

            nginx = compose.get("services", {}).get("nginx", {})

            # Get current port mappings
            current_ports = nginx.get("ports", [])
            for port_map in current_ports:
                if isinstance(port_map, str):
                    analysis["current_mappings"].append(port_map)
                    # Parse port mapping, handling env vars like ${HTTP_PORT:-80}
                    host_port = self._parse_port_mapping(port_map)
                    if host_port:
                        analysis["current_exposed_ports"].append(host_port)

            # Recommend configuration based on SSL type
            if ssl_type == "upstream":
                analysis["recommended_upstream_port"] = self._find_available_port(
                    analysis["current_exposed_ports"]
                )
                analysis["changes_needed"].append({
                    "file": "docker-compose.yml",
                    "service": "nginx",
                    "change": "ports",
                    "from": analysis["current_mappings"],
                    "to": [f'{analysis["recommended_upstream_port"]}:80']
                })

            # Get Docker service name
            analysis["docker_hostname"] = "nginx"

        except Exception as e:
            analysis["error"] = str(e)

        return analysis

    def _find_available_port(self, current_ports: List[str]) -> str:
        """Find an available port for upstream proxy connection"""
        # Common alternative ports to try
        candidates = ["8080", "8888", "8000", "3000", "8081"]

        for port in candidates:
            if port not in current_ports:
                return port

        return "8080"  # Default fallback


class ProxyConfigGenerator:
    """Generate upstream proxy configuration for various proxy servers"""

    def __init__(self, config: Dict[str, Any]):
        self.odk_domain = config.get("odk_domain")
        self.s3_domain = config.get("s3_domain")
        self.upstream_port = config.get("upstream_port", "8080")
        self.odk_host = config.get("odk_host", "localhost")  # Docker host from upstream proxy's perspective

    def generate_all(self) -> Dict[str, str]:
        """Generate configuration for all common proxy types"""
        return {
            "traefik": self._traefik_config(),
            "nginx": self._nginx_config(),
            "caddy": self._caddy_config(),
            "haproxy": self._haproxy_config()
        }

    def _traefik_config(self) -> str:
        """Generate Traefik docker-compose labels"""
        return f"""# Add these labels to your ODK Central container/service in docker-compose.yml:
# Or use in Traefik dynamic configuration

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRAEFIK DOCKER COMPOSE LABELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

labels:
  - "traefik.enable=true"

  # ══════════════════════════════════════════════════════════════════════════
  # ODK Main Application ({self.odk_domain})
  # ══════════════════════════════════════════════════════════════════════════
  - "traefik.http.routers.odk.rule=Host(`{self.odk_domain}`)"
  - "traefik.http.routers.odk.entrypoints=websecure"
  - "traefik.http.routers.odk.tls=true"
  - "traefik.http.routers.odk.tls.certresolver=letsencrypt"
  - "traefik.http.services.odk.loadbalancer.server.port={self.upstream_port}"

  # ══════════════════════════════════════════════════════════════════════════
  # Garage S3 API ({self.s3_domain})
  # ══════════════════════════════════════════════════════════════════════════
  - "traefik.http.routers.odk-s3.rule=Host(`{self.s3_domain}`)"
  - "traefik.http.routers.odk-s3.entrypoints=websecure"
  - "traefik.http.routers.odk-s3.tls=true"
  - "traefik.http.routers.odk-s3.tls.certresolver=letsencrypt"
  - "traefik.http.services.odk-s3.loadbalancer.server.port={self.upstream_port}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRAEFIK DYNAMIC CONFIGURATION (YAML)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Save as: /etc/traefik/dynamic/odk-central.yaml

http:
  routers:
    odk:
      rule: "Host(`{self.odk_domain}`)"
      service: "odk"
      entryPoints:
        - "websecure"
      tls:
        certResolver: "letsencrypt"

    odk-s3:
      rule: "Host(`{self.s3_domain}`)"
      service: "odk"
      entryPoints:
        - "websecure"
      tls:
        certResolver: "letsencrypt"

  services:
    odk:
      loadBalancer:
        servers:
          - url: "http://{self.odk_host}:{self.upstream_port}"
"""

    def _nginx_config(self) -> str:
        """Generate Nginx upstream proxy configuration"""
        return f"""# Add this to your upstream Nginx configuration:

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NGINX UPSTREAM REVERSE PROXY CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Define upstream backend (ODK Nginx in HTTP mode)
upstream odk_backend {{
    server {self.odk_host}:{self.upstream_port};
    keepalive 32;
}}

# ══════════════════════════════════════════════════════════════════════════
# ODK Main Application
# ══════════════════════════════════════════════════════════════════════════
server {{
    listen 443 ssl http2;
    server_name {self.odk_domain};

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/{self.odk_domain}.crt;
    ssl_certificate_key /etc/nginx/ssl/{self.odk_domain}.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Logging
    access_log /var/log/nginx/odk.access.log;
    error_log /var/log/nginx/odk.error.log;

    # Proxy to ODK
    location / {{
        proxy_pass http://odk_backend;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
}}

# ══════════════════════════════════════════════════════════════════════════
# Garage S3 API (same backend, different hostname)
# ══════════════════════════════════════════════════════════════════════════
server {{
    listen 443 ssl http2;
    server_name {self.s3_domain};

    # SSL Configuration (can use same cert with SAN)
    ssl_certificate /etc/nginx/ssl/{self.odk_domain}.crt;
    ssl_certificate_key /etc/nginx/ssl/{self.odk_domain}.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Logging
    access_log /var/log/nginx/odk-s3.access.log;
    error_log /var/log/nginx/odk-s3.error.log;

    # Proxy to ODK Nginx (will route to Garage internally by hostname)
    location / {{
        proxy_pass http://odk_backend;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # S3-specific settings
        client_max_body_size 100m;
        proxy_buffering off;

        # Timeouts for large file uploads
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }}
}}

# HTTP to HTTPS redirect
server {{
    listen 80;
    server_name {self.odk_domain} {self.s3_domain};
    return 301 https://$http_host$request_uri;
}}
"""

    def _caddy_config(self) -> str:
        """Generate Caddyfile configuration"""
        return f"""# Add this to your Caddyfile:

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CADDYFILE CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ══════════════════════════════════════════════════════════════════════════
# ODK Main Application
# ══════════════════════════════════════════════════════════════════════════
{self.odk_domain} {{
    reverse_proxy {self.odk_host}:{self.upstream_port}
}}

# ══════════════════════════════════════════════════════════════════════════
# Garage S3 API
# ══════════════════════════════════════════════════════════════════════════
{self.s3_domain} {{
    reverse_proxy {self.odk_host}:{self.upstream_port}
}}

# Caddy automatically handles HTTPS with Let's Encrypt!
"""

    def _haproxy_config(self) -> str:
        """Generate HAProxy configuration"""
        return f"""# Add this to your HAProxy configuration:

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HAPROXY CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━══════════━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Define backend
backend odk_backend
    balance leastconn
    server odk1 {self.odk_host}:{self.upstream_port} check

# ══════════════════════════════════════════════════════════════════════════
# ODK Main Application - Frontend
# ══════════════════════════════════════════════════════════════════════════
frontend odk_frontend
    mode http
    bind :443 ssl crt /etc/haproxy/certs/{self.odk_domain}.pem alpn h2,http/1.1
    http-request set-header X-Forwarded-Proto https

    # ODK Main Application
    acl is_odk hdr(host) -i {self.odk_domain}
    use_backend odk_backend if is_odk

    # Garage S3 API
    acl is_s3 hdr(host) -i {self.s3_domain}
    use_backend odk_backend if is_s3

    default_backend odk_backend


# ══════════════════════════════════════════════════════════════════════════
# HTTP to HTTPS redirect
# ══════════════════════════════════════════════════════════════════════════
frontend http_redirect
    mode http
    bind :80
    http-request redirect scheme https
"""


class GarageSetup:
    """Main Garage S3 setup orchestrator"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self.detector = SSLDetector(self.project_root)
        self.port_analyzer = PortAnalyzer(self.project_root / "docker-compose.yml")
        self.detection = None
        self.port_analysis = None
        self.config = {
            "ssl_type": None,
            "odk_domain": None,
            "s3_domain": None,
            "s3_server": None,
            "upstream_port": None,
            "odk_host": None
        }
        # Full docker compose command for dev setup
        self.compose_cmd = "docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central"

    def print_header(self, title: str):
        """Print a formatted header"""
        print("\n" + "=" * 70)
        print(f"{Colors.BOLD}{title}{Colors.ENDC}")
        print("=" * 70)

    def format_detection_report(self, detection: Dict) -> str:
        """Format detection results as a readable report"""
        report = []

        ssl_type = detection["ssl_type"] or "Not detected"
        ssl_source = detection["ssl_source"] or "Unknown"
        confidence = detection["confidence"] or "unknown"

        confidence_emoji = {
            "high": f"{Colors.OKGREEN}✅{Colors.ENDC}",
            "medium": f"{Colors.WARNING}⚠️{Colors.ENDC}",
            "low": f"{Colors.OKCYAN}❓{Colors.ENDC}",
            "unknown": f"{Colors.OKCYAN}❓{Colors.ENDC}"
        }.get(confidence, "❓")

        type_labels = {
            "letsencrypt": "Let's Encrypt (on ODK Nginx)",
            "customssl": "Custom SSL Certificates (on ODK Nginx)",
            "upstream": "Upstream Reverse Proxy",
            "unknown": "Unknown / Not Configured"
        }

        report.append(f"\nSSL Type:   {confidence_emoji} {type_labels.get(ssl_type, ssl_type)}")
        report.append(f"Source:     {ssl_source}")
        report.append(f"Confidence: {confidence.upper()}")

        if detection.get("domain"):
            report.append(f"\nDomain:     {detection['domain']}")
            if detection.get("extra_server_names"):
                report.append(f"Extra:      {', '.join(detection['extra_server_names'])}")

        if detection.get("nginx_ports"):
            report.append(f"\nNginx Ports: {', '.join(detection['nginx_ports'])}")

        cert_info = detection.get("certificate_info", {})
        if cert_info.get("cert_details"):
            details = cert_info["cert_details"]
            report.append(f"\n{Colors.OKBLUE}📜 Certificate Details:{Colors.ENDC}")
            if details.get("subject"):
                report.append(f"   Subject:  {details['subject']}")
            if details.get("sans"):
                report.append(f"   SANs:     {details['sans']}")
            if details.get("valid_until"):
                report.append(f"   Expires:  {details['valid_until']}")

        if detection.get("warnings"):
            report.append(f"\n{Colors.WARNING}Warnings:{Colors.ENDC}")
            for warning in detection["warnings"]:
                report.append(f"   {Colors.WARNING}•{Colors.ENDC} {warning}")

        return "\n".join(report)

    def ask_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Ask a yes/no question"""
        if HAS_QUESTIONARY:
            return confirm(prompt, default=default).ask()
        else:
            default_str = "Y/n" if default else "y/N"
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            if not response:
                return default
            return response.startswith("y")

    def ask_choice(self, prompt: str, choices: List[Tuple[str, str]], default: Optional[str] = None) -> str:
        """Ask user to choose from options"""
        if HAS_QUESTIONARY:
            return select(
                prompt,
                choices=[Choice(title=name, value=value) for name, value in choices]
            ).ask()
        else:
            print(f"\n{prompt}")
            for i, (name, value) in enumerate(choices, 1):
                default_marker = " (default)" if value == default else ""
                print(f"{i}. {name}{default_marker}")

            default_idx = next((i for i, (_, v) in enumerate(choices) if v == default), 0)
            response = input(f"Enter choice [1-{len(choices)}] [{default_idx + 1}]: ").strip()
            if not response:
                return choices[default_idx][1]

            try:
                idx = int(response) - 1
                if 0 <= idx < len(choices):
                    return choices[idx][1]
            except ValueError:
                pass

            return choices[0][1]

    def ask_text(self, prompt: str, default: str = "") -> str:
        """Ask for text input"""
        if HAS_QUESTIONARY:
            return text(prompt, default=default).ask()
        else:
            if default:
                prompt = f"{prompt} [{default}]: "
            else:
                prompt = f"{prompt}: "
            return input(prompt).strip() or default

    def detect_ssl_setup(self) -> str:
        """Detect and confirm SSL setup with user"""
        Colors.info("Detecting current SSL configuration...")

        self.detection = self.detector.detect()

        self.print_header("🔍 Detected SSL Configuration")
        print(self.format_detection_report(self.detection))
        print("=" * 70)

        detected_type = self.detection["ssl_type"]
        confidence = self.detection["confidence"]

        # Auto-confirm if high confidence
        if confidence == "high" and detected_type != "unknown":
            if self.ask_yes_no(
                f"\nDetected {detected_type} SSL setup. Is this correct?",
                default=True
            ):
                return detected_type

        # Ask user to choose
        return self.ask_choice(
            "\nHow is SSL currently handled for ODK Central?",
            [
                ("Self-signed certificates on ODK Nginx (local development)", "selfsign"),
                ("Upstream reverse proxy (Traefik, Caddy, Nginx, etc.)", "upstream"),
                ("Let's Encrypt on ODK Nginx container", "letsencrypt"),
                ("Custom SSL certificates on ODK Nginx container", "customssl"),
            ],
            default=detected_type if detected_type in ["selfsign", "upstream", "letsencrypt", "customssl"] else "selfsign"
        )

    def get_domains(self):
        """Get ODK domain and S3 subdomain"""
        existing_domain = self.detection.get("domain")

        if not existing_domain:
            Colors.warn("Could not detect domain from .env file")

        self.config["odk_domain"] = self.ask_text(
            "ODK Domain",
            default=existing_domain or "odk.example.com"
        )

        default_s3 = f"s3.{self.config['odk_domain']}"
        self.config["s3_domain"] = self.ask_text(
            "S3 Subdomain",
            default=default_s3
        )

    def configure_upstream(self):
        """Configure for upstream reverse proxy scenario"""
        self.print_header("🔧 Upstream Reverse Proxy Configuration")

        # Analyze ports
        self.port_analysis = self.port_analyzer.analyze("upstream")

        recommended_port = self.port_analysis["recommended_upstream_port"]

        Colors.info(f"Current ODK Nginx ports: {', '.join(self.port_analysis['current_exposed_ports']) or 'none'}")
        Colors.info(f"Recommended upstream port: {recommended_port}")

        self.config["upstream_port"] = self.ask_text(
            "Port for upstream proxy to connect",
            default=recommended_port
        )

        self.config["s3_server"] = f"https://{self.config['s3_domain']}"

        # Get ODK host from upstream proxy's perspective
        self.config["odk_host"] = self.ask_text(
            "ODK host (as seen from upstream proxy)",
            default="localhost"
        )

        print(f"\n{Colors.OKGREEN}Summary:{Colors.ENDC}")
        print(f"  S3_SERVER will be set to: {self.config['s3_server']}")
        print(f"  ODK Nginx will listen on HTTP: {self.config['upstream_port']}")
        print(f"  Your upstream proxy should forward:")
        print(f"    • https://{self.config['odk_domain']} → http://{self.config['odk_host']}:{self.config['upstream_port']}")
        print(f"    • https://{self.config['s3_domain']} → http://{self.config['odk_host']}:{self.config['upstream_port']}")

        # Generate and show proxy configs
        if self.ask_yes_no("\nGenerate upstream proxy configuration?", default=True):
            self.show_proxy_configs()

    def show_proxy_configs(self):
        """Generate and display proxy configurations"""
        generator = ProxyConfigGenerator(self.config)
        configs = generator.generate_all()

        self.print_header("📋 Upstream Proxy Configuration")

        print(f"\n{Colors.BOLD}Choose your proxy server:{Colors.ENDC}")

        proxy_type = self.ask_choice(
            "Which proxy server are you using?",
            [
                ("Traefik", "traefik"),
                ("Nginx", "nginx"),
                ("Caddy", "caddy"),
                ("HAProxy", "haproxy"),
                ("Show all", "all")
            ]
        )

        if proxy_type == "all":
            for name, config in configs.items():
                print(f"\n{Colors.UNDERLINE}{Colors.BOLD}{name.upper()}{Colors.ENDC}")
                print(config)
        else:
            print(f"\n{configs[proxy_type]}")

        # Ask to save
        if self.ask_yes_no(f"\nSave {proxy_type.upper()} config to file?", default=False):
            filename = f"upstream-{proxy_type}-conf.txt"
            filepath = self.project_root / filename
            filepath.write_text(configs[proxy_type])
            Colors.ok(f"Saved to {filename}")

    def configure_letsencrypt(self):
        """Configure for Let's Encrypt scenario"""
        self.print_header("🔧 Let's Encrypt Configuration")

        self.config["s3_server"] = f"https://{self.config['s3_domain']}"

        # Explain S3 access pattern and DNS requirements
        Colors.header("\n📋 S3 DNS Requirements")
        print(f"""
Garage S3 uses virtual-hosted-style access (like AWS S3):
  URL Pattern:  https://<bucket-name>.{self.config['s3_domain']}/<object>
  Example:      https://odk-central.{self.config['s3_domain']}/submission.xml

You have TWO certificate options:

{Colors.BOLD}Option 1: Specific Certificate (Recommended - Easier){Colors.ENDC}
  Add each bucket domain to EXTRA_SERVER_NAME:
    • {self.config['s3_domain']}
    • odk-central.{self.config['s3_domain']}
    • {self.config['odk_domain']}

  Let's Encrypt will automatically include all EXTRA_SERVER_NAME domains.

{Colors.BOLD}Option 2: Wildcard Certificate{Colors.ENDC}
  Request: *.s3.yourdomain.com
  DNS Entry: *.s3.yourdomain.com → your server IP

  Covers all current and future buckets, but requires DNS validation.
""")

        cert_type = self.ask_choice(
            "Which certificate type do you prefer?",
            [
                ("Specific (easier - add each bucket to EXTRA_SERVER_NAME)", "specific"),
                ("Wildcard (requires DNS validation)", "wildcard"),
            ],
            default="specific"
        )

        if cert_type == "specific":
            Colors.info(f"\n✓ Will use specific certificates")
            Colors.ok(f"Let's Encrypt will cover: {self.config['s3_domain']}")
            Colors.info(f"   Add new bucket domains to EXTRA_SERVER_NAME as needed")
        else:
            Colors.info(f"\n✓ Will use wildcard certificate: *.{self.config['s3_domain']}")
            Colors.warn(f"   Requires DNS entry: *.{self.config['s3_domain']} → your server IP")

    def configure_selfsign(self):
        """Configure for self-signed certificates (local development)"""
        self.print_header("🔧 Self-Signed SSL Configuration")

        Colors.info("\n💡 Self-signed certificates are great for local development!")

        # Explain /etc/hosts requirement
        Colors.header("\n📋 S3 Access Pattern")
        print(f"""
Garage S3 uses virtual-hosted-style access (like AWS S3):
  URL Pattern:  https://<bucket-name>.{self.config['s3_domain']}/<object>
  Example:      https://odk-central.{self.config['s3_domain']}/submission.xml

{Colors.BOLD}For local development, add to /etc/hosts:{Colors.ENDC}
  127.0.0.1  {self.config['odk_domain']}
  127.0.0.1  odk-central.{self.config['s3_domain']}
  127.0.0.1  <any-other-bucket>.{self.config['s3_domain']}

Your browser will show security warnings - this is normal.
""")

        self.config["s3_server"] = f"https://{self.config['s3_domain']}"

    def configure_customssl(self):
        """Configure for custom SSL scenario"""
        self.print_header("🔧 Custom SSL Configuration")

        # Explain S3 access pattern and certificate requirements
        Colors.header("\n📋 S3 Access Pattern & Certificate Requirements")
        print(f"""
Garage S3 uses virtual-hosted-style access (like AWS S3):
  URL Pattern:  https://<bucket-name>.{self.config['s3_domain']}/<object>
  Example:      https://odk-central.{self.config['s3_domain']}/submission.xml

{Colors.BOLD}Your certificate must cover these domains:{Colors.ENDC}
  • {self.config['odk_domain']} (for ODK Central)
  • odk-central.{self.config['s3_domain']} (for your S3 bucket)
  • {self.config['s3_domain']} (base S3 domain)

{Colors.BOLD}Certificate Options:{Colors.ENDC}
  1. Specific Certificate: Add SANs for each bucket domain
  2. Wildcard Certificate: *.{self.config['s3_domain']} (covers all buckets)

{Colors.BOLD}DNS Requirements:{Colors.ENDC}
  • {self.config['odk_domain']} → your server IP
  • odk-central.{self.config['s3_domain']} → your server IP
  • For wildcard: *.{self.config['s3_domain']} → your server IP
""")

        cert_covers = self.ask_yes_no(
            f"\nDoes your custom certificate already cover {self.config['s3_domain']}?",
            default=False
        )

        self.config["s3_server"] = f"https://{self.config['s3_domain']}"

        if not cert_covers:
            Colors.warn("\n⚠️  Your certificate needs to be updated:")
            print(f"\n   Required Subject Alternative Names (SANs):")
            print(f"     • {self.config['odk_domain']}")
            print(f"     • {self.config['s3_domain']}")
            print(f"     • odk-central.{self.config['s3_domain']}")
            print(f"\n   Or use a wildcard: *.{self.config['s3_domain']}")

    def _generate_garage_config(self) -> Path:
        """Generate Garage configuration file (idempotent - preserves existing rpc_secret)"""
        # Ensure garage directory exists
        garage_dir = self.project_root / "garage"
        garage_dir.mkdir(exist_ok=True)

        config_file = garage_dir / "garage.toml"

        # Check if config file already exists and preserve rpc_secret
        existing_rpc_secret = None
        if config_file.exists():
            try:
                existing_content = config_file.read_text()
                # Extract existing rpc_secret if present
                import re
                match = re.search(r'rpc_secret\s*=\s*"([^"]+)"', existing_content)
                if match:
                    existing_rpc_secret = match.group(1)
                    Colors.info(f"Preserving existing RPC secret from {config_file.relative_to(self.project_root)}")
            except Exception as e:
                Colors.warn(f"Could not read existing config: {e}")

        # Generate a random RPC secret only if not preserving existing one
        if not existing_rpc_secret:
            import secrets
            rpc_secret = secrets.token_hex(32)
            Colors.ok("Generated new RPC secret")
        else:
            rpc_secret = existing_rpc_secret

        config_content = f"""metadata_dir = "/data/meta"
data_dir = "/data/data"
db_engine = "lmdb"

replication_factor = 1

rpc_bind_addr = "[::]:3901"
rpc_secret = "{rpc_secret}"

[s3_api]
s3_region = "garage"
api_bind_addr = "[::]:3900"
root_domain = ".s3.{self.config['odk_domain']}"

[s3_web]
bind_addr = "[::]:3903"
root_domain = ".web.{self.config['odk_domain']}"
index = "index.html"
"""
        config_file.write_text(config_content)
        Colors.ok(f"Generated Garage configuration: {config_file.relative_to(self.project_root)}")
        return config_file

    def _run_garage_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str]:
        """Run a command in the Garage container"""
        try:
            # The Garage image is minimal (scratch-based), so we exec the binary directly
            # The binary is at /garage in the container
            result = subprocess.run(
                ["docker", "exec", "odk-garage", "/garage"] + command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            # Combine stdout and stderr for output (Garage CLI might use either)
            output = result.stdout
            if not output.strip() and result.stderr.strip():
                output = result.stderr
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError:
            return False, "Docker not found"
        except Exception as e:
            return False, str(e)

    def _ensure_garage_running(self) -> bool:
        """Ensure Garage container is running with latest config"""
        try:
            # Check if container exists and is running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=odk-garage", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            already_running = "Up" in result.stdout

            # Always restart to ensure latest config is loaded
            if already_running:
                Colors.info("Restarting Garage container to pick up latest configuration...")
                result = subprocess.run(
                    ["docker", "compose", "-f", "docker-compose-garage.yml", "restart", "garage"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.project_root
                )
                if result.returncode != 0:
                    Colors.warn(f"Restart warning: {result.stderr}")
            else:
                # Start it
                Colors.info("Starting Garage container...")
                result = subprocess.run(
                    ["docker", "compose", "-f", "docker-compose-garage.yml", "up", "-d"],
                    capture_output=True,
                    text=True,
                    timeout=120,  # Increase timeout for image pull
                    cwd=self.project_root
                )

                if result.returncode != 0:
                    # Check if it's a network error
                    if "network" in result.stderr.lower() or "network" in result.stdout.lower():
                        Colors.error("Network error. Try creating the odk-net network:")
                        print("   docker network create odk-net")
                    Colors.error(f"Failed to start Garage: {result.stderr}")
                    return False

            # Wait for Garage to be ready
            Colors.info("Waiting for Garage to be ready...")
            max_wait = 60  # Increased from 30 to 60 seconds
            import time
            for i in range(max_wait):
                time.sleep(1)

                # First check if container is actually running
                result = subprocess.run(
                    ["docker", "ps", "--filter", "name=odk-garage", "--format", "{{.Status}}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if "Up" not in result.stdout:
                    if i % 5 == 0:
                        print(f"  Container not running yet... ({i}s)")
                    continue

                # Container is up, check if S3 API port is accessible (port 3900)
                # The Garage image is minimal (scratch-based) so we can't exec into it
                # Instead we check if the port is listening
                try:
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                         "--connect-timeout", "2", "http://127.0.0.1:3900"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    # Any HTTP response (200, 403, 404, etc.) means Garage is up
                    # Empty response means connection failed
                    http_code = result.stdout.strip()
                    if http_code and http_code != "000":
                        Colors.ok(f"Garage is ready (S3 API responding with HTTP {http_code})")
                        # Configure cluster layout for single-node setup
                        self._configure_garage_layout()
                        return True
                except Exception:
                    pass  # Port not ready yet, keep waiting

                if i % 5 == 0 and i > 0:
                    print(f"  Still waiting... ({i}s)")
                    # Show what's happening
                    if i == 10:
                        Colors.info("  (Garage can take 30-60 seconds to fully start)")

            Colors.error("Garage failed to start in time")
            Colors.info("\nTroubleshooting:")
            Colors.info("  1. Check container status: docker ps -a | grep odk-garage")
            Colors.info("  2. Check Garage logs: docker logs odk-garage")
            Colors.info("  3. Check if S3 API is responding: curl http://127.0.0.1:3900")
            Colors.info("  4. Try manual restart: docker compose -f docker-compose-garage.yml restart")
            return False

        except Exception as e:
            Colors.error(f"Error ensuring Garage is running: {e}")
            return False

    def _get_storage_size(self) -> str:
        """Get storage size from config or prompt user for first-time setup"""
        garage_dir = self.project_root / "garage"
        storage_config_file = garage_dir / "storage.conf"

        # Check if storage size is already configured
        if storage_config_file.exists():
            try:
                stored_size = storage_config_file.read_text().strip()
                Colors.info(f"Using configured storage size: {stored_size}")
                return stored_size
            except Exception:
                pass

        # First-time setup - prompt for storage size
        Colors.header("\n💾 Garage Storage Size")
        print("How much storage should be allocated for Garage S3?")
        print("This will be used for storing ODK form attachments and other binary files.")
        print("")
        print("Common sizes:")
        print("  • 1G   - Testing only (fits ~200-500 photos)")
        print("  • 5G   - Small projects (~1,000-5,000 photos)")
        print("  • 10G  - Medium projects (~2,000-10,000 photos)")
        print("  • 50G  - Large projects (~10,000-50,000 photos)")
        print("  • 100G+ - Production deployments")
        print("")

        # Get user input with validation
        while True:
            try:
                user_input = input("Storage size (e.g., 10G, 500M, 1T) [default: 10G]: ").strip()
                if not user_input:
                    user_input = "10G"

                # Validate format (number + unit)
                import re
                if not re.match(r'^\d+[MGTP]$', user_input, re.IGNORECASE):
                    Colors.error("Invalid format. Use format like: 10G, 500M, 1T")
                    continue

                # Save to config file for next time
                storage_config_file.write_text(user_input.upper())
                Colors.ok(f"Storage size set to: {user_input.upper()}")
                return user_input.upper()

            except KeyboardInterrupt:
                print("\n")
                raise
            except Exception as e:
                Colors.error(f"Invalid input: {e}")

    def _configure_garage_layout(self):
        """Configure Garage cluster layout for single-node setup"""
        try:
            # Check if layout is already configured
            success, output = self._run_garage_command(["layout", "show"], timeout=10)
            # Layout is configured if version > 0 AND there are nodes with roles
            is_configured = success and "version: 0" not in output and "No nodes" not in output
            if is_configured:
                Colors.ok("Garage cluster layout already configured")
                return

            # Get node ID
            success, output = self._run_garage_command(["node", "id"], timeout=10)
            if not success:
                Colors.warn("Could not get Garage node ID, skipping layout configuration")
                return

            # Extract node ID (64 hex characters)
            import re
            match = re.search(r'([a-f0-9]{64})', output)
            if not match:
                Colors.warn("Could not parse Garage node ID, skipping layout configuration")
                return

            node_id = match.group(1)

            # Get storage size (prompt first time, use stored value thereafter)
            storage_size = self._get_storage_size()

            Colors.info(f"Configuring Garage cluster layout for node: {node_id[:8]}...")

            # Assign node to zone dc1 with configured capacity
            success, _ = self._run_garage_command(
                ["layout", "assign", node_id, "-z", "dc1", "-c", storage_size],
                timeout=10
            )
            if not success:
                Colors.warn("Could not assign Garage node layout")
                return

            # Apply the layout
            success, output = self._run_garage_command(
                ["layout", "apply", "--version", "1"],
                timeout=10
            )
            if success:
                Colors.ok(f"Garage cluster layout configured with {storage_size} storage")
            else:
                Colors.warn("Could not apply Garage cluster layout")

        except Exception as e:
            Colors.warn(f"Error configuring Garage layout: {e}")

    def _detect_odk_network(self) -> Optional[str]:
        """Detect the network name used by ODK services from running containers"""
        try:
            # First, try to inspect running containers to get actual network
            containers_to_check = ["central-nginx-1", "central-service-1", "central-client-1"]

            # Collect all networks from containers
            all_networks = {}  # base_network -> full_network

            for container in containers_to_check:
                result = subprocess.run(
                    ["docker", "inspect", "-f", "{{range $net, $conf := .NetworkSettings.Networks}}{{$net}} {{end}}", container],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0 and result.stdout.strip():
                    networks = result.stdout.strip().split()
                    for net in networks:
                        if net != "bridge" and not net.startswith("host_"):
                            # HIGHEST PRIORITY: Exact 'web' network (external network)
                            if net == "web":
                                Colors.ok(f"Found exact 'web' network from {container}: {net}")
                                return "web"

                            # SECOND PRIORITY: Networks where last component is 'web'
                            # e.g., central_web -> web
                            base_network = net
                            if "_" in net:
                                parts = net.split("_")
                                if len(parts) >= 2:
                                    base_network = "_".join(parts[1:])

                            if base_network == "web":
                                Colors.ok(f"Found 'web' network from {container}: {net}")
                                return "web"

                            all_networks[base_network] = net

            # If we found networks, prefer named ones (not 'default')
            if all_networks:
                # Skip 'default' network - it's auto-created by Docker Compose
                for base_net in all_networks:
                    if base_net != "default":
                        Colors.ok(f"Using network: {base_net} (from {all_networks[base_net]})")
                        return base_net

            Colors.info("No running ODK containers found, checking docker-compose.yml...")
            # Fallback: read docker-compose.yml
            with open(self.docker_compose) as f:
                compose = yaml.safe_load(f)

            # Get nginx service networks
            nginx = compose.get("services", {}).get("nginx", {})
            networks = nginx.get("networks", [])

            if networks:
                # Prefer 'web' network if available
                if "web" in networks:
                    Colors.ok("Found 'web' network in docker-compose.yml")
                    return "web"
                # Otherwise use first network, but skip 'default'
                for network in networks:
                    if network != "default":
                        Colors.info(f"Using network from docker-compose.yml: {network}")
                        return network
                # Fallback to first network
                network_name = networks[0]
                Colors.info(f"Using network in docker-compose.yml: {network_name}")
                return network_name

            # Fallback: check top-level networks
            top_networks = compose.get("networks", {})
            if top_networks:
                # Prefer 'web' if it exists
                if "web" in top_networks:
                    return "web"
                # Skip 'default' network if possible
                for net_name in top_networks:
                    if net_name != "default":
                        Colors.info(f"Using top-level network: {net_name}")
                        return net_name
                first_network = list(top_networks.keys())[0]
                Colors.info(f"Using top-level network: {first_network}")
                return first_network

            return None

        except Exception as e:
            Colors.warn(f"Could not detect network: {e}")
            return None

    def _ensure_network_exists(self, network_name: str = None):
        """Ensure the Docker network exists"""
        if not network_name:
            network_name = "odk-net"  # Default fallback

        try:
            # Check if network exists
            result = subprocess.run(
                ["docker", "network", "ls", "--filter", f"name={network_name}", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if network_name in result.stdout:
                return  # Network exists

            # Create the network
            Colors.info(f"Creating {network_name} network...")
            result = subprocess.run(
                ["docker", "network", "create", network_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                Colors.warn(f"Could not create network: {result.stderr}")
            else:
                Colors.ok(f"Created {network_name} network")

        except Exception as e:
            Colors.warn(f"Network check failed: {e}")

    def _parse_garage_key_output(self, output: str) -> Optional[Dict[str, str]]:
        """Parse Garage key creation output to extract key ID and secret"""
        key_id = None
        secret_key = None

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Key ID:") or line.startswith("Key ID:"):
                key_id = line.split(":", 1)[1].strip()
            elif line.startswith("Secret key:") or line.startswith("Secret key:"):
                secret_key = line.split(":", 1)[1].strip()

        if key_id and secret_key:
            return {"access_key": key_id, "secret_key": secret_key}
        return None

    def _check_if_key_exists(self, key_name: str) -> Optional[Dict[str, str]]:
        """Check if a Garage key already exists and return its details"""
        success, output = self._run_garage_command(["key", "list"])
        if not success:
            return None

        # Check if our key exists in the list
        for line in output.splitlines():
            if key_name in line:
                # Key exists, but we can't recover the secret key
                # Need to create a new one or ask user
                return None

        return None

    def _read_existing_s3_credentials(self) -> Optional[Dict[str, str]]:
        """Read existing S3 credentials from .env file"""
        if not self.env_file.exists():
            return None

        try:
            env_content = self.env_file.read_text()
            credentials = {}

            for line in env_content.splitlines():
                line = line.strip()
                if line.startswith("S3_SERVER="):
                    credentials["s3_server"] = line.split("=", 1)[1].strip()
                elif line.startswith("S3_ACCESS_KEY="):
                    credentials["access_key"] = line.split("=", 1)[1].strip()
                elif line.startswith("S3_SECRET_KEY="):
                    credentials["secret_key"] = line.split("=", 1)[1].strip()
                elif line.startswith("S3_BUCKET_NAME="):
                    credentials["bucket_name"] = line.split("=", 1)[1].strip()

            # Check if we have all required credentials
            if all(k in credentials for k in ["s3_server", "access_key", "secret_key", "bucket_name"]):
                return credentials
        except Exception as e:
            Colors.warn(f"Could not read existing .env: {e}")

        return None

    def _check_if_bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket already exists"""
        success, output = self._run_garage_command(["bucket", "list"])
        if not success:
            return False

        return bucket_name in output

    def provision_garage(self) -> Dict[str, str]:
        """Provision Garage with keys and bucket (idempotent)"""
        key_name = "odk-central-key"
        bucket_name = "odk-central"

        Colors.header("🔧 Provisioning Garage S3 Storage")

        # Step 1: Ensure Garage is running
        if not self._ensure_garage_running():
            Colors.error("Failed to start Garage. Please start it manually:")
            print("   docker compose -f docker-compose-garage.yml up -d")
            raise Exception("Garage not available")

        # Step 2: Check for existing credentials in .env
        Colors.info("\nChecking for existing S3 credentials...")
        existing_credentials = self._read_existing_s3_credentials()

        credentials = None
        if existing_credentials:
            # Verify the key still exists in Garage
            Colors.info(f"Found credentials in .env for key: {existing_credentials['access_key']}")
            success, output = self._run_garage_command(["key", "info", existing_credentials["access_key"]])
            if success:
                Colors.ok("Reusing existing S3 credentials (key is valid in Garage)")
                credentials = {
                    "access_key": existing_credentials["access_key"],
                    "secret_key": existing_credentials["secret_key"],
                    "s3_server": existing_credentials["s3_server"]
                }
            else:
                Colors.warn("Key from .env not found in Garage, will create new key")

        # Step 3: Create new key only if needed
        if not credentials:
            Colors.info("Creating new S3 key...")
            success, output = self._run_garage_command(
                ["key", "create", key_name],
                timeout=30
            )

            if not success or not output.strip():
                Colors.error(f"Failed to create key: {output if output else '(empty output)'}")
                if not success:
                    Colors.info("\nTroubleshooting:")
                    Colors.info("  1. Check if cluster layout is configured:")
                    Colors.info("     docker exec odk-garage /garage cluster status")
                    Colors.info("  2. Check Garage logs: docker logs odk-garage | tail -50")
                    Colors.info("  3. Try manual key creation:")
                    Colors.info(f"     docker exec odk-garage /garage key create {key_name}")
                raise Exception("Key creation failed")

            credentials = self._parse_garage_key_output(output)
            if not credentials:
                Colors.error("Failed to parse key output")
                Colors.info(f"Garage output:\n{output}")
                raise Exception("Key parsing failed")

            Colors.ok(f"Created S3 key: {credentials['access_key']}")

        # Step 4: Create bucket if it doesn't exist
        Colors.info("\nChecking for existing bucket...")
        if self._check_if_bucket_exists(bucket_name):
            Colors.ok(f"Bucket '{bucket_name}' already exists")
        else:
            Colors.info(f"Creating bucket '{bucket_name}'...")
            success, output = self._run_garage_command(
                ["bucket", "create", bucket_name],
                timeout=30
            )

            if not success:
                Colors.warn(f"Bucket creation issue: {output}")
            else:
                Colors.ok(f"Created bucket '{bucket_name}'")

        # Step 5: Grant permissions (idempotent - safe to run multiple times)
        Colors.info(f"Granting key permissions on bucket...")
        success, output = self._run_garage_command(
            ["bucket", "allow", bucket_name, "--read", "--write", "--key", credentials["access_key"]],
            timeout=30
        )

        if not success:
            Colors.warn(f"Permission grant issue: {output}")
        else:
            Colors.ok(f"Granted permissions to key")

        credentials["bucket_name"] = bucket_name
        return credentials

    def generate_garage_credentials(self) -> Dict[str, str]:
        """
        Provision Garage S3 storage (idempotent)
        - Ensures Garage is running
        - Creates S3 keys using Garage CLI
        - Creates bucket if needed
        - Grants permissions
        """
        return self.provision_garage()

    def generate_garage_docker_compose(self) -> str:
        """Generate Garage docker-compose configuration"""
        # Detect network from ODK docker-compose.yml
        network_name = self.config.get("detected_network", "default")

        config = {
            "version": "3.8",
            "services": {
                "garage": {
                    "image": "dxflrs/garage:v2.1.0",
                    "container_name": "odk-garage",
                    "command": ["./garage", "server"],
                    "ports": ["127.0.0.1:3900:3900", "127.0.0.1:3903:3903"],
                    "volumes": [
                        "garage_data:/data",
                        "./garage/garage.toml:/etc/garage.toml:ro"
                    ],
                    "environment": {"RUST_LOG": "info"},
                    "networks": ["default"]
                }
            },
            "volumes": {"garage_data": {}},
            "networks": {}
        }

        # Add network based on scenario - use detected network
        if self.config["ssl_type"] == "letsencrypt" or self.config["ssl_type"] == "customssl":
            config["networks"]["default"] = {"name": network_name, "external": True}

        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    def generate_nginx_s3_conf(self) -> str:
        """Generate Nginx S3 configuration template"""
        if self.config["ssl_type"] == "upstream":
            # HTTP configuration for upstream proxy
            return f"""server {{
  listen 80;
  http2 on;
  server_name s3.${{DOMAIN}};
  server_tokens off;

  client_max_body_size 100m;

  # Proxy to Garage S3 API
  location / {{
    proxy_pass http://garage:3900;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Handle large file uploads/downloads
    proxy_buffering off;
  }}
}}
"""
        else:
            # HTTPS configuration for Let's Encrypt / Custom SSL
            return f"""server {{
  listen 443 ssl;
  http2 on;
  server_name s3.${{DOMAIN}};
  server_tokens off;

  ssl_certificate /etc/${{SSL_TYPE}}/live/${{CERT_DOMAIN}}/fullchain.pem;
  ssl_certificate_key /etc/${{SSL_TYPE}}/live/${{CERT_DOMAIN}}/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
  ssl_prefer_server_ciphers off;

  client_max_body_size 100m;

  # Proxy to Garage S3 API
  location / {{
    proxy_pass http://garage:3900;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Handle large file uploads/downloads
    proxy_buffering off;
  }}
}}
"""

    def update_env_file(self, s3_credentials: Dict[str, str]):
        """Update .env with S3 configuration"""
        lines = []

        if self.env_file.exists():
            existing = self.env_file.read_text().splitlines()

            # Preserve all lines except S3_*
            for line in existing:
                if line.startswith("S3_"):
                    continue
                lines.append(line)

        # Add S3 configuration
        lines.extend([
            "",
            "# S3 Blob Storage (Garage)",
            f"S3_SERVER={self.config['s3_server']}",
            f"S3_ACCESS_KEY={s3_credentials['access_key']}",
            f"S3_SECRET_KEY={s3_credentials['secret_key']}",
            f"S3_BUCKET_NAME={s3_credentials['bucket_name']}",
        ])

        # Handle EXTRA_SERVER_NAME for Let's Encrypt
        if self.config["ssl_type"] == "letsencrypt":
            new_lines = []
            extra_updated = False
            for line in lines:
                if line.startswith("EXTRA_SERVER_NAME="):
                    existing = line.split("=", 1)[1].strip('"\'')
                    if self.config["s3_domain"] not in existing:
                        line = f'EXTRA_SERVER_NAME="{existing} {self.config["s3_domain"]}"'
                    extra_updated = True
                new_lines.append(line)

            if not extra_updated:
                # Add EXTRA_SERVER_NAME after SSL_TYPE line
                for i, line in enumerate(new_lines):
                    if line.startswith("SSL_TYPE="):
                        new_lines.insert(i + 1, f'EXTRA_SERVER_NAME="{self.config["s3_domain"]}"')
                        break

            lines = new_lines

        self.env_file.write_text("\n".join(lines) + "\n")
        Colors.ok(f"Updated .env")

    def update_docker_compose(self):
        """Update docker-compose.yml if needed"""
        if self.config["ssl_type"] == "upstream" and self.port_analysis:
            changes = self.port_analysis.get("changes_needed", [])
            if changes:
                Colors.warn("\n⚠️  Manual change required:")
                print("\nYou need to update docker-compose.yml nginx service ports:")
                print(f"  FROM: {changes[0]['from']}")
                print(f"  TO:   {changes[0]['to']}")
                print("\nThis allows your upstream proxy to connect to ODK Nginx.")

    def update_nginx_setup_script(self):
        """Automatically integrate S3 config processing into setup-odk.sh"""
        setup_script_path = self.project_root / "files" / "nginx" / "setup-odk.sh"

        if not setup_script_path.exists():
            Colors.warn(f"setup-odk.sh not found at {setup_script_path}")
            return False

        try:
            content = setup_script_path.read_text()

            # Check if S3 config processing is already integrated
            if "s3.conf.template" in content:
                Colors.ok("S3 config processing already integrated into setup-odk.sh")
                return True

            # Find the line where we need to insert the S3 config processing
            # We want to insert it after the odk.conf.template generation (after line 84)
            marker_line = "> /etc/nginx/conf.d/odk.conf"

            if marker_line not in content:
                Colors.warn("Could not find insertion point in setup-odk.sh")
                return False

            # Prepare the S3 config processing block
            s3_config_block = """

# Generate S3 API config for Garage
CERT_DOMAIN=$( [ "$SSL_TYPE" = "customssl" ] && echo "local" || echo "$DOMAIN") \\
/scripts/envsub.awk \\
  < /usr/share/odk/nginx/s3.conf.template \\
  > /etc/nginx/conf.d/s3.conf"""

            # Insert the S3 config block after the marker
            lines = content.split('\n')
            new_lines = []
            inserted = False

            for i, line in enumerate(lines):
                new_lines.append(line)
                if not inserted and marker_line in line and i > 80 and i < 90:
                    new_lines.append(s3_config_block)
                    inserted = True

            if not inserted:
                Colors.warn("Could not insert S3 config block into setup-odk.sh")
                return False

            # Write the updated content
            setup_script_path.write_text('\n'.join(new_lines))
            Colors.ok(f"Updated {setup_script_path.relative_to(self.project_root)} with S3 config processing")
            return True

        except Exception as e:
            Colors.warn(f"Could not update setup-odk.sh: {e}")
            return False

    def _add_s3_volume_mount_to_compose(self):
        """Add s3.conf.template volume mount to docker-compose.yml nginx service"""
        compose_file = self.project_root / "docker-compose.yml"

        if not compose_file.exists():
            Colors.warn(f"docker-compose.yml not found at {compose_file}")
            return False

        try:
            content = compose_file.read_text()

            # Check if s3.conf.template is already mounted
            if "s3.conf.template" in content:
                Colors.ok("s3.conf.template volume mount already exists in docker-compose.yml")
                return True

            # Find the line with odk.conf.template and add s3.conf.template after it
            marker = "./files/nginx/odk.conf.template:/usr/share/odk/nginx/odk.conf.template:ro"

            if marker not in content:
                Colors.warn("Could not find odk.conf.template volume mount in docker-compose.yml")
                return False

            # The new volume mount line to add
            new_volume = '      - ./files/nginx/s3.conf.template:/usr/share/odk/nginx/s3.conf.template:ro'

            lines = content.split('\n')
            new_lines = []
            inserted = False

            for i, line in enumerate(lines):
                new_lines.append(line)
                if not inserted and marker in line:
                    new_lines.append(new_volume)
                    inserted = True

            if not inserted:
                Colors.warn("Could not insert s3.conf.template volume mount into docker-compose.yml")
                return False

            # Write the updated content
            compose_file.write_text('\n'.join(new_lines))
            Colors.ok(f"Added s3.conf.template volume mount to {compose_file.relative_to(self.project_root)}")
            return True

        except Exception as e:
            Colors.warn(f"Could not update docker-compose.yml: {e}")
            return False

    def _check_existing_setup_health(self) -> Dict[str, bool]:
        """Comprehensive health check of existing Garage S3 setup"""
        health_checks = {
            "garage_running": False,
            "s3_credentials_valid": False,
            "odk_can_reach_garage": False,
            "host_can_reach_garage": False,
            "all_healthy": False
        }

        Colors.header("\n🔍 Checking Existing Garage S3 Setup")

        # Check 1: Is Garage container running?
        print("\n[1/4] Checking if Garage container is running...")
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=odk-garage", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if "Up" in result.stdout:
            Colors.ok("✓ Garage container is running")
            health_checks["garage_running"] = True
        else:
            Colors.warn("✗ Garage container is not running")
            return health_checks

        # Check 2: Are S3 credentials configured and valid?
        print("\n[2/4] Checking S3 credentials...")
        existing_creds = self._read_existing_s3_credentials()

        if existing_creds:
            # Verify key exists in Garage
            success, _ = self._run_garage_command(
                ["key", "info", existing_creds["access_key"]],
                timeout=10
            )
            if success:
                Colors.ok(f"✓ S3 key '{existing_creds['access_key']}' is valid in Garage")
                health_checks["s3_credentials_valid"] = True
            else:
                Colors.warn("✗ S3 key from .env not found in Garage")
        else:
            Colors.info("ℹ️  No S3 credentials configured yet")

        # Check 3: Can ODK service reach Garage?
        print("\n[3/4] Checking if ODK service can reach Garage...")
        odk_containers = ["central-service-1", "central-client-1"]
        odk_can_reach = False

        # First, show which ODK containers are running
        running_odk_containers = []
        for container in odk_containers:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and container in result.stdout:
                running_odk_containers.append(container)

        if not running_odk_containers:
            Colors.warn("✗ No ODK containers are running")
            Colors.info("  Start ODK containers with: docker compose up -d")
        else:
            Colors.info(f"  Found running ODK containers: {', '.join(running_odk_containers)}")

        # Check what networks Garage is on
        print("  Checking Garage container networks...")
        garage_networks = subprocess.run(
            ["docker", "inspect", "odk-garage", "-f",
             "{{range $net, $conf := .NetworkSettings.Networks}}{{$net}} {{end}}"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if garage_networks.returncode == 0:
            networks = garage_networks.stdout.strip().split()
            Colors.info(f"  Garage is on networks: {', '.join(networks) if networks else 'none'}")
        else:
            Colors.warn("  Could not determine Garage's networks")

        # Check what networks ODK containers are on
        for container in running_odk_containers:
            result = subprocess.run(
                ["docker", "inspect", container, "-f",
                 "{{range $net, $conf := .NetworkSettings.Networks}}{{$net}} {{end}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                networks = result.stdout.strip().split()
                Colors.info(f"  {container} is on networks: {', '.join(networks)}")

        # Now test connectivity (silent internal checks, only show final result)
        for container in running_odk_containers:
            # Try bash's built-in TCP test (works even without curl/nc/wget)
            result = subprocess.run(
                ["docker", "exec", container, "sh", "-c",
                 "timeout 5 bash -c 'cat < /dev/null > /dev/tcp/odk-garage/3900' 2>/dev/null"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                Colors.ok(f"✓ {container} can reach Garage S3 API")
                odk_can_reach = True
                break
            else:
                # Try with /bin/sh as fallback
                result = subprocess.run(
                    ["docker", "exec", container, "sh", "-c",
                     "timeout 5 sh -c '(echo > /dev/tcp/odk-garage/3900) >/dev/null 2>&1'"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    Colors.ok(f"✓ {container} can reach Garage S3 API")
                    odk_can_reach = True
                    break

        if not odk_can_reach:
            Colors.warn("✗ ODK service cannot reach Garage")
            Colors.info("\n  Troubleshooting:")
            Colors.info("  • Ensure Garage and ODK share at least one Docker network")
            Colors.info(f"  • Garage network: {', '.join(garage_networks.stdout.strip().split()) if garage_networks.returncode == 0 else 'unknown'}")
            Colors.info("  • Check: docker network inspect <network-name>")

        # Check 4: Can host reach Garage via hostname?
        print("\n[4/4] Checking if host can reach Garage S3 hostname...")
        s3_server = self.config.get("s3_server", "https://s3.central.local")

        try:
            # Parse hostname from S3_SERVER
            from urllib.parse import urlparse
            hostname = urlparse(s3_server).hostname

            if hostname:
                result = subprocess.run(
                    ["curl", "-k", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                     f"{s3_server}/health",  # Just check if we can connect
                     ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # Any response means we can reach it (404 is fine, just means no health endpoint)
                if result.stdout.strip() and result.stdout.strip() != "000":
                    Colors.ok(f"✓ Host can reach Garage at {hostname}")
                    health_checks["host_can_reach_garage"] = True
                else:
                    Colors.info(f"ℹ️  Cannot reach Garage at {hostname} (may not be fully configured yet)")
        except Exception as e:
            Colors.info(f"ℹ️  Host connectivity check skipped: {e}")

        # Overall health assessment
        # Distinguish between first-time setup and existing healthy setup
        garage_healthy = health_checks["garage_running"]
        has_credentials = existing_creds is not None
        credentials_valid = health_checks["s3_credentials_valid"]

        # Setup is healthy if Garage is running AND (no credentials yet OR credentials are valid)
        all_critical_healthy = garage_healthy and (not has_credentials or credentials_valid)

        # Track if this is first-time setup (no S3 credentials in .env yet)
        is_first_time_setup = garage_healthy and not has_credentials

        health_checks["all_healthy"] = all_critical_healthy
        health_checks["is_first_time_setup"] = is_first_time_setup

        print("\n" + "=" * 70)
        if is_first_time_setup:
            Colors.ok("✓ Garage is running - ready for first-time S3 setup")
        elif all_critical_healthy:
            Colors.ok("✓ All critical checks passed - existing setup is healthy")
        else:
            Colors.warn("⚠️  Some checks failed - setup may need attention")

        return health_checks

    def generate_files(self, s3_credentials: Dict[str, str]):
        """Generate all configuration files"""
        self.print_header("📄 Generating Configuration Files")

        # Generate garage.toml
        self._generate_garage_config()

        # Generate docker-compose-garage.yml
        garage_compose_path = self.project_root / "docker-compose-garage.yml"
        garage_compose_path.write_text(self.generate_garage_docker_compose())
        Colors.ok(f"Generated {garage_compose_path.name}")

        # Generate Nginx config template
        s3_conf_template_path = self.project_root / "files" / "nginx" / "s3.conf.template"
        s3_conf_template_path.write_text(self.generate_nginx_s3_conf())
        Colors.ok(f"Generated {s3_conf_template_path.relative_to(self.project_root)}")

        # Generate actual s3.conf with variables substituted (bind-mounted into container)
        self._generate_s3_conf()

        # Integrate S3 config processing into nginx setup script
        self.update_nginx_setup_script()

        # Add s3.conf volume mount to docker-compose.yml
        self._ensure_s3_conf_volume_mount()

        # Update .env
        self.update_env_file(s3_credentials)

        # Update docker-compose if needed
        self.update_docker_compose()

    def _generate_s3_conf(self):
        """Generate s3.conf with variables substituted (for bind mount)"""
        import re

        s3_conf_path = self.project_root / "files" / "nginx" / "s3.conf"

        # Read template
        template_path = self.project_root / "files" / "nginx" / "s3.conf.template"
        if not template_path.exists():
            Colors.warn(f"s3.conf.template not found, skipping s3.conf generation")
            return False

        try:
            content = template_path.read_text()

            # Substitute variables using regex (similar to envsub)
            domain = self.config.get("domain", "central.local")
            ssl_type = self.config.get("ssl_type", "selfsign")
            cert_domain = "local" if ssl_type == "customssl" else domain

            # Substitute ${VAR} style variables
            content = re.sub(r'\$\{DOMAIN\}', domain, content)
            content = re.sub(r'\$\{SSL_TYPE\}', ssl_type, content)
            content = re.sub(r'\$\{CERT_DOMAIN\}', cert_domain, content)

            # Write the generated file
            s3_conf_path.write_text(content)
            Colors.ok(f"Generated {s3_conf_path.relative_to(self.project_root)} (bind-mounted)")
            return True

        except Exception as e:
            Colors.warn(f"Could not generate s3.conf: {e}")
            return False

    def _ensure_s3_conf_volume_mount(self):
        """Ensure s3.conf volume mount exists in docker-compose.yml"""
        compose_file = self.project_root / "docker-compose.yml"

        if not compose_file.exists():
            return False

        try:
            content = compose_file.read_text()

            # Check if s3.conf volume mount already exists
            if "./files/nginx/s3.conf:/etc/nginx/conf.d/s3.conf:ro" in content:
                Colors.ok("s3.conf volume mount already exists in docker-compose.yml")
                return True

            # Find the s3.conf.template line and add s3.conf after it
            marker = "./files/nginx/s3.conf.template:/usr/share/odk/nginx/s3.conf.template:ro"

            if marker not in content:
                # Already have the mount from manual edit
                if "files/nginx/s3.conf" in content:
                    Colors.ok("s3.conf volume mount found in docker-compose.yml")
                    return True
                Colors.warn("Could not find s3.conf.template volume mount")
                return False

            # The new volume mount line to add
            new_volume = '      # Optional: Pre-generated S3 config (run: make nginx-s3-conf or ./scripts/generate-s3-conf.sh)\n      - ./files/nginx/s3.conf:/etc/nginx/conf.d/s3.conf:ro'

            lines = content.split('\n')
            new_lines = []
            inserted = False

            for i, line in enumerate(lines):
                new_lines.append(line)
                if not inserted and marker in line:
                    new_lines.append(new_volume)
                    inserted = True

            if not inserted:
                Colors.warn("Could not add s3.conf volume mount to docker-compose.yml")
                return False

            # Write the updated content
            compose_file.write_text('\n'.join(new_lines))
            Colors.ok("Added s3.conf volume mount to docker-compose.yml")
            return True

        except Exception as e:
            Colors.warn(f"Could not update docker-compose.yml: {e}")
            return False

    def print_next_steps(self, s3_credentials: Dict[str, str]):
        """Print instructions for next steps"""
        self.print_header("✅ Setup Complete! Next Steps")

        print(f"""
{Colors.BOLD}Garage S3 storage has been fully configured:{Colors.ENDC}
  ✓ Garage container started
  ✓ S3 keys generated and saved to .env
  ✓ Bucket '{s3_credentials['bucket_name']}' created
  ✓ Permissions granted
  ✓ Nginx S3 config generated and bind-mounted

{Colors.BOLD}Remaining steps to activate S3 storage:{Colors.ENDC}

{Colors.BOLD}1. Restart ODK Nginx (loads bind-mounted s3.conf):{Colors.ENDC}
   {self.compose_cmd} restart nginx

{Colors.BOLD}2. Restart ODK Service to pick up S3 configuration:{Colors.ENDC}
   {self.compose_cmd} restart service

{Colors.BOLD}3. Verify S3 configuration:{Colors.ENDC}
   {self.compose_cmd} exec service env | grep S3_SERVER

{Colors.BOLD}4. Test S3 access (optional):{Colors.ENDC}
   curl -sk https://odk-central.s3.{self.config.get("domain", "central.local")}/{s3_credentials['bucket_name']}/

{Colors.BOLD}Regenerate s3.conf if .env changes:{Colors.ENDC}
   python garage/setup-garage.py --regenerate-s3-conf

{Colors.BOLD}Garage Web UI (for debugging):{Colors.ENDC}
   http://localhost:3903
""")

        if self.config["ssl_type"] == "upstream":
            print(f"""
{Colors.WARNING}⚠️  UPSTREAM PROXY SETUP REQUIRED:{Colors.ENDC}

Before S3 access will work, ensure your upstream proxy is configured to forward:
   • https://{self.config['odk_domain']} → http://{self.config['odk_host']}:{self.config['upstream_port']}
   • https://{self.config['s3_domain']} → http://{self.config['odk_host']}:{self.config['upstream_port']}

See the proxy configuration generated earlier for details.
""")

    def run(self):
        """Main setup flow"""
        try:
            print(f"""
{Colors.BOLD}{Colors.OKBLUE}
╔══════════════════════════════════════════════════════════════════════╗
║                   ODK Central + Garage S3 Setup                      ║
╚══════════════════════════════════════════════════════════════════════╝
{Colors.ENDC}
""")

            # Step 1: Detect SSL setup
            self.config["ssl_type"] = self.detect_ssl_setup()

            # Step 2: Get domains
            self.get_domains()

            # Step 2.5: Check if existing Garage setup is healthy
            health = self._check_existing_setup_health()

            # Step 2.6: Check if s3.conf exists (bind-mounted nginx config)
            s3_conf_path = self.project_root / "files" / "nginx" / "s3.conf"
            if not s3_conf_path.exists():
                Colors.warn("\n⚠️  s3.conf not found (nginx S3 configuration)")
                print("\nThe bind-mounted s3.conf file is missing.")
                print("This file is required for nginx to proxy S3 requests to Garage.")
                print("\nThis can happen when:")
                print("  • First-time setup")
                print("  • .env file was modified")
                print("  • Files were cleaned up")

                if self.ask_yes_no("\nRegenerate s3.conf from template?", default=True):
                    self._generate_s3_conf()
                    Colors.ok("s3.conf generated successfully")
                else:
                    Colors.warn("Skipping s3.conf generation. Nginx S3 proxy may not work.")
            elif health.get("is_first_time_setup"):
                # Existing s3.conf but first-time setup - check if it needs regeneration
                Colors.info("\nℹ️  Found existing s3.conf")

            print("\n" + "=" * 70)
            if health.get("is_first_time_setup"):
                Colors.header("🆕 First-Time Garage S3 Setup")
                print("\nGarage is running and ready for S3 configuration.")
                print("\nWhat happens next:")
                print("  • New S3 credentials will be generated")
                print("  • S3 bucket will be created (or reused if already exists)")
                print("  • Configuration files will be generated")
                print("  • ODK Nginx and Service will need to be restarted")

                if not self.ask_yes_no("\nProceed with S3 setup?", default=True):
                    Colors.info("\nSetup cancelled by user.")
                    sys.exit(0)

            elif health["all_healthy"]:
                Colors.header("✓ Existing Garage S3 Setup is Healthy!")
                print("\nAll critical checks passed. Your existing setup is working correctly.")
                print("The script will preserve your existing configuration (RPC secret, S3 keys, bucket).")
                print("\nWhat happens next:")
                print("  • Existing credentials will be reused")
                print("  • Configuration files will be regenerated (if needed)")
                print("  • Garage container will be restarted to pick up any config changes")

                if not self.ask_yes_no(
                    "\nProceed with setup (will preserve existing credentials)?",
                    default=True
                ):
                    Colors.info("\nSetup cancelled by user.")
                    sys.exit(0)
            else:
                Colors.info("Setup check complete.")
                print("The script will provision or repair the Garage S3 configuration.")

            # Step 3: Configure based on SSL type
            if self.config["ssl_type"] == "upstream":
                self.configure_upstream()
            elif self.config["ssl_type"] == "letsencrypt":
                self.configure_letsencrypt()
            elif self.config["ssl_type"] == "selfsign":
                self.configure_selfsign()
            else:  # customssl
                self.configure_customssl()

            # Ask for confirmation before provisioning
            if not self.ask_yes_no(
                "\nReady to provision Garage S3 storage and generate configuration?",
                default=True
            ):
                Colors.info("Setup cancelled.")
                return

            # Step 4: Detect network early and generate docker-compose file first
            Colors.header("🔍 Detecting ODK Docker network")

            odk_network = self._detect_odk_network()

            if odk_network:
                print(f"\nFound network: {Colors.OKGREEN}{odk_network}{Colors.ENDC}")
                print(f"Garage will join this network to communicate with ODK services.")

                # Ask user to confirm
                if not self.ask_yes_no(
                    f"\nUse network '{odk_network}' for Garage?",
                    default=True
                ):
                    # Ask user for custom network name
                    custom_network = self.ask_text(
                        "Enter network name to use",
                        default=odk_network
                    )
                    odk_network = custom_network

                self.config["detected_network"] = odk_network
                self._ensure_network_exists(odk_network)
            else:
                Colors.warn("Could not detect ODK network")
                odk_network = self.ask_text(
                    "Enter network name for Garage (e.g., odk-net, web, default)",
                    default="default"
                )
                self.config["detected_network"] = odk_network

            Colors.ok(f"Using network: {odk_network}")

            # Step 5: Generate Garage configuration file
            Colors.info("Generating Garage configuration...")
            self._generate_garage_config()

            # Step 6: Generate docker-compose-garage.yml with correct network
            Colors.info("Generating docker-compose-garage.yml...")
            garage_compose_path = self.project_root / "docker-compose-garage.yml"
            garage_compose_path.write_text(self.generate_garage_docker_compose())
            Colors.ok("Generated docker-compose-garage.yml")

            # Step 7: Provision Garage (starts container, generates keys, creates bucket)
            s3_credentials = self.generate_garage_credentials()

            # Step 8: Generate remaining files (nginx config, .env)
            Colors.info("Generating remaining configuration files...")
            s3_conf_path = self.project_root / "files" / "nginx" / "s3.conf.template"
            s3_conf_path.write_text(self.generate_nginx_s3_conf())
            Colors.ok(f"Generated {s3_conf_path.relative_to(self.project_root)}")

            # Integrate S3 config processing into nginx setup script
            Colors.info("Integrating S3 config into nginx setup script...")
            self.update_nginx_setup_script()

            # Add s3.conf.template volume mount to docker-compose.yml
            Colors.info("Adding s3.conf.template volume mount to docker-compose.yml...")
            self._add_s3_volume_mount_to_compose()

            # Update .env
            self.update_env_file(s3_credentials)

            # Update docker-compose if needed
            self.update_docker_compose()

            # Step 9: Print next steps
            self.print_next_steps(s3_credentials)

        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}Setup cancelled by user.{Colors.ENDC}")
            sys.exit(1)
        except Exception as e:
            print(f"\n\n{Colors.FAIL}Error: {e}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Entry point"""
    setup = GarageSetup()
    setup.run()


if __name__ == "__main__":
    main()
