# ui_tk.py
"""Tkinter-based UI for the timer application."""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from config import (
    BG_COLOR, FG_COLOR, FG_COLOR_SUBDUED, DIVIDER_COLOR, SELECTED_BG_COLOR,
    FONT_TIME, FONT_MONO, READ_INTERVAL_MS,
    PAD_X, PAD_TOP, PAD_IGT_BOTTOM, PAD_SUBLINE_BOTTOM, PAD_DIVIDER, PAD_SPLITS_BOTTOM
)
from controller import TimerController
from model import Split, ChapterTotal


class TimerWindow:
    """Main UI window for the timer."""

    def __init__(self):
        self.root = tk.Tk()
        self._configure_window()
        self.controller = TimerController()
        self._build_widgets()
        self._schedule_poll()

    def _configure_window(self):
        """Configure the main window."""
        self.root.title("TEW IGT Timer")
        self.root.configure(bg=BG_COLOR)
        self.root.geometry("220x300")
        self.root.resizable(False, False)

    # =========================================================================
    # Widget Building
    # =========================================================================

    def _build_widgets(self):
        """Build all UI widgets."""
        self._configure_styles()

        # IGT Display (centered)
        self.label_igt = tk.Label(
            self.root, text="00:00:00",
            bg=BG_COLOR, fg=FG_COLOR, font=FONT_TIME
        )
        self.label_igt.pack(pady=(PAD_TOP, PAD_IGT_BOTTOM))

        # Chapter + Split (single row)
        self._build_subline()

        # Divider
        tk.Frame(self.root, bg=DIVIDER_COLOR, height=1).pack(fill="x", padx=PAD_X, pady=PAD_DIVIDER)

        # Split list
        self.split_tree = self._create_split_tree()
        self.split_tree.pack(padx=PAD_X, pady=(0, PAD_SPLITS_BOTTOM), fill="both", expand=True)

        # Bindings
        self.split_tree.bind("<MouseWheel>", self._on_mousewheel)
        self.split_tree.bind("<Button-3>", self._show_context_menu)

    def _configure_styles(self):
        """Configure ttk styles for a compact, minimal layout."""
        style = ttk.Style(self.root)
        style.configure(
            "Split.Treeview",
            background=BG_COLOR,
            fieldbackground=BG_COLOR,
            foreground=FG_COLOR_SUBDUED,
            font=FONT_MONO,
            rowheight=18,
            borderwidth=0
        )
        style.map(
            "Split.Treeview",
            background=[("selected", SELECTED_BG_COLOR)],
            foreground=[("selected", FG_COLOR_SUBDUED)]
        )
        style.layout("Split.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    def _build_subline(self):
        """Build the compact chapter/split subline."""
        frame = tk.Frame(self.root, bg=BG_COLOR)
        frame.pack(fill="x", padx=PAD_X, pady=(0, PAD_SUBLINE_BOTTOM))

        self.label_chapter = tk.Label(
            frame, text="Ch --",
            bg=BG_COLOR, fg=FG_COLOR, font=FONT_MONO
        )
        self.label_chapter.pack(side="left")

        self.label_current = tk.Label(
            frame, text="Split 00:00",
            bg=BG_COLOR, fg=FG_COLOR, font=FONT_MONO
        )
        self.label_current.pack(side="right")

    def _create_labeled_row(
        self, 
        label_text: str, 
        initial_value: str,
        font_label: tuple = FONT_MONO,
        font_value: tuple = FONT_MONO,
        pack_opts: Optional[dict] = None
    ) -> tk.Label:
        """
        Create a row with a label and value display.
        
        Returns the value label widget for later updates.
        """
        frame = tk.Frame(self.root, bg=BG_COLOR)
        frame.pack(**(pack_opts or {}))

        tk.Label(
            frame, text=label_text,
            bg=BG_COLOR, fg=FG_COLOR, font=font_label
        ).pack(side="left")

        value_label = tk.Label(
            frame, text=initial_value,
            bg=BG_COLOR, fg=FG_COLOR, font=font_value, anchor="w"
        )
        value_label.pack(side="left")

        return value_label

    def _create_split_tree(self) -> ttk.Treeview:
        """Create the split history treeview."""
        tree = ttk.Treeview(
            self.root,
            columns=("time",),
            show="tree",
            selectmode="browse",
            style="Split.Treeview"
        )
        tree.column("#0", anchor="w", width=90, stretch=True)
        tree.column("time", anchor="center", width=60, stretch=False)
        return tree

    # =========================================================================
    # Polling and Updates
    # =========================================================================

    def _schedule_poll(self):
        """Schedule the next poll."""
        self.root.after(READ_INTERVAL_MS, self._poll)

    def _poll(self):
        """Main polling loop."""
        display, new_split, chapter_total = self.controller.tick()

        # Update display labels
        self.label_igt.config(text=display.igt_text)
        self.label_chapter.config(text=f"Ch {display.chapter_text}")
        self.label_current.config(text=f"Split {display.current_segment_text}")

        # Add new entries to split list
        if new_split:
            self._add_entry_to_list(new_split.label, new_split.formatted_time)

        if chapter_total:
            self._add_entry_to_list(
                chapter_total.label, 
                chapter_total.formatted_time, 
                add_blank_after=True
            )

        self._schedule_poll()

    def _add_entry_to_list(self, label: str, time: str, add_blank_after: bool = False):
        """Add an entry to the split listbox."""
        self.split_tree.insert("", "end", text=label, values=(time,))

        if add_blank_after:
            self.split_tree.insert("", "end", text="", values=("",))

        # Auto-scroll to bottom
        self.split_tree.yview_moveto(1.0)

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        direction = -1 if event.delta > 0 else 1
        self.split_tree.yview_scroll(direction, "units")

    def _show_context_menu(self, event):
        """Show right-click context menu."""
        menu = tk.Menu(self.root, tearoff=0, bg=BG_COLOR, fg=FG_COLOR)
        menu.add_command(label="Copy All", command=self._copy_all_splits)
        menu.add_command(label="Copy Selected", command=self._copy_selected_split)
        menu.add_separator()
        menu.add_command(label="Reset Splits", command=self._reset_splits)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # =========================================================================
    # Actions
    # =========================================================================

    def _copy_to_clipboard(self, text: str):
        """Copy text to system clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _copy_all_splits(self):
        """Copy all splits to clipboard."""
        lines = []
        for item_id in self.split_tree.get_children(""):
            item = self.split_tree.item(item_id)
            label = item.get("text", "")
            values = item.get("values", [])
            time = values[0] if values else ""
            if not label and not time:
                lines.append("")
            else:
                lines.append(f"{label} {time}".strip())
        self._copy_to_clipboard("\n".join(lines))

    def _copy_selected_split(self):
        """Copy selected split to clipboard."""
        selection = self.split_tree.selection()
        if selection:
            item = self.split_tree.item(selection[0])
            label = item.get("text", "")
            values = item.get("values", [])
            time = values[0] if values else ""
            self._copy_to_clipboard(f"{label} {time}".strip())

    def _reset_splits(self):
        """Reset all splits."""
        self.controller.reset_splits()
        self.split_tree.delete(*self.split_tree.get_children(""))

    # =========================================================================
    # Main Loop
    # =========================================================================

    def run(self):
        """Start the UI main loop."""
        self.root.mainloop()
