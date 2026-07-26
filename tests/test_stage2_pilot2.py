"""Tests for the Stage 2 pilot round-2 driver (experiments/stage2_pilot2.py).

Deterministic, offline, no GPU, no corpus read. The end-to-end tests build a
complete synthetic round-1 directory plus a synthetic MediaSum record set in
``tmp_path``, then run build -> export-gate -> verify -> ingest-gate ->
finalize -> export-pred -> verify against it. The corpus fetch is injected, so
nothing here opens the 4.45 GB file or a socket.

The fixture deliberately includes a subject burned for Q-A and a pool answer
that IS quotable from the rendered grounding, because those are the two things
that must never reach a prompt.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from doppler import stage2_render as R  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P2 = _load("stage2_pilot2_under_test", ROOT / "experiments/stage2_pilot2.py")
P1 = P2.P1


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ---------------------------------------------------------------------------
# Small pure pieces
# ---------------------------------------------------------------------------


def test_the_blocked_clusters_are_the_test_cluster_plus_the_same_date_ones():
    split = {"test": {"cluster_id": "cl9"},
             "excluded_same_date": [{"cluster_id": "cl4",
                                     "reason": "shares_test_date"},
                                    {"cluster_id": "cl5"}]}
    assert P2.excluded_cluster_ids(split) == ["cl4", "cl5", "cl9"]


def test_a_split_with_no_same_date_exclusions_blocks_only_the_test_cluster():
    assert P2.excluded_cluster_ids({"test": {"cluster_id": "cl1"}}) == ["cl1"]


def test_set_names_cover_every_arm_and_variant_exactly_once():
    names = P2.pred_set_names()
    assert len(names) == len(P2.ARMS) * len(P2.VARIANTS) == len(set(names))
    assert "pred_zeroinfo_redacted_standard" in names


def _meta(correct=1, n=4):
    return {"idx": 0, "item_id": "C1:T:3", "canonical_id": "C1",
            "correct_index": correct, "n_options": n}


def test_the_gate_scores_an_argmax_hit_and_the_mass_on_the_true_option():
    got = P2.score_gate(_meta(correct=1),
                        "Reasoning here.\nA: 0.05 B: 0.85 C: 0.05 D: 0.05")
    assert got["parsed"] is True
    assert got["argmax_correct"] is True
    assert got["p_correct"] == pytest.approx(0.85)
    # margin = true option minus the best rival, which is what the gate turned on
    assert got["margin"] == pytest.approx(0.80)


def test_a_gate_miss_has_a_negative_margin():
    got = P2.score_gate(_meta(correct=1),
                        "A: 0.85 B: 0.05 C: 0.05 D: 0.05")
    assert got["margin"] == pytest.approx(-0.80)


def test_an_unparsed_gate_reply_has_no_margin():
    assert P2.score_gate(_meta(), "nothing here")["margin"] is None


def test_the_gate_scores_an_argmax_miss():
    got = P2.score_gate(_meta(correct=1),
                        "A: 0.85 B: 0.05 C: 0.05 D: 0.05")
    assert got["argmax_correct"] is False
    assert got["argmax_index"] == 0


def test_an_unparseable_gate_reply_is_recorded_not_guessed():
    got = P2.score_gate(_meta(), "I refuse to answer.")
    assert got["parsed"] is False
    assert got["argmax_correct"] is None


def test_a_missing_gate_completion_is_a_parse_failure():
    assert P2.score_gate(_meta(), None)["parsed"] is False


# ---------------------------------------------------------------------------
# Projection and sbatch
# ---------------------------------------------------------------------------


def _rows(n, words=500):
    return [{"prompt_words": words,
             "prompt_tokens_est": int(words * P2.TOKENS_PER_WORD),
             "max_output_tokens": P2.PREDICTION_MAX_OUTPUT_TOKENS,
             "item_id": f"i{k}", "arm": "twin_redacted"} for k in range(n)]


def test_both_phases_together_stay_under_the_abort_threshold():
    proj = P2.projection(_rows(10), _rows(100))
    assert proj["total_projected_node_hours"] < P2.PROJECTION_ABORT_NODE_HOURS
    assert proj["walltime_bounded_worst_case_node_hours"] < 1.5
    assert set(proj["jobs"]) == {"stage2_pilot2_gate", "stage2_pilot2_pred"}


def test_the_context_check_refuses_a_prompt_that_would_not_fit(monkeypatch):
    monkeypatch.setattr(P2, "MAX_MODEL_LEN", 128)
    with pytest.raises(SystemExit, match="does not fit"):
        P2.context_check(_rows(1, words=4000))


def test_the_gate_sbatch_asks_for_one_whole_node_and_the_debug_qos():
    text = P2.gate_sbatch(0.06)
    assert "--gpus-per-node=4" in text
    assert f"--qos={P2.GATE_QOS}" in text
    assert f"--account={P2.ACCOUNT}" in text
    assert "prompts_$f.jsonl" in text and '"gate"' in text
    assert "runs/stage2_pilot2" in text          # never round 1's directory


def test_the_prediction_sbatch_lists_all_ten_prompt_files_and_no_debug_qos():
    text = P2.pred_sbatch(0.08)
    for name in P2.pred_set_names():
        assert f'"{name}"' in text
    assert "--qos=" not in text
    assert "runs/stage2_pilot2" in text


# ---------------------------------------------------------------------------
# End to end on a synthetic round-1 directory
# ---------------------------------------------------------------------------

#: Disjoint filler vocabularies. Guard (a) refuses a grounding block sharing a
#: 10-word run with the true answer, so the fixture's grounding, its answers and
#: its pool answers must not collide by accident.
GROUND_FILLER = " ".join(f"gx{i}" for i in range(40))
ANSWER_FILLER = " ".join(f"ay{i}" for i in range(40))

#: Six, like the real draw: three with a wiki page, two long-tail, plus one
#: retained in place after being burned for Q-A. D1's loader refuses any other
#: shape, so the fixture has to be the real shape.
SUBJECTS = [
    ("C10001", "Zorvath Quilliman", "long-tail", 0, False),
    ("C10002", "Brastock Venneby", "long-tail", 1, True),      # burned for Q-A
    ("C10003", "Chalmot Drexworth", "has-page", 2, False),
    ("C10004", "Dornith Falquay", "long-tail", 3, False),
    ("C10005", "Ekwith Grumbold", "has-page", 4, False),
    ("C10006", "Fanther Holvist", "has-page", 5, False),
]
QA_SUBJECTS = [cid for cid, _n, _w, _p, burned in SUBJECTS if not burned]
DONORS = {cid: f"C2000{k + 1}" for k, (cid, *_r) in enumerate(SUBJECTS)}
DONOR_NAMES = {
    "C20001": "Ilvaro Jantwick", "C20002": "Kesmir Lundhaven",
    "C20003": "Morvath Nexbury", "C20004": "Orlaith Pruvane",
    "C20005": "Quenlow Rathmar", "C20006": "Suvrith Tolquist",
}

N_POOL_TRANSCRIPTS = 8


def _mk_turns(tid, n_pairs, who, filler):
    rows = []
    for k in range(n_pairs):
        rows.append({"transcript_id": tid, "turn_idx": 2 * k, "role": "host",
                     "speaker_label": "ANCHOR, host", "resolved_label": None,
                     "d32_program_host": None,
                     "text": f"Host question {k} on {tid}?"})
        rows.append({"transcript_id": tid, "turn_idx": 2 * k + 1,
                     "role": "guest", "speaker_label": who.upper(),
                     "resolved_label": None, "d32_program_host": None,
                     "text": f"Guest reply {k} from {tid}. {filler}"})
    return rows


def _write_person(base: Path, cid: str, name: str, n_items: int):
    base.mkdir(parents=True, exist_ok=True)
    grounding = _mk_turns(f"{cid}-G1", 4, name, GROUND_FILLER) \
        + _mk_turns(f"{cid}-G2", 4, name, GROUND_FILLER)
    (base / "grounding_turns.jsonl").write_text(
        "\n".join(json.dumps(r) for r in grounding) + "\n", encoding="utf-8")
    (base / "split.json").write_text(json.dumps({
        "canonical_id": cid, "canonical_name": name, "rule": "synthetic",
        "grounding": [
            {"cluster_id": "c1", "transcript_id": f"{cid}-G1",
             "date": "2011-01-01", "program": "PROG ONE", "title": "t1"},
            {"cluster_id": "c2", "transcript_id": f"{cid}-G2",
             "date": "2012-01-01", "program": "PROG TWO", "title": "t2"}],
        "test": {"cluster_id": "c3", "transcript_id": f"{cid}-T",
                 "date": "2013-01-01", "program": "PROG THREE", "title": "t3"},
        "excluded_same_date": [],
    }), encoding="utf-8")

    items = []
    for k in range(n_items):
        answer = f"True answer {k} for {cid}. {ANSWER_FILLER}"
        items.append({"item_id": f"{cid}:{cid}-T:{k}", "canonical_id": cid,
                      "transcript_id": f"{cid}-T", "q_turn_idx": k,
                      "question": f"{name}, what did you make of item {k}?",
                      "answer": answer, "answer_words": len(answer.split()),
                      "flags": []})
    (base / "qa_items.jsonl").write_text(
        "\n".join(json.dumps(r) for r in items) + ("\n" if items else ""),
        encoding="utf-8")


def _pool_record(cid, name, k):
    """One extra interview for the subject: an answer nothing else contains."""
    speakers = [name.upper()]
    utts = ["Thanks for having me."]
    for j in range(2):
        speakers.append("ANCHOR, host")
        utts.append(f"What did you conclude about matter {k} number {j}?")
        speakers.append(name.upper())
        utts.append("Pool answer. " + " ".join(
            f"pw{cid}n{k}s{j}t{i}" for i in range(40)))
    return {"id": f"{cid}-P{k}", "program": "PROG POOL", "date": "2010-01-01",
            "speaker": speakers, "utt": utts}


def _leaky_record(cid, name):
    """An interview whose answer IS the subject's rendered grounding text.

    The anti-leak rule has to throw this one out; without it in the fixture the
    rule is only tested in the unit file, never on the driver's real path.
    """
    return {"id": f"{cid}-LEAK", "program": "PROG LEAK", "date": "2010-01-01",
            "speaker": [name.upper(), "ANCHOR, host", name.upper()],
            "utt": ["Thanks for having me.",
                    "And what happened next in that room?",
                    f"Guest reply 0 from {cid}-G1. {GROUND_FILLER}"]}


@pytest.fixture
def rig(tmp_path, monkeypatch):
    root = tmp_path / "stage2_pilot"
    root.mkdir()
    (root / "dev_subjects.json").write_text(json.dumps({
        "seed": 47, "rule": "synthetic", "drawn_at": "2026-07-26",
        "n_eligible": 6,
        "subjects": [
            dict({"canonical_id": cid, "canonical_name": name,
                  "wiki_status": wiki, "shuffle_pos": pos},
                 **({"burned_for_qa": True} if burned else {}))
            for cid, name, wiki, pos, burned in SUBJECTS],
        "burned": [], "burned_for_qa": ["C10002"], "replacements": [],
    }), encoding="utf-8")
    for cid, name, _w, _p, _b in SUBJECTS:
        _write_person(root / "subjects" / cid, cid, name, 2)
    for cid, donor in DONORS.items():
        _write_person(root / "donors" / donor, donor, DONOR_NAMES[donor], 0)
    (root / "imposter_pairs.json").write_text(
        json.dumps({"method": "synthetic", "pairs": DONORS}), encoding="utf-8")

    def transcripts(cid):
        rows = [{"transcript_id": f"{cid}-T", "cluster_id": "c3",
                 "date": "2013-01-01", "program": "PROG THREE",
                 "substantive": True},
                {"transcript_id": f"{cid}-LEAK", "cluster_id": "cL",
                 "date": "2010-01-01", "program": "PROG LEAK",
                 "substantive": False}]
        rows += [{"transcript_id": f"{cid}-P{k}", "cluster_id": f"cp{k}",
                  "date": "2010-01-01", "program": "PROG POOL",
                  "substantive": k % 2 == 0}
                 for k in range(N_POOL_TRANSCRIPTS)]
        return rows

    rows = {cid: {"canonical_id": cid, "canonical_name": name,
                  "variants": [name], "transcripts": transcripts(cid)}
            for cid, name, _w, _p, _b in SUBJECTS}
    rows.update({d: {"canonical_id": d, "canonical_name": n, "variants": [n],
                     "transcripts": []} for d, n in DONOR_NAMES.items()})
    monkeypatch.setattr(P1, "pool_rows", lambda: rows)

    records = {}
    for cid, name, _w, _p, _b in SUBJECTS:
        for k in range(N_POOL_TRANSCRIPTS):
            records[f"{cid}-P{k}"] = _pool_record(cid, name, k)
        records[f"{cid}-LEAK"] = _leaky_record(cid, name)

    out = tmp_path / "stage2_pilot2"
    return Args(pilot1_dir=root, out_dir=out, floor=0.0, force=False,
                fetch_fn=lambda ids: {t: records[t] for t in ids
                                      if t in records},
                pre_gate=False, nodedir=None, skip_cost=True,
                records=records)


def _build(rig):
    assert P2.cmd_build(rig) == 0


def test_build_writes_a_pool_and_candidates_for_every_qa_subject(rig, capsys):
    _build(rig)
    summary = json.loads((rig.out_dir / "build_summary.json").read_text())
    assert summary["totals"]["subjects"] == 5          # the burned one is out
    assert summary["totals"]["items_built"] == 10      # 5 subjects x 2 items
    for cid in QA_SUBJECTS:
        base = rig.out_dir / "subjects" / cid
        assert (base / "answer_pool.jsonl").exists()
        assert (base / "candidates.jsonl").read_text().strip()


def test_the_burned_subject_never_gets_a_candidate_directory(rig):
    _build(rig)
    assert not (rig.out_dir / "subjects" / "C10002").exists()


def test_every_candidate_option_is_the_subjects_own_answer(rig):
    _build(rig)
    for cid in QA_SUBJECTS:
        for line in (rig.out_dir / "subjects" / cid
                     / "candidates.jsonl").read_text().splitlines():
            row = json.loads(line)
            assert {o["source_canonical_id"] for o in row["options"]} == {cid}
            assert row["options"][row["correct_index"]]["kind"] == "true"


def test_the_leaky_pool_answer_is_excluded_and_the_exclusion_is_counted(rig):
    _build(rig)
    summary = json.loads((rig.out_dir / "build_summary.json").read_text())
    per = {r["canonical_id"]: r for r in summary["per_subject"]}
    assert per["C10001"]["anti_leak_excluded"] >= 1
    excluded = [json.loads(l) for l in (rig.out_dir / "subjects/C10001"
                / "pool_excluded.jsonl").read_text().splitlines()]
    assert any(r["source_transcript_id"] == "C10001-LEAK" for r in excluded)
    pool = [json.loads(l) for l in (rig.out_dir / "subjects/C10001"
            / "answer_pool.jsonl").read_text().splitlines()]
    assert all(r["source_transcript_id"] != "C10001-LEAK" for r in pool)


def test_the_pool_never_contains_the_test_interview(rig):
    _build(rig)
    for cid in QA_SUBJECTS:
        pool = [json.loads(l) for l in (rig.out_dir / "subjects" / cid
                / "answer_pool.jsonl").read_text().splitlines()]
        assert all(r["source_transcript_id"] != f"{cid}-T" for r in pool)


def test_the_build_summary_carries_the_floor_sweep_and_the_upstream_digests(rig):
    _build(rig)
    summary = json.loads((rig.out_dir / "build_summary.json").read_text())
    sweep = summary["similarity_floor_sweep"]
    assert sweep["floors"][0] == "0.00"
    counts = [sweep["total"][f] for f in sweep["floors"]]
    assert counts == sorted(counts, reverse=True)
    assert summary["upstream_sha256"]["dev_subjects.json"]
    assert summary["cost_usd"] == 0.0


def test_export_gate_then_verify_round_trips(rig):
    _build(rig)
    assert P2.cmd_export_gate(rig) == 0
    doc = json.loads((rig.out_dir / "exports"
                      / "export_manifest_gate.json").read_text())
    assert doc["arm"] == "zeroinfo_redacted" and doc["variant"] == "standard"
    assert doc["files"]["gate"]["n_prompts"] == 10
    assert P2.cmd_verify(rig) == 0


def test_a_gate_prompt_carries_no_excerpts_and_no_name(rig):
    _build(rig)
    P2.cmd_export_gate(rig)
    prompts = [json.loads(l) for l in (rig.out_dir / "exports"
               / "prompts_gate.jsonl").read_text().splitlines()]
    for row in prompts:
        assert R.EXCERPTS_HEADER not in row["prompt"]
        assert "Zorvath" not in row["prompt"]
        assert "Quilliman" not in row["prompt"]


def test_export_gate_refuses_to_overwrite_without_force(rig):
    _build(rig)
    P2.cmd_export_gate(rig)
    with pytest.raises(SystemExit, match="already exists"):
        P2.cmd_export_gate(rig)
    rig.force = True
    assert P2.cmd_export_gate(rig) == 0


def test_verify_without_any_export_manifest_is_a_loud_failure(rig):
    _build(rig)
    with pytest.raises(SystemExit, match="no export manifest"):
        P2.cmd_verify(rig)


def test_export_pred_refuses_the_final_set_before_the_gate_has_run(rig):
    _build(rig)
    with pytest.raises(SystemExit, match="items_final.jsonl not found"):
        P2.cmd_export_pred(rig)


def _run_gate(rig, solved_idxs):
    """Fake a gate run: ``solved_idxs`` are the prompts the arm gets right."""
    P2.cmd_export_gate(rig)
    metas = [json.loads(l) for l in (rig.out_dir / "exports"
             / "meta_gate.jsonl").read_text().splitlines()]
    node = rig.out_dir.parent / "node"
    node.mkdir(parents=True, exist_ok=True)
    lines = []
    for meta in metas:
        c = int(meta["correct_index"])
        if meta["idx"] not in solved_idxs:
            c = (c + 1) % int(meta["n_options"])
        dist = [0.05] * 4
        dist[c] = 0.85
        lines.append(json.dumps({
            "idx": meta["idx"], "tokens_in": 400, "tokens_out": 40,
            "text": "A: %.2f B: %.2f C: %.2f D: %.2f" % tuple(dist)}))
    (node / "completions_gate.jsonl").write_text("\n".join(lines) + "\n",
                                                 encoding="utf-8")
    rig.nodedir = node
    assert P2.cmd_ingest_gate(rig) == 0


def test_the_gate_rejects_exactly_the_items_the_zero_info_arm_solved(rig):
    _build(rig)
    _run_gate(rig, solved_idxs={0, 2, 5})
    gate = json.loads((rig.out_dir / "gate_results.json").read_text())
    assert gate["n_candidates"] == 10
    assert gate["n_rejected"] == 3
    assert gate["pre_gate_zeroinfo_argmax_accuracy"] == pytest.approx(0.3)
    assert P2.cmd_finalize(rig) == 0
    final = [json.loads(l) for l in (rig.out_dir
             / "items_final.jsonl").read_text().splitlines()]
    assert len(final) == 7
    assert not (set(r["item_id"] for r in final)
                & set(gate["rejected_item_ids"]))


def test_the_full_two_phase_chain_exports_ten_sets_and_verifies(rig):
    _build(rig)
    _run_gate(rig, solved_idxs={0})
    P2.cmd_finalize(rig)
    assert P2.cmd_export_pred(rig) == 0
    doc = json.loads((rig.out_dir / "exports"
                      / "export_manifest_pred.json").read_text())
    assert doc["n_items"] == 9
    assert len(doc["files"]) == len(P2.ARMS) * len(P2.VARIANTS)
    for info in doc["files"].values():
        assert info["n_prompts"] == 9
    assert P2.cmd_verify(rig) == 0


def test_a_gate_that_solves_everything_leaves_no_items_to_predict(rig):
    _build(rig)
    _run_gate(rig, solved_idxs=set(range(10)))
    P2.cmd_finalize(rig)
    assert json.loads((rig.out_dir
                       / "finalize_summary.json").read_text())["n_final"] == 0
    with pytest.raises(SystemExit, match="no items to export"):
        P2.cmd_export_pred(rig)


def test_the_pre_gate_export_is_labelled_as_projection_only(rig):
    _build(rig)
    rig.pre_gate = True
    assert P2.cmd_export_pred(rig) == 0
    doc = json.loads((rig.out_dir / "exports"
                      / "export_manifest_pred.json").read_text())
    assert "PRE-GATE" in doc["item_source"]


def test_a_tampered_prompt_file_fails_verify(rig):
    _build(rig)
    P2.cmd_export_gate(rig)
    path = rig.out_dir / "exports" / "prompts_gate.jsonl"
    path.write_text(path.read_text() + json.dumps({"idx": 99, "prompt": "x"})
                    + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="sha256"):
        P2.cmd_verify(rig)


def test_bootstrap_writes_both_sbatch_files_and_a_config(rig):
    _build(rig)
    assert P2.cmd_bootstrap(rig) == 0
    assert (rig.out_dir / "stage2_pilot2_gate.sbatch").exists()
    assert (rig.out_dir / "stage2_pilot2_pred.sbatch").exists()
    config = json.loads((rig.out_dir / "config.json").read_text())
    assert config["confirmatory"] is False
    assert config["similarity_floor_applied_at_build"] == 0.0
    assert config["projection"]["total_projected_node_hours"] < 1.5
    man = json.loads((rig.out_dir / "manifest.json").read_text())
    assert set(man["jobs"]) == {"stage2_pilot2_gate", "stage2_pilot2_pred"}


def test_record_appends_a_job_id_and_a_status_to_the_manifest(rig):
    _build(rig)
    P2.cmd_bootstrap(rig)
    P2.cmd_record(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                       job_id="12345", status="submitted", node_hours=None,
                       note="synthetic", anomaly=None))
    man = json.loads((rig.out_dir / "manifest.json").read_text())
    entry = man["jobs"]["stage2_pilot2_gate"]
    assert entry["slurm_job_ids"] == ["12345"]
    assert entry["status"] == "submitted"


def test_round_two_never_writes_into_round_ones_directory(rig):
    before = sorted(p.name for p in rig.pilot1_dir.rglob("*"))
    _build(rig)
    P2.cmd_export_gate(rig)
    P2.cmd_bootstrap(rig)
    assert sorted(p.name for p in rig.pilot1_dir.rglob("*")) == before


# ---------------------------------------------------------------------------
# Billing from sacct, and the phase-2 ingest
# ---------------------------------------------------------------------------


SACCT_LINE = "50378388|COMPLETED|00:05:12|1|0:0\n"


def test_bill_takes_node_hours_from_sacct_not_from_a_wall_clock(rig,
                                                                monkeypatch):
    _build(rig)
    P2.cmd_bootstrap(rig)
    monkeypatch.setattr(P1, "run", lambda argv, check=True: SACCT_LINE)
    assert P2.cmd_bill(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                            job_id="50378388")) == 0
    man = json.loads((rig.out_dir / "manifest.json").read_text())
    entry = man["jobs"]["stage2_pilot2_gate"]
    # 00:05:12 = 312 s on 1 node -> 0.0867 node-hours.
    assert entry["actual_node_hours"] == pytest.approx(0.0867, abs=1e-4)
    assert entry["status"] == "completed"
    assert entry["sacct"][0]["alloc_nodes"] == 1
    assert P2.billed_node_hours(rig.out_dir, "stage2_pilot2_gate") == \
        pytest.approx(0.0867, abs=1e-4)


def test_bill_refuses_an_empty_sacct_reply(rig, monkeypatch):
    _build(rig)
    monkeypatch.setattr(P1, "run", lambda argv, check=True: "")
    with pytest.raises(SystemExit, match="sacct returned nothing"):
        P2.cmd_bill(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                         job_id="1"))


def test_the_sacct_number_wins_over_the_in_process_one_in_the_gate_ingest(
        rig, monkeypatch):
    _build(rig)
    P2.cmd_bootstrap(rig)
    monkeypatch.setattr(P1, "run", lambda argv, check=True: SACCT_LINE)
    P2.cmd_bill(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                     job_id="50378388"))
    _run_gate(rig, solved_idxs={0})
    node = rig.nodedir
    (node / "completions_gate.jsonl.summary.json").write_text(json.dumps({
        "engine_init_seconds": 10.0, "generation_wall_seconds": 2.0}),
        encoding="utf-8")
    P2.cmd_ingest_gate(rig)
    gate = json.loads((rig.out_dir / "gate_results.json").read_text())
    assert gate["node_hours_source"] == "sacct"
    assert gate["node_hours"] == pytest.approx(0.0867, abs=1e-4)
    assert gate["node_hours_in_process"] == pytest.approx(0.0033, abs=1e-4)


def _run_pred(rig, correct_arms=("twin_redacted",)):
    """Fake a phase-2 run: the named arms answer correctly, the rest do not."""
    node = rig.nodedir or (rig.out_dir.parent / "node")
    node.mkdir(parents=True, exist_ok=True)
    rig.nodedir = node
    for arm in P2.ARMS:
        for variant in P2.VARIANTS:
            name = P2.set_name(arm, variant)
            metas = [json.loads(l) for l in (rig.out_dir / "exports"
                     / f"meta_{name}.jsonl").read_text().splitlines()]
            lines = []
            for meta in metas:
                c = int(meta["correct_index"])
                if arm not in correct_arms:
                    c = (c + 1) % int(meta["n_options"])
                dist = [0.05] * 4
                dist[c] = 0.85
                lines.append(json.dumps({
                    "idx": meta["idx"], "tokens_in": 900, "tokens_out": 60,
                    "text": "A: %.2f B: %.2f C: %.2f D: %.2f" % tuple(dist)}))
            (node / f"completions_{name}.jsonl").write_text(
                "\n".join(lines) + "\n", encoding="utf-8")
            (node / f"completions_{name}.jsonl.summary.json").write_text(
                json.dumps({"engine_init_seconds": 200.0,
                            "generation_wall_seconds": 3.0}), encoding="utf-8")
    assert P2.cmd_ingest_pred(rig) == 0


def test_the_phase_two_ingest_scores_every_arm_and_writes_records(rig):
    _build(rig)
    _run_gate(rig, solved_idxs={0})
    P2.cmd_finalize(rig)
    P2.cmd_export_pred(rig)
    _run_pred(rig)
    analysis = json.loads((rig.out_dir / "analysis.json").read_text())
    assert analysis["n_records"] == 9 * len(P2.ARMS) * len(P2.VARIANTS)
    assert analysis["accuracy"]["standard"]["twin_redacted"]["n"] == 9
    assert analysis["accuracy"]["standard"]["twin_redacted"][
        "argmax_accuracy"] == 1.0
    assert analysis["accuracy"]["standard"]["imposter_redacted"][
        "argmax_accuracy"] == 0.0
    for arm in P2.ARMS:
        for variant in P2.VARIANTS:
            assert (rig.out_dir / "records"
                    / f"{P2.set_name(arm, variant)}.jsonl").exists()


def test_the_analysis_carries_the_pre_gate_number_and_the_by_construction_note(
        rig):
    _build(rig)
    _run_gate(rig, solved_idxs={0, 3})
    P2.cmd_finalize(rig)
    P2.cmd_export_pred(rig)
    _run_pred(rig)
    analysis = json.loads((rig.out_dir / "analysis.json").read_text())
    assert analysis["gate"]["pre_gate_zeroinfo_argmax_accuracy"] == \
        pytest.approx(0.2)
    assert analysis["gate"]["n_rejected"] == 2
    assert "BY CONSTRUCTION" in analysis["gate"]["note"]


def test_the_ingest_reports_lift_against_both_baselines_per_variant(rig):
    _build(rig)
    _run_gate(rig, solved_idxs={0})
    P2.cmd_finalize(rig)
    P2.cmd_export_pred(rig)
    _run_pred(rig)
    lift = json.loads((rig.out_dir / "analysis.json").read_text())["lift"]
    for variant in P2.VARIANTS:
        assert lift[variant]["twin_redacted_minus_zeroinfo_redacted"][
            "mean_argmax_delta"] == 1.0
        assert lift[variant]["twin_redacted_minus_imposter_redacted"][
            "mean_argmax_delta"] == 1.0


def test_a_missing_completion_file_is_recorded_not_silently_scored(rig):
    _build(rig)
    _run_gate(rig, solved_idxs={0})
    P2.cmd_finalize(rig)
    P2.cmd_export_pred(rig)
    _run_pred(rig)
    (rig.nodedir / "completions_pred_twin_named_stripped.jsonl").unlink()
    P2.cmd_ingest_pred(rig)
    analysis = json.loads((rig.out_dir / "analysis.json").read_text())
    assert analysis["n_missing_completions"] == 9
    assert analysis["accuracy"]["stripped"]["twin_named"]["n"] == 0


def test_skip_cost_writes_no_ledger_line(rig, monkeypatch):
    written = []
    monkeypatch.setattr(P2, "append_cost_log",
                        lambda entry, path: written.append(entry))
    _build(rig)
    _run_gate(rig, solved_idxs={0})          # rig.skip_cost is True
    P2.cmd_finalize(rig)
    P2.cmd_export_pred(rig)
    _run_pred(rig)
    assert written == []


def test_a_ledger_line_states_a_measured_zero_api_cost(rig, monkeypatch):
    written = []
    monkeypatch.setattr(P2, "append_cost_log",
                        lambda entry, path: written.append(entry))
    monkeypatch.setattr(P1, "run", lambda argv, check=True: SACCT_LINE)
    _build(rig)
    P2.cmd_bootstrap(rig)
    P2.cmd_bill(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                     job_id="50378388"))
    rig.skip_cost = False
    _run_gate(rig, solved_idxs={0})
    assert len(written) == 1
    entry = written[0]
    assert entry["cost_usd"] == 0.0          # measured, not unknown
    assert entry["backend"] == "leonardo-batch"
    assert entry["run_id"] == "stage2_pilot2/gate"
    assert entry["node_hours"] == pytest.approx(0.0867, abs=1e-4)


def test_a_failed_attempt_is_billed_too_and_attempts_accumulate(rig,
                                                                monkeypatch):
    _build(rig)
    P2.cmd_bootstrap(rig)
    # A node-level failure still costs the whole allocation.
    monkeypatch.setattr(P1, "run",
                        lambda argv, check=True: "111|FAILED|00:03:21|1|1:0\n")
    P2.cmd_bill(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                     job_id="111"))
    monkeypatch.setattr(P1, "run",
                        lambda argv, check=True: "222|COMPLETED|00:05:12|1|0:0\n")
    P2.cmd_bill(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                     job_id="222"))
    entry = json.loads((rig.out_dir / "manifest.json").read_text())[
        "jobs"]["stage2_pilot2_gate"]
    assert entry["slurm_job_ids"] == ["111", "222"]
    assert len(entry["sacct"]) == 2
    assert entry["status"] == "completed"
    # 0.0558 wasted + 0.0867 useful, not 0.0867.
    assert entry["actual_node_hours"] == pytest.approx(0.1425, abs=1e-4)


def test_re_billing_the_same_job_id_does_not_double_count_it(rig, monkeypatch):
    _build(rig)
    P2.cmd_bootstrap(rig)
    monkeypatch.setattr(P1, "run", lambda argv, check=True: SACCT_LINE)
    P2.cmd_bill(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                     job_id="50378388"))
    P2.cmd_bill(Args(out_dir=rig.out_dir, name="stage2_pilot2_gate",
                     job_id="50378388"))
    entry = json.loads((rig.out_dir / "manifest.json").read_text())[
        "jobs"]["stage2_pilot2_gate"]
    assert len(entry["sacct"]) == 1
    assert entry["actual_node_hours"] == pytest.approx(0.0867, abs=1e-4)


# ---------------------------------------------------------------------------
# The doubled-distribution parse artifact
# ---------------------------------------------------------------------------


DOUBLED = ("Reasoning about the options.\n\n"
           "A: 0.10\nB: 0.70\nC: 0.05\nD: 0.15\n\n"
           "A: 0.10 B: 0.70 C: 0.05 D: 0.15")


def test_the_frozen_parser_rejects_a_doubled_distribution(monkeypatch):
    # Not a bug in this driver -- D8's renormalise window is [0.8, 1.2] and a
    # doubled line states a mass of ~2.0. Pinned so nobody "fixes" it here.
    assert R.parse_distribution(DOUBLED, 4) is None
    assert P2.score_gate(_meta(correct=1), DOUBLED)["parsed"] is False


def test_the_diagnostic_recovers_what_the_doubled_reply_actually_said():
    got = P2.relaxed_reread(DOUBLED)
    assert got == pytest.approx([0.10, 0.70, 0.05, 0.15])


def test_the_diagnostic_returns_nothing_for_a_reply_with_no_distribution():
    assert P2.relaxed_reread("I refuse to answer.") is None
    assert P2.relaxed_reread(None) is None


def test_the_diagnostic_reports_a_recovered_reply_as_argmax_correct():
    metas = [{"idx": 0, "item_id": "C1:T:3", "canonical_id": "C1",
              "correct_index": 1, "n_options": 4}]
    records = [P2.score_gate(metas[0], DOUBLED)]
    diag = P2.diagnose_parse_failures(records, metas, {0: DOUBLED})
    assert diag["n_parse_failures"] == 1
    assert diag["n_recoverable"] == 1
    assert diag["n_recoverable_argmax_correct"] == 1
    assert "DIAGNOSTIC ONLY" in diag["note"]


def test_the_diagnostic_marks_an_unreadable_reply_as_unrecoverable():
    metas = [{"idx": 0, "item_id": "C1:T:3", "canonical_id": "C1",
              "correct_index": 1, "n_options": 4}]
    records = [P2.score_gate(metas[0], "no numbers here")]
    diag = P2.diagnose_parse_failures(records, metas, {0: "no numbers here"})
    assert diag["n_recoverable"] == 0
    assert diag["records"][0]["recoverable"] is False


def test_a_parsed_record_never_appears_in_the_diagnostic():
    metas = [{"idx": 0, "item_id": "C1:T:3", "canonical_id": "C1",
              "correct_index": 1, "n_options": 4}]
    good = "A: 0.05 B: 0.85 C: 0.05 D: 0.05"
    diag = P2.diagnose_parse_failures([P2.score_gate(metas[0], good)], metas,
                                      {0: good})
    assert diag["n_parse_failures"] == 0


# ---------------------------------------------------------------------------
# The two diagnostics
# ---------------------------------------------------------------------------


def test_export_diagnostics_writes_both_sets_over_the_candidate_items(rig):
    _build(rig)
    assert P2.cmd_export_diagnostics(rig) == 0
    doc = json.loads((rig.out_dir / "exports"
                      / "export_manifest_diag.json").read_text())
    assert doc["n_items"] == 10
    assert set(doc["files"]) == {"gate_stripped", "gate_qblind"}
    for info in doc["files"].values():
        assert info["n_prompts"] == 10
    assert "DIAGNOSTIC ONLY" in doc["status"]


def test_the_question_blind_export_really_drops_the_question(rig):
    _build(rig)
    P2.cmd_export_diagnostics(rig)
    prompts = [json.loads(l) for l in (rig.out_dir / "exports"
               / "prompts_gate_qblind.jsonl").read_text().splitlines()]
    for row in prompts:
        assert "HOST:" not in row["prompt"]
        assert "what did you make of item" not in row["prompt"]


def test_the_stripped_diagnostic_uses_the_frozen_arm_template(rig):
    _build(rig)
    P2.cmd_export_diagnostics(rig)
    prompts = [json.loads(l) for l in (rig.out_dir / "exports"
               / "prompts_gate_stripped.jsonl").read_text().splitlines()]
    # It IS the frozen zeroinfo_redacted prompt -- question and all -- only the
    # option texts are the entity-stripped ones.
    for row in prompts:
        assert row["prompt"].startswith(R.ZEROINFO_PREAMBLE)
        assert "HOST:" in row["prompt"]


def test_both_diagnostics_run_in_one_job(rig):
    _build(rig)
    text = P2.diag_sbatch(0.07)
    for name in P2.diag_set_names():
        assert f'"{name}"' in text
    # One engine init: a single batch_generate invocation takes both files.
    assert text.count("python jobs/batch_generate.py") == 1


def test_a_diagnostic_prompt_is_never_redacted_less_than_an_arm(rig):
    _build(rig)
    P2.cmd_export_diagnostics(rig)
    for name in P2.diag_set_names():
        for line in (rig.out_dir / "exports"
                     / f"prompts_{name}.jsonl").read_text().splitlines():
            row = json.loads(line)
            assert "Zorvath" not in row["prompt"]
            assert "Quilliman" not in row["prompt"]


def _run_diag(rig, solved):
    """Fake a diagnostic run. ``solved[name]`` = idxs the arm gets right."""
    node = rig.nodedir or (rig.out_dir.parent / "node")
    node.mkdir(parents=True, exist_ok=True)
    rig.nodedir = node
    for name in P2.diag_set_names():
        metas = [json.loads(l) for l in (rig.out_dir / "exports"
                 / f"meta_{name}.jsonl").read_text().splitlines()]
        lines = []
        for meta in metas:
            c = int(meta["correct_index"])
            if meta["idx"] not in solved[name]:
                c = (c + 1) % int(meta["n_options"])
            dist = [0.05] * 4
            dist[c] = 0.85
            lines.append(json.dumps({
                "idx": meta["idx"], "tokens_in": 500, "tokens_out": 50,
                "text": "A: %.2f B: %.2f C: %.2f D: %.2f" % tuple(dist)}))
        (node / f"completions_{name}.jsonl").write_text("\n".join(lines) + "\n",
                                                        encoding="utf-8")
        (node / f"completions_{name}.jsonl.summary.json").write_text(
            json.dumps({"engine_init_seconds": 200.0,
                        "generation_wall_seconds": 3.0}), encoding="utf-8")
    assert P2.cmd_ingest_diagnostics(rig) == 0


def test_the_decomposition_puts_the_gate_baseline_beside_both_diagnostics(rig):
    _build(rig)
    _run_gate(rig, solved_idxs=set(range(10)))
    P2.cmd_export_diagnostics(rig)
    _run_diag(rig, {"gate_stripped": {0, 1, 2, 3, 4},
                    "gate_qblind": {0}})
    doc = json.loads((rig.out_dir
                      / "diagnostic_results.json").read_text())
    dec = doc["decomposition"]
    assert dec["baseline_standard"]["argmax_accuracy"] == 1.0
    assert dec["gate_stripped"]["argmax_accuracy"] == 0.5
    assert dec["gate_qblind"]["argmax_accuracy"] == 0.1
    assert "DIAGNOSTIC ONLY" in doc["status"]


def test_the_diagnostic_never_writes_an_arm_or_a_final_item_set(rig):
    _build(rig)
    _run_gate(rig, solved_idxs=set(range(10)))
    P2.cmd_export_diagnostics(rig)
    _run_diag(rig, {"gate_stripped": set(), "gate_qblind": set()})
    assert not (rig.out_dir / "items_final.jsonl").exists()
    assert not (rig.out_dir / "records").exists()
