
# model.py
"""Data models for the timer application."""

from dataclasses import dataclass, field, asdict
from typing import Optional, Protocol


def format_time(total_seconds: Optional[int], include_hours: bool = True) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    if total_seconds is None:
        return "--:--:--" if include_hours else "--:--"
    
    total_seconds = max(0, total_seconds)
    h, remainder = divmod(total_seconds, 3600)
    m, s = divmod(remainder, 60)
    
    if include_hours or h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class Displayable(Protocol):
    """Protocol for items that can be displayed in the split list."""
    
    @property
    def label(self) -> str: ...
    
    @property
    def formatted_time(self) -> str: ...


@dataclass
class GameSnapshot:
    """Snapshot of game state from memory."""
    attached: bool = False
    igt_seconds: Optional[int] = None
    chapter: Optional[int] = None
    subsection_a: str = ""
    subsection_b: str = ""
    
    @property
    def current_subsection(self) -> str:
        """Get the currently active subsection (prefer B over A)."""
        return self.subsection_b or self.subsection_a


@dataclass
class Split:
    """Represents a single split."""
    chapter: str
    number: int
    duration_seconds: int
    subsection_name: str = ""
    
    @property
    def label(self) -> str:
        """Format split label (e.g., '10.1')."""
        return f"{self.chapter}.{self.number}"
    
    @property
    def formatted_time(self) -> str:
        """Format split time."""
        return format_time(self.duration_seconds, include_hours=False)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ChapterTotal:
    """Represents totals for a completed chapter."""
    chapter: str
    total_seconds: int
    split_count: int
    
    @property
    def label(self) -> str:
        """Format chapter total label."""
        return f"ΣCh{self.chapter}"
    
    @property
    def formatted_time(self) -> str:
        """Format total time."""
        return format_time(self.total_seconds, include_hours=False)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class SplitHistory:
    """Manages the history of splits."""
    splits: list[Split] = field(default_factory=list)
    chapter_totals: dict[str, ChapterTotal] = field(default_factory=dict)
    finalized_chapters: set[str] = field(default_factory=set)
    
    def add_split(self, split: Split):
        """Add a new split to history."""
        self.splits.append(split)
    
    def finalize_chapter(self, chapter: str) -> Optional[ChapterTotal]:
        """Calculate and store totals for a chapter."""
        if chapter in self.finalized_chapters or chapter in ("", "--"):
            return None
        
        chapter_splits = self.get_splits_for_chapter(chapter)
        if not chapter_splits:
            return None
        
        total_seconds = sum(s.duration_seconds for s in chapter_splits)
        if total_seconds <= 0:
            return None
        
        self.finalized_chapters.add(chapter)
        chapter_total = ChapterTotal(
            chapter=chapter,
            total_seconds=total_seconds,
            split_count=len(chapter_splits)
        )
        self.chapter_totals[chapter] = chapter_total
        return chapter_total
    
    def get_splits_for_chapter(self, chapter: str) -> list[Split]:
        """Get all splits for a specific chapter."""
        return [s for s in self.splits if s.chapter == chapter]
    
    def get_used_numbers_for_chapter(self, chapter: str) -> set[int]:
        """Get all split numbers already used in a chapter."""
        return {s.number for s in self.get_splits_for_chapter(chapter)}
    
    def clear(self):
        """Clear all split history."""
        self.splits.clear()
        self.chapter_totals.clear()
        self.finalized_chapters.clear()
    
    def is_chapter_finalized(self, chapter: str) -> bool:
        """Check if a chapter has been finalized."""
        return chapter in self.finalized_chapters


@dataclass
class TimerState:
    """Internal state for the timer logic."""
    run_active: bool = False
    segment_start_igt: Optional[int] = None
    current_subsection: str = ""
    current_chapter: Optional[int] = None
    last_subsection_b: str = ""
    seen_nonblank_b_this_chapter: bool = False
    carryover_subsection_b: str = ""
    last_seen_igt: Optional[int] = None
    in_load_transition: bool = False
    last_valid_igt: Optional[int] = None  # Preserved during load transitions for display
    
    def reset(self):
        """Reset all state to defaults."""
        self.run_active = False
        self.segment_start_igt = None
        self.current_subsection = ""
        self.current_chapter = None
        self.last_subsection_b = ""
        self.seen_nonblank_b_this_chapter = False
        self.carryover_subsection_b = ""
        self.last_seen_igt = None
        self.in_load_transition = False
        self.last_valid_igt = None
    
    def start_new_chapter(self, chapter: int, igt: int, carryover_subsection_b: str = ""):
        """Reset state for a new chapter."""
        self.current_chapter = chapter
        self.last_subsection_b = ""
        self.seen_nonblank_b_this_chapter = False
        self.carryover_subsection_b = carryover_subsection_b
        self.segment_start_igt = igt
        self.current_subsection = ""


@dataclass
class DisplayInfo:
    """Information to display in the UI."""
    igt_text: str = "--:--:--"
    chapter_text: str = "--"
    current_segment_text: str = "--:--"
    attached: bool = False
    
    @classmethod
    def not_attached(cls) -> "DisplayInfo":
        """Create a display info for when not attached to game."""
        return cls()
