import json
import os
import tempfile

import pytest

from components.services.trust_calibrator import TrustCalibrator
from components.models.hypothesis import FixStep


def make_calibrator(tmpdir: str) -> TrustCalibrator:
    tc = TrustCalibrator()
    # Override data dir via monkeypatching the DATA_DIR used in path construction
    import components.services.trust_calibrator as tc_mod
    tc_mod.DATA_DIR = tmpdir
    return tc


@pytest.fixture
def tmpdir_calibrator(tmp_path):
    import components.services.trust_calibrator as tc_mod
    original = tc_mod.DATA_DIR
    tc_mod.DATA_DIR = str(tmp_path)
    yield TrustCalibrator()
    tc_mod.DATA_DIR = original


def test_record_and_classify(tmpdir_calibrator):
    tc = tmpdir_calibrator
    tc.record_decision("tech1", "systemctl restart nginx", approved=True)
    tc.record_decision("tech1", "systemctl restart nginx", approved=True)
    tc.record_decision("tech1", "systemctl restart nginx", approved=False)

    summary = tc.get_trust_summary("tech1")
    cat = summary["systemctl_restart"]
    assert cat["approved"] == 2
    assert cat["rejected"] == 1
    assert abs(cat["approval_rate"] - 2 / 3) < 1e-9


def test_classify_other():
    tc = TrustCalibrator()
    assert tc.classify("echo hello") == "other"


def test_classify_apt_install():
    tc = TrustCalibrator()
    assert tc.classify("apt-get install -y curl") == "apt_install"


def test_reorder_low_trust_moves_to_end(tmpdir_calibrator):
    tc = tmpdir_calibrator
    # Record 4 rejections for disk_cleanup to make rate < 0.4 with > 3 decisions
    for _ in range(4):
        tc.record_decision("tech1", "find /var/log -delete", approved=False)

    steps = [
        FixStep(command="find /var/log -delete", rationale="clean logs", risk_level="high"),
        FixStep(command="systemctl restart nginx", rationale="restart", risk_level="low"),
    ]
    reordered = tc.reorder_fix_steps("tech1", steps)
    # disk_cleanup with 0% approval rate should be last
    assert reordered[-1].command == "find /var/log -delete"


def test_high_risk_category_demoted_below_50_pct(tmpdir_calibrator):
    tc = tmpdir_calibrator
    # systemctl_stop: 1 approve, 3 reject → rate = 0.25 < 0.5
    tc.record_decision("tech1", "systemctl stop nginx", approved=True)
    for _ in range(3):
        tc.record_decision("tech1", "systemctl stop nginx", approved=False)

    steps = [
        FixStep(command="systemctl stop nginx", rationale="stop", risk_level="high"),
        FixStep(command="systemctl restart nginx", rationale="restart", risk_level="low"),
    ]
    reordered = tc.reorder_fix_steps("tech1", steps)
    assert reordered[-1].command == "systemctl stop nginx"


def test_unknown_category_keeps_order(tmpdir_calibrator):
    tc = tmpdir_calibrator
    steps = [
        FixStep(command="echo foo", rationale="first", risk_level="low"),
        FixStep(command="echo bar", rationale="second", risk_level="low"),
        FixStep(command="echo baz", rationale="third", risk_level="low"),
    ]
    reordered = tc.reorder_fix_steps("tech1", steps)
    # All unknown, all stay at 0.5, so original sort should be stable
    commands = [s.command for s in reordered]
    assert commands == ["echo foo", "echo bar", "echo baz"]
