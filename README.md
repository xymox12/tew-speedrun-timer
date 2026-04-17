# The Evil Within IGT Speedrun Timer

A speedrun timer that reads in-game time (IGT) directly from process memory and auto-splits based on checkpoint changes.

## Quick Start

```bash
pip install -r requirements.txt
python main.py  # Requires The Evil Within running
```

## Architecture

```
EvilWithin.exe -> MemoryReader -> TimerController -> TimerWindow (UI)
```

The timer polls game memory every 200ms, detects state changes, and triggers splits automatically.

## Memory Pointers

The application reads four values from game memory. All addresses are relative to the `EvilWithin.exe` module base address.

### IGT (In-Game Time)

**Purpose:** The authoritative speedrun timer value (in seconds).

**Pointer Chain:**
```
Base + 0x02258E00 -> +0x68 -> +0x28 -> +0x00 = Player entity in idGameLocal
                                    -> +0x8D8C = IGT value (int32)
```

This is a multi-level pointer that navigates to the player entity within the game's `idGameLocal` entity list:
1. Read pointer at `base + BASE_OFFSET` (0x02258E00)
2. Add `0x68`, read pointer
3. Add `0x28`, read pointer (points to player entity)
4. Add `0x8D8C` to get final address containing IGT within the player entity

**Implementation:** `memory_reader.py:53-59` (`resolve_pointer_chain`)

### Chapter Number

**Purpose:** Identifies current chapter (1-15). Used for split labeling and chapter totals.

**Address:** `base + 0x225DCE8` (direct read)

### Subsection A

**Purpose:** The player's spawn/entry point checkpoint name. Used to detect segment reloads vs checkpoint loads.

**Address:** Pointer at `base + 0x9C58A88` -> offset `0x218`

The struct pointer is dereferenced first, then the subsection string is read at offset `0x218` within that struct.

### Subsection B

**Purpose:** Current active checkpoint. Changes trigger splits.

**Address:** `base + 0x9C83638` (direct string read)

This is the primary split trigger - when `subsection_b` changes, a new split is recorded.

## String Encoding

Game strings can be stored in multiple formats. The `StringField` class auto-detects and caches:
- Inline UTF-16 (wide)
- Inline UTF-8
- Pointer to UTF-16
- Pointer to UTF-8

## Split Detection Logic

1. **Subsection B changes** -> Create split with duration since last checkpoint
2. **Chapter changes** -> Finalize previous chapter total, reset segment timer
3. **IGT goes backward** -> Detect reset type (segment reload / checkpoint load / full reset)
4. **IGT goes to 0 briefly** -> Load transition, freeze display at last valid IGT

### Subsection Carryover

When entering a new chapter, `subsection_b` may briefly retain a stale value from the previous chapter. The controller tracks `seen_nonblank_b_this_chapter` and `carryover_subsection_b` to avoid false split triggers.

## Split Numbering

Splits are numbered using `SUBSECTION_MAP` in `subsection_data.py`:

```python
SUBSECTION_MAP = {
    (chapter, "subsection_name"): split_number,
    # Example:
    (1, "st13_gamedesign_b_player_start_1"): 2,
    (9, "gamedesign01_player_start_1"): [3, 4, 5],  # Multiple possible
}
```

When a subsection has multiple possible numbers (visited multiple times), the first unused number is selected.

## Configuration

Key values in `config.py`:

| Constant | Value | Description |
|----------|-------|-------------|
| `PROC_NAME` | `EvilWithin.exe` | Target process |
| `READ_INTERVAL_MS` | `200` | Polling interval |
| `BASE_OFFSET` | `0x02258E00` | IGT pointer chain start |
| `POINTER_OFFSETS` | `(0x68, 0x28, 0x8D8C)` | IGT chain offsets |

## Testing

```bash
pytest                           # All tests
pytest tests/test_controller.py  # Controller tests only
```

Tests use `FakeMemoryReader` to simulate game states without running the actual game.
