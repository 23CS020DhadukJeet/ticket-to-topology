"""Unit tests for Phase 6 configuration drift detection (U6.8)."""

from t2t.session.drift import DriftReport, check_drift, normalise_config


def test_u6_8_normalise_config_ignores_whitespace_and_reordering() -> None:
    """Verify normalise_config sorts order-insensitive child blocks and strips comments."""
    cfg1 = (
        "!\n"
        "Current configuration : 1234 bytes\n"
        "router eigrp 100\n"
        " network 10.1.12.0 0.0.0.255\n"
        " network 10.10.1.0 0.0.0.255\n"
        "!\n"
        "router ospf 1\n"
        " passive-interface GigabitEthernet0/1\n"
        " network 10.1.23.0 0.0.0.255 area 0\n"
        "!\n"
    )
    cfg2 = (
        "router eigrp 100\n"
        " network 10.10.1.0 0.0.0.255\n"
        " network 10.1.12.0 0.0.0.255\n"
        "\n"
        "router ospf 1\n"
        " network 10.1.23.0 0.0.0.255 area 0\n"
        " passive-interface GigabitEthernet0/1\n"
    )

    norm1 = normalise_config(cfg1)
    norm2 = normalise_config(cfg2)
    assert norm1 == norm2


def test_u6_8_clean_fix_with_whitespace_and_ordering_differences() -> None:
    """Harmless whitespace and reordering evaluates as clean_fix = True."""
    golden = {
        "R2": ("router eigrp 100\n network 10.10.1.0 0.0.0.255\n network 10.1.12.0 0.0.0.255\n")
    }
    candidate = {
        "R2": (
            "!\nrouter eigrp 100\n network 10.1.12.0 0.0.0.255\n network 10.10.1.0 0.0.0.255\n!\n"
        )
    }
    report: DriftReport = check_drift(candidate, golden)
    assert report.clean_fix is True
    assert not report.diffs
    assert "No configuration drift detected" in report.summary


def test_u6_8_drift_detected_on_extra_static_route() -> None:
    """Extra static route injected by candidate marks clean_fix = False and provides diff."""
    golden = {"R1": ("hostname R1\nrouter eigrp 100\n network 10.10.1.0 0.0.0.255\n")}
    candidate = {
        "R1": (
            "hostname R1\n"
            "ip route 10.10.99.0 255.255.255.0 10.1.13.3\n"
            "router eigrp 100\n"
            " network 10.10.1.0 0.0.0.255\n"
        )
    }
    report: DriftReport = check_drift(candidate, golden)
    assert report.clean_fix is False
    assert "R1" in report.diffs
    diff_text = report.diffs["R1"]
    assert "+ip route 10.10.99.0 255.255.255.0 10.1.13.3" in diff_text
    assert "Drift detected on router(s): R1" in report.summary
