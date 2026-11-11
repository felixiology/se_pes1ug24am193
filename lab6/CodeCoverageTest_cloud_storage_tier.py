"""Lab 6 - tests written to reach >= 90% LINE coverage of cloud_storage_tier.py."""
import pytest
from cloud_storage_tier import process_storage_tenants, monitor_replication_latency


def make_tenant(tier="hot", buckets=None, vault=False, active=True):
    """Small helper to build a tenant dictionary."""
    return {
        "account_active": active,
        "tier": tier,
        "has_backup_vault": vault,
        "buckets": buckets if buckets is not None else [],
    }


# ---------- process_storage_tenants ----------

def test_single_active_hot_tenant():
    # Starter test: normal hot bucket, no discount, no egress charge
    tenants = [make_tenant("hot", [{"size_gb": 100, "corrupted": False, "egress_gb": 50}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == 2.5
    assert result["status"] == "BILLED"


def test_invalid_tenants_not_a_list():
    with pytest.raises(ValueError):
        process_storage_tenants("not a list", 5.0)






def test_cool_tier_large_bucket_with_egress_and_vault():
    # 1000 GB * 0.015 = 15.0, 10% discount -> 13.5
    # egress 150 GB -> (150 - 100) * 0.08 = 4.0, vault fee = 10.0
    tenants = [
        make_tenant(
            "cool",
            [{"size_gb": 1000, "corrupted": False, "egress_gb": 150}],
            vault=True,
        )
    ]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(27.5)
    assert result["status"] == "BILLED"


def test_archive_tier_corrupted_bucket_resets_charge():
    # First bucket adds 100 * 0.005 = 0.5, then a corrupted archive bucket
    # resets the charge to 0 and stops. Only the vault fee (5.0) remains.
    tenants = [
        make_tenant(
            "archive",
            [
                {"size_gb": 100, "corrupted": False},
                {"size_gb": 50, "corrupted": True},
            ],
            vault=True,
        )
    ]
    result = process_storage_tenants(tenants, 5.0)
    assert result["total_billed"] == pytest.approx(5.0)
    assert result["status"] == "BILLED"


def test_hot_tier_corrupted_bucket_is_not_charged():
    tenants = [make_tenant("hot", [{"size_gb": 100, "corrupted": True}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result == {"total_billed": 0.0, "status": "ZERO_USAGE"}




def test_zero_size_bucket_is_flagged():
    tenants = [make_tenant("hot", [{"size_gb": 0}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result == {"total_billed": 0.0, "status": "ZERO_USAGE"}


def test_audit_flagged_when_more_than_four_flagged_buckets():
    bad_buckets = [{"size_gb": 0} for _ in range(5)]
    good_bucket = {"size_gb": 100}
    tenants = [make_tenant("hot", bad_buckets + [good_bucket])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["status"] == "AUDIT_FLAGGED"
    assert result["total_billed"] == pytest.approx(2.5)




# ---------- monitor_replication_latency ----------

def test_latency_no_data():
    assert monitor_replication_latency([]) == "NO_DATA"


def test_latency_sync_lag_alert():
    assert monitor_replication_latency([[100, 250, 300]]) == "SYNC_LAG_ALERT"

