from pathlib import Path
import sys

# Ensure project root is on sys.path so we can import project modules when running directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controller import TimerController
from model import GameSnapshot


class FakeMemoryReader:
    """Feeds predetermined snapshots to the controller."""

    def __init__(self, snapshots):
        self.snapshots = list(snapshots)

    def read_snapshot(self) -> GameSnapshot:
        if not self.snapshots:
            raise RuntimeError("No more snapshots available")
        return self.snapshots.pop(0)


def test_load_transition_keeps_display_values():
    """IGT dropping to 0 during loads should preserve last valid display."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=True, igt_seconds=120, chapter=1, subsection_a="intro", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=0, chapter=1, subsection_a="intro", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=130, chapter=1, subsection_a="intro", subsection_b=""),
    ])

    display1, split1, _ = controller.tick()
    assert display1.attached is True
    assert display1.igt_text == "00:02:00"
    assert split1 is None  # no subsection B yet, so no split

    display2, split2, _ = controller.tick()
    assert display2.attached is True
    # Should reuse last valid IGT instead of blanking when IGT reads as 0
    assert display2.igt_text == "00:02:00"
    assert controller.state.in_load_transition is True
    assert split2 is None

    display3, split3, _ = controller.tick()
    assert controller.state.in_load_transition is False
    assert display3.igt_text == "00:02:10"
    assert split3 is None


def test_low_igt_load_transition_keeps_display_values():
    """Loads early in a chapter should retain the prior IGT instead of showing 00:00."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=True, igt_seconds=5, chapter=1, subsection_a="player_start", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=0, chapter=1, subsection_a="player_start", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=8, chapter=1, subsection_a="player_start", subsection_b=""),
    ])

    display1, split1, _ = controller.tick()
    assert display1.igt_text == "00:00:05"
    assert split1 is None

    display2, split2, _ = controller.tick()
    assert display2.attached is True
    assert display2.igt_text == "00:00:05"
    assert display2.current_segment_text == "00:00"
    assert controller.state.in_load_transition is True
    assert split2 is None

    display3, split3, _ = controller.tick()
    assert display3.igt_text == "00:00:08"
    assert controller.state.in_load_transition is False
    assert split3 is None


def test_load_transition_holds_display_when_igt_is_temporarily_unreadable():
    """An attached unreadable IGT should keep the last valid display during an active load."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=True, igt_seconds=120, chapter=1, subsection_a="intro", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=0, chapter=1, subsection_a="intro", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=None, chapter=1, subsection_a="intro", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=130, chapter=1, subsection_a="intro", subsection_b=""),
    ])

    controller.tick()
    controller.tick()

    display3, split3, _ = controller.tick()
    assert display3.attached is True
    assert display3.igt_text == "00:02:00"
    assert display3.current_segment_text == "00:00"
    assert controller.state.in_load_transition is True
    assert split3 is None

    display4, split4, _ = controller.tick()
    assert display4.igt_text == "00:02:10"
    assert controller.state.in_load_transition is False
    assert split4 is None


def test_load_to_earlier_point_uses_lower_resumed_igt():
    """After holding during a load, the display should switch to the lower resumed IGT immediately."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=True, igt_seconds=120, chapter=5, subsection_a="segA", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=0, chapter=5, subsection_a="segA", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=40, chapter=3, subsection_a="segB", subsection_b=""),
    ])

    display1, split1, _ = controller.tick()
    assert display1.igt_text == "00:02:00"
    assert split1 is None

    display2, split2, _ = controller.tick()
    assert display2.igt_text == "00:02:00"
    assert controller.state.in_load_transition is True
    assert split2 is None

    display3, split3, _ = controller.tick()
    assert display3.igt_text == "00:00:40"
    assert controller.state.in_load_transition is False
    assert split3 is None


def test_detached_state_does_not_reuse_stale_display_values():
    """Detaching from the game should blank the UI instead of holding the last in-load time."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=True, igt_seconds=120, chapter=1, subsection_a="intro", subsection_b=""),
        GameSnapshot(attached=False),
    ])

    controller.tick()
    display2, split2, chapter_total2 = controller.tick()
    assert display2.attached is False
    assert display2.igt_text == "--:--:--"
    assert display2.current_segment_text == "--:--"
    assert split2 is None
    assert chapter_total2 is None


def test_mid_chapter_load_no_split_until_change():
    """Loading mid-chapter with subsection_b set should NOT fire a split until subsection changes."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Load into chapter 3 at pl_start_village_inside (not a player_start marker)
        GameSnapshot(attached=True, igt_seconds=100, chapter=3, subsection_a="", subsection_b="pl_start_village_inside"),
        # Still at same checkpoint - no split
        GameSnapshot(attached=True, igt_seconds=110, chapter=3, subsection_a="", subsection_b="pl_start_village_inside"),
        # Move to next checkpoint - NOW a split should fire
        GameSnapshot(attached=True, igt_seconds=125, chapter=3, subsection_a="", subsection_b="gd03_em_player_start_check_1"),
    ])

    # First tick: attach mid-chapter, no split (just initializing state)
    display1, split1, _ = controller.tick()
    assert split1 is None
    assert controller.state.run_active is True
    assert controller.state.segment_start_igt == 100
    # State should now have seen_nonblank_b_this_chapter=True and last_subsection_b set
    assert controller.state.seen_nonblank_b_this_chapter is True
    assert controller.state.last_subsection_b == "pl_start_village_inside"

    # Second tick: still at same checkpoint, no split
    display2, split2, _ = controller.tick()
    assert split2 is None

    # Third tick: moved to new checkpoint, split fires for segment from pl_start_village_inside
    display3, split3, _ = controller.tick()
    assert split3 is not None
    assert split3.chapter == "3"
    assert split3.subsection_name == "pl_start_village_inside"
    # pl_start_village_inside maps to 2 in SUBSECTION_MAP
    assert split3.number == 2
    assert split3.duration_seconds == 25  # 125 - 100


def test_segment_reload_vs_full_reset():
    """Backwards IGT in same chapter/subsection should not wipe splits."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Start at segA
        GameSnapshot(attached=True, igt_seconds=10, chapter=1, subsection_a="", subsection_b="segA"),
        # Move to segB - creates first split
        GameSnapshot(attached=True, igt_seconds=20, chapter=1, subsection_a="", subsection_b="segB"),
        # Quickload back to segB (same subsection, IGT backwards) - segment reload
        GameSnapshot(attached=True, igt_seconds=15, chapter=1, subsection_a="", subsection_b="segB"),
        # Full reset: different chapter, IGT backwards
        GameSnapshot(attached=True, igt_seconds=3, chapter=2, subsection_a="", subsection_b="segC"),
    ])

    # First tick: attach at segA, no split yet
    _, split1, _ = controller.tick()
    assert split1 is None
    assert controller.state.segment_start_igt == 10

    # Second tick: moved to segB, split created for segment from segA
    _, split2, _ = controller.tick()
    assert split2 is not None
    assert split2.subsection_name == "segA"
    assert len(controller.history.splits) == 1
    first_start = controller.state.segment_start_igt
    assert first_start == 20  # Updated to current IGT after split

    # Third tick: segment reload (same chapter/subsection, IGT backwards)
    display3, split3, _ = controller.tick()
    assert split3 is None
    assert len(controller.history.splits) == 1  # Split preserved
    assert controller.state.segment_start_igt == 15  # Reset to new IGT
    assert controller.state.segment_start_igt != first_start
    assert display3.current_segment_text == "00:00"
    assert display3.igt_text == "00:00:15"

    # Fourth tick: full reset (different chapter, IGT backwards)
    _, split4, _ = controller.tick()
    assert split4 is None
    assert controller.history.splits == []
    assert controller.state.run_active is False
    assert controller.state.segment_start_igt is None


def test_subsection_change_creates_split_and_numbers_from_map():
    """A change in subsection B should create a split with mapped numbering."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Load at st13_gamedesign_b_player_start_1 (maps to 2)
        GameSnapshot(attached=True, igt_seconds=10, chapter=1, subsection_a="", subsection_b="st13_gamedesign_b_player_start_1"),
        # Move to st13_gamedesign_b_player_start_2 (maps to 3)
        GameSnapshot(attached=True, igt_seconds=25, chapter=1, subsection_a="", subsection_b="st13_gamedesign_b_player_start_2"),
        # Move to st13_gamedesign_b_player_start_3 (maps to 5)
        GameSnapshot(attached=True, igt_seconds=40, chapter=1, subsection_a="", subsection_b="st13_gamedesign_b_player_start_3"),
    ])

    # First tick: no split (just loading in)
    _, first_split, _ = controller.tick()
    assert first_split is None

    # Second tick: split for segment from player_start_1
    _, second_split, _ = controller.tick()
    assert second_split is not None
    assert second_split.subsection_name == "st13_gamedesign_b_player_start_1"
    assert second_split.number == 2  # From SUBSECTION_MAP
    assert second_split.duration_seconds == 15  # 25 - 10

    # Third tick: split for segment from player_start_2
    _, third_split, _ = controller.tick()
    assert third_split is not None
    assert third_split.subsection_name == "st13_gamedesign_b_player_start_2"
    assert third_split.number == 3  # From SUBSECTION_MAP
    assert third_split.duration_seconds == 15  # 40 - 25

    assert controller.history.get_used_numbers_for_chapter("1") == {2, 3}


def test_first_subsection_marker_finalizes_previous_chapter():
    """Hitting a first-subsection marker should finalize the chapter on next tick."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Start at checkpoint in chapter 1
        GameSnapshot(attached=True, igt_seconds=5, chapter=1, subsection_a="", subsection_b="st13_gamedesign_b_player_start_1"),
        # Move to another checkpoint to create a split
        GameSnapshot(attached=True, igt_seconds=15, chapter=1, subsection_a="", subsection_b="st13_gamedesign_b_player_start_2"),
        # Hit a player_start marker (first subsection marker)
        GameSnapshot(attached=True, igt_seconds=25, chapter=1, subsection_a="player_start", subsection_b=""),
        # Next tick should finalize
        GameSnapshot(attached=True, igt_seconds=30, chapter=1, subsection_a="", subsection_b=""),
    ])

    # First tick: no split (loading)
    _, split1, _ = controller.tick()
    assert split1 is None

    # Second tick: split created
    _, split2, _ = controller.tick()
    assert split2 is not None
    assert controller.history.splits[-1].chapter == "1"

    # Third tick: marker hit, pending finalization set (no chapter_total yet)
    _, split3, chapter_total3 = controller.tick()
    assert split3 is None
    assert chapter_total3 is None

    # Fourth tick: chapter finalized
    _, split4, chapter_total4 = controller.tick()
    assert split4 is None
    assert chapter_total4 is not None
    assert chapter_total4.chapter == "1"
    assert chapter_total4.total_seconds == split2.duration_seconds
    assert controller.history.is_chapter_finalized("1")


def test_first_subsection_marker_splits_as_one():
    """Departing from a first-subsection marker should create split number 1."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Load directly into player_start marker (first subsection)
        GameSnapshot(attached=True, igt_seconds=5, chapter=1, subsection_a="player_start", subsection_b=""),
        # Move to next checkpoint to trigger split
        GameSnapshot(attached=True, igt_seconds=20, chapter=1, subsection_a="player_start",
                     subsection_b="st13_gamedesign_b_player_start_1"),
    ])

    # First tick: seeding state, no split yet
    _, split1, _ = controller.tick()
    assert split1 is None
    assert controller.state.current_subsection == "player_start"

    # Second tick: first subsection B appears, split should reference player_start and be numbered 1
    _, split2, _ = controller.tick()
    assert split2 is not None
    assert split2.subsection_name == "player_start"
    assert split2.number == 1
    assert split2.duration_seconds == 15  # 20 - 5


def test_chapter_text_shows_correct_split_number():
    """UI chapter text should show correct split number based on SUBSECTION_MAP after recording splits."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Load at a later checkpoint (pl_start_village_inside maps to 2)
        GameSnapshot(attached=True, igt_seconds=50, chapter=3, subsection_a="", subsection_b="pl_start_village_inside"),
        # Move to next checkpoint (gd03_em_player_start_check_1 maps to 3)
        GameSnapshot(attached=True, igt_seconds=70, chapter=3, subsection_a="", subsection_b="gd03_em_player_start_check_1"),
        # Stay at same checkpoint
        GameSnapshot(attached=True, igt_seconds=80, chapter=3, subsection_a="", subsection_b="gd03_em_player_start_check_1"),
    ])

    # First tick: at pl_start_village_inside, display should show 3.2 (from map)
    display1, split1, _ = controller.tick()
    assert split1 is None
    assert display1.chapter_text == "3.2"

    # Second tick: moved to gd03_em_player_start_check_1, split recorded, display should show 3.3
    display2, split2, _ = controller.tick()
    assert split2 is not None
    assert split2.number == 2  # Departing from pl_start_village_inside
    assert display2.chapter_text == "3.3"

    # Third tick: still at same checkpoint, display still 3.3
    display3, split3, _ = controller.tick()
    assert split3 is None
    assert display3.chapter_text == "3.3"


def test_chapter_change_ignores_carryover_subsection_b():
    """Quickloading into a later chapter should split using the entry checkpoint even if subsection B jumps ahead."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Start in chapter 3 at gd03_em_player_start_check_2
        GameSnapshot(attached=True, igt_seconds=100, chapter=3, subsection_a="", subsection_b="gd03_em_player_start_check_2"),
        # Quickload into chapter 5 but subsection_b still reports the old chapter 3 value
        GameSnapshot(attached=True, igt_seconds=200, chapter=5, subsection_a="st06_asylummain_player_start_4", subsection_b="gd03_em_player_start_check_2"),
        # Subsection B jumps straight to the next checkpoint (5.6) once load finishes
        GameSnapshot(attached=True, igt_seconds=220, chapter=5, subsection_a="st06_asylummain_player_start_4", subsection_b="st06_asylummain_player_start_kidrescue_restart_a_02"),
        # Move to the following checkpoint (5.7), which should split for 5.6
        GameSnapshot(attached=True, igt_seconds=235, chapter=5, subsection_a="st06_asylummain_player_start_5", subsection_b="st06_asylummain_player_start_5"),
    ])

    # First tick seeds chapter 3 state
    display1, first_split, _ = controller.tick()
    assert first_split is None
    assert controller.state.current_chapter == 3
    assert controller.state.last_subsection_b == "gd03_em_player_start_check_2"

    # Second tick switches to chapter 5 but subsection_b is still the old value; it should be ignored
    display2, second_split, _ = controller.tick()
    assert second_split is None
    assert controller.state.current_chapter == 5
    assert controller.state.seen_nonblank_b_this_chapter is False
    assert controller.state.last_subsection_b == ""
    assert display2.chapter_text == "5.5"

    # Third tick hits the first new subsection B (5.6) and should create a split for the entry checkpoint (5.5)
    display3, third_split, _ = controller.tick()
    assert third_split is not None
    assert third_split.chapter == "5"
    assert third_split.number == 5  # st06_asylummain_player_start_4 maps to split 5.5
    assert third_split.subsection_name == "st06_asylummain_player_start_4"
    assert third_split.duration_seconds == 20  # 220 - 200
    assert display3.chapter_text == "5.6"

    # Fourth tick moves again and should split for the prior subsection (5.6)
    display4, fourth_split, _ = controller.tick()
    assert fourth_split is not None
    assert fourth_split.number == 6  # st06_asylummain_player_start_kidrescue_restart_a_02 -> 6
    assert fourth_split.subsection_name == "st06_asylummain_player_start_kidrescue_restart_a_02"
    assert fourth_split.duration_seconds == 15  # 235 - 220
    assert display4.chapter_text == "5.4"  # st06_asylummain_player_start_5 maps to split 5.4 (per SUBSECTION_MAP)


def test_chapter_change_accepts_shared_subsection_names():
    """Carryover subsection B that is valid in the new chapter should be treated as the first split."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Start in chapter 4 at player_start_1 (also exists in chapter 15)
        GameSnapshot(attached=True, igt_seconds=100, chapter=4, subsection_a="", subsection_b="player_start_1"),
        # Quickload into chapter 15; subsection_b still reports player_start_1, which is valid for chapter 15
        GameSnapshot(attached=True, igt_seconds=200, chapter=15, subsection_a="player_start_1",
                     subsection_b="player_start_1"),
        # Move to the next checkpoint in chapter 15 so the previous subsection can split
        GameSnapshot(attached=True, igt_seconds=230, chapter=15, subsection_a="player_start_4",
                     subsection_b="player_start_4"),
    ])

    # First tick seeds chapter 4 state
    _, first_split, _ = controller.tick()
    assert first_split is None
    assert controller.state.current_chapter == 4

    # Second tick transitions to chapter 15, but subsection_b remains valid, so it should count as the first seen B
    _, second_split, _ = controller.tick()
    assert second_split is None
    assert controller.state.current_chapter == 15
    assert controller.state.seen_nonblank_b_this_chapter is True
    assert controller.state.current_subsection == "player_start_1"

    # Third tick: new checkpoint triggers split for the shared subsection name using chapter 15 numbering
    _, third_split, _ = controller.tick()
    assert third_split is not None
    assert third_split.subsection_name == "player_start_1"
    assert third_split.number == 8  # From SUBSECTION_MAP for chapter 15
    assert third_split.duration_seconds == 30  # 230 - 200


def test_checkpoint_load_does_not_create_false_split():
    """Loading a different checkpoint in the same chapter should not create a synthetic split."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Establish initial checkpoint state.
        GameSnapshot(attached=True, igt_seconds=100, chapter=1, subsection_a="", subsection_b="segA"),
        # Load a different checkpoint in the same chapter.
        GameSnapshot(attached=True, igt_seconds=90, chapter=1, subsection_a="segLoad", subsection_b=""),
        # The loaded checkpoint stabilizes in subsection B - still no split.
        GameSnapshot(attached=True, igt_seconds=100, chapter=1, subsection_a="segLoad", subsection_b="segLoad"),
        # Moving away from the loaded checkpoint should create the next real split.
        GameSnapshot(attached=True, igt_seconds=120, chapter=1, subsection_a="segB", subsection_b="segB"),
    ])

    _, first_split, _ = controller.tick()
    assert first_split is None
    assert controller.state.last_subsection_b == "segA"

    _, second_split, _ = controller.tick()
    assert second_split is None
    assert controller.state.segment_start_igt == 90
    assert controller.state.current_subsection == "segLoad"

    _, third_split, _ = controller.tick()
    assert third_split is None
    assert controller.state.last_subsection_b == "segLoad"

    _, fourth_split, _ = controller.tick()
    assert fourth_split is not None
    assert fourth_split.subsection_name == "segLoad"
    assert fourth_split.duration_seconds == 30  # 120 - 90


def test_pending_finalization_survives_chapter_change():
    """A queued chapter finalization should not be lost if the next tick also changes chapters."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=True, igt_seconds=5, chapter=1, subsection_a="", subsection_b="st13_gamedesign_b_player_start_1"),
        GameSnapshot(attached=True, igt_seconds=15, chapter=1, subsection_a="", subsection_b="st13_gamedesign_b_player_start_2"),
        GameSnapshot(attached=True, igt_seconds=25, chapter=1, subsection_a="player_start", subsection_b=""),
        GameSnapshot(attached=True, igt_seconds=30, chapter=2, subsection_a="player_start", subsection_b=""),
    ])

    controller.tick()
    _, split2, _ = controller.tick()
    assert split2 is not None

    _, split3, chapter_total3 = controller.tick()
    assert split3 is None
    assert chapter_total3 is None

    _, split4, chapter_total4 = controller.tick()
    assert split4 is None
    assert chapter_total4 is not None
    assert chapter_total4.chapter == "1"
    assert chapter_total4.total_seconds == split2.duration_seconds


def test_chapter_text_uses_next_unused_ambiguous_mapping():
    """Display numbering should match the next unused split for list-based subsection mappings."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=True, igt_seconds=100, chapter=9, subsection_a="", subsection_b="gamedesign01_player_start_1"),
        GameSnapshot(attached=True, igt_seconds=110, chapter=9, subsection_a="", subsection_b="gamedesign01_player_start_4"),
        GameSnapshot(attached=True, igt_seconds=120, chapter=9, subsection_a="", subsection_b="gamedesign01_player_start_2"),
    ])

    display1, split1, _ = controller.tick()
    assert split1 is None
    assert display1.chapter_text == "9.3"

    display2, split2, _ = controller.tick()
    assert split2 is not None
    assert split2.number == 3
    assert display2.chapter_text == "9.2"

    display3, split3, _ = controller.tick()
    assert split3 is not None
    assert split3.number == 2
    assert display3.chapter_text == "9.4"


def test_new_game_starts_at_igt_zero():
    """A new game starting at IGT=0 should track time correctly from the beginning."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # New game starts at IGT=0
        GameSnapshot(attached=True, igt_seconds=0, chapter=1, subsection_a="player_start", subsection_b=""),
        # Time passes, still at starting checkpoint
        GameSnapshot(attached=True, igt_seconds=5, chapter=1, subsection_a="player_start", subsection_b=""),
        # Player moves to first checkpoint
        GameSnapshot(attached=True, igt_seconds=10, chapter=1, subsection_a="player_start",
                     subsection_b="st13_gamedesign_b_player_start_1"),
    ])

    # First tick at IGT=0: run should start with segment_start_igt=0
    display1, split1, _ = controller.tick()
    assert split1 is None
    assert controller.state.run_active is True
    assert controller.state.segment_start_igt == 0  # Critical: must be 0, not 1
    assert display1.igt_text == "00:00:00"
    assert display1.current_segment_text == "00:00"

    # Second tick at IGT=5: segment time should match IGT
    display2, split2, _ = controller.tick()
    assert split2 is None
    assert display2.igt_text == "00:00:05"
    assert display2.current_segment_text == "00:05"  # Should be 5, not 4

    # Third tick at IGT=10: split should have full 10 seconds
    display3, split3, _ = controller.tick()
    assert split3 is not None
    assert split3.duration_seconds == 10  # Full 10 seconds from IGT=0
    assert split3.subsection_name == "player_start"
    assert split3.number == 1


def test_reset_splits_clears_all_state():
    """Manual reset_splits() should clear all splits and state."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Build up some state
        GameSnapshot(attached=True, igt_seconds=10, chapter=1, subsection_a="", subsection_b="segA"),
        GameSnapshot(attached=True, igt_seconds=20, chapter=1, subsection_a="", subsection_b="segB"),
        # After reset, continue from here
        GameSnapshot(attached=True, igt_seconds=25, chapter=1, subsection_a="", subsection_b="segB"),
    ])

    # Build up state with a split
    controller.tick()
    _, split1, _ = controller.tick()
    assert split1 is not None
    assert len(controller.history.splits) == 1
    assert controller.state.run_active is True

    # Reset everything
    controller.reset_splits()
    assert controller.history.splits == []
    assert controller.state.run_active is False
    assert controller.state.segment_start_igt is None
    assert controller.state.current_chapter is None

    # Next tick should restart fresh
    display, split2, _ = controller.tick()
    assert split2 is None
    assert controller.state.run_active is True
    assert controller.state.segment_start_igt == 25


def test_detect_reset_requires_more_than_one_second_backwards():
    """IGT going backwards by exactly 1 second should not trigger reset (timing tolerance)."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        # Start at segA
        GameSnapshot(attached=True, igt_seconds=100, chapter=1, subsection_a="", subsection_b="segA"),
        # IGT goes back by exactly 1 second - should NOT be treated as reset
        GameSnapshot(attached=True, igt_seconds=99, chapter=1, subsection_a="", subsection_b="segA"),
        # IGT goes back by 2 seconds - SHOULD be treated as reset
        GameSnapshot(attached=True, igt_seconds=97, chapter=1, subsection_a="", subsection_b="segA"),
    ])

    # First tick: establish state
    controller.tick()
    assert controller.state.last_seen_igt == 100

    # Second tick: 1 second backwards - no reset (within tolerance)
    controller.tick()
    assert controller.state.last_seen_igt == 99  # Updated, not reset
    assert controller.state.segment_start_igt == 100  # Unchanged

    # Third tick: 2 seconds backwards - segment reload
    controller.tick()
    assert controller.state.segment_start_igt == 97  # Reset to new IGT


def test_not_attached_returns_default_display():
    """When not attached to process, should return default DisplayInfo."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=False),
    ])

    display, split, chapter_total = controller.tick()
    assert display.attached is False
    assert display.igt_text == "--:--:--"
    assert display.chapter_text == "--"
    assert split is None
    assert chapter_total is None


def test_none_igt_returns_not_attached():
    """When IGT is None (unreadable), should return not attached state."""
    controller = TimerController()
    controller.reader = FakeMemoryReader([
        GameSnapshot(attached=True, igt_seconds=None, chapter=1),
    ])

    display, split, chapter_total = controller.tick()
    assert display.attached is False
    assert split is None
