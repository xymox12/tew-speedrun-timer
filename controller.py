# controller.py
"""Timer controller handling game state and split detection."""

from typing import Optional

from config import FIRST_SUBSECTION_MARKERS, DEBUG
from subsection_data import SUBSECTION_MAP
from memory_reader import MemoryReader
from model import (
    TimerState, DisplayInfo, GameSnapshot, SplitHistory,
    Split, ChapterTotal, format_time
)

# Map subsection names (lowercase) to the chapters they can appear in.
SUBSECTION_CHAPTER_INDEX: dict[str, set[int]] = {}
for (chapter, subsection_name), _ in SUBSECTION_MAP.items():
    SUBSECTION_CHAPTER_INDEX.setdefault(subsection_name.lower(), set()).add(chapter)


def debug_print(*args):
    """Print debug messages if DEBUG is enabled."""
    if DEBUG:
        print("[DEBUG]", *args)


class TimerController:
    """Controls timer logic and manages splits."""

    def __init__(self):
        self.reader = MemoryReader()
        self.state = TimerState()
        self.history = SplitHistory()
        self._pending_finalize_chapter: Optional[str] = None
        self.subsection_chapter_index: dict[str, set[int]] = {
            name: set(chapters) for name, chapters in SUBSECTION_CHAPTER_INDEX.items()
        }

    def tick(self) -> tuple[DisplayInfo, Optional[Split], Optional[ChapterTotal]]:
        """
        Update timer state based on current memory snapshot.
        
        Returns:
            Tuple of (display_info, new_split_or_none, chapter_total_or_none)
        """
        snap = self.reader.read_snapshot()

        early_result = self._handle_non_processable_snapshot(snap)
        if early_result is not None:
            return early_result

        self._cache_last_valid_igt(snap.igt_seconds)

        new_split, chapter_total = self._process_snapshot(snap)
        display = self._create_display_info(snap)

        return display, new_split, chapter_total

    # =========================================================================
    # Snapshot Processing
    # =========================================================================

    def _process_snapshot(self, snap: GameSnapshot) -> tuple[Optional[Split], Optional[ChapterTotal]]:
        """Process a game snapshot and detect split events."""
        igt = snap.igt_seconds
        chapter_str = str(snap.chapter) if snap.chapter is not None else ""

        debug_print(
            f"IGT={igt}, Chapter={snap.chapter}, SubA='{snap.subsection_a}' SubB='{snap.subsection_b}'"
        )

        # Handle load transition (IGT briefly goes to 0)
        if self._is_in_load_transition(igt):
            return None, None

        # Handle reset detection
        if self._handle_reset_if_needed(snap, igt):
            return None, None

        self.state.last_seen_igt = igt

        # Handle chapter change
        chapter_total = self._handle_chapter_change(snap, igt)

        # Start run if needed
        self._start_run_if_needed(snap, igt)

        # Seed current subsection carefully (avoid stale subsection B during chapter swaps)
        if not self.state.current_subsection:
            subB_matches_chapter = self._is_subsection_valid_for_chapter(snap.chapter, snap.subsection_b)
            carryover = self.state.carryover_subsection_b
            carryover_invalid = carryover and not self._is_subsection_valid_for_chapter(snap.chapter, carryover)

            if (
                carryover_invalid
                and snap.subsection_b == carryover
                and snap.subsection_a
            ):
                # B is still the carryover value; use subsection A (entry point) instead.
                self.state.current_subsection = snap.subsection_a
            elif subB_matches_chapter and snap.subsection_b:
                self.state.current_subsection = snap.subsection_b
            elif snap.subsection_a:
                self.state.current_subsection = snap.subsection_a
            elif snap.current_subsection:
                self.state.current_subsection = snap.current_subsection

        # Process pending chapter finalization
        if self._pending_finalize_chapter:
            pending_total = self.history.finalize_chapter(self._pending_finalize_chapter)
            self._pending_finalize_chapter = None
            if pending_total is not None:
                chapter_total = pending_total

        # Check for first subsection marker
        self._check_first_subsection_marker(snap)

        # Detect split
        new_split = self._detect_split(snap, igt, chapter_str)

        return new_split, chapter_total

    def _handle_non_processable_snapshot(
        self,
        snap: GameSnapshot
    ) -> Optional[tuple[DisplayInfo, Optional[Split], Optional[ChapterTotal]]]:
        """Return an early response for detached or temporarily unreadable snapshots."""
        if not snap.attached:
            self.state.in_load_transition = False
            return DisplayInfo.not_attached(), None, None

        if snap.igt_seconds is not None:
            return None

        if self._update_load_transition(None):
            return self._create_display_info(snap), None, None

        return DisplayInfo.not_attached(), None, None

    def _cache_last_valid_igt(self, igt: Optional[int]):
        """Store the most recent positive IGT for temporary display hold during loads."""
        if igt is not None and igt > 0:
            self.state.last_valid_igt = igt

    def _is_subsection_valid_for_chapter(self, chapter: Optional[int], subsection: str) -> bool:
        """Return True unless we know this subsection belongs to another chapter."""
        if not subsection:
            return False

        subsection_lower = subsection.lower()
        if subsection_lower in FIRST_SUBSECTION_MARKERS:
            return True

        chapters = self.subsection_chapter_index.get(subsection_lower)
        if chapters is None:
            return True  # No mapping info; assume valid.

        if chapter is None:
            return False

        return chapter in chapters

    def _register_subsection_chapter(self, chapter: Optional[int], subsection: str):
        """Learn that a subsection belongs to a chapter (for future validation)."""
        if chapter is None or not subsection:
            return

        subsection_lower = subsection.lower()
        chapters = self.subsection_chapter_index.setdefault(subsection_lower, set())
        chapters.add(chapter)

    def _can_enter_load_transition(self) -> bool:
        """Return True when a zero/unreadable IGT can be safely treated as a transient load."""
        return (
            self.state.run_active and
            self.state.last_seen_igt is not None and
            self.state.last_seen_igt > 0 and
            self.state.last_valid_igt is not None
        )

    def _update_load_transition(self, igt: Optional[int]) -> bool:
        """Update load-transition state and return whether the current tick should be treated as loading."""
        if self.state.in_load_transition:
            if igt is not None and igt > 0:
                debug_print(f"Load complete, IGT={igt}")
                self.state.in_load_transition = False
                return False
            return True

        if igt in (0, None) and self._can_enter_load_transition():
            debug_print("Load transition detected")
            self.state.in_load_transition = True
            return True

        return False

    def _is_in_load_transition(self, igt: Optional[int]) -> bool:
        """Check if we're in a load transition (IGT briefly goes to 0 or becomes unreadable)."""
        return self._update_load_transition(igt)

    def _handle_reset_if_needed(self, snap: GameSnapshot, igt: int) -> bool:
        """
        Detect and handle IGT going backwards (quickload/restart).

        Returns True if a reset was handled and processing should stop.
        """
        if not self._detect_reset(igt):
            return False

        # Check if it's a segment reload vs checkpoint load vs full reset
        same_chapter = (snap.chapter == self.state.current_chapter)

        # After loading, subsection_a is where we spawned - use it as primary indicator
        spawned_at = snap.subsection_a
        same_subsection = (
            spawned_at == self.state.current_subsection or
            spawned_at == self.state.last_subsection_b or
            # Fallback if subsection_a is empty: check if subsection_b unchanged
            (not spawned_at and snap.subsection_b == self.state.last_subsection_b)
        )

        if same_chapter and same_subsection:
            # Segment reload (death/quickload at same checkpoint) - just reset segment timer
            debug_print(f"Segment reload detected - resetting segment timer to IGT={igt}")
            self.state.segment_start_igt = igt
            self.state.last_seen_igt = igt
        elif same_chapter and spawned_at:
            # Loaded a different checkpoint in the same chapter
            debug_print(f"Checkpoint load detected - {self.state.current_subsection} -> {spawned_at}")
            self.state.segment_start_igt = igt
            self.state.last_seen_igt = igt
            self.state.current_subsection = spawned_at
            self.state.last_subsection_b = spawned_at
            self.state.seen_nonblank_b_this_chapter = True
        else:
            # Full reset - clear everything
            debug_print("Full reset detected - clearing splits")
            self.state.reset()
            self.history.clear()
            self._pending_finalize_chapter = None

        return True

    def _detect_reset(self, current_igt: int) -> bool:
        """Detect if IGT went backwards (quickload/restart)."""
        if self.state.last_seen_igt is None:
            return False
        return current_igt + 1 < self.state.last_seen_igt

    def _handle_chapter_change(self, snap: GameSnapshot, igt: int) -> Optional[ChapterTotal]:
        """Handle chapter transitions, returns chapter total if one was finalized."""
        chapter = snap.chapter
        
        if chapter is None or chapter == self.state.current_chapter:
            return None

        debug_print(f"Chapter change: {self.state.current_chapter} -> {chapter}")

        # Finalize previous chapter
        chapter_total = None
        if self.state.current_chapter is not None:
            prev_chapter_str = str(self.state.current_chapter)
            chapter_total = self.history.finalize_chapter(prev_chapter_str)

        # Reset state for new chapter
        carryover_subsection_b = self.state.last_subsection_b
        if carryover_subsection_b and self._is_subsection_valid_for_chapter(chapter, carryover_subsection_b):
            carryover_subsection_b = ""
        self.state.start_new_chapter(chapter, igt, carryover_subsection_b)

        return chapter_total

    def _start_run_if_needed(self, snap: GameSnapshot, igt: int):
        """Start the run if conditions are met."""
        if self.state.run_active:
            return

        if snap.chapter is not None and igt >= 0:
            debug_print(f"[ATTACH] Starting run at IGT={igt}, Chapter={snap.chapter}")

            # Determine starting segment time:
            # - New game or chapter quickload (very low IGT): Start from 0 so segment matches IGT
            # - Mid-run attach (high IGT): Use current IGT so segment shows 0 on attach
            if igt <= 5:
                # Low IGT - treat as chapter start (force segment to 0)
                # This handles both new games (IGT=0) and chapter quickloads (IGT=1)
                debug_print(f"[ATTACH] Low IGT detected, forcing segment_start_igt=0")
                self.state.segment_start_igt = 0
            else:
                # High IGT - mid-run attach
                debug_print(f"[ATTACH] Mid-run attach, setting segment_start_igt={igt}")
                self.state.segment_start_igt = igt

            self.state.run_active = True
            # Do NOT pre-seed seen_nonblank_b_this_chapter or last_subsection_b here.
            # Let _detect_split handle the first subsection_b naturally - since
            # igt == segment_start_igt on attach, no split will fire until the
            # player actually moves to a new checkpoint.

    def _check_first_subsection_marker(self, snap: GameSnapshot):
        """Check if we've hit a first subsection marker (triggers chapter finalization)."""
        subsection_key = snap.current_subsection.lower()
        
        if subsection_key not in FIRST_SUBSECTION_MARKERS:
            return
        
        if self._pending_finalize_chapter is not None:
            return
        
        if not self.history.splits:
            return

        chapter_to_finalize = self.history.splits[-1].chapter
        if (chapter_to_finalize and 
            chapter_to_finalize != "--" and
            not self.history.is_chapter_finalized(chapter_to_finalize)):
            self._pending_finalize_chapter = chapter_to_finalize

    # =========================================================================
    # Split Detection
    # =========================================================================

    def _detect_split(self, snap: GameSnapshot, igt: int, chapter_str: str) -> Optional[Split]:
        """Detect if a split should occur based on subsection B changes."""
        subB = snap.subsection_b

        if not subB:
            return None

        subB_valid = self._is_subsection_valid_for_chapter(snap.chapter, subB)

        # Handle carryover from previous chapter
        if not self._handle_carryover_subsection(snap, subB, subB_valid):
            return None

        # Validate subsection for current chapter
        if not subB_valid:
            debug_print(
                f"Subsection B '{subB}' not valid for chapter {snap.chapter}; waiting for correct subsection"
            )
            return None

        self._register_subsection_chapter(snap.chapter, subB)

        # Determine if we should split and what subsection triggered it
        should_split, split_subsection = self._should_create_split(snap, subB, igt)
        self.state.last_subsection_b = subB

        if not should_split:
            return None

        # Create and record the split
        return self._create_and_record_split(snap, igt, chapter_str, split_subsection, subB)

    def _handle_carryover_subsection(self, snap: GameSnapshot, subB: str, subB_valid: bool) -> bool:
        """
        Handle stale subsection B carried over from previous chapter.

        Returns False if processing should stop (subsection is stale carryover).
        """
        if self.state.seen_nonblank_b_this_chapter or not self.state.carryover_subsection_b:
            return True

        carryover = self.state.carryover_subsection_b
        carryover_valid = self._is_subsection_valid_for_chapter(snap.chapter, carryover)

        if carryover_valid:
            # Carryover is valid for this chapter too, clear it
            self.state.carryover_subsection_b = ""
            return True

        # Carryover is not valid for this chapter
        if subB == carryover:
            debug_print(f"Ignoring carryover subsection B from previous chapter: {subB}")
            return False

        if subB_valid:
            debug_print(f"Carryover subsection B cleared: {carryover} -> {subB}")
            if not self.state.current_subsection and snap.subsection_a:
                # Use the entry checkpoint as our departure reference for the upcoming split
                self.state.current_subsection = snap.subsection_a
            self.state.carryover_subsection_b = ""

        return True

    def _should_create_split(self, snap: GameSnapshot, subB: str, igt: int) -> tuple[bool, Optional[str]]:
        """
        Determine if a split should be created.

        Returns (should_split, split_subsection) where split_subsection is the
        departure point (where we came FROM, not where we arrived).
        """
        if not self.state.seen_nonblank_b_this_chapter:
            # First subsection B in this chapter
            debug_print(f"First subsection B in chapter: {subB}")
            self.state.seen_nonblank_b_this_chapter = True

            if self.state.segment_start_igt is not None and igt > self.state.segment_start_igt:
                split_subsection = self.state.current_subsection or snap.subsection_a
                return True, split_subsection

            return False, None

        if subB != self.state.last_subsection_b:
            # Subsection changed
            debug_print(f"Subsection B changed: {self.state.last_subsection_b} -> {subB}")
            return True, self.state.last_subsection_b

        return False, None

    def _create_and_record_split(
        self,
        snap: GameSnapshot,
        igt: int,
        chapter_str: str,
        split_subsection: Optional[str],
        new_subsection: str
    ) -> Optional[Split]:
        """
        Create a split object and update state.

        Returns the new Split or None if duration is invalid.
        """
        if self.state.segment_start_igt is None:
            return None

        duration = igt - self.state.segment_start_igt
        if duration <= 0:
            return None

        split_number = self._get_split_number(snap.chapter, split_subsection, chapter_str)

        split = Split(
            chapter=chapter_str,
            number=split_number,
            duration_seconds=duration,
            subsection_name=split_subsection
        )

        debug_print(f"NEW SPLIT: {split.label} - {split.formatted_time}")

        # Update state for next segment
        self.state.segment_start_igt = igt
        self.state.current_subsection = new_subsection
        self.history.add_split(split)

        return split

    def _get_split_number(self, chapter: Optional[int], subsection: str, chapter_str: str) -> int:
        """Determine the split number for a subsection."""
        used_numbers = self.history.get_used_numbers_for_chapter(chapter_str)

        # Check if this is a first subsection marker (chapter start = split 1)
        if subsection and subsection.lower() in FIRST_SUBSECTION_MARKERS:
            return 1

        # Try SUBSECTION_MAP first (case-insensitive lookup)
        if chapter is not None and subsection:
            subsection_lower = subsection.lower()
            map_value = SUBSECTION_MAP.get((chapter, subsection_lower))

            if map_value is not None:
                if isinstance(map_value, list):
                    # Multiple possible - find first unused
                    for num in map_value:
                        if num not in used_numbers:
                            return num
                    # All options used, return first one anyway
                    return map_value[0]
                else:
                    # Single mapped value - always use it for this subsection
                    return map_value

        # Fallback: find next unused number
        next_num = 1
        while next_num in used_numbers:
            next_num += 1
        return next_num

    # =========================================================================
    # Display Creation
    # =========================================================================

    def _create_display_info(self, snap: GameSnapshot) -> DisplayInfo:
        """Create DisplayInfo from current state and snapshot."""
        chapter = snap.chapter

        igt = self._get_display_igt(snap.igt_seconds)

        # Calculate current segment time
        current_segment_seconds = None
        if self.state.segment_start_igt is not None and igt is not None:
            current_segment_seconds = max(0, igt - self.state.segment_start_igt)
            debug_print(f"[DISPLAY] IGT={igt}, segment_start={self.state.segment_start_igt}, current_segment={current_segment_seconds}")

        # Determine chapter.split text
        chapter_text = self._format_chapter_text(snap, chapter)

        return DisplayInfo(
            igt_text=format_time(igt),
            chapter_text=chapter_text,
            current_segment_text=format_time(current_segment_seconds, include_hours=False),
            attached=True
        )

    def _get_display_igt(self, igt: Optional[int]) -> Optional[int]:
        """Return the IGT value that should be shown in the UI for the current tick."""
        if (
            self.state.in_load_transition and
            igt in (0, None) and
            self.state.last_valid_igt is not None
        ):
            return self.state.last_valid_igt

        return igt

    def _get_effective_display_subsection(self, snap: GameSnapshot) -> str:
        """Return subsection best representing the player's current checkpoint for display."""
        subB = snap.subsection_b
        subA = snap.subsection_a
        carryover = self.state.carryover_subsection_b
        carryover_invalid = (
            carryover and not self._is_subsection_valid_for_chapter(snap.chapter, carryover)
        )

        # If subsection_a matches our tracked position but subsection_b differs,
        # prefer subsection_a (handles stale subsection_b after checkpoint load)
        if subA and subA == self.state.current_subsection:
            if self._is_subsection_valid_for_chapter(snap.chapter, subA):
                if subB != subA:
                    return subA

        if subB and self._is_subsection_valid_for_chapter(snap.chapter, subB):
            if not (carryover_invalid and subB == carryover):
                return subB

        if subA:
            return subA

        return self.state.current_subsection or subB or ""

    def _format_chapter_text(self, snap: GameSnapshot, chapter: Optional[int]) -> str:
        """Format the chapter.split display text."""
        if chapter is None:
            return "--"

        chapter_str = str(chapter)

        # Determine best subsection to represent current position
        current_sub = self._get_effective_display_subsection(snap)

        # Check if at chapter start marker
        if current_sub and current_sub.lower() in FIRST_SUBSECTION_MARKERS:
            return f"{chapter}.1"

        if not current_sub:
            current_sub = self.state.current_subsection

        current_split_num = self._get_split_number(chapter, current_sub, chapter_str)

        return f"{chapter}.{current_split_num}"

    def _lookup_split_number(self, chapter: int, subsection: str) -> Optional[int]:
        """Look up split number from the subsection map (case-insensitive)."""
        if not subsection:
            return None

        map_value = SUBSECTION_MAP.get((chapter, subsection.lower()))
        if map_value is None:
            return None

        if isinstance(map_value, list):
            return map_value[0]
        return map_value

    # =========================================================================
    # Public Methods
    # =========================================================================

    def reset_splits(self):
        """Manually reset all splits."""
        self.state.reset()
        self.history.clear()
        self._pending_finalize_chapter = None
