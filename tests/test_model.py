from pathlib import Path
import sys

import pytest

# Ensure project root is on sys.path so we can import model when running the test directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import Split, SplitHistory, ChapterTotal, GameSnapshot, DisplayInfo, TimerState, format_time


@pytest.mark.parametrize(
    "total_seconds, include_hours, expected",
    [
        (None, True, "--:--:--"),
        (-5, True, "00:00:00"),
        (59, True, "00:00:59"),
        (65, False, "01:05"),
        (3661, True, "01:01:01"),
    ],
)
def test_format_time(total_seconds, include_hours, expected):
    assert format_time(total_seconds, include_hours=include_hours) == expected


def test_split_history_finalize_and_clear():
    history = SplitHistory()
    history.add_split(Split(chapter="1", number=1, duration_seconds=10))
    history.add_split(Split(chapter="1", number=2, duration_seconds=20))
    history.add_split(Split(chapter="2", number=1, duration_seconds=5))

    total = history.finalize_chapter("1")
    assert total is not None
    assert total.total_seconds == 30
    assert total.split_count == 2
    assert history.is_chapter_finalized("1")

    # Re-finalizing or invalid chapters should be no-ops
    assert history.finalize_chapter("1") is None
    assert history.finalize_chapter("--") is None
    assert history.finalize_chapter("") is None

    history.clear()
    assert history.splits == []
    assert history.chapter_totals == {}
    assert history.finalized_chapters == set()


def test_split_label_and_formatted_time():
    """Split properties should format correctly."""
    split = Split(chapter="5", number=3, duration_seconds=125, subsection_name="test_sub")
    assert split.label == "5.3"
    assert split.formatted_time == "02:05"

    # Edge case: large duration
    long_split = Split(chapter="10", number=1, duration_seconds=3661)
    assert long_split.label == "10.1"
    assert long_split.formatted_time == "01:01:01"  # Hours included when > 0


def test_chapter_total_label_and_formatted_time():
    """ChapterTotal properties should format correctly."""
    total = ChapterTotal(chapter="3", total_seconds=185, split_count=4)
    assert total.label == "ΣCh3"
    assert total.formatted_time == "03:05"

    # Large time
    big_total = ChapterTotal(chapter="15", total_seconds=7265, split_count=10)
    assert big_total.label == "ΣCh15"
    assert big_total.formatted_time == "02:01:05"


def test_game_snapshot_current_subsection():
    """GameSnapshot.current_subsection should prefer subsection_b over subsection_a."""
    # Both set - prefer B
    snap1 = GameSnapshot(attached=True, igt_seconds=100, chapter=1,
                         subsection_a="entry_point", subsection_b="checkpoint_1")
    assert snap1.current_subsection == "checkpoint_1"

    # Only A set
    snap2 = GameSnapshot(attached=True, igt_seconds=100, chapter=1,
                         subsection_a="entry_point", subsection_b="")
    assert snap2.current_subsection == "entry_point"

    # Only B set
    snap3 = GameSnapshot(attached=True, igt_seconds=100, chapter=1,
                         subsection_a="", subsection_b="checkpoint_1")
    assert snap3.current_subsection == "checkpoint_1"

    # Neither set
    snap4 = GameSnapshot(attached=True, igt_seconds=100, chapter=1)
    assert snap4.current_subsection == ""


def test_display_info_not_attached():
    """DisplayInfo.not_attached() should return default unattached state."""
    display = DisplayInfo.not_attached()
    assert display.attached is False
    assert display.igt_text == "--:--:--"
    assert display.chapter_text == "--"
    assert display.current_segment_text == "--:--"


def test_timer_state_reset():
    """TimerState.reset() should clear all state to defaults."""
    state = TimerState()
    state.run_active = True
    state.segment_start_igt = 500
    state.current_subsection = "test_sub"
    state.current_chapter = 5
    state.last_subsection_b = "last_sub"
    state.seen_nonblank_b_this_chapter = True
    state.carryover_subsection_b = "carryover"
    state.last_seen_igt = 500
    state.in_load_transition = True
    state.last_valid_igt = 500

    state.reset()

    assert state.run_active is False
    assert state.segment_start_igt is None
    assert state.current_subsection == ""
    assert state.current_chapter is None
    assert state.last_subsection_b == ""
    assert state.seen_nonblank_b_this_chapter is False
    assert state.carryover_subsection_b == ""
    assert state.last_seen_igt is None
    assert state.in_load_transition is False
    assert state.last_valid_igt is None


def test_timer_state_start_new_chapter():
    """TimerState.start_new_chapter() should reset chapter-specific state."""
    state = TimerState()
    state.run_active = True
    state.segment_start_igt = 100
    state.current_subsection = "old_sub"
    state.current_chapter = 3
    state.last_subsection_b = "old_b"
    state.seen_nonblank_b_this_chapter = True

    state.start_new_chapter(chapter=5, igt=200, carryover_subsection_b="carried")

    assert state.current_chapter == 5
    assert state.segment_start_igt == 200
    assert state.current_subsection == ""
    assert state.last_subsection_b == ""
    assert state.seen_nonblank_b_this_chapter is False
    assert state.carryover_subsection_b == "carried"
    # run_active should be unchanged
    assert state.run_active is True


def test_format_time_edge_cases():
    """Additional edge cases for format_time."""
    # Zero
    assert format_time(0) == "00:00:00"
    assert format_time(0, include_hours=False) == "00:00"

    # Exactly one hour
    assert format_time(3600) == "01:00:00"
    assert format_time(3600, include_hours=False) == "01:00:00"  # Hours shown when > 0

    # Just under one hour
    assert format_time(3599) == "00:59:59"
    assert format_time(3599, include_hours=False) == "59:59"
