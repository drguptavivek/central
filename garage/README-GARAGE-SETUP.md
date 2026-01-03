# Garage S3 Setup Script

Automated setup script for configuring [Garage S3](https://garagehq.deuxfleurs.fr/) as blob storage for ODK Central.

## Quick Start

Run the setup script from the project root:

```bash
uv run --with pyyaml --with questionary python garage/setup-garage.py
```

Or with pip:

```bash
pip install -r garage/requirements-garage.txt
python garage/setup-garage.py
```

## What It Does

The script automatically:

1. **Detects your current SSL setup** (Let's Encrypt, Custom SSL, or Upstream Proxy)
2. **Analyzes your Docker configuration** (ports, networks)
3. **Generates all necessary files**:
   - `garage/garage.toml` - Garage configuration file
   - `garage/storage.conf` - Storage size configuration
   - `docker-compose-garage.yml` - Garage service definition (v2.1.0)
   - `files/nginx/s3.conf.template` - Nginx routing for S3
   - `.env` - Updates with S3 credentials
4. **Provisions Garage S3 resources**:
   - Starts Garage container
   - Creates cluster layout with configured storage
   - Generates S3 access keys
   - Creates bucket and grants permissions
5. **Provides upstream proxy configs** (Traefik, Nginx, Caddy, HAProxy) if needed

## Features

### 🏥 Pre-Flight Health Checks
Before making any changes, the script performs comprehensive health checks on existing Garage S3 setups:

1. **Garage Container Status** - Verifies the Garage container is running
2. **S3 Credentials Validation** - Checks that credentials in `.env` are valid in Garage
3. **ODK Connectivity** - Tests if ODK services can reach Garage via Docker network
4. **Host Connectivity** - Tests if the host can reach Garage via configured hostname

If all checks pass, the script shows confirmation that your existing setup is healthy and asks if you want to proceed. The script preserves your existing RPC secret and S3 credentials.

### 🔍 Smart Detection
- Automatically detects SSL setup from `.env` and `docker-compose.yml`
- Detects ODK's Docker network automatically
- Shows detected config and asks for confirmation

### 🔐 Idempotent & Safe
- **RPC Secret**: Preserves existing secret if `garage.toml` exists
- **Storage Size**: Prompts on first run, reuses stored value thereafter
- **S3 Keys**: Reuses existing credentials from `.env` if valid
- **Buckets**: Skips creation if already exists
- **Permissions**: Safe to run multiple times

### 💾 Configurable Storage

First-time setup prompts for storage allocation:

```
╔══════════════════════════════════════════════════════════════════════╗
║                      💾 Garage Storage Size                          ║
╚══════════════════════════════════════════════════════════════════════╝

How much storage should be allocated for Garage S3?
This will be used for storing ODK form attachments and other binary files.

Common sizes:
  • 1G   - Testing only (fits ~200-500 photos)
  • 5G   - Small projects (~1,000-5,000 photos)
  • 10G  - Medium projects (~2,000-10,000 photos)
  • 50G  - Large projects (~10,000-50,000 photos)
  • 100G+ - Production deployments

Storage size (e.g., 10G, 500M, 1T) [default: 10G]:
```

Subsequent runs automatically use the configured size:
```
ℹ️  Using configured storage size: 5G
```

## Supported SSL Scenarios

| Scenario | Description |
|----------|-------------|
| **Self-Signed** | For local development (default: `central.local`) |
| **Let's Encrypt** | ODK Nginx handles SSL with Let's Encrypt certificates |
| **Custom SSL** | ODK Nginx handles SSL with your own certificates |
| **Upstream Proxy** | Traefik, Caddy, Nginx, or HAProxy in front handles SSL |

When you run the script, you'll see these options:

```
How is SSL currently handled for ODK Central? (Use arrow keys)
  • Self-signed certificates on ODK Nginx (local development)
  • Upstream reverse proxy (Traefik, Caddy, Nginx, etc.)
  • Let's Encrypt on ODK Nginx container
  • Custom SSL certificates on ODK Nginx container
```

## Files Generated

```
central/
├── garage/
│   ├── garage.toml                 # Garage configuration (RPC secret preserved)
│   ├── storage.conf                # Storage size configuration
│   ├── setup-garage.py             # Setup script
│   ├── requirements-garage.txt     # Python dependencies
│   └── README-GARAGE-SETUP.md      # This file
├── docker-compose-garage.yml       # Garage service definition (v2.1.0)
├── files/nginx/s3.conf.template    # Nginx S3 routing config
└── .env                            # Updated with S3_* variables
```

## Idempotency Summary

| Component | First Run | Subsequent Runs |
|-----------|-----------|------------------|
| RPC Secret | Generate new | Preserve existing |
| Storage Size | Prompt user | Use stored value |
| S3 Keys | Create new | Reuse existing |
| Bucket | Create new | Skip if exists |
| Permissions | Grant | Safe to re-grant |
| Network Detection | Auto-detect | Auto-detect |

## Example Output

### First Run (New Setup)

```
╔══════════════════════════════════════════════════════════════════════╗
║                   ODK Central + Garage S3 Setup                      ║
╚══════════════════════════════════════════════════════════════════════╝

🔍 Detecting current SSL configuration...

======================================================================
🔍 Detected SSL Configuration
======================================================================

SSL Type:   ⚠️  Upstream Reverse Proxy
Source:     INFERRED: Self-signed certificate detected
Confidence: MEDIUM

Domain:     central.local
Extra:      10.0.2.2

======================================================================

Detected selfsigned SSL setup. Is this correct? [Y/n]: yes

ODK Domain [central.local]:
S3 Subdomain [s3.central.local]:

======================================================================
🔍 Checking Existing Garage S3 Setup
======================================================================

[1/4] Checking if Garage container is running...
✗ Garage container is not running

======================================================================
Existing setup check complete.
The script will provision a new Garage S3 setup or repair existing configuration.

======================================================================
✅ Setup Complete! Next Steps
======================================================================

1. Restart ODK Nginx to pick up S3 routing config:
   docker compose restart nginx

2. Restart ODK Service to pick up S3 configuration:
   docker compose restart service

3. Verify S3 connectivity:
   docker compose logs service | grep -i s3
```

### Subsequent Run (Existing Healthy Setup)

```
======================================================================
🔍 Checking Existing Garage S3 Setup
======================================================================

[1/4] Checking if Garage container is running...
✓ Garage container is running

[2/4] Checking S3 credentials...
✓ S3 key 'GKabc123' is valid in Garage

[3/4] Checking if ODK service can reach Garage...
✓ central-service-1 can reach Garage S3 API

[4/4] Checking if host can reach Garage S3 hostname...
✓ Host can reach Garage at s3.central.local

======================================================================
✓ All critical checks passed - existing setup is healthy
======================================================================

======================================================================
✓ Existing Garage S3 Setup is Healthy!
======================================================================

All critical checks passed. Your existing setup is working correctly.
The script will preserve your existing configuration (RPC secret, S3 keys, bucket).

What happens next:
  • Existing credentials will be reused
  • Configuration files will be regenerated (if needed)
  • Garage container will be restarted to pick up any config changes

Proceed with setup (will preserve existing credentials)? [Y/n]:
```

## Upstream Proxy Users

If you're using an upstream reverse proxy (Traefik, Caddy, etc.), the script will:

1. Detect your current port configuration
2. Suggest an HTTP port for ODK Nginx (default: 8080)
3. Generate **ready-to-use proxy configurations** for your proxy server
4. Show you exactly what to add to your proxy config

The script supports generating configurations for:
- **Traefik** (docker-compose labels and dynamic YAML)
- **Nginx** (upstream reverse proxy)
- **Caddy** (Caddyfile)
- **HAProxy** (haproxy.cfg)

## Troubleshooting

### Script fails with "ModuleNotFoundError: No module named 'yaml'"

Install dependencies:
```bash
pip install pyyaml questionary
```

Or use `uv`:
```bash
uv run --with pyyaml --with questionary python garage/setup-garage.py
```

### Detection shows "Unknown" SSL type

Check your `.env` file and ensure `SSL_TYPE` is set correctly:
```bash
grep SSL_TYPE .env
```

### Garage container fails to start

Check Docker logs:
```bash
docker compose -f docker-compose-garage.yml logs garage
```

Ensure port 3900 is not already in use:
```bash
lsof -i :3900
```

### Change storage size

Delete `garage/storage.conf` and rerun the script:
```bash
rm garage/storage.conf
uv run --with pyyaml --with questionary python garage/setup-garage.py
```

**Warning**: Changing storage size requires recreating the Garage cluster layout, which may temporarily disrupt S3 operations.

### Reset and start over

To completely reset Garage S3 setup:
```bash
# Stop and remove Garage
docker compose -f docker-compose-garage.yml down -v

# Remove configuration files
rm -rf garage/garage.toml garage/storage.conf

# Remove S3 credentials from .env (edit manually or use sed)
vi .env  # Remove S3_* lines

# Re-run the setup script
uv run --with pyyaml --with questionary python garage/setup-garage.py
```

## Security Notes

- **Garage ports** (3900, 3903) are bound to `127.0.0.1` by default for security
- **S3 credentials** are auto-generated with cryptographically secure random values
- **RPC secret** is auto-generated as a 64-byte hex string for cluster communication
- For production, consider using Docker secrets for additional credential protection

## Garage Version

This script uses **Garage v2.1.0**, the latest stable release. See [Garage documentation](https://garagehq.deuxfleurs.fr/) for details.

## Related Documentation

- [Garage Quick Start](https://garagehq.deuxfleurs.fr/documentation/quick-start/)
- [Garage Real-World Deployment](https://garagehq.deuxfleurs.fr/documentation/cookbook/real-world/)
- [S3 Blob Storage Architecture](../docs/vg/s3-blob-storage-architecture.md)
