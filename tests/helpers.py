def assert_no_overlaps(blocks):
    ordered = sorted(blocks, key=lambda b: b.start_time)
    for prev, nxt in zip(ordered, ordered[1:]):
        assert prev.end_time <= nxt.start_time, (
            f"overlap: {prev.ref_type}#{prev.ref_id} [{prev.start_time}-{prev.end_time}] "
            f"vs {nxt.ref_type}#{nxt.ref_id} [{nxt.start_time}-{nxt.end_time}]"
        )


def total_minutes(blocks):
    return sum((b.end_time - b.start_time).total_seconds() / 60 for b in blocks)
