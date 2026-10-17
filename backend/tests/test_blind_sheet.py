"""Blind rating sheet for D2 criterion 5. No Ollama: the committed result file (a static JSON) and
in-memory fakes only. Nothing here rates anything; a fake sheet is built in the test, never the
real `benchmarks/llm/blind_rating_2026-10-15.md`.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "benchmarks" / "llm"


def load(name):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bs = load("blind_sheet")

TOPICS = bs.TOPICS
STRATEGIES = bs.STRATEGIES


def _source_result() -> dict:
    return json.loads((RESULTS_DIR / bs.SOURCE_FILE).read_text(encoding="utf-8"))


# --- item selection -----------------------------------------------------------------------------


def test_llm_selection_is_exactly_the_run_one_three_topic_generations():
    picked = bs.select_llm_items(_source_result())
    assert len(picked) == 12
    assert set(picked) == {(t, s) for t in TOPICS for s in STRATEGIES}


def test_template_selection_has_12_items_one_per_pair():
    from app.generation.adapters import TemplateFallback

    picked = bs.select_template_items(TemplateFallback())
    assert len(picked) == 12
    assert set(picked) == {(t, s) for t in TOPICS for s in STRATEGIES}


def test_the_item_that_fails_would_ship_is_included():
    """The rating judges what the model actually produced, not what the fallback hides: a reply that fails would_ship
    must still appear on the sheet, as-is.

    Expected value history:
      r2: inheritance/example in the SOURCE file fails would_ship (source: the r2 file)  <- lead finding, S9 blind sheet
      r3: no item in the r3 source fails would_ship, so the failing item is constructed in the test (a truncated example with no closed block)  <- owner decision B, 2026-10-17 (backendPlan/15 section 0)
    If this fails, decide: a regression, or a second intended change needing its own ruling."""
    from app.generation.postprocess import finalise, would_ship

    result = _source_result()
    g = next(
        g for g in result["generations"]
        if g["run"] == 1 and g["topic"] == "inheritance" and g["strategy"] == "example"
    )
    # make the source's inheritance/example a truncated reply with no closed java block
    g["raw_text"] = "Here is a short example.\n\n```java\nclass Dog extends Animal {\n    void bark() {"
    g["done_reason"] = "length"
    g["final_text"] = finalise(g["raw_text"], g["strategy"], truncated=True)
    picked = bs.select_llm_items(result)
    assert ("inheritance", "example") in picked
    assert would_ship(g["raw_text"], g["strategy"], True) is False
    assert picked[("inheritance", "example")] == g["final_text"]


def test_the_real_r3_source_ships_every_selected_item():
    """Recorded fact about the r3 source (run 1, the three topics): all 12 items are shippable in form."""
    from app.generation.postprocess import would_ship

    picked = bs.select_llm_items(_source_result())
    gens = {(g["topic"], g["strategy"]): g for g in _source_result()["generations"] if g["run"] == 1}
    for key in picked:
        g = gens[key]
        assert would_ship(g["raw_text"], g["strategy"], g["done_reason"] == "length") is True, key


def test_llm_selection_values_are_exactly_the_run_one_final_text():
    result = _source_result()
    picked = bs.select_llm_items(result)
    run1_by_pair = {
        (g["topic"], g["strategy"]): g["final_text"]
        for g in result["generations"]
        if g["run"] == 1 and g["topic"] in TOPICS
    }
    run2_by_pair = {
        (g["topic"], g["strategy"]): g["final_text"]
        for g in result["generations"]
        if g["run"] == 2 and g["topic"] in TOPICS
    }
    assert picked == run1_by_pair
    # precondition for this test to mean anything: run 2's text actually differs somewhere
    assert any(run1_by_pair[k] != run2_by_pair[k] for k in run1_by_pair)


def test_llm_selection_raises_on_a_finalise_mismatch():
    result = _source_result()
    result = json.loads(json.dumps(result))  # deep copy
    for g in result["generations"]:
        if g["run"] == 1 and g["topic"] == "inheritance" and g["strategy"] == "theory":
            g["final_text"] = "SOMETHING ELSE ENTIRELY"
    with pytest.raises(ValueError, match="finalise"):
        bs.select_llm_items(result)


def test_llm_selection_raises_when_a_pair_is_missing():
    result = _source_result()
    result = json.loads(json.dumps(result))
    result["generations"] = [
        g for g in result["generations"]
        if not (g["run"] == 1 and g["topic"] == "loops" and g["strategy"] == "theory")
    ]
    with pytest.raises(ValueError, match="missing"):
        bs.select_llm_items(result)


# --- normalisation --------------------------------------------------------------------------------


def test_normalise_strips_trailing_whitespace_and_collapses_blank_lines_and_fixes_the_check_gap():
    raw = "Loops repeat code.   \n\t\n\n\n**Check:** Why?   \n\n\n"
    out = bs.normalise(raw)
    assert out == "Loops repeat code.\n\n**Check:** Why?\n"


def test_normalise_inserts_the_missing_blank_line_before_check():
    assert bs.normalise("Loops repeat code.\n**Check:** Why?") == "Loops repeat code.\n\n**Check:** Why?\n"


def test_normalise_does_not_duplicate_an_already_correct_blank_line():
    # regression: a naive lookahead-based substitution can double the newlines
    once = bs.normalise("Loops repeat code.\n\n**Check:** Why?")
    assert once == "Loops repeat code.\n\n**Check:** Why?\n"
    assert bs.normalise(once) == once  # idempotent


def test_normalise_never_changes_the_wording():
    text = "Some   trailing   words stay put.\n\n**Check:** Still here?"
    out = bs.normalise(text)
    assert "Some   trailing   words stay put." in out  # internal spacing untouched, only line-trailing ws


def test_the_same_normalise_function_is_applied_to_both_sides():
    from app.generation.adapters import TemplateFallback

    llm_items = bs.select_llm_items(_source_result())
    template_items = bs.select_template_items(TemplateFallback())
    rows = bs.build_rows(llm_items, template_items, bs.SEED)
    for row in rows:
        assert row["text"] == bs.normalise(row["text"])  # already normalised, and idempotent


# --- shuffle / determinism ------------------------------------------------------------------------


def _rows():
    from app.generation.adapters import TemplateFallback

    llm_items = bs.select_llm_items(_source_result())
    template_items = bs.select_template_items(TemplateFallback())
    return llm_items, template_items


def test_building_twice_gives_byte_identical_sheet_and_key():
    sheet1, key1 = bs.build_sheet_and_key()
    sheet2, key2 = bs.build_sheet_and_key()
    assert sheet1 == sheet2
    assert json.dumps(key1, sort_keys=True) == json.dumps(key2, sort_keys=True)


def test_a_different_seed_gives_a_different_order():
    llm_items, template_items = _rows()
    rows_a = bs.build_rows(llm_items, template_items, bs.SEED)
    rows_b = bs.build_rows(llm_items, template_items, bs.SEED + 1)
    order_a = [(r["topic"], r["strategy"], r["side"]) for r in rows_a]
    order_b = [(r["topic"], r["strategy"], r["side"]) for r in rows_b]
    assert order_a != order_b


def test_labels_run_r01_to_r24_in_shuffled_order():
    llm_items, template_items = _rows()
    rows = bs.build_rows(llm_items, template_items, bs.SEED)
    assert [r["id"] for r in rows] == [f"R{i:02d}" for i in range(1, 25)]


# --- no tells --------------------------------------------------------------------------------------


def test_the_built_sheet_contains_no_forbidden_word():
    sheet, _ = bs.build_sheet_and_key()
    for word in ("llm", "template", "fallback", "ollama", "llama", "model"):
        assert not re.search(word, sheet, re.IGNORECASE), word


def test_check_no_tells_raises_when_a_forbidden_word_is_present():
    with pytest.raises(ValueError, match="forbidden word"):
        bs.check_no_tells("## R01: loops / theory\n\nThis text mentions a template here.\n")


# --- key consistency --------------------------------------------------------------------------------


def test_every_id_is_in_the_key_exactly_once_and_matches_its_item():
    llm_items, template_items = _rows()
    rows = bs.build_rows(llm_items, template_items, bs.SEED)
    key = bs.render_key(rows, bs.SEED, bs.SOURCE_FILE)
    assert set(key["items"]) == {f"R{i:02d}" for i in range(1, 25)}
    assert len(key["items"]) == 24
    for row in rows:
        assert key["items"][row["id"]] == row["side"]
    assert list(key["items"].values()).count("llm") == 12
    assert list(key["items"].values()).count("template") == 12


# --- scorer, using a fake sheet built in the test -----------------------------------------------------


def _fake_sheet(ratings: dict[str, str]) -> str:
    parts = ["# fake sheet for testing\n"]
    for item_id, rating in ratings.items():
        parts.append(f"## {item_id}: loops / theory\n\nSome body text.\n\n**Check:** Why?\n\nRating (1-5): {rating}\n")
    return "\n".join(parts)


def _fake_key(sides: dict[str, str]) -> dict:
    return {"seed": 1, "source": "fake.json", "items": dict(sides)}


def test_scorer_computes_a_correct_mean_per_side():
    sides = {"R01": "llm", "R02": "llm", "R03": "template", "R04": "template"}
    ratings = {"R01": "4", "R02": "2", "R03": "5", "R04": "1"}
    result = bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))
    assert result["n_llm"] == 2 and result["n_template"] == 2
    assert result["mean_llm"] == 3.0 and result["mean_template"] == 3.0


def test_scorer_pass_when_llm_at_least_3_and_at_least_template():
    sides = {"R01": "llm", "R02": "template"}
    ratings = {"R01": "4", "R02": "3"}
    result = bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))
    assert result["llm_ge_3"] is True and result["llm_ge_template"] is True
    assert result["criterion_5"] == "PASS"


def test_scorer_fail_when_llm_mean_below_3():
    sides = {"R01": "llm", "R02": "template"}
    ratings = {"R01": "2", "R02": "1"}
    result = bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))
    assert result["llm_ge_3"] is False
    assert result["criterion_5"] == "FAIL"


def test_scorer_fail_when_llm_mean_below_template_mean():
    sides = {"R01": "llm", "R02": "template"}
    ratings = {"R01": "3", "R02": "5"}
    result = bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))
    assert result["llm_ge_3"] is True
    assert result["llm_ge_template"] is False
    assert result["criterion_5"] == "FAIL"


def test_scorer_raises_on_a_blank_rating():
    sides = {"R01": "llm", "R02": "template"}
    ratings = {"R01": "", "R02": "3"}
    with pytest.raises(ValueError, match="R01"):
        bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))


@pytest.mark.parametrize("bad", ["0", "6", "3.5", "three", "-1"])
def test_scorer_raises_on_an_out_of_range_or_non_integer_rating(bad):
    sides = {"R01": "llm", "R02": "template"}
    ratings = {"R01": bad, "R02": "3"}
    with pytest.raises(ValueError, match="R01"):
        bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))


def test_scorer_raises_on_an_id_missing_from_the_key():
    sides = {"R01": "llm"}  # R02 is rated but absent from the key
    ratings = {"R01": "4", "R02": "3"}
    with pytest.raises(ValueError, match="R02"):
        bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))


def test_scorer_raises_on_an_id_missing_from_the_sheet():
    sides = {"R01": "llm", "R02": "template"}
    ratings = {"R01": "4"}  # R02 never rated, not even with a blank line
    with pytest.raises(ValueError, match="R02"):
        bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))


def test_a_partially_rated_sheet_is_never_scored():
    sides = {"R01": "llm", "R02": "template", "R03": "llm"}
    ratings = {"R01": "4", "R02": "3", "R03": ""}
    with pytest.raises(ValueError, match="R03"):
        bs.score_sheet(_fake_sheet(ratings), _fake_key(sides))


# --- CLI ---------------------------------------------------------------------------------------------


def test_cli_build_into_a_temp_dir_gives_exit_0(tmp_path):
    code = bs.main(["build", "--out", str(tmp_path)])
    assert code == 0
    assert (tmp_path / bs.SHEET_NAME).exists()
    assert (tmp_path / bs.KEY_NAME).exists()


def test_cli_build_again_without_force_gives_exit_1_and_leaves_files_unchanged(tmp_path, capsys):
    assert bs.main(["build", "--out", str(tmp_path)]) == 0
    sheet_before = (tmp_path / bs.SHEET_NAME).read_bytes()
    key_before = (tmp_path / bs.KEY_NAME).read_bytes()
    code = bs.main(["build", "--out", str(tmp_path)])
    assert code == 1
    assert "already exists" in capsys.readouterr().err
    assert (tmp_path / bs.SHEET_NAME).read_bytes() == sheet_before
    assert (tmp_path / bs.KEY_NAME).read_bytes() == key_before


def test_cli_build_with_force_overwrites(tmp_path):
    assert bs.main(["build", "--out", str(tmp_path)]) == 0
    assert bs.main(["build", "--out", str(tmp_path), "--force"]) == 0


def test_cli_score_on_an_incomplete_fake_sheet_gives_exit_1(tmp_path, capsys):
    sides = {"R01": "llm", "R02": "template"}
    ratings = {"R01": "4", "R02": ""}
    sheet_path = tmp_path / "sheet.md"
    key_path = tmp_path / "key.json"
    sheet_path.write_text(_fake_sheet(ratings), encoding="utf-8")
    key_path.write_text(json.dumps(_fake_key(sides)), encoding="utf-8")
    code = bs.main(["score", str(sheet_path), str(key_path)])
    assert code == 1
    assert "ValueError" in capsys.readouterr().err


def test_cli_score_on_a_complete_fake_sheet_gives_exit_0(tmp_path, capsys):
    sides = {"R01": "llm", "R02": "template"}
    ratings = {"R01": "4", "R02": "3"}
    sheet_path = tmp_path / "sheet.md"
    key_path = tmp_path / "key.json"
    sheet_path.write_text(_fake_sheet(ratings), encoding="utf-8")
    key_path.write_text(json.dumps(_fake_key(sides)), encoding="utf-8")
    code = bs.main(["score", str(sheet_path), str(key_path)])
    assert code == 0
    assert "criterion_5" in capsys.readouterr().out


# --- R3: the r3 sheet's constants, and the void r2 files stay untouched ------------------------------------------

import hashlib  # noqa: E402

R2_SHEET = RESULTS_DIR / "blind_rating_2026-10-15.md"
R2_KEY = RESULTS_DIR / "blind_key_2026-10-15.json"
R2_SHEET_SHA256 = "312b9c9799feb85d397769ddbf9fea9af18e6292072c5fdc751ede4268e2340a"
R2_KEY_SHA256 = "0b349c65444fbbfb1d33f04101871bbbf6e5ee9c458a3a41a49c5cd0bacbffb5"


def test_the_blind_sheet_constants_are_the_r3_ones():
    """Expected value history:
      r2: SEED 20261015, SHEET_DATE 2026-10-15, SOURCE llama3.2_3b_2026-10-15_np110_r2.json  <- S9 blind sheet
      r3: SEED 20261017, SHEET_DATE 2026-10-17, SOURCE llama3.2_3b_2026-10-17_np220_r3.json  <- owner decision B, 2026-10-17 (backendPlan/15 section 0)
    If this fails, decide: a regression, or a second intended change needing its own ruling."""
    assert bs.SEED == 20261017
    assert bs.SHEET_DATE == "2026-10-17"
    assert bs.SOURCE_FILE == "llama3.2_3b_2026-10-17_np220_r3.json"
    assert bs.SHEET_NAME == "blind_rating_2026-10-17.md" and bs.KEY_NAME == "blind_key_2026-10-17.json"


def test_building_the_r3_sheet_never_touches_the_void_r2_sheet_and_key(tmp_path):
    before = (hashlib.sha256(R2_SHEET.read_bytes()).hexdigest(), hashlib.sha256(R2_KEY.read_bytes()).hexdigest())
    assert before == (R2_SHEET_SHA256, R2_KEY_SHA256)  # the void r2 files are exactly as committed
    # an output directory that ALREADY holds the r2 sheet and key, and --force: the worst case. If the builder
    # wrote under the r2 names it would overwrite them here.
    import shutil

    shutil.copy(R2_SHEET, tmp_path / R2_SHEET.name)
    shutil.copy(R2_KEY, tmp_path / R2_KEY.name)
    assert bs.main(["build", "--out", str(tmp_path), "--results-dir", str(RESULTS_DIR), "--force"]) == 0
    assert (tmp_path / "blind_rating_2026-10-17.md").exists() and (tmp_path / "blind_key_2026-10-17.json").exists()
    assert (hashlib.sha256((tmp_path / R2_SHEET.name).read_bytes()).hexdigest(),
            hashlib.sha256((tmp_path / R2_KEY.name).read_bytes()).hexdigest()) == before
    after = (hashlib.sha256(R2_SHEET.read_bytes()).hexdigest(), hashlib.sha256(R2_KEY.read_bytes()).hexdigest())
    assert after == before  # and the real r2 files were never written either


def test_the_default_output_names_cannot_collide_with_the_r2_names():
    assert bs.SHEET_NAME != R2_SHEET.name and bs.KEY_NAME != R2_KEY.name
