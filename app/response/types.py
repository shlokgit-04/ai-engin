from typing import Any


class FormattedResponse:
    """A formatted executive response."""

    def __init__(self, text: str, intent: str, template: str = "default") -> None:
        self.text = text
        self.intent = intent
        self.template = template

    def __str__(self) -> str:
        return self.text
