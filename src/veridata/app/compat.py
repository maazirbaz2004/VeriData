"""Streamlit compatibility shim and headless runner for environments without streamlit installed."""

from __future__ import annotations

import sys
from typing import Any, Callable


class _MockStreamlit:
    """Mock Streamlit interface allowing headless execution and testing when Streamlit is not installed."""

    session_state: dict[str, Any] = {}

    def __enter__(self) -> _MockStreamlit:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_page_config(self, *args: Any, **kwargs: Any) -> None:
        pass

    def title(self, text: str) -> None:
        pass

    def header(self, text: str) -> None:
        pass

    def subheader(self, text: str) -> None:
        pass

    def write(self, *args: Any, **kwargs: Any) -> None:
        pass

    def markdown(self, text: str, *args: Any, **kwargs: Any) -> None:
        pass

    def info(self, text: str) -> None:
        pass

    def warning(self, text: str) -> None:
        pass

    def error(self, text: str) -> None:
        pass

    def success(self, text: str) -> None:
        pass

    def button(self, label: str, key: str | None = None, **kwargs: Any) -> bool:
        return False

    def download_button(self, label: str, data: Any, file_name: str, **kwargs: Any) -> bool:
        return False

    def file_uploader(self, label: str, **kwargs: Any) -> Any:
        return None

    def columns(self, spec: int | list[int | float]) -> list[_MockStreamlit]:
        count = spec if isinstance(spec, int) else len(spec)
        return [_MockStreamlit() for _ in range(count)]

    def tabs(self, titles: list[str]) -> list[_MockStreamlit]:
        return [_MockStreamlit() for _ in titles]

    def expander(self, label: str, **kwargs: Any) -> _MockStreamlit:
        return _MockStreamlit()

    def status(self, label: str, **kwargs: Any) -> _MockStreamlit:
        return _MockStreamlit()

    def chat_message(self, role: str, **kwargs: Any) -> _MockStreamlit:
        return _MockStreamlit()

    def chat_input(self, placeholder: str = "") -> str | None:
        return None

    def dataframe(self, *args: Any, **kwargs: Any) -> None:
        pass

    def metric(self, label: str, value: Any, delta: Any = None, **kwargs: Any) -> None:
        pass

    def image(self, *args: Any, **kwargs: Any) -> None:
        pass

    def selectbox(self, label: str, options: list[Any], **kwargs: Any) -> Any:
        return options[0] if options else None

    def slider(self, label: str, min_value: Any, max_value: Any, value: Any, **kwargs: Any) -> Any:
        return value

    def toggle(self, label: str, value: bool = False, **kwargs: Any) -> bool:
        return value

    def checkbox(self, label: str, value: bool = False, **kwargs: Any) -> bool:
        return value

    def divider(self) -> None:
        pass

    def caption(self, text: str) -> None:
        pass

    def container(self) -> _MockStreamlit:
        return _MockStreamlit()

    def pyplot(self, *args: Any, **kwargs: Any) -> None:
        pass

    def update(self, *args: Any, **kwargs: Any) -> None:
        pass

    @property
    def sidebar(self) -> _MockStreamlit:
        return self


try:
    import streamlit as st  # type: ignore
except ImportError:
    st = _MockStreamlit()  # type: ignore
