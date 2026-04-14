# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A speedrun timer for "The Evil Within" that reads in-game time (IGT) from process memory and automatically detects splits based on game state changes.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application (requires The Evil Within running)
python main.py

# Run tests
pytest                           # All tests
pytest -q                        # Concise output
pytest tests/test_controller.py  # Single file
```

## Architecture

**MVC pattern with memory-reading backend:**

```
main.py → TimerWindow (ui_tk.py)
              ↓
         TimerController (controller.py)
              ↓
         MemoryReader (memory_reader.py) → EvilWithin.exe process memory
```

**Data flow each tick (200ms polling):**
1. `MemoryReader.read_snapshot()` reads IGT, chapter, and subsection strings from game memory
2. `controller.tick()` processes the snapshot: detects splits, resets, chapter changes
3. Returns `DisplayInfo` + optional `Split`/`ChapterTotal` for UI update

## Key Modules

| Module | Responsibility |
|--------|----------------|
| `controller.py` | Split detection, reset handling, chapter transitions, state machine |
| `model.py` | Data classes: `GameSnapshot`, `TimerState`, `Split`, `ChapterTotal`, `DisplayInfo` |
| `memory_reader.py` | Process attachment, pointer chain traversal, string encoding detection |
| `config.py` | Memory offsets, UI colors, timing constants |
| `subsection_data.py` | Maps (chapter, subsection_name) → split_number for all 15 chapters |

## State Machine Logic (controller.py)

**Critical state transitions:**
- **Load transition**: IGT→0 while run active; display freezes at last valid IGT
- **Split detection**: `subsection_b` changes → create Split, reset segment timer
- **Chapter change**: Finalize previous chapter total (ΣCh#), handle subsection carryover
- **Reset detection**: IGT goes backward → segment reload, checkpoint load, or full reset

**Subsection carryover**: When entering a new chapter, `subsection_b` may briefly hold a stale value from the previous chapter. The controller uses `seen_nonblank_b_this_chapter` flag to avoid false split triggers.

## Testing Approach

Tests use `FakeMemoryReader` to simulate game states without running the actual game. Key test scenarios:
- Load transitions preserving display
- Reset detection (segment/checkpoint/full)
- Chapter boundary handling with subsection carryover
- Split numbering via SUBSECTION_MAP lookup

## Memory Reading Details

The game stores strings in two formats that `memory_reader.py` auto-detects:
- Direct embedded UTF-16 strings (subsection_a)
- Pointer to UTF-8 string (subsection_b)

Pointer chain: `BASE_OFFSET` → multiple dereferences via `POINTER_OFFSETS` → IGT value

See AGENTS.md for coding style, commit guidelines, and testing requirements.
