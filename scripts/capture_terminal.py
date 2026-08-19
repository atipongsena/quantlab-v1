"""Render a terminal capture from a command's real output.

The output is obtained by running the command and reading its stdout. Nothing is typed
in by hand. The result is written as SVG rather than a raster image on purpose: the text
stays as text in the file, so anyone can grep the committed asset and check it against
what the command prints on their own machine.

Each capture records the command, exit code, and capture time in the image itself.

    python scripts/capture_terminal.py --all
    python scripts/capture_terminal.py --name factor-research
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "docs" / "images"

PYTHON = sys.executable

BACKGROUND = "#101418"
CHROME = "#1b2027"
TEXT = "#c9d1d9"
DIM = "#6e7781"
PROMPT = "#7ee787"
COMMAND = "#e3b341"
LINE_HEIGHT = 19
CHAR_WIDTH = 8.4
PAD_X = 18
HEADER = 40
# Wrapping keeps every capture a similar width. One long line would otherwise widen
# the whole image, and GitHub scales it down until nothing is readable.
MAX_COLUMNS = 104


@dataclass(frozen=True, slots=True)
class Capture:
    name: str
    argv: list[str]
    display: str
    max_lines: int = 60


CAPTURES: tuple[Capture, ...] = (
    Capture(
        name="market-data-verification",
        argv=[PYTHON, "scripts/verify_market_data.py", "--fixture", "us_research"],
        display="python scripts/verify_market_data.py --fixture us_research",
        max_lines=24,
    ),
    Capture(
        name="factor-research",
        argv=[
            PYTHON,
            "-m",
            "apps.cli.main",
            "factor",
            "research",
            "momentum_12_1",
            "--dataset",
            "DATASET-US-30Y-v001",
        ],
        display="quantlab factor research momentum_12_1 --dataset DATASET-US-30Y-v001",
        max_lines=50,
    ),
    Capture(
        name="backtest",
        argv=[
            PYTHON,
            "-m",
            "apps.cli.main",
            "backtest",
            "run",
            "configs/strategies/us-price-composite-v1.yaml",
            "--dataset",
            "DATASET-US-30Y-v001",
            "--start",
            "2015-01-02",
            "--end",
            "2024-12-31",
        ],
        display=(
            "quantlab backtest run configs/strategies/us-price-composite-v1.yaml "
            "--dataset DATASET-US-30Y-v001 --start 2015-01-02 --end 2024-12-31"
        ),
        max_lines=30,
    ),
    Capture(
        name="validation",
        argv=[
            PYTHON,
            "-m",
            "apps.cli.main",
            "validate",
            "run",
            "configs/validation/default-v1.yaml",
            "--strategy",
            "configs/strategies/us-price-composite-v1.yaml",
            "--dataset",
            "DATASET-US-30Y-v001",
            "--start",
            "2015-01-02",
            "--end",
            "2024-12-31",
        ],
        display=(
            "quantlab validate run configs/validation/default-v1.yaml "
            "--strategy configs/strategies/us-price-composite-v1.yaml "
            "--dataset DATASET-US-30Y-v001 --start 2015-01-02 --end 2024-12-31"
        ),
        max_lines=48,
    ),
    Capture(
        name="model-compare",
        argv=[
            PYTHON,
            "-m",
            "apps.cli.main",
            "model",
            "compare",
            "--dataset",
            "DATASET-US-30Y-v001",
            "--control",
            "--permutations",
            "8",
        ],
        display=("quantlab model compare --dataset DATASET-US-30Y-v001 --control --permutations 8"),
        max_lines=30,
    ),
)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _wrap(display: str, width: int) -> list[str]:
    """Break a long command across lines at argument boundaries."""
    words = display.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) > width and current:
            lines.append(current + " \\")
            current = "    " + word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _soft_wrap(line: str, width: int) -> list[str]:
    """Wrap an over-long output line, keeping the original indentation."""
    if len(line) <= width:
        return [line]

    indent = " " * (len(line) - len(line.lstrip()) + 2)
    wrapped: list[str] = []
    current = ""
    for word in line.split(" "):
        candidate = word if not current else f"{current} {word}"
        if len(candidate) > width and current:
            wrapped.append(current)
            current = indent + word
        else:
            current = candidate
    if current:
        wrapped.append(current)
    return wrapped


def _colour(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith(("=", "-")) and set(stripped) <= {"=", "-"}:
        return DIM
    if stripped.startswith(("PASS:", "pass ")) or " pass " in line[:12]:
        return PROMPT
    if stripped.startswith(("FAIL:", "INDISTINGUISHABLE")):
        return "#ff7b72"
    if "RESEARCH_ONLY" in line or "Verdict" in line or "Champion" in line:
        return COMMAND
    return TEXT


def render_svg(capture: Capture, command_line: str, output: str, exit_code: int) -> str:
    lines = output.rstrip("\n").split("\n")
    if len(lines) > capture.max_lines:
        kept = lines[: capture.max_lines - 1]
        # Do not leave the capture ending on a section header or a rule: that reads
        # as if the command produced nothing underneath it.
        while kept and (not kept[-1].strip() or kept[-1].rstrip().endswith(":")):
            kept.pop()
        lines = [*kept, f"... {len(lines) - len(kept)} more lines"]

    lines = [part for line in lines for part in _soft_wrap(line, MAX_COLUMNS)]

    command_lines = _wrap(f"$ {command_line}", 96)
    body = command_lines + lines
    footer = (
        f"captured {datetime.now().astimezone():%Y-%m-%d %H:%M %Z}  |  exit {exit_code}"
        f"  |  regenerate: python scripts/capture_terminal.py --name {capture.name}"
    )

    width = int(max(len(line) for line in [*body, footer]) * CHAR_WIDTH) + 2 * PAD_X
    width = max(width, 720)
    height = HEADER + (len(body) + 3) * LINE_HEIGHT + PAD_X

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="ui-monospace,SFMono-Regular,'
        f'Menlo,Consolas,monospace" font-size="13">',
        f'<rect width="{width}" height="{height}" rx="8" fill="{BACKGROUND}"/>',
        f'<rect width="{width}" height="{HEADER}" rx="8" fill="{CHROME}"/>',
        f'<rect y="{HEADER - 8}" width="{width}" height="8" fill="{CHROME}"/>',
        '<circle cx="20" cy="20" r="6" fill="#ff5f57"/>',
        '<circle cx="40" cy="20" r="6" fill="#febc2e"/>',
        '<circle cx="60" cy="20" r="6" fill="#28c840"/>',
        f'<text x="86" y="25" fill="{DIM}">quantlab</text>',
    ]

    y = HEADER + LINE_HEIGHT + 2
    for line in command_lines:
        parts.append(
            f'<text x="{PAD_X}" y="{y}" fill="{COMMAND}" '
            f'xml:space="preserve">{_escape(line)}</text>'
        )
        y += LINE_HEIGHT

    for line in lines:
        parts.append(
            f'<text x="{PAD_X}" y="{y}" fill="{_colour(line)}" '
            f'xml:space="preserve">{_escape(line)}</text>'
        )
        y += LINE_HEIGHT

    parts.append(
        f'<text x="{PAD_X}" y="{y + LINE_HEIGHT}" fill="{DIM}" font-size="11">'
        f"{_escape(footer)}</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def capture_one(capture: Capture) -> int:
    print(f"running {capture.name}: {shlex.join(capture.argv)}")
    completed = subprocess.run(  # noqa: S603 - fixed argv defined in this file
        capture.argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        print(completed.stdout[-2000:], file=sys.stderr)
        print(completed.stderr[-2000:], file=sys.stderr)
        print(f"FAIL: {capture.name} exited {completed.returncode}", file=sys.stderr)
        return completed.returncode

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / f"terminal-{capture.name}.svg"
    target.write_text(
        render_svg(capture, capture.display, completed.stdout, completed.returncode),
        encoding="utf-8",
    )
    print(f"  wrote {target.relative_to(REPO_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Capture a single named command")
    parser.add_argument("--all", action="store_true", help="Capture every command")
    parser.add_argument("--list", action="store_true", help="List available captures")
    args = parser.parse_args(argv)

    if args.list:
        for capture in CAPTURES:
            print(f"{capture.name:28} {capture.display}")
        return 0

    selected = [c for c in CAPTURES if c.name == args.name] if args.name else list(CAPTURES)
    if args.name and not selected:
        print(f"No capture named '{args.name}'", file=sys.stderr)
        return 1
    if not args.name and not args.all:
        parser.print_help()
        return 1

    for capture in selected:
        code = capture_one(capture)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
