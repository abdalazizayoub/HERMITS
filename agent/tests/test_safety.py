import pytest

from components.services.safety import SafetyLayer


@pytest.fixture
def safety():
    return SafetyLayer()


# --- Blocked patterns ---

def test_rm_rf_system_path_blocked(safety):
    result = safety.check("rm -rf /etc/nginx")
    assert result.safe is False
    assert "system path" in result.reason


def test_rm_rf_var_log_allowed(safety):
    result = safety.check("rm -rf /var/log/nginx/access.log")
    assert result.safe is True


def test_rm_rf_tmp_allowed(safety):
    result = safety.check("rm -rf /tmp/cache")
    assert result.safe is True


def test_rm_rf_var_cache_allowed(safety):
    result = safety.check("rm -rf /var/cache/apt/archives")
    assert result.safe is True


def test_dd_write_to_device_blocked(safety):
    result = safety.check("dd if=/dev/zero of=/dev/sda")
    assert result.safe is False
    assert "device" in result.reason


def test_mkfs_blocked(safety):
    result = safety.check("mkfs.ext4 /dev/sdb1")
    assert result.safe is False


def test_direct_block_device_write_blocked(safety):
    result = safety.check("echo data > /dev/sda")
    assert result.safe is False


def test_chmod_777_recursive_root_blocked(safety):
    result = safety.check("chmod -R 777 /")
    assert result.safe is False


def test_chmod_777_system_dir_blocked(safety):
    result = safety.check("chmod 777 /etc")
    assert result.safe is False
    result2 = safety.check("chmod 777 /var")
    assert result2.safe is False


def test_drop_table_blocked(safety):
    result = safety.check("psql -c 'DROP TABLE users'")
    assert result.safe is False


def test_drop_database_blocked(safety):
    result = safety.check("DROP DATABASE mydb")
    assert result.safe is False


def test_shutdown_blocked(safety):
    result = safety.check("shutdown -h now")
    assert result.safe is False


def test_reboot_blocked(safety):
    result = safety.check("reboot")
    assert result.safe is False


def test_halt_blocked(safety):
    result = safety.check("halt")
    assert result.safe is False


def test_ufw_disable_blocked(safety):
    result = safety.check("ufw disable")
    assert result.safe is False


def test_iptables_flush_blocked(safety):
    result = safety.check("iptables -F")
    assert result.safe is False


def test_disable_fail2ban_blocked(safety):
    result = safety.check("systemctl disable fail2ban")
    assert result.safe is False


def test_deleting_etc_blocked(safety):
    result = safety.check("rm -r /etc/nginx")
    assert result.safe is False


def test_reading_pem_key_blocked(safety):
    result = safety.check("cat /etc/ssl/private/server.pem")
    assert result.safe is False


def test_reading_private_key_blocked(safety):
    result = safety.check("cat /home/user/.ssh/id_rsa.key")
    assert result.safe is False


# --- Secret detection ---

def test_hardcoded_password_blocked(safety):
    result = safety.check("mysql -u root -pMySecret123 -e 'show databases'")
    assert result.safe is False
    assert "secret" in result.reason.lower()


def test_token_equals_value_blocked(safety):
    result = safety.check("curl -H 'Authorization: token=abc123xyz' https://api.example.com")
    assert result.safe is False


def test_variable_reference_allowed(safety):
    result = safety.check("curl -H \"Authorization: Bearer $TOKEN\" https://api.example.com")
    assert result.safe is True


# --- Safe commands ---

def test_systemctl_restart_allowed(safety):
    result = safety.check("systemctl restart nginx")
    assert result.safe is True


def test_curl_health_check_allowed(safety):
    result = safety.check("curl -sf http://localhost/health")
    assert result.safe is True


def test_journalctl_allowed(safety):
    result = safety.check("journalctl -u nginx --since '1 hour ago'")
    assert result.safe is True


def test_df_allowed(safety):
    result = safety.check("df -h /var/lib/postgresql")
    assert result.safe is True
