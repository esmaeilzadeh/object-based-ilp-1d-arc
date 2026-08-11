from solver.run_meta import collect_run_meta, mark_finished, slim_meta


def test_collect_run_meta_has_required_keys():
    meta = collect_run_meta(mode="block_primary", timeout=60, jobs=2, trials="0,1,2")
    for key in (
        "schema",
        "started_at",
        "git_sha",
        "git_branch",
        "git_dirty",
        "hostname",
        "platform",
        "mode",
        "timeout",
        "jobs",
        "trials",
    ):
        assert key in meta
    assert meta["schema"] == "eval-run-meta/v1"
    assert meta["mode"] == "block_primary"
    assert meta["timeout"] == 60
    assert meta["finished_at"] is None


def test_mark_finished_sets_timestamp():
    meta = collect_run_meta(mode="block_primary", timeout=1)
    done = mark_finished(meta)
    assert done["finished_at"]
    assert meta["finished_at"] is None


def test_slim_meta_subset():
    meta = collect_run_meta(mode="block_primary", timeout=60, jobs=1)
    slim = slim_meta(meta)
    assert set(slim) <= set(meta)
    assert slim["mode"] == "block_primary"
