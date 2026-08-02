"""Palestine solidarity tab — resources and links."""
from __future__ import annotations

from PyQt5.QtWidgets import QVBoxLayout

from gui.common import build_palestine_panel


class PalestineTabMixin:
    """Mixin: Palestine tab (external resource links + solidarity framing)."""

    def _add_palestine_tab(self) -> None:
        palestine_tab = self._make_tab_page()
        palestine_tab_layout = QVBoxLayout(palestine_tab)
        palestine_tab_layout.setContentsMargins(0, 0, 0, 0)
        palestine_tab_layout.addWidget(self._doc_tab(build_palestine_panel()))
        self.tabs.addTab(palestine_tab, "Palestine")
