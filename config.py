# config.py
"""Configuration settings for the timer application."""

# Process and memory settings
PROC_NAME = "EvilWithin.exe"

# IGT pointer chain
BASE_OFFSET = 0x02258E00
POINTER_OFFSETS = (0x68, 0x28, 0x8D8C)

# Memory offsets for chapter and subsections
OFFSETS = {
    "chapter_rel": 0x225DCE8,
    "struct_ptr_rel": 0x9C58A88,
    "map_name_off": 0x0F0,
    "subA_off": 0x218,
    "subB_abs": 0x9C83638,
}

# Timing
READ_INTERVAL_MS = 200

# UI settings
BG_COLOR = "#1E1E1E"
FG_COLOR = "#E0E0E0"
FG_COLOR_SUBDUED = "#B2B2B2"    # Chapter/split labels
DIVIDER_COLOR = "#2B2B2B"       # Horizontal divider line
SELECTED_BG_COLOR = "#2A3442"   # Selected row in split list
FONT_TIME = ("Consolas", 16)
FONT_MONO = ("Consolas", 10)

# UI padding (left/right, top, bottom)
PAD_X = 10                  # Horizontal padding for content
PAD_TOP = 12               # Top padding above IGT
PAD_IGT_BOTTOM = 6          # Below IGT label
PAD_SUBLINE_BOTTOM = 2      # Below chapter/split line
PAD_DIVIDER = (4, 6)        # Above/below divider line
PAD_SPLITS_BOTTOM = 16      # Below split list

# Split numbering configuration
SPLIT_START_NUMBER = 1

# First subsection markers that indicate chapter start
FIRST_SUBSECTION_MARKERS = {
    "player_start",
    "st06_asylummain_player_start_chapter4_division",
}

# Debug mode
DEBUG = False
