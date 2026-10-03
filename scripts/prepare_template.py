"""Generate a privacy-safe template from a user-owned source workbook."""

import argparse
from pathlib import Path

from app.services.excel_export import create_empty_template

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("templates/成品日检表模板.xlsx"))
    args = parser.parse_args()
    create_empty_template(args.source, args.output)
    print(args.output)
