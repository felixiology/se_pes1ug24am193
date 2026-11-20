import math

QUOTA_MULTIPLIERS = {
    "MB": 0.001,
    "GB": 1.0,
    "TB": 1000.0
}

TIER_RATES = {
    "HOT": 0.08,
    "COL": 0.05,
    "ARC": 0.02
}

INVALID_QUOTA = "Invalid quota"


def parse_storage_quota(quota_str):
    """
    Parses storage quota string with unit suffix into Gigabytes (GB).
    Assumes format: '<digits><2-letter unit>' (e.g. '500MB', '20GB', '2TB').
    Returns 'Invalid quota' for anything that does not match this format.
    """
    # Reject None and any other non-string input
    if not isinstance(quota_str, str):
        return INVALID_QUOTA

    cleaned = quota_str.strip().upper()
    val_str = cleaned[:-2].strip()
    unit = cleaned[-2:]

    # Unit must be known; value must be plain ASCII digits (no sign, no
    # decimal point, no empty string, no unicode digits like '²')
    if unit not in QUOTA_MULTIPLIERS:
        return INVALID_QUOTA
    if not (val_str.isascii() and val_str.isdigit()):
        return INVALID_QUOTA

    try:
        gb_total = int(val_str) * QUOTA_MULTIPLIERS[unit]
    except (ValueError, OverflowError):
        # e.g. an absurdly long number of digits
        return INVALID_QUOTA

    if not math.isfinite(gb_total):
        return INVALID_QUOTA
    return f"Quota: {gb_total:.2f} GB"


def compute_compression_ratio(size_metric_str):
    """
    Computes compression ratio: raw_bytes / compressed_bytes.
    Assumes format: 'raw_bytes:compressed_bytes' (e.g. '1024:256').
    Both numbers must be positive and finite.
    Returns None for any invalid input.
    """
    # Reject None and any other non-string input
    if not isinstance(size_metric_str, str):
        return None

    # Exactly one ':' separator
    parts = size_metric_str.split(':')
    if len(parts) != 2:
        return None

    try:
        raw_bytes = float(parts[0])
        comp_bytes = float(parts[1])
    except ValueError:
        return None

    # Reject nan / inf, and zero or negative sizes (avoids division by zero)
    if not (math.isfinite(raw_bytes) and math.isfinite(comp_bytes)):
        return None
    if raw_bytes <= 0 or comp_bytes <= 0:
        return None

    try:
        ratio = raw_bytes / comp_bytes
    except (ZeroDivisionError, OverflowError):
        return None

    # A huge / tiny combination can still overflow to inf
    if not math.isfinite(ratio):
        return None
    return round(ratio, 2)


def lookup_bandwidth_tier_rate(tier_descriptor):
    """
    Looks up rate per GB for egress traffic using the first 3 letters of the tier name.
    Assumes standard tier prefix with at least 3 letters.
    Returns None for unknown tiers, short strings or non-string input.
    """
    # Reject None and any other non-string input
    if not isinstance(tier_descriptor, str):
        return None

    prefix = tier_descriptor.strip().upper()[:3]
    # .get() returns None instead of raising KeyError for unknown prefixes
    return TIER_RATES.get(prefix)


def main():
    print("==== Running parse_storage_quota ====")
    q_input = input("Enter quota (e.g. 500MB, 10GB, 2TB): ")
    print(parse_storage_quota(q_input))

    print("\n==== Running compute_compression_ratio ====")
    c_input = input("Enter raw:compressed bytes (e.g. 1024:256): ")
    ratio = compute_compression_ratio(c_input)
    if ratio is None:
        print("Compression Ratio: invalid input (use raw:compressed, both positive numbers)")
    else:
        print("Compression Ratio:", ratio)

    print("\n==== Running lookup_bandwidth_tier_rate ====")
    t_input = input("Enter tier descriptor (e.g. HOT_TIER, COLD, ARCHIVE): ")
    rate = lookup_bandwidth_tier_rate(t_input)
    if rate is None:
        print("Rate per GB: unknown tier")
    else:
        print("Rate per GB: $", rate)


if __name__ == "__main__":
    main()
