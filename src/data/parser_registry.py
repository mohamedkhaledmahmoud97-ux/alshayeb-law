"""
Parser registry for ALSHAYEB LAW.

Maps source_type strings to BaseParser instances.
The ingestion orchestrator uses this registry to look up the correct
parser for a given source file without importing concrete parsers directly.

Usage
-----
    from src.data.parser_registry import registry
    from src.data.statute_parser import StatuteParser

    registry.register(StatuteParser())
    parser = registry.get("statute")
"""

from __future__ import annotations

from src.data.base_parser import BaseParser


class ParserRegistry:
    """Registry mapping source_type → BaseParser instance."""

    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        """Register a parser. Overwrites any existing parser for the same source_type."""
        self._parsers[parser.source_type] = parser

    def get(self, source_type: str) -> BaseParser:
        """
        Return the parser for source_type.

        Raises:
            KeyError: if no parser is registered for source_type.
        """
        if source_type not in self._parsers:
            raise KeyError(
                f"No parser registered for source_type={source_type!r}. "
                f"Registered types: {list(self._parsers)}"
            )
        return self._parsers[source_type]

    def registered_types(self) -> list[str]:
        return list(self._parsers)


# Module-level singleton — import and use directly.
registry = ParserRegistry()
