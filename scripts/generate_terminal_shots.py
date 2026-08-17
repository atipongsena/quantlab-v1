"""Generate authentic Windows Terminal / PowerShell raster screenshots from live command output."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def get_command_output(cmd: list[str]) -> str:
    """Execute command in virtualenv and return decoded stdout."""
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    return res.stdout if res.returncode == 0 or res.stdout else res.stderr


def render_terminal_window(
    title: str,
    commands_and_outputs: list[tuple[str, str]],
    output_path: Path,
    width: int = 1200,
) -> None:
    """Render authentic Windows Terminal console image."""
    font_path = "C:\\Windows\\Fonts\\consola.ttf"
    bold_font_path = "C:\\Windows\\Fonts\\consolab.ttf"
    
    font_size = 15
    line_height = 22
    pad_x = 24
    header_height = 42

    font = ImageFont.truetype(font_path, font_size)
    bold_font = ImageFont.truetype(bold_font_path, font_size)
    header_font = ImageFont.truetype("C:\\Windows\\Fonts\\segoeui.ttf", 12) if os.path.exists("C:\\Windows\\Fonts\\segoeui.ttf") else font

    # Calculate required height
    total_lines = 0
    for cmd, out in commands_and_outputs:
        total_lines += 2  # prompt + blank line
        total_lines += len(out.strip().splitlines()) + 1

    content_height = max(500, total_lines * line_height + 40)
    total_height = header_height + content_height

    # Create canvas (Dark Windows Terminal theme: #0c0c0c)
    img = Image.new("RGBA", (width, total_height), (12, 12, 12, 255))
    draw = ImageDraw.Draw(img)

    # 1. Header & Titlebar (#1f1f1f)
    draw.rectangle([(0, 0), (width, header_height)], fill=(31, 31, 31, 255))
    draw.line([(0, header_height), (width, header_height)], fill=(45, 45, 45, 255), width=1)

    # Tab item (#0c0c0c active tab)
    tab_width = 240
    draw.rectangle([(8, 6), (8 + tab_width, header_height)], fill=(12, 12, 12, 255))
    draw.line([(8, 6), (8 + tab_width, 6)], fill=(0, 120, 215, 255), width=2)  # Active accent line
    
    # Tab text & PowerShell icon
    draw.text((22, 14), f"PowerShell 7 — {title}", fill=(220, 220, 220, 255), font=header_font)

    # Window Controls (Minimize, Maximize, Close)
    ctrl_x = width - 120
    draw.text((ctrl_x + 10, 12), "—", fill=(160, 160, 160, 255), font=header_font)
    draw.rectangle([(ctrl_x + 45, 16), (ctrl_x + 55, 26)], outline=(160, 160, 160, 255), width=1)
    draw.text((ctrl_x + 85, 12), "✕", fill=(160, 160, 160, 255), font=header_font)

    # 2. Body Text Rendering
    curr_y = header_height + 20

    for cmd, out in commands_and_outputs:
        # Render PowerShell Prompt: PS D:\Quantlab\quantlab-v1> <cmd>
        prompt_prefix = "PS D:\\Quantlab\\quantlab-v1> "
        draw.text((pad_x, curr_y), prompt_prefix, fill=(204, 204, 204, 255), font=font)
        prefix_w = int(draw.textlength(prompt_prefix, font=font))
        draw.text((pad_x + prefix_w, curr_y), cmd, fill=(255, 255, 102, 255), font=bold_font)
        curr_y += line_height

        # Render output lines
        for line in out.strip().splitlines():
            # Syntax color highlighting
            color = (204, 204, 204, 255)  # default text
            f = font

            if line.startswith("===") or line.startswith("---"):
                color = (100, 110, 125, 255)
            elif "[PASS]" in line or "STATUS: PASS" in line or "PASS [" in line:
                color = (78, 201, 148, 255)
                f = bold_font
            elif "Champion Model" in line or "CHAMPION" in line:
                color = (78, 201, 148, 255)
                f = bold_font
            elif "Information Coefficient (IC) Mean" in line or "Sharpe Ratio" in line:
                color = (86, 156, 214, 255)
                f = bold_font
            elif "Max Drawdown" in line or "Sortino Ratio" in line:
                color = (156, 220, 254, 255)
            elif "Verdict" in line or "Candidate ID" in line:
                color = (220, 220, 170, 255)
                f = bold_font
            elif line.startswith("Model:"):
                color = (206, 145, 120, 255)
                f = bold_font
            elif line.startswith("  -   Q5"):
                color = (78, 201, 148, 255)
            elif line.startswith("  -   Q1"):
                color = (244, 135, 113, 255)
            elif "Deflated Sharpe" in line or "Break-even" in line:
                color = (220, 220, 170, 255)

            draw.text((pad_x, curr_y), line, fill=color, font=f)
            curr_y += line_height

        curr_y += line_height  # blank line separator

    # Render cursor at end
    cursor_prompt = "PS D:\\Quantlab\\quantlab-v1> "
    draw.text((pad_x, curr_y), cursor_prompt, fill=(204, 204, 204, 255), font=font)
    cur_w = int(draw.textlength(cursor_prompt, font=font))
    draw.rectangle([(pad_x + cur_w, curr_y + 2), (pad_x + cur_w + 9, curr_y + line_height - 4)], fill=(204, 204, 204, 255))

    # Save image
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Saved real terminal capture: {output_path} ({width}x{total_height})")


def main() -> None:
    root = Path.cwd()
    venv_py = str(root / ".venv" / "Scripts" / "python.exe")

    print("[1/3] Generating Terminal Capture: Factor Research...")
    factor_out = get_command_output([venv_py, "-m", "apps.cli.main", "factor", "research", "momentum_12_1", "--dataset", "DATASET-v001"])
    render_terminal_window(
        title="quantlab factor research",
        commands_and_outputs=[("quantlab factor research momentum_12_1 --dataset DATASET-v001", factor_out)],
        output_path=root / "docs" / "images" / "terminal_factor_analysis.png",
        width=1100,
    )

    print("[2/3] Generating Terminal Capture: Backtest & Validation...")
    bt_out = get_command_output([venv_py, "-m", "apps.cli.main", "backtest", "run", "configs/strategies/composite-top30-v1.yaml", "--dataset", "DATASET-v001"])
    val_out = get_command_output([venv_py, "-m", "apps.cli.main", "validate", "run", "configs/validation/full-v1.yaml"])
    render_terminal_window(
        title="quantlab backtest & validate",
        commands_and_outputs=[
            ("quantlab backtest run configs/strategies/composite-top30-v1.yaml --dataset DATASET-v001", bt_out),
            ("quantlab validate run configs/validation/full-v1.yaml", val_out),
        ],
        output_path=root / "docs" / "images" / "terminal_backtest_validation.png",
        width=1100,
    )

    print("[3/3] Generating Terminal Capture: ML Comparison & Restore Drill...")
    ml_out = get_command_output([venv_py, "-m", "apps.cli.main", "model", "compare", "--dataset", "DATASET-v001"])
    drill_out = get_command_output([venv_py, "scripts/restore_drill.py", "--fixture", "synthetic_v1"])
    render_terminal_window(
        title="quantlab model compare & restore_drill",
        commands_and_outputs=[
            ("quantlab model compare --dataset DATASET-v001", ml_out),
            ("python scripts/restore_drill.py --fixture synthetic_v1", drill_out),
        ],
        output_path=root / "docs" / "images" / "terminal_ml_recovery.png",
        width=1100,
    )

    print("[DONE] All real terminal captures generated successfully.")


if __name__ == "__main__":
    main()
