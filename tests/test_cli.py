"""Tests for CLI commands using typer CliRunner."""
import json

import pytest
from typer.testing import CliRunner

from trk.cli import app
from trk import storage

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_data_dir(monkeypatch, tmp_path):
    """Redirect hyp data dir to a temp directory for each test."""
    data = tmp_path / "hyp"
    data.mkdir()
    monkeypatch.setattr(storage, "data_dir", lambda: data)
    # Also patch state_path to use the temp dir
    monkeypatch.setattr(storage, "state_path", lambda t: data / f"{t}.json")
    yield data


def test_targets_empty():
    result = runner.invoke(app, ["targets"])
    assert result.exit_code == 0
    assert "No targets" in result.output


def test_init_creates_target(isolated_data_dir):
    result = runner.invoke(app, ["init", "acme"])
    assert result.exit_code == 0
    assert (isolated_data_dir / "acme.json").exists()


def test_targets_lists_after_init(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["targets"])
    assert "acme" in result.output


def test_show_basic(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert result.exit_code == 0
    assert "acme" in result.output


def test_new_adds_hypothesis(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["new", "-t", "acme", "--desc", "XSS via postMessage", "--priority", "1"])
    assert result.exit_code == 0
    assert "H1" in result.output

    # Verify in show output
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "XSS via postMessage" in result.output


def test_new_sequential_ids(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "first"])
    result = runner.invoke(app, ["new", "-t", "acme", "--desc", "second"])
    assert "H2" in result.output


def test_close_hypothesis(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "dead end test"])
    result = runner.invoke(app, ["close", "H1", "-t", "acme", "--conclusion", "It was dead."])
    assert result.exit_code == 0
    assert "closed H1" in result.output

    # Show --closed should list it
    result = runner.invoke(app, ["show", "-t", "acme", "--closed"])
    assert "dead end test" in result.output
    assert "It was dead." in result.output


def test_confirm_creates_confirmation(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "XSS candidate"])
    result = runner.invoke(app, [
        "confirm", "H1", "-t", "acme",
        "--conclusion", "Confirmed XSS",
        "--title", "DOM XSS in postMessage",
        "--severity", "high",
    ])
    assert result.exit_code == 0
    assert "C1" in result.output

    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "C1" in result.output


def test_confirmation_update(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "test"])
    runner.invoke(app, [
        "confirm", "H1", "-t", "acme",
        "--conclusion", "yes",
        "--title", "XSS",
        "--severity", "high",
    ])
    result = runner.invoke(app, [
        "confirmation", "C1", "-t", "acme",
        "--status", "confirmed_needs_exfil",
        "--notes", "alert() works",
    ])
    assert result.exit_code == 0

    result = runner.invoke(app, ["show", "-t", "acme", "--confirmations"])
    assert "confirmed_needs_exfil" in result.output
    assert "alert() works" in result.output


def test_last_action(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["last", "Injected hook override", "-t", "acme"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "Injected hook override" in result.output


def test_block_unblock(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["block", "Waiting for rate limit reset", "-t", "acme"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "Waiting for rate limit reset" in result.output

    runner.invoke(app, ["unblock", "-t", "acme"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "BLOCKED" not in result.output


def test_show_json(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "H1 desc", "--priority", "2"])
    result = runner.invoke(app, ["show", "-t", "acme", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["target"] == "acme"
    open_hyps = [h for h in data["hypotheses"] if h["status"] == "open"]
    assert len(open_hyps) == 1
    assert open_hyps[0]["id"] == "H1"


def test_export_markdown(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "Test hyp"])
    result = runner.invoke(app, ["export", "-t", "acme", "--format", "md"])
    assert result.exit_code == 0
    assert "# Security Research: acme" in result.output
    assert "Test hyp" in result.output


def test_export_json(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["export", "-t", "acme", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["target"] == "acme"


def test_missing_target_raises():
    result = runner.invoke(app, ["show"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Queue tests
# ---------------------------------------------------------------------------

def test_qadd_creates_item(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["qadd", "-t", "acme", "--desc", "chunk_abc.js L123 — postMessage handler", "--queue", "listeners"])
    assert result.exit_code == 0
    assert "Q1" in result.output
    assert "listeners" in result.output


def test_qadd_sequential_ids(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "first", "--queue", "q"])
    result = runner.invoke(app, ["qadd", "-t", "acme", "--desc", "second", "--queue", "q"])
    assert "Q2" in result.output


def test_qadd_shows_in_show(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "chunk_abc.js handler"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "chunk_abc.js handler" in result.output
    assert "QUEUE:" in result.output


def test_qdone_marks_item(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "some listener"])
    result = runner.invoke(app, ["qdone", "Q1", "-t", "acme"])
    assert result.exit_code == 0
    assert "done Q1" in result.output


def test_qdone_with_hyp_link(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "listener"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "test hypothesis"])
    result = runner.invoke(app, ["qdone", "Q1", "-t", "acme", "--hyp", "H1"])
    assert result.exit_code == 0
    assert "→ H1" in result.output


def test_qdone_removes_from_pending_in_show(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "listener A"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "listener B"])
    runner.invoke(app, ["qdone", "Q1", "-t", "acme"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    # Q1 done, Q2 still pending — show only prints the next pending item
    assert "listener B" in result.output
    assert "1/2 done" in result.output


def test_qskip(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "skip me"])
    result = runner.invoke(app, ["qskip", "Q1", "-t", "acme"])
    assert result.exit_code == 0
    assert "skipped Q1" in result.output


def test_qshow(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "handler one", "--queue", "listeners"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "handler two", "--queue", "listeners"])
    runner.invoke(app, ["qdone", "Q1", "-t", "acme"])
    result = runner.invoke(app, ["qshow", "-t", "acme"])
    assert result.exit_code == 0
    assert "listeners" in result.output
    assert "[x]" in result.output
    assert "[ ]" in result.output


def test_qshow_filter_by_queue(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "thing A", "--queue", "queue_a"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "thing B", "--queue", "queue_b"])
    result = runner.invoke(app, ["qshow", "-t", "acme", "--queue", "queue_a"])
    assert "thing A" in result.output
    assert "thing B" not in result.output


def test_qbulk_adds_multiple(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["qbulk", "-t", "acme", "--queue", "listeners"],
                           input="chunk_abc.js L123 — handler A\nchunk_def.js L456 — handler B\nchunk_ghi.js L89 — handler C\n")
    assert result.exit_code == 0
    assert "Q1" in result.output
    assert "Q3" in result.output

    result = runner.invoke(app, ["qshow", "-t", "acme"])
    assert "handler A" in result.output
    assert "handler B" in result.output
    assert "handler C" in result.output


def test_qbulk_skips_blank_lines(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["qbulk", "-t", "acme"],
                           input="\n  \nhandler A\n\nhandler B\n")
    assert result.exit_code == 0
    # only 2 items added (blank lines skipped)
    result = runner.invoke(app, ["qshow", "-t", "acme"])
    assert "handler A" in result.output
    assert "handler B" in result.output


def test_export_includes_queue(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--queue", "listeners", "--desc", "chunk_abc.js L123"])
    runner.invoke(app, ["qdone", "Q1", "-t", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--queue", "listeners", "--desc", "chunk_def.js L456"])
    result = runner.invoke(app, ["export", "-t", "acme", "--format", "md"])
    assert result.exit_code == 0
    assert "Work Queues" in result.output
    assert "listeners" in result.output
    assert "[x]" in result.output
    assert "[ ]" in result.output


# ---------------------------------------------------------------------------
# update tests
# ---------------------------------------------------------------------------

def test_update_next_action(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "XSS via postMessage"])
    result = runner.invoke(app, ["update", "H1", "-t", "acme", "--next", "try with opener.postMessage"])
    assert result.exit_code == 0
    assert "updated H1" in result.output
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "try with opener.postMessage" in result.output


def test_update_priority(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "test hyp", "--priority", "3"])
    runner.invoke(app, ["update", "H1", "-t", "acme", "--priority", "1"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "P1" in result.output


def test_update_desc(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "original desc"])
    runner.invoke(app, ["update", "H1", "-t", "acme", "--desc", "revised desc"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "revised desc" in result.output
    assert "original desc" not in result.output


def test_update_not_found(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["update", "H99", "-t", "acme", "--next", "whatever"])
    assert result.exit_code != 0


def test_update_no_options_errors(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "test"])
    result = runner.invoke(app, ["update", "H1", "-t", "acme"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# grep tests
# ---------------------------------------------------------------------------

def test_grep_hypothesis_desc(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "XSS via postMessage"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "CSRF in logout"])
    result = runner.invoke(app, ["grep", "postMessage", "-t", "acme"])
    assert result.exit_code == 0
    assert "postMessage" in result.output
    assert "CSRF" not in result.output


def test_grep_attempt_payload(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "redirect bypass"])
    runner.invoke(app, ["try", "H1", "redirect_uri=@@evil", "-t", "acme"])
    result = runner.invoke(app, ["grep", "@@evil", "-t", "acme"])
    assert "@@evil" in result.output


def test_grep_note(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["note", "API uses RS256 JWT", "-t", "acme"])
    result = runner.invoke(app, ["grep", "RS256", "-t", "acme"])
    assert "RS256" in result.output
    assert "note[1]" in result.output


def test_grep_no_match(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "XSS test"])
    result = runner.invoke(app, ["grep", "sqli", "-t", "acme"])
    assert result.exit_code == 0
    assert "No matches" in result.output


def test_grep_case_insensitive(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "XSS via postMessage"])
    result = runner.invoke(app, ["grep", "xss", "-t", "acme"])
    assert "XSS" in result.output


def test_grep_confirmation(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "XSS candidate"])
    runner.invoke(app, [
        "confirm", "H1", "-t", "acme",
        "--conclusion", "yes",
        "--title", "DOM XSS in postMessage handler",
        "--severity", "high",
    ])
    result = runner.invoke(app, ["grep", "postMessage", "-t", "acme"])
    assert "C1" in result.output
    assert "DOM XSS" in result.output


# ---------------------------------------------------------------------------
# rm tests
# ---------------------------------------------------------------------------

def test_rm_hypothesis(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "to be removed"])
    runner.invoke(app, ["new", "-t", "acme", "--desc", "keeper"])
    result = runner.invoke(app, ["rm", "H1", "-t", "acme"])
    assert result.exit_code == 0
    assert "removed H1" in result.output
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert "to be removed" not in result.output
    assert "keeper" in result.output


def test_rm_not_found(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["rm", "H99", "-t", "acme"])
    assert result.exit_code != 0


def test_note_rm(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["note", "first note", "-t", "acme"])
    runner.invoke(app, ["note", "second note", "-t", "acme"])
    result = runner.invoke(app, ["note", "--rm", "1", "-t", "acme"])
    assert result.exit_code == 0
    assert "first note" in result.output  # echoes removed text
    result = runner.invoke(app, ["notes", "-t", "acme"])
    assert "first note" not in result.output
    assert "second note" in result.output


def test_note_rm_out_of_range(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["note", "only note", "-t", "acme"])
    result = runner.invoke(app, ["note", "--rm", "5", "-t", "acme"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Note tests
# ---------------------------------------------------------------------------

def test_note_appends(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["note", "API uses RS256 JWT", "-t", "acme"])
    assert result.exit_code == 0
    assert "note added" in result.output


def test_notes_lists(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["note", "API uses RS256 JWT", "-t", "acme"])
    runner.invoke(app, ["note", "rate limit at 10 req/s", "-t", "acme"])
    result = runner.invoke(app, ["notes", "-t", "acme"])
    assert result.exit_code == 0
    assert "API uses RS256 JWT" in result.output
    assert "rate limit at 10 req/s" in result.output


def test_notes_empty(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    result = runner.invoke(app, ["notes", "-t", "acme"])
    assert result.exit_code == 0
    assert "No notes" in result.output


def test_note_appears_in_show(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["note", "endpoint /admin exists but 403s", "-t", "acme"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    assert result.exit_code == 0
    assert "endpoint /admin exists but 403s" in result.output
    assert "NOTES:" in result.output


def test_note_has_timestamp(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["note", "something observed", "-t", "acme"])
    result = runner.invoke(app, ["notes", "-t", "acme"])
    # timestamp format [YYYY-MM-DD]
    assert "[20" in result.output


def test_note_appears_in_export(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["note", "RS256 JWT observed", "-t", "acme"])
    result = runner.invoke(app, ["export", "-t", "acme", "--format", "md"])
    assert result.exit_code == 0
    assert "## Notes" in result.output
    assert "RS256 JWT observed" in result.output


def test_queue_show_summary_counts(isolated_data_dir):
    runner.invoke(app, ["init", "acme"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "L1", "--queue", "test_q"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "L2", "--queue", "test_q"])
    runner.invoke(app, ["qadd", "-t", "acme", "--desc", "L3", "--queue", "test_q"])
    runner.invoke(app, ["qdone", "Q1", "-t", "acme"])
    result = runner.invoke(app, ["show", "-t", "acme"])
    # should show "1/3 done, 2 pending"
    assert "1/3 done" in result.output
    assert "2 pending" in result.output
