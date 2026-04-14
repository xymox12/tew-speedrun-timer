# memory_reader.py
"""Memory reading utilities for game state extraction."""

from typing import Optional, Callable, TypeVar
import psutil
import pymem
import pymem.process

from config import PROC_NAME, BASE_OFFSET, POINTER_OFFSETS, OFFSETS, DEBUG
from model import GameSnapshot


def debug_print(*args):
    """Print debug messages if DEBUG is enabled."""
    if DEBUG:
        print("[DEBUG]", *args)


T = TypeVar('T')


# =============================================================================
# Safe Read Helpers
# =============================================================================

def safe_read(func: Callable[[], T], fallback: T = None) -> T:
    """Execute a read function with exception handling."""
    try:
        return func()
    except Exception:
        return fallback


def safe_read_chain(*funcs: Callable[[], T], fallback: T = None) -> T:
    """Try multiple read functions in order, return first success."""
    for func in funcs:
        result = safe_read(func)
        if result is not None:
            return result
    return fallback


# =============================================================================
# Low-Level Memory Operations
# =============================================================================

def get_module_base(pm: pymem.Pymem, module_name: str) -> int:
    """Get the base address of a module."""
    mod = pymem.process.module_from_name(pm.process_handle, module_name)
    return mod.lpBaseOfDll


def resolve_pointer_chain(pm: pymem.Pymem, base_addr: int,
                          base_offset: int, ptr_offsets: tuple) -> int:
    """Follow a chain of pointers to get final address."""
    addr = pm.read_longlong(base_addr + base_offset)
    for off in ptr_offsets[:-1]:
        addr = pm.read_longlong(addr + off)
    return addr + ptr_offsets[-1]


def read_ptr(pm: pymem.Pymem, addr: int) -> int:
    """Read a pointer value (tries 64-bit then 32-bit)."""
    return safe_read_chain(
        lambda: pm.read_longlong(addr),
        lambda: pm.read_int(addr),
        fallback=0
    )


def read_int_auto(pm: pymem.Pymem, addr: int) -> Optional[int]:
    """Read an int value, handling both direct and pointer-to-int cases."""
    # Try direct read first
    direct = safe_read(lambda: pm.read_int(addr))
    if direct is not None and direct not in (0, -1):
        return direct
    
    # Try pointer dereference
    ptr = read_ptr(pm, addr)
    if ptr:
        return safe_read(lambda: pm.read_int(ptr))
    
    return None


# =============================================================================
# String Reading
# =============================================================================

def is_valid_string(s: str) -> bool:
    """Check if a string is valid (not garbled/corrupted)."""
    if not s:
        return True
    printable_count = sum(1 for c in s if 32 <= ord(c) <= 126 or c in '\n\r\t')
    return printable_count / len(s) >= 0.5


def read_string(pm: pymem.Pymem, addr: int, wide: bool = False, 
                max_len: int = 512) -> str:
    """
    Read a null-terminated string from memory.
    
    Args:
        pm: Pymem instance
        addr: Memory address to read from
        wide: If True, read as UTF-16 (wide string), else UTF-8/Latin-1
        max_len: Maximum characters to read
    
    Returns:
        Decoded string or empty string on failure
    """
    if not addr:
        return ""
    
    try:
        raw = bytearray()
        step = 2 if wide else 1
        null_terminator = b"\x00\x00" if wide else b"\x00"
        
        for i in range(max_len):
            chunk = pm.read_bytes(addr + i * step, step)
            if not chunk or chunk == null_terminator:
                break
            raw += chunk
        
        if not raw:
            return ""
        
        encoding = "utf-16-le" if wide else "utf-8"
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")
    
    except Exception:
        return ""


class StringField:
    """
    Reads a string field that may be stored in various formats.
    
    Automatically detects whether the string is:
    - Inline or behind a pointer
    - C-style (UTF-8) or wide (UTF-16)
    
    Caches the detected mode for subsequent reads.
    """
    
    # All possible (pointer_mode, wide) combinations to try
    MODES = [
        (True, False),   # ptr + C string
        (True, True),    # ptr + wide string
        (False, False),  # inline + C string
        (False, True),   # inline + wide string
    ]

    def __init__(self, pm: pymem.Pymem, addr_func: Callable[[], int], name: str):
        self.pm = pm
        self.addr_func = addr_func
        self.name = name
        self._cached_mode: Optional[tuple[bool, bool]] = None

    def _try_read(self, base_addr: int, is_ptr: bool, is_wide: bool) -> str:
        """Attempt to read string with specific mode."""
        addr = read_ptr(self.pm, base_addr) if is_ptr else base_addr
        if not addr:
            return ""
        return read_string(self.pm, addr, wide=is_wide)

    def read(self) -> str:
        """Read the string, using cached mode if available."""
        base = self.addr_func()
        if not base:
            return ""

        # Try cached mode first
        if self._cached_mode:
            result = self._try_read(base, *self._cached_mode)
            if result and is_valid_string(result):
                return result
            self._cached_mode = None

        # Try all modes
        for mode in self.MODES:
            result = self._try_read(base, *mode)
            if result and is_valid_string(result):
                self._cached_mode = mode
                return result

        return ""


# =============================================================================
# Main Memory Reader Class
# =============================================================================

class MemoryReader:
    """Reads game memory and returns snapshots."""

    def __init__(self):
        self._pm: Optional[pymem.Pymem] = None
        self._base_addr: Optional[int] = None
        self._addresses: dict[str, int] = {}
        self._subA_reader: Optional[StringField] = None
        self._subB_reader: Optional[StringField] = None

    def _find_process(self) -> Optional[int]:
        """Find the game process ID."""
        for proc in psutil.process_iter(["name"]):
            name = proc.info.get("name")
            if name and name.lower() == PROC_NAME.lower():
                return proc.pid
        return None

    def _is_attached(self) -> bool:
        """Check if we're still attached to the process."""
        if self._pm is None:
            return False
        try:
            self._pm.read_int(self._addresses.get("igt_base", 0))
            return True
        except Exception:
            return False

    def _setup_addresses(self):
        """Calculate all memory addresses after attaching."""
        base = self._base_addr
        self._addresses = {
            "igt_base": base + BASE_OFFSET,
            "chapter": base + OFFSETS["chapter_rel"],
            "struct_ptr": base + OFFSETS["struct_ptr_rel"],
            "subB": base + OFFSETS["subB_abs"],
        }

    def _setup_string_readers(self):
        """Initialize string field readers."""
        def get_subA_addr() -> int:
            struct_ptr = read_ptr(self._pm, self._addresses["struct_ptr"])
            return (struct_ptr + OFFSETS["subA_off"]) if struct_ptr else 0

        self._subA_reader = StringField(self._pm, get_subA_addr, "subA")
        self._subB_reader = StringField(self._pm, lambda: self._addresses["subB"], "subB")

    def attach(self) -> bool:
        """Attach to the game process."""
        if self._is_attached():
            return True

        # Reset state
        self._pm = None
        self._base_addr = None

        pid = self._find_process()
        if pid is None:
            return False

        try:
            self._pm = pymem.Pymem()
            self._pm.open_process_from_id(pid)
            self._base_addr = get_module_base(self._pm, PROC_NAME)
            self._setup_addresses()
            self._setup_string_readers()
            return True
        except Exception:
            self._pm = None
            self._base_addr = None
            return False

    def read_snapshot(self) -> GameSnapshot:
        """Read current game state from memory."""
        if not self.attach():
            return GameSnapshot(attached=False)

        # Read IGT
        igt_seconds = safe_read(lambda: self._pm.read_int(
            resolve_pointer_chain(self._pm, self._base_addr, BASE_OFFSET, POINTER_OFFSETS)
        ))
        debug_print(f"[MEMORY] Read IGT from memory: {igt_seconds}")

        # Read chapter
        chapter = safe_read(lambda: read_int_auto(self._pm, self._addresses["chapter"]))

        # Read subsections
        subsection_a = safe_read(lambda: self._subA_reader.read().strip(), "")
        subsection_b = safe_read(lambda: self._subB_reader.read().strip(), "")

        return GameSnapshot(
            attached=True,
            igt_seconds=igt_seconds,
            chapter=chapter,
            subsection_a=subsection_a,
            subsection_b=subsection_b
        )
