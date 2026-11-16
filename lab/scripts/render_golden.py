"""Render golden router config templates from environment variables."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PLACEHOLDERS = {"", "change-me", "{{LAB_PASSWORD}}", "changeme"}


def render_all(
    template_dir: Path = Path("lab/golden"),
    output_dir: Path = Path("lab/golden/rendered"),
) -> list[Path]:
    """Render all .cfg.tpl files in template_dir into output_dir.

    Raises:
        ValueError: If LAB_PASSWORD is unset or equals an insecure placeholder.
    """
    load_dotenv()
    password = os.getenv("LAB_PASSWORD", "").strip()

    if not password or password in PLACEHOLDERS:
        raise ValueError(
            "refuses to run: LAB_PASSWORD is unset or equals placeholder. "
            "Please set a valid LAB_PASSWORD in your .env file."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_files: list[Path] = []

    for tpl_path in template_dir.glob("*.cfg.tpl"):
        content = tpl_path.read_text(encoding="utf-8")
        rendered_content = content.replace("{{LAB_PASSWORD}}", password)

        # Output filename: R1.cfg.tpl -> R1.cfg
        out_name = tpl_path.name[:-4] if tpl_path.name.endswith(".tpl") else f"{tpl_path.name}.cfg"
        out_path = output_dir / out_name
        out_path.write_text(rendered_content, encoding="utf-8")
        rendered_files.append(out_path)

    return rendered_files


def main() -> None:
    """CLI entrypoint for rendering golden configurations."""
    try:
        rendered = render_all()
        print(f"Successfully rendered {len(rendered)} config(s) to lab/golden/rendered/:")
        for f in rendered:
            print(f"  - {f.name}")
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
