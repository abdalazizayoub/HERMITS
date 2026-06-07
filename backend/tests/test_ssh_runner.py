from servers.ssh import runner


def test_build_recon_commands_uses_postgres_hints():
    commands = runner._build_recon_commands(service_hint="postgresql", ticket_text="")
    assert "pg_users" in commands
    assert "pg_grants" in commands
    assert "pg_seq_grants" in commands
    assert "pg_databases" in commands
    assert "app_configs" not in commands


def test_build_recon_commands_uses_web_hints():
    commands = runner._build_recon_commands(service_hint="nginx", ticket_text="")
    assert "app_configs" in commands
    assert "upload_dirs" in commands
    assert "port_mismatch" in commands


def test_build_recon_commands_no_hint_uses_default_subset():
    commands = runner._build_recon_commands(service_hint="", ticket_text="")
    assert "app_configs" in commands
    assert "upload_dirs" in commands
    assert "listening_ports" in commands
    assert "port_mismatch" in commands
