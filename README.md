# OPNsense Network Dashboard

A Flask-based dashboard for monitoring OPNsense gateways, interface traffic, and HAProxy services.

## Features

- **Gateway Status** - Real-time gateway monitoring with RTT, loss, and active status
- **Interface Traffic** - WAN/WAN2 traffic cards with cumulative byte counts
- **Services** - HAProxy backend server health monitoring
- **Real-Time Traffic** - Live traffic chart (1-second resolution)
- **Traffic History** - Historical traffic graphs (1min, 5min, 1hr, 24hr resolutions)
- **Session-based Authentication** - Secure login with remember-me functionality

## Screenshots

The dashboard features a dark theme optimized for monitoring displays. Cards and charts adapt to screen size for desktop and mobile viewing.

## Prerequisites

- Python 3.8+
- OPNsense firewall with API access enabled
- HAProxy plugin (for services monitoring)

## Quick Start (Development)

### 1. Clone the repository

```bash
git clone git@github.com:MartialM1nd/opndash.git
cd opndash
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the example env file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# OPNsense connection
OPNSENSE_URL=https://your-opnsense-ip:10443
OPNSENSE_API_KEY=your_api_key
OPNSENSE_API_SECRET=your_api_secret
OPNSENSE_VERIFY_SSL=false  # Set to true if using valid certificates

# Dashboard authentication
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your_secure_password

# Session security (generate a long random string)
SECRET_KEY=your-secret-key-here
```

### 5. Get OPNsense API credentials

1. Log into OPNsense web interface
2. Navigate to **System > Access > Users**
3. Add a new user or edit existing
4. Generate API key/secret pair
5. Assign appropriate permissions (read-only is sufficient)

### 6. Run the development server

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## Production Deployment

### Using Gunicorn

Gunicorn is included in requirements.txt for production use.

```bash
# Basic usage
gunicorn app:app -b 0.0.0.0:5000

# With workers (recommended)
gunicorn app:app -b 0.0.0.0:5000 -w 4

# With Unix socket (for nginx)
gunicorn app:app -b unix:/tmp/opndash.sock -w 4
```

### Systemd Service Example

Create `/etc/systemd/system/opndash.service`:

```ini
[Unit]
Description=OPNsense Network Dashboard
After=network.target

[Service]
Type=notify
User=your-user
Group=your-group
WorkingDirectory=/path/to/opndash
Environment="PATH=/path/to/opndash/venv/bin"
ExecStart=/path/to/opndash/venv/bin/gunicorn app:app -b 127.0.0.1:5000 -w 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable opndash
sudo systemctl start opndash
```

### FreeBSD with rc.d Script

Create `/usr/local/etc/rc.d/opndash`:

```sh
#!/bin/sh
#
# PROVIDE: opndash
# REQUIRE: NETWORKING
# KEYWORD: shutdown

. /etc/rc.subr

name="opndash"
rcvar="${name}_enable"
command="/usr/home/USER/opndash/venv/bin/gunicorn"
command_args="app:app -b 127.0.0.1:5000 -w 4 --chdir /usr/home/USER/opndash"
pidfile="/var/run/${name}/${name}.pid"
start_cmd="${name}_start"
stop_cmd="${name}_stop"
status_cmd="${name}_status"

opndash_start() {
    echo "Starting ${name}..."
    mkdir -p /var/run/${name}
    cd /usr/home/USER/opndash
    /usr/home/USER/opndash/venv/bin/gunicorn app:app -b 127.0.0.1:5000 -w 4 --pid /var/run/${name}/${name}.pid
}

opndash_stop() {
    echo "Stopping ${name}..."
    if [ -f /var/run/${name}/${name}.pid ]; then
        kill $(cat /var/run/${name}/${name}.pid)
        rm -f /var/run/${name}/${name}.pid
    fi
}

opndash_status() {
    if [ -f /var/run/${name}/${name}.pid ]; then
        echo "${name} is running as pid $(cat /var/run/${name}/${name}.pid)"
    else
        echo "${name} is not running"
    fi
}

load_rc_config ${name}
run_rc_command "$1"
```

Make executable and enable:

```bash
sudo chmod +x /usr/local/etc/rc.d/opndash
sudo sysrc opndash_enable=yes
sudo service opndash start
```

**Notes:**
- Replace `USER` with your actual username
- Adjust paths as needed for your installation
- The script uses Gunicorn with 4 workers
- For SSL/TLS, use a reverse proxy (see below)

### Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name dashboard.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL Certificates

For production, always use valid SSL certificates. Update `OPNSENSE_VERIFY_SSL=true` and ensure the certificate matches your OPNsense hostname.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPNSENSE_URL` | `https://10.10.5.1:10443` | OPNsense API URL |
| `OPNSENSE_API_KEY` | - | API key from OPNsense |
| `OPNSENSE_API_SECRET` | - | API secret from OPNsense |
| `OPNSENSE_VERIFY_SSL` | `false` | Verify SSL certificates |
| `DASHBOARD_USERNAME` | `admin` | Dashboard login username |
| `DASHBOARD_PASSWORD` | `changeme` | Dashboard login password |
| `SECRET_KEY` | `dev-secret-change-in-production` | Flask session secret |
| `REFRESH_INTERVAL` | `5` | Gateway/services refresh rate (seconds) |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard (requires login) |
| `/login` | GET/POST | Authentication |
| `/logout` | GET | End session |
| `/api/gateways` | GET | Gateway status data |
| `/api/traffic` | GET | Interface traffic data |
| `/api/traffic/history` | GET | Historical traffic (`?range=0/1/2/3`) |
| `/api/haproxy/services` | GET | HAProxy service status |

## File Structure

```
opndash/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore rules
├── scripts/
│   └── cpucoretemp.sh  # CPU temperature script (unused by default)
├── templates/
│   ├── dashboard.html  # Main dashboard page
│   └── login.html      # Login page
└── flask_session/      # Session data (gitignored)
```

## Security Notes

- Change default credentials before deployment
- Use a strong, random `SECRET_KEY` in production
- Consider restricting access via firewall or VPN
- Enable SSL verification in production
- The `.env` file contains sensitive credentials - never commit it

## Troubleshooting

**API returns 401 Unauthorized**
- Verify API key/secret are correct
- Check user has API access permissions in OPNsense

**Gateway uptime shows "-"**
- Uptime data is not available via the routing API endpoint used

**Charts not loading**
- Check browser console for JavaScript errors
- Verify Chart.js CDN is accessible

**Mobile layout issues**
- The dashboard adapts to screens 1008px and wider
- For smaller screens, horizontal scrolling is available for tables and charts

## License

MIT