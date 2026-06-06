import pytest
from app.ssh.safety import safety_check

# ── Hard fails — must be blocked ─────────────────────────────────────────────

def test_blocks_rm_rf_root():
    safe, reason, _ = safety_check("rm -rf /")
    assert not safe

def test_blocks_chmod_R_777():
    safe, reason, _ = safety_check("chmod -R 777 /var/www")
    assert not safe

def test_blocks_ufw_disable():
    safe, reason, _ = safety_check("ufw disable")
    assert not safe

def test_blocks_drop_database():
    safe, reason, _ = safety_check("DROP DATABASE production")
    assert not safe

def test_blocks_truncate_log():
    safe, reason, _ = safety_check("truncate /var/log/syslog")
    assert not safe

def test_blocks_history_clear():
    safe, reason, _ = safety_check("history -c")
    assert not safe

def test_blocks_chown_R_etc():
    safe, reason, _ = safety_check("chown -R www-data /etc")
    assert not safe

def test_blocks_chown_R_var():
    safe, reason, _ = safety_check("chown -R nobody /var")
    assert not safe

# ── Safe commands — must pass through ────────────────────────────────────────

def test_allows_df():
    safe, _, _ = safety_check("df -h")
    assert safe

def test_allows_journalctl():
    safe, _, _ = safety_check("journalctl -p err -n 50 --no-pager")
    assert safe

def test_allows_systemctl_status():
    safe, _, _ = safety_check("systemctl status mysql")
    assert safe

def test_allows_systemctl_restart():
    safe, _, _ = safety_check("systemctl restart nginx")
    assert safe

def test_allows_systemctl_enable():
    safe, _, _ = safety_check("systemctl enable myapp")
    assert safe

def test_allows_scoped_chown():
    safe, _, _ = safety_check("chown www-data:www-data /var/www/uploads")
    assert safe

def test_allows_chmod_specific():
    safe, _, _ = safety_check("chmod 755 /opt/myapp")
    assert safe

def test_allows_public_test():
    safe, _, _ = safety_check("sudo /opt/hackathon/public-test.sh")
    assert safe

# ── Warnings — safe but flagged ───────────────────────────────────────────────

def test_warns_systemctl_stop():
    safe, _, warnings = safety_check("systemctl stop nginx")
    assert safe
    assert len(warnings) > 0

def test_warns_reboot():
    safe, _, warnings = safety_check("reboot")
    assert safe
    assert len(warnings) > 0