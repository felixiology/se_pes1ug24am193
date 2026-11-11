"""Lab 6 - tests written to reach >= 90% BRANCH coverage of cloud_storage_tier.py.

Contains the line-coverage tests plus extra tests that exercise both the
True and False outcome of every decision (boundaries, defaults, resets).
"""
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


# ====================================================================
# Tests carried over from the line-coverage file
# ====================================================================

def test_single_active_hot_tenant():
    tenants = [make_tenant("hot", [{"size_gb": 100, "corrupted": False, "egress_gb": 50}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == 2.5
    assert result["status"] == "BILLED"


def test_invalid_tenants_not_a_list():
    with pytest.raises(ValueError):
        process_storage_tenants("not a list", 5.0)


def test_negative_support_fee():
    with pytest.raises(ValueError):
        process_storage_tenants([], -1.0)


def test_inactive_tenant_is_skipped():
    tenants = [make_tenant("hot", [{"size_gb": 100}], active=False)]
    result = process_storage_tenants(tenants, 10.0)
    assert result == {"total_billed": 0.0, "status": "ZERO_USAGE"}


def test_cool_tier_large_bucket_with_egress_and_vault():
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


def test_unknown_tier_is_flagged():
    tenants = [make_tenant("glacier", [{"size_gb": 100}])]
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


def test_empty_tenant_list_is_zero_usage():
    result = process_storage_tenants([], 10.0)
    assert result == {"total_billed": 0.0, "status": "ZERO_USAGE"}


def test_latency_no_data():
    assert monitor_replication_latency([]) == "NO_DATA"


def test_latency_sync_lag_alert():
    assert monitor_replication_latency([[100, 250, 300]]) == "SYNC_LAG_ALERT"


def test_latency_synced():
    assert monitor_replication_latency([[100, 150], [50, 60]]) == "SYNCED"


# ====================================================================
# Extra tests for branch coverage
# ====================================================================

# ---- input validation: each part of the "or" condition ----

def test_tenants_dict_instead_of_list_raises():
    with pytest.raises(ValueError):
        process_storage_tenants({"account_active": True}, 5.0)


def test_zero_support_fee_is_valid():
    # fee == 0 is NOT negative, so no error is raised
    assert process_storage_tenants([], 0)["status"] == "ZERO_USAGE"


# ---- default values when keys are missing ----

def test_missing_account_active_is_treated_as_inactive():
    tenants = [{"tier": "hot", "buckets": [{"size_gb": 100}]}]
    result = process_storage_tenants(tenants, 10.0)
    assert result["status"] == "ZERO_USAGE"


def test_missing_tier_defaults_to_hot():
    tenants = [{"account_active": True, "buckets": [{"size_gb": 100}]}]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(2.5)


def test_missing_buckets_with_backup_vault_charges_only_fee():
    tenants = [{"account_active": True, "tier": "hot", "has_backup_vault": True}]
    result = process_storage_tenants(tenants, 10.0)
    assert result == {"total_billed": 10.0, "status": "BILLED"}


def test_bucket_defaults_for_corrupted_and_egress():
    tenants = [make_tenant("hot", [{"size_gb": 100}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(2.5)


# ---- tier rates ----

def test_cool_tier_normal_bucket():
    tenants = [make_tenant("cool", [{"size_gb": 200}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(3.0)


def test_archive_tier_normal_bucket():
    tenants = [make_tenant("archive", [{"size_gb": 200}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(1.0)


# ---- boundary values ----

def test_bucket_exactly_500_gb_gets_no_discount():
    tenants = [make_tenant("hot", [{"size_gb": 500}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(12.5)


def test_bucket_501_gb_gets_discount_and_egress_101_is_charged():
    # 501 * 0.025 * 0.90 = 11.2725, egress (101 - 100) * 0.08 = 0.08
    tenants = [make_tenant("hot", [{"size_gb": 501, "egress_gb": 101}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(11.35)


def test_egress_exactly_100_gb_is_free():
    tenants = [make_tenant("hot", [{"size_gb": 100, "egress_gb": 100}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(2.5)


def test_negative_size_bucket_is_flagged():
    tenants = [make_tenant("hot", [{"size_gb": -5}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["status"] == "ZERO_USAGE"


# ---- corrupted buckets ----

def test_corrupted_hot_bucket_still_pays_egress():
    # corrupted bucket adds 0 storage cost, but egress (150 - 100) * 0.08 = 4.0 is billed
    tenants = [make_tenant("hot", [{"size_gb": 100, "corrupted": True, "egress_gb": 150}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(4.0)


def test_corrupted_archive_bucket_first_in_list():
    tenants = [make_tenant("archive", [{"size_gb": 50, "corrupted": True}])]
    result = process_storage_tenants(tenants, 10.0)
    assert result["status"] == "ZERO_USAGE"


# ---- backup vault True / False ----

def test_backup_vault_fee_added_to_normal_tenant():
    tenants = [make_tenant("hot", [{"size_gb": 100}], vault=True)]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(12.5)


# ---- multiple tenants ----

def test_multiple_tenants_are_summed_and_inactive_one_ignored():
    tenants = [
        make_tenant("hot", [{"size_gb": 100}]),
        make_tenant("cool", [{"size_gb": 100}], active=False),
        make_tenant("archive", [{"size_gb": 100}]),
    ]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == pytest.approx(3.0)


# ---- audit threshold boundary (flagged > 4) ----

def test_exactly_four_flagged_buckets_is_not_audit_flagged():
    buckets = [{"size_gb": 0} for _ in range(4)] + [{"size_gb": 100}]
    tenants = [make_tenant("hot", buckets)]
    result = process_storage_tenants(tenants, 10.0)
    assert result["status"] == "BILLED"
    assert result["total_billed"] == pytest.approx(2.5)


def test_flagged_buckets_across_tenants_accumulate():
    tenants = [
        make_tenant("glacier", [{"size_gb": 100}]),
        make_tenant("glacier", [{"size_gb": 100}]),
        make_tenant("glacier", [{"size_gb": 100}]),
        make_tenant("hot", [{"size_gb": 0}, {"size_gb": 0}]),
    ]
    result = process_storage_tenants(tenants, 10.0)
    assert result["status"] == "AUDIT_FLAGGED"
    assert result["total_billed"] == 0.0


# ---- monitor_replication_latency: more branches ----

def test_latency_none_is_no_data():
    assert monitor_replication_latency(None) == "NO_DATA"


def test_latency_single_spike_is_not_an_alert():
    assert monitor_replication_latency([[250]]) == "SYNCED"


def test_latency_streak_resets_after_normal_reading():
    assert monitor_replication_latency([[250, 100, 250]]) == "SYNCED"


def test_latency_exactly_200_is_not_lag():
    assert monitor_replication_latency([[200, 200, 200]]) == "SYNCED"


def test_latency_alert_found_on_second_node():
    assert monitor_replication_latency([[10, 20], [300, 400]]) == "SYNC_LAG_ALERT"


def test_latency_streak_does_not_carry_between_nodes():
    assert monitor_replication_latency([[10, 250], [250, 10]]) == "SYNCED"


def test_latency_node_with_no_readings():
    assert monitor_replication_latency([[]]) == "SYNCED"
