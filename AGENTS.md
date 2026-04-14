# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the entry point that launches the Tkinter UI in `ui_tk.py`.
- Core logic lives in `controller.py` (split detection) and `model.py` (data classes, time formatting, state management).
- `memory_reader.py` attaches to `EvilWithin.exe` via `pymem`/`psutil` using offsets in `config.py`; game subsection labels are mapped in `subsection_data.py`.
- Tests sit in `tests/` (`test_controller.py`, `test_model.py`). Keep new assets or helpers alongside the module they exercise.

## Setup, Build, and Run Commands
- Create env & install deps: `python -m venv .venv && source .venv/bin/activate` (or `Scripts\\activate`) then `pip install -r requirements.txt`.
- Run the timer locally: `python main.py` (expects The Evil Within running so memory offsets resolve).
- Run tests: `pytest` from repo root. Add `-q` for concise output when iterating.

## Coding Style & Naming Conventions
- Python, 4-space indentation, PEP 8 alignment. Favor short, imperative function names for actions and noun-based names for data structures.
- Type hints are expected (see `controller.py`, `model.py`); include return types on public helpers.
- Use docstrings for modules/classes/functions with non-obvious behavior. Keep debug output behind `DEBUG` in `config.py` or localized `debug_print` helpers.

## Testing Guidelines
- Add `tests/test_<module>.py` with `test_*` functions. Prefer small, deterministic cases over integration tests.
- Mock `MemoryReader` interactions when logic does 