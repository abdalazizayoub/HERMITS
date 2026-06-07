# Policy memory
_Apply standard Linux sysadmin best practices and minimal-change principles._

## Common Linux Misconfiguration Patterns

### Port misconfigurations
- If a service is running (visible in ps/processes) but the expected port is not in ss/ports output, always check EnvironmentFile entries in the systemd unit file.
- Command to find env file: `systemctl cat <service>.service | grep EnvironmentFile`
- Command to read it: `cat /etc/<service>.env`
- Fix: `sudo sed -i 's/PORT=<wrong>/PORT=<correct>/' /path/to/file && sudo systemctl restart <service>`
- This is a 2-command fix — never requires enable, never requires reinstall.

### Service not starting on boot
- Symptom: works after manual restart, fails after reboot
- Check: `systemctl is-enabled <service>`
- Fix: `sudo systemctl enable <service>`
- Always pair with start if not running: `sudo systemctl start <service>`

### Permission denied on uploads/writes
- Check directory ownership: `ls -la /path/to/dir`
- Fix: `sudo chown <service-user>:<service-user> /path/to/dir`
- Never use chmod -R 777 — use targeted chown instead.

### Service can read but not write to database
- Check PostgreSQL user privileges: `sudo -u postgres psql -c "\du"`
- Check if table exists: `sudo -u postgres psql -d <db> -c "\dt"`
- Fix missing privilege: `sudo -u postgres psql -c "GRANT INSERT ON <table> TO <user>;"`

### External service unreachable
- Check /etc/hosts for DNS overrides: `cat /etc/hosts | grep <hostname>`
- Check firewall rules: `sudo ufw status`
- Test connectivity: `curl -v http://<host>:<port>/ping`
- Fix missing hosts entry: `echo "<ip> <hostname>" | sudo tee -a /etc/hosts`

## Known incident patterns for this environment

### Pattern: Service on wrong port (ticket type: API unreachable)
Recon signal: ss -tulpn shows port X but ticket expects port Y, env file has wrong PORT=
Diagnostic: `systemctl cat customer-status.service | grep EnvironmentFile` then `cat /etc/customer-status.env`
Fix: `sudo sed -i 's/PORT=8008/PORT=8080/' /etc/customer-status.env && sudo systemctl daemon-reload && sudo systemctl restart --no-block customer-status.service`
Also check: `sudo systemctl enable customer-status.service` if not enabled

### Pattern: Upload directory wrong permissions (ticket type: permission denied)
Recon signal: ls -la on upload dir shows wrong owner, service runs as specific user
Diagnostic: `find /etc/systemd/system -name '*.service' | xargs grep -i user=` then `ls -la /var/www/uploads`
Fix: `sudo chown -R SERVICE_USER:SERVICE_USER /path/to/uploads`

### Pattern: Partner service DNS not resolving (ticket type: sync/partner unreachable)
Recon signal: `getent hosts partner-api.internal` returns nothing, /etc/hosts missing entry
Diagnostic: `cat /etc/hosts | grep partner` then `curl -v http://partner-api.internal/ping`
Fix: `echo "127.0.0.1 partner-api.internal" | sudo tee -a /etc/hosts`

### Pattern: PostgreSQL missing write privilege (ticket type: DB read-only / insert fails)
Recon signal: pg_grants shows no INSERT privilege for app user on relevant tables
Diagnostic: `sudo -u postgres psql -c '\dp'` to check grants
Fix: `sudo -u postgres psql -c "GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO APP_USER;"`

### Pattern: Monitoring collector not running (ticket type: dashboard no data)
Recon signal: collector/metrics service inactive or missing in systemctl, no recent data
Diagnostic: `systemctl status COLLECTOR.service`
Fix: `sudo systemctl enable --now COLLECTOR.service`
