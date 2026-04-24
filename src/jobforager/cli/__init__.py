from __future__ import annotations

import sys
from typing import Sequence

from jobforager.cli.parser import build_parser
from jobforager.cli.commands import (
    _print_help_status,
    _run_health_command,
    _run_hunt_command,
    _run_search_command,
    _run_validate_command,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "help"):
        _print_help_status()
        return 0

    if args.command == "hunt":
        return _run_hunt_command(args)

    if args.command == "validate":
        return _run_validate_command(args)

    if args.command == "search":
        return _run_search_command(args)

    if args.command == "health":
        return _run_health_command(args)

    parser.print_help()
    return 0
