"""Cross-platform arrow-key menu using msvcrt on Windows and termios on Unix."""

import sys
import os


HEADER = r"""
    ███╗   ██╗██╗     ██╗   ██╗
    ████╗  ██║██║     ╚██╗ ██╔╝
    ██╔██╗ ██║██║      ╚████╔╝
    ██║╚██╗██║██║       ╚██╔╝
    ██║ ╚████║███████╗   ██║
    ╚═╝  ╚═══╝╚══════╝   ╚═╝
"""


def _clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _print_header():
    print("\033[1;36m" + HEADER + "\033[0m")
    print("\033[1;32m" + "=" * 60 + "\033[0m")


def _get_key_windows():
    """Read a single keypress on Windows using msvcrt."""
    import msvcrt

    ch = msvcrt.getch()
    if ch in (b"\x00", b"\xe0"):
        ch2 = msvcrt.getch()
        if ch2 == b"H":
            return "UP"
        if ch2 == b"P":
            return "DOWN"
        if ch2 == b"K":
            return "LEFT"
        if ch2 == b"M":
            return "RIGHT"
        return None
    if ch == b"\r" or ch == b"\n":
        return "ENTER"
    if ch == b"\x1b":
        return "ESC"
    if ch == b"\x03":
        raise KeyboardInterrupt
    try:
        return ch.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _get_key_unix():
    """Read a single keypress on Unix-like systems."""
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                if ch3 == "A":
                    return "UP"
                if ch3 == "B":
                    return "DOWN"
                if ch3 == "C":
                    return "RIGHT"
                if ch3 == "D":
                    return "LEFT"
            return "ESC"
        if ch == "\r" or ch == "\n":
            return "ENTER"
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _get_key():
    if os.name == "nt":
        return _get_key_windows()
    return _get_key_unix()


def arrow_select(title: str, choices: list[tuple[str, str]], banner: str = "") -> str | None:
    """Show an arrow-key navigable menu and return the selected key."""
    selected = 0
    total = len(choices)

    while True:
        _clear_screen()
        _print_header()
        if banner:
            print(banner)

        if title:
            print(f"\n  \033[1;36m{title}\033[0m\n")

        for i, (key, label) in enumerate(choices):
            if i == selected:
                print(f"  \033[1;36m> {label}\033[0m")
            else:
                print(f"  \033[90m  {label}\033[0m")

        print("\n  \033[90m[Arrow keys to move, Enter to select, ESC to cancel]\033[0m")

        key_pressed = _get_key()
        if key_pressed == "UP":
            selected = (selected - 1) % total
        elif key_pressed == "DOWN":
            selected = (selected + 1) % total
        elif key_pressed == "ENTER":
            return choices[selected][0]
        elif key_pressed == "ESC":
            return None


def arrow_confirm(title: str, default: bool = False) -> bool:
    """Show a yes/no prompt with arrow keys."""
    options = [(True, "Yes"), (False, "No")]
    selected = 0 if default else 1

    while True:
        _clear_screen()
        _print_header()
        print(f"\n  \033[1;36m{title}\033[0m\n")

        for i, (val, label) in enumerate(options):
            if i == selected:
                print(f"  \033[1;36m> {label}\033[0m")
            else:
                print(f"  \033[90m  {label}\033[0m")

        print("\n  \033[90m[Arrow keys to move, Enter to select, ESC to cancel]\033[0m")

        key_pressed = _get_key()
        if key_pressed == "UP" or key_pressed == "DOWN":
            selected = 1 - selected
        elif key_pressed == "ENTER":
            return options[selected][0]
        elif key_pressed == "ESC":
            return default


def arrow_text(title: str, default: str = "") -> str:
    """Show a text input prompt."""
    _clear_screen()
    _print_header()
    print(f"\n  \033[1;36m{title}\033[0m")
    if default:
        print(f"  \033[90m(default: {default})\033[0m")
    print()
    val = input("  >> ").strip()
    return val if val else default


def arrow_number(title: str, default: int = 0, min_val: int = 0, max_val: int = 100000) -> int:
    """Show a number input prompt with validation."""
    while True:
        _clear_screen()
        _print_header()
        print(f"\n  \033[1;36m{title}\033[0m")
        print(f"  \033[90m(default: {default}, range: {min_val}-{max_val})\033[0m")
        print()
        val = input("  >> ").strip()
        if not val:
            return default
        try:
            num = int(val)
            if min_val <= num <= max_val:
                return num
            print(f"\n  \033[1;31mMust be between {min_val} and {max_val}. Press any key...\033[0m")
            _get_key()
        except ValueError:
            print("\n  \033[1;31mPlease enter a valid number. Press any key...\033[0m")
            _get_key()
