import re

from hypothesis import given, strategies as st
from processor import parse_storage_quota, compute_compression_ratio, lookup_bandwidth_tier_rate


# ---------------------------------------------------------------------
# 1. "Must never crash" tests (random text and None as input)
# ---------------------------------------------------------------------

@given(st.text() | st.none())
def test_parse_storage_quota_no_crash(s):
    try:
        parse_storage_quota(s)
    except Exception as e:
        assert False, f"parse_storage_quota crashed with: {e!r}"


@given(st.text() | st.none())
def test_compute_compression_ratio_safe(s):
    try:
        compute_compression_ratio(s)
    except Exception as e:
        assert False, f"compute_compression_ratio crashed with: {e!r}"


@given(st.text() | st.none())
def test_lookup_bandwidth_tier_rate_safe(s):
    try:
        lookup_bandwidth_tier_rate(s)
    except Exception as e:
        assert False, f"lookup_bandwidth_tier_rate crashed with: {e!r}"


# ---------------------------------------------------------------------
# 2. Result-validity tests (no crash is not enough: results must make sense)
# ---------------------------------------------------------------------

@given(st.text() | st.none())
def test_parse_storage_quota_result_is_valid(s):
    # Either the error message or a non-negative number with 2 decimals
    result = parse_storage_quota(s)
    assert result == "Invalid quota" or re.fullmatch(r"Quota: \d+\.\d{2} GB", result), result


@given(st.text() | st.none())
def test_compression_ratio_result_is_finite_and_non_negative(s):
    result = compute_compression_ratio(s)
    assert result is None or (result >= 0 and result == result and result != float("inf")), result


@given(st.text() | st.none())
def test_lookup_rate_is_known_rate_or_none(s):
    assert lookup_bandwidth_tier_rate(s) in (None, 0.08, 0.05, 0.02)


# ---------------------------------------------------------------------
# 3. Valid inputs must still work after hardening
# ---------------------------------------------------------------------

MULTIPLIERS = {"MB": 0.001, "GB": 1.0, "TB": 1000.0}


@given(st.integers(min_value=0, max_value=10**6), st.sampled_from(["MB", "GB", "TB"]))
def test_parse_storage_quota_valid_inputs(value, unit):
    assert parse_storage_quota(f"{value}{unit}") == f"Quota: {value * MULTIPLIERS[unit]:.2f} GB"


@given(st.integers(min_value=1, max_value=10**9), st.integers(min_value=1, max_value=10**9))
def test_compression_ratio_valid_inputs(raw, comp):
    assert compute_compression_ratio(f"{raw}:{comp}") == round(raw / comp, 2)


@given(st.sampled_from(["HOT", "COL", "ARC"]), st.text())
def test_lookup_rate_valid_prefixes(prefix, suffix):
    expected = {"HOT": 0.08, "COL": 0.05, "ARC": 0.02}[prefix]
    assert lookup_bandwidth_tier_rate(prefix + suffix) == expected
