# main.py
"""Entry point for the timer application."""

from ui_tk import TimerWindow


def main():
    """Entry point for the timer application."""
    window = TimerWindow()
    window.run()


if __name__ == "__main__":
    main()
