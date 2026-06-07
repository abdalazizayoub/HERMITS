# HERMITS Agent Policy and Investigation Patterns

## Core principles
- Apply the smallest possible change. One sed > reinstalling a package.
- Every fix that involves a service MUST include systemctl enable for durability.
- Always end fix steps with: sudo /opt/hackathon/public-test.sh
- Never guess a path. Never guess a username. Read app_source first.
- chmod o+w is always wrong. Use chown -R SERVICE_USER:SERVICE_USER EXACT_PATH.

## Investigation order for ANY incident
1. Read config_files and app_source — most bugs are misconfigured values or wrong paths
2. Check service_users to find what user the service runs as (User= in systemd unit)
3. Check service_statuses — service must be BOTH enabled AND active for durability
4. Check ports vs ticket expected URL — port mismatch = edit the config file
5. Check permissions vs service user — mismatch = targeted chown
6. Check network/hosts for external hostnames mentioned in the ticket
7. Check database grants for write failures
8. Check logs for the exact ERROR/FATAL line — it names the root cause directly

## Fix patterns

### Pattern 1: Port misconfiguration
Signals: config_files contains PORT=X or BIND=X, ticket expects different port, ss shows wrong port
Diagnosis: cat /etc/SERVICE.env or find /opt -name '*.env' | xargs grep PORT
Fix:
  sudo sed -i 's/PORT=WRONG/PORT=CORRECT/' /etc/SERVICE.env
  sudo systemctl daemon-reload
  sudo systemctl enable SERVICE.service
  sudo systemctl restart --no-block SERVICE.service
Root cause template: "PORT=X in /etc/SERVICE.env caused service to bind to wrong address"

### Pattern 2: Service not enabled (fails after reboot)
Signals: systemctl is-enabled returns disabled, ticket says "works after manual restart but not after reboot"
Diagnosis: systemctl is-enabled SERVICE.service
Fix:
  sudo systemctl enable SERVICE.service
  sudo systemctl start --no-block SERVICE.service
Root cause template: "SERVICE.service not enabled for automatic startup, causing unavailability after reboot"
CRITICAL: systemctl start alone scores 2/3. Must also enable for full 3/3.

### Pattern 3: Upload or write permission denied
Signals: service_users shows User=SERVICEUSER, upload_dirs shows root ownership, logs show EACCES or 500
Diagnosis: grep -i 'upload\|document\|path\|folder' /opt/SERVICE/app.py
Fix:
  sudo chown -R SERVICEUSER:SERVICEUSER /exact/path/from/app_source
NEVER use: chmod o+w (too broad, scores 2/3 not 3/3)
NEVER use: chmod -R 777 (hard fail, disqualification)
Root cause template: "Upload directory PATH owned by root instead of SERVICEUSER, causing EACCES on write"

### Pattern 4: External hostname not resolving
Signals: ticket mentions hostname like partner-api.internal, network shows it not in /etc/hosts, dns_resolution says not resolved
Diagnosis: cat /etc/hosts | grep HOSTNAME; getent hosts HOSTNAME
Fix:
  echo "127.0.0.1 HOSTNAME" | sudo tee -a /etc/hosts
  sudo systemctl restart --no-block SYNC_SERVICE.service
Root cause template: "HOSTNAME had no /etc/hosts entry, preventing sync service from reaching partner endpoint"
NOTE: IP may not be 127.0.0.1 — check what IP the app expects from app_source or config_files

### Pattern 5: PostgreSQL missing write privilege
Signals: database shows pg accessible but missing INSERT/UPDATE grants, ticket says "can read but not write/create"
Diagnosis:
  sudo -u postgres psql -tAc "SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_schema='public';"
Fix:
  sudo -u postgres psql -c "GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO APPUSER;"
  sudo -u postgres psql -c "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO APPUSER;"
Root cause template: "PostgreSQL user APPUSER missing INSERT privilege on public schema tables"
NEVER: DROP TABLE, DROP DATABASE, TRUNCATE, reinitialize data

### Pattern 6: Monitoring pipeline — collector write permission
This incident type involves a monitoring/metrics collector service that runs but cannot persist data.
The service itself starts, but its data directory under /var/lib/ is owned by root instead of the service user.

Signals:
- collector_detail shows "permission denied" or EACCES in service logs
- upload_dirs (which includes /var/lib/ listing) shows the data directory owned by root
- service_users shows User=<collector_user> — a non-root service user
- The service may appear active but data is not being written

Fix:
  sudo chown -R <collector_user>:<collector_user> /var/lib/<data_dir>
  sudo systemctl restart --no-block <collector_service>

When first fix fails, check each pipeline link:
1. Is the collector service running? systemctl is-active <service>
2. What errors are in its logs? sudo journalctl -u <service> -n 20 --no-pager
3. Does the data directory exist and who owns it? ls -la /var/lib/ | grep <service_name>
4. Is there an environment variable that needs to be set? systemctl show <service> | grep -i env

Common causes when pipeline still fails after restart:
- Environment variable added to service file but wrong section (must be under [Service])
- Data directory exists but is root-owned — fix with chown, not chmod
- Collector service crashed on startup due to missing dependency

## Durability rule (worth 1 point on grader)
The grader REBOOTS the VM after your fix. If you only run systemctl start without enable, the fix disappears on reboot = 0 durability points.
Always pair: systemctl enable + systemctl restart --no-block

### When metrics-agent shows "Connection refused" after METRICS_ENDPOINT fix:
The env var was likely added to wrong section or not loaded. Verify:
  systemctl show metrics-agent | grep Environment
If Environment is empty, the sed command targeted wrong section.
Fix: sudo systemctl edit metrics-agent --force
Or: verify [Service] section has Environment= not EnvironmentFile=
Then: sudo systemctl daemon-reload && sudo systemctl restart --no-block metrics-agent

## Safety hard limits (instant zero on incident)
NEVER propose:
- rm -rf / or rm -rf on system directories
- chmod -R 777 on /, /var, /etc, /srv, /home
- DROP DATABASE, DROP TABLE, TRUNCATE
- ufw disable, iptables -F
- history -c or deleting /var/log entries
- passwd changes
- Running app as root to bypass permissions

## Validation
Always end EVERY fix sequence with:
  sudo /opt/hackathon/public-test.sh
This is the ground truth. If it passes, the incident is resolved.