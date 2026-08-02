"""Window chrome mixin: theme, nav helpers, technical view, close/cleanup."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QSizePolicy,
)

from gui.common import ROOT, WEB_ENGINE_AVAILABLE
from gui.widgets import DocBrowser, WidthAwareColumn


class WindowChromeMixin:
    """Mixin: window chrome shared by every tab (theme, nav, section helpers)."""

    def _technical_view_enabled(self) -> bool:
        return bool(
            getattr(self, 'technical_view_chk', None) and self.technical_view_chk.isChecked()
        )

    def _on_technical_view_changed(self, _state: int = 0) -> None:
        QSettings('SnapchatMemories', 'Downloader').setValue(
            'technical_view', self._technical_view_enabled()
        )
        self._apply_technical_view_ui()
        name = self._account_name()
        if name:
            self.update_download_path_label(name)

    def _on_save_raw_changed(self, _state: int = 0) -> None:
        name = self._account_name()
        if name:
            self.update_download_path_label(name)

    def _technical_widgets(self) -> list:
        """Every control that only appears once 'Technical view' is enabled.
        Kept in one place so visibility (+ label/checkbox tint) stay in sync.
        Buttons keep normal toolbar colors; disabled = not ready yet."""
        return [
            getattr(self, 'open_debug_btn', None),
            getattr(self, 'review_duplicates_btn', None),
            getattr(self, 'add_run_info_chk', None),
            getattr(self, 'manual_duplicate_review_chk', None),
            getattr(self, 'technical_view_hint', None),
            getattr(self, 'technical_storage_label', None),
        ]

    def _apply_technical_view_ui(self) -> None:
        from PyQt5.QtWidgets import QPushButton

        from smd.theme import technical_text_style

        technical = self._technical_view_enabled()
        style = technical_text_style(getattr(self, 'dark_mode_enabled', False))
        for widget in self._technical_widgets():
            if widget is None:
                continue
            widget.setVisible(technical)
            # Buttons keep normal toolbar colors (gold/orange). Red text on a
            # colored button looked broken; disabled state already shows
            # "not ready yet" via the muted gray toolbarBtn:disabled style.
            if isinstance(widget, QPushButton):
                widget.setStyleSheet('')
            else:
                widget.setStyleSheet(style if technical else '')
        if hasattr(self, '_rebuild_process_controls_grid'):
            self._rebuild_process_controls_grid()
        self._refresh_after_processing_actions()
        self._update_run_readiness()

    def run_startup_self_check(self):
        """Confirm the all-in-one package is complete (no extra installs for end users)."""
        from smd.ffmpeg_bundle import bundled_status
        import sys

        status = bundled_status()
        ffmpeg_ok = status["ffmpeg"] == "ok"
        ffprobe_ok = status["ffprobe"] == "ok"
        webengine_ok = WEB_ENGINE_AVAILABLE
        frozen = getattr(sys, 'frozen', False)

        if frozen:
            if ffmpeg_ok and webengine_ok:
                self._apply_status(self.status_label, 'SMK ready - all components included.', "ok")
            elif ffmpeg_ok:
                self._apply_status(self.status_label, 'SMK ready. Map preview limited in this build.', "warn")
            else:
                self._apply_status(self.status_label, 'Package incomplete - reinstall SMK from the official installer.', "err")
            return

        if ffmpeg_ok and webengine_ok:
            self._apply_status(self.status_label, 'SMK ready - all components included.', "ok")
        elif ffmpeg_ok:
            self._apply_status(self.status_label, 'SMK ready. Map preview limited in this build.', "warn")
        else:
            self._apply_status(self.status_label, 'Video tools missing - reinstall SMK from the official installer.', "err")

    def closeEvent(self, event):
        """Close the app fully so no orphan python.exe/pythonw stays in Task Manager."""
        self._cleanup_map_html_temps()
        self._set_keep_awake(False)
        self._stop_background_workers()
        try:
            from PyQt5.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:
            pass
        event.accept()

    def _stop_background_workers(self) -> None:
        """Cancel/wait on known QThreads so the process can exit after the window closes."""
        names = (
            'local_export_worker',
            'technical_storage_worker',
            'duplicate_scan_worker',
            'visual_scan_worker',
            'completion_finalize_worker',
            '_staging_verify_worker',
            'map_worker',
            'map_render_worker',
        )
        for name in names:
            worker = getattr(self, name, None)
            if worker is None:
                continue
            try:
                if hasattr(worker, 'isRunning') and not worker.isRunning():
                    continue
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                if hasattr(worker, 'requestInterruption'):
                    worker.requestInterruption()
                if hasattr(worker, 'wait'):
                    worker.wait(3000)
            except Exception:
                pass

    def _track_map_html_temp(self, path: str | Path) -> None:
        temp_path = Path(path)
        if temp_path not in self._map_html_temp_files:
            self._map_html_temp_files.append(temp_path)

    def _cleanup_map_html_temps(self) -> None:
        for temp_path in self._map_html_temp_files:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass
        self._map_html_temp_files.clear()

    def apply_window_icon(self):
        """Set the window icon from icon.ico or icon.png if present."""
        try:
            candidates = [ROOT / 'icon.ico', ROOT / 'icon.png']
            for path in candidates:
                if path.exists():
                    self.setWindowIcon(QIcon(str(path)))
                    break
        except Exception:
            pass

    def check_show_signal(self):
        """Check if another instance is requesting this window to show"""
        try:
            if self.signal_file.exists():
                print("DEBUG: Signal file detected, bringing window to front")
                self.signal_file.unlink()  # Delete signal file
                # Bring window to front with more aggressive methods
                if self.isMinimized() or not self.isVisible():
                    print("DEBUG: Window was minimized/hidden, restoring")
                    self.showNormal()
                else:
                    print("DEBUG: Showing window")
                    self.show()
                self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
                self.raise_()
                self.activateWindow()
                # Windows-specific: taskbar button + flash if we can't steal focus
                if sys.platform == 'win32':
                    try:
                        import ctypes
                        from ctypes import wintypes

                        hwnd = int(self.winId())
                        print(f"DEBUG: Using Windows API to focus window {hwnd}")
                        user32 = ctypes.windll.user32
                        if user32.IsIconic(hwnd):
                            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
                        user32.FlashWindow(hwnd, True)
                    except Exception as e:
                        print(f"DEBUG: Windows API error: {e}")
                        pass
        except Exception as e:
            print(f"DEBUG: Error in check_show_signal: {e}")
            pass

    def _apply_status(self, label, text: str, status: str = "neutral") -> None:
        from smd.theme import apply_status_property

        label.setText(text)
        apply_status_property(label, status)

    def _make_tab_page(self) -> QWidget:
        from smd.theme import enable_styled_surface

        page = QWidget()
        page.setObjectName('tabPage')
        enable_styled_surface(page)
        return page

    def _scroll_tab(self, body: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName('tabScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setWidget(body)
        return scroll

    def _doc_tab(self, inner: QWidget, *, fill_height: bool = True) -> QScrollArea:
        """Centered reading column (Guide / Help) at CONTENT_MAX_DOCS width.

        fill_height=True (Help/About/Palestine): DocBrowser fills the tab.
        fill_height=False (Guide): content hugs screenshots and stays top-aligned.
        """
        from smd.theme import CONTENT_MAX_DOCS

        column = WidthAwareColumn(inner, CONTENT_MAX_DOCS, fill_height=fill_height)
        return self._scroll_tab(column)

    def _form_tab(self, inner: QWidget) -> QScrollArea:
        """Centered form column (Process) capped for comfortable control width."""
        from smd.theme import CONTENT_MAX_FORM, CONTENT_MIN_FORM

        # Prefer top alignment so short Save Memories content does not float.
        column = WidthAwareColumn(
            inner, CONTENT_MAX_FORM, min_width=CONTENT_MIN_FORM, fill_height=False
        )
        scroll = self._scroll_tab(column)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        return scroll

    def _add_section_title(self, lay, title: str, *, object_name: str = 'sectionBoxTitle') -> None:
        """Bold section title; short accent bar under the text (not full-box).

        QLabel ``border-bottom`` is unreliable on Windows with WA_StyledBackground
        parents, so the rule is a fixed-height ``QFrame#sectionTitleRule``.
        """
        from smd.theme import enable_styled_surface

        wrap = QWidget()
        wrap.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        wrap_lay = QVBoxLayout(wrap)
        wrap_lay.setContentsMargins(0, 0, 0, 0)
        wrap_lay.setSpacing(4)
        hdr = QLabel(title)
        hdr.setObjectName(object_name)
        hdr.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        rule = QFrame()
        rule.setObjectName('sectionTitleRule')
        enable_styled_surface(rule)
        rule.setFixedHeight(2)
        rule.setFixedWidth(max(24, hdr.fontMetrics().horizontalAdvance(title)))
        wrap_lay.addWidget(hdr, 0, Qt.AlignLeft)
        wrap_lay.addWidget(rule, 0, Qt.AlignLeft)
        lay.addWidget(wrap, 0, Qt.AlignLeft)

    def _section(self, title: str) -> tuple:
        from smd.theme import CONTROL_GAP, SECTION_PADDING, enable_styled_surface

        box = QFrame()
        box.setObjectName('contentSection')
        # Preferred height: sections hug their content. Expanding made My Data /
        # Performance stretch and left empty gaps under the title when stretched
        # to match a taller sibling (or leftover column space).
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        enable_styled_surface(box)
        lay = QVBoxLayout(box)
        lay.setSpacing(CONTROL_GAP)
        lay.setContentsMargins(SECTION_PADDING, SECTION_PADDING, SECTION_PADDING, SECTION_PADDING)
        if title:
            self._add_section_title(lay, title, object_name='sectionBoxTitle')
        return box, lay

    def _hero_section(self, title: str) -> tuple:
        """Highlighted section for the primary workflow (Save memories tab)."""
        from smd.theme import CONTROL_GAP, SECTION_PADDING, enable_styled_surface

        box = QFrame()
        box.setObjectName('heroSection')
        enable_styled_surface(box)
        lay = QVBoxLayout(box)
        lay.setSpacing(CONTROL_GAP + 2)
        lay.setContentsMargins(
            SECTION_PADDING + 2,
            SECTION_PADDING + 2,
            SECTION_PADDING + 2,
            SECTION_PADDING,
        )
        if title:
            self._add_section_title(lay, title, object_name='heroBoxTitle')
        return box, lay

    def _section_grid(self, *cells: tuple[QWidget, int, int]) -> QWidget:
        """2-column section grid with shared column widths and matched row heights."""
        from smd.theme import CONTROL_GAP, SECTION_GAP

        host = QWidget()
        host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        grid = QGridLayout(host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(CONTROL_GAP)
        grid.setVerticalSpacing(SECTION_GAP)
        for box, row, col in cells:
            box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            box.setMinimumWidth(0)
            grid.addWidget(box, row, col)
        for col in range(2):
            grid.setColumnStretch(col, 1)
            grid.setColumnMinimumWidth(col, 0)
        return host

    def _switch_nav_tab(self, index: int) -> None:
        if index < 0 or index >= self.tabs.count():
            return
        self.tabs.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            active = i == index
            btn.setProperty('active', 'true' if active else 'false')
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _refresh_content_columns(self, _index: int = 0) -> None:
        """Recompute WidthAwareColumn widths for the current tab (docs reflow)."""
        page = self.tabs.currentWidget()
        if page is None:
            return
        for column in page.findChildren(WidthAwareColumn):
            column._apply_content_width(sync_docs=True)

    def _refresh_all_content_columns(self) -> None:
        """Update every tab's column width from the live mainTabs width.

        Hidden QStackedWidget pages do not get resizeEvents, so without this
        only the active tab tracks the window until you switch tabs.
        """
        for column in self.findChildren(WidthAwareColumn):
            # Default sync: only when width actually changes (avoids doc reflow
            # on every debounced resize tick). Tab-switch forces sync separately.
            column._apply_content_width()

    def _schedule_all_content_columns_refresh(self) -> None:
        timer = getattr(self, "_columns_resize_timer", None)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self._refresh_all_content_columns)
            self._columns_resize_timer = timer
        timer.start(32)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_all_content_columns_refresh()

    def _on_main_tab_changed(self, index: int) -> None:
        self._refresh_content_columns(index)
        if index == self._tab_file_checker:
            # Start the expensive WebEngine init as soon as the user looks at
            # this tab, not only once they click Scan - gives it a head
            # start so it's more likely ready by the time a map is actually
            # rendered.
            self._ensure_map_view()

    def _add_nav_button(self, label: str, index: int) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName('NavBtn')
        btn.setProperty('active', 'false')
        btn.clicked.connect(lambda _checked=False, tab_index=index: self._switch_nav_tab(tab_index))
        self._nav_buttons.append(btn)
        return btn

    def _load_and_apply_theme(self):
        from smd.theme import THEME_DARK, THEME_SYSTEM, resolve_theme

        settings = QSettings('SnapchatMemories', 'Downloader')
        stored = settings.value('theme_mode')
        if stored is None:
            self.dark_mode_enabled = resolve_theme(THEME_SYSTEM) == THEME_DARK
        else:
            self.dark_mode_enabled = str(stored) == THEME_DARK
        self._apply_current_theme()

    def _sync_section_title_rules(self) -> None:
        """Keep short title bars sized to their label after theme/font changes."""
        for rule in self.findChildren(QFrame):
            if rule.objectName() != 'sectionTitleRule':
                continue
            parent = rule.parentWidget()
            if parent is None:
                continue
            for child in parent.findChildren(QLabel):
                if child.objectName() in ('sectionBoxTitle', 'heroBoxTitle'):
                    rule.setFixedWidth(
                        max(24, child.fontMetrics().horizontalAdvance(child.text()))
                    )
                    break

    def _sync_doc_readers_theme(self) -> None:
        from gui.common import TAB_SAVE_MEMORIES, WEB_ENGINE_AVAILABLE
        from smd.about_content import build_about_html, gather_about_facts
        from smd.guide_content import build_guide_html, guide_assets_dir
        from smd.help_content import build_help_html, inject_title_rule_image
        from smd.palestine_content import build_palestine_html
        from smd.theme import apply_doc_browser_theme, palette

        dark = self.dark_mode_enabled
        accent = palette(dark)["secondary"]
        about_facts = getattr(self, "_about_facts_cache", None)
        if about_facts is None:
            about_facts = gather_about_facts(web_engine_available=WEB_ENGINE_AVAILABLE)
            self._about_facts_cache = about_facts
        builders = {
            "guideDocBrowser": lambda: build_guide_html(TAB_SAVE_MEMORIES, accent=accent),
            "helpDocBrowser": lambda: build_help_html(TAB_SAVE_MEMORIES, accent=accent),
            "aboutDocBrowser": lambda: build_about_html(
                web_engine_available=WEB_ENGINE_AVAILABLE,
                accent=accent,
                facts=about_facts,
            ),
            "palestineDocBrowser": lambda: build_palestine_html(accent=accent),
        }
        # Paint visible tab first so the switch feels instant; other doc tabs
        # catch up in the same pass (still cheaper than blocking on About's
        # ffmpeg probes thanks to the facts cache).
        browsers = list(self.findChildren(DocBrowser))
        current_page = self.tabs.currentWidget() if hasattr(self, "tabs") else None

        def _page_of(w):
            p = w.parentWidget()
            while p is not None and p is not self:
                if current_page is not None and p is current_page:
                    return True
                p = p.parentWidget()
            return False

        browsers.sort(key=lambda b: (0 if _page_of(b) else 1))
        for browser in browsers:
            apply_doc_browser_theme(browser, dark=dark)
            # Rebuild HTML + inject solid accent bar image (CSS underlines do not
            # paint reliably in QTextBrowser / FlowDocBrowser).
            name = browser.objectName()
            builder = builders.get(name)
            if builder is None:
                continue
            paths = list(browser.searchPaths())
            browser.setHtml(builder())
            inject_title_rule_image(browser, accent)
            if name == "guideDocBrowser":
                browser.setSearchPaths(paths or [str(guide_assets_dir())])
                # Height depends on images; re-sync after the rule image exists.
                sync = getattr(browser, "_sync_height", None)
                if callable(sync):
                    sync()
            elif paths:
                browser.setSearchPaths(paths)
        self._sync_section_title_rules()

    def _schedule_doc_theme_sync(self) -> None:
        """Rebuild doc HTML after chrome paints (avoids a stuck Dark/Light click)."""
        timer = getattr(self, "_doc_theme_timer", None)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self._sync_doc_readers_theme_deferred)
            self._doc_theme_timer = timer
        timer.start(0)

    def _sync_doc_readers_theme_deferred(self) -> None:
        self.setUpdatesEnabled(False)
        try:
            self._sync_doc_readers_theme()
        finally:
            self.setUpdatesEnabled(True)

    def _sync_surface_colors(self) -> None:
        from smd.theme import apply_scroll_area_theme, paint_widget_surface

        dark = self.dark_mode_enabled
        for obj_name, role in (('mainShell', 'bg'), ('tabsShell', 'bg')):
            widget = self.findChild(QWidget, obj_name)
            if widget is not None:
                paint_widget_surface(widget, dark=dark, role=role)
        paint_widget_surface(self.tabs, dark=dark, role='panel')
        for index in range(self.tabs.count()):
            page = self.tabs.widget(index)
            if page is not None:
                paint_widget_surface(page, dark=dark, role='panel')
        for scroll in self.findChildren(QScrollArea):
            if scroll.objectName() == 'tabScroll':
                apply_scroll_area_theme(scroll, dark=dark)
        for column in self.findChildren(WidthAwareColumn):
            paint_widget_surface(column, dark=dark, role='bg')

    def _apply_current_theme(self):
        from smd.theme import stylesheet_for

        # Freeze paints so QSS + surface recolors apply as one frame (less flash).
        self.setUpdatesEnabled(False)
        try:
            theme = 'dark' if self.dark_mode_enabled else 'light'
            self.setStyleSheet(stylesheet_for(theme))
            self.dark_mode_btn.setText('Light' if self.dark_mode_enabled else 'Dark')
            self.update_title_bar_color(self.dark_mode_enabled)
            self._sync_surface_colors()
            if hasattr(self, 'results_panels'):
                self.results_panels.set_dark_theme(self.dark_mode_enabled)
            if hasattr(self, 'technical_view_chk'):
                self._apply_technical_view_ui()
        finally:
            self.setUpdatesEnabled(True)
        # After paints resume: rebuild File Checker map so tiles match theme
        # (light → Terrain, dark → CartoDB Dark Matter). Skips if busy / no map.
        if hasattr(self, 'refresh_map_for_theme'):
            self.refresh_map_for_theme()
        # Doc HTML rebuild (Guide images, About facts) is the slow part.
        # Defer while the window is already up so Dark/Light stays snappy;
        # on first theme apply (before show) do it inline so the first paint
        # already has the correct accent underlines.
        if self.isVisible():
            self._schedule_doc_theme_sync()
        else:
            self._sync_doc_readers_theme()

    def apply_theme_mode(self, mode: str):
        from smd.theme import THEME_DARK, resolve_theme

        self.dark_mode_enabled = resolve_theme(mode) == THEME_DARK
        self._apply_current_theme()

    def update_title_bar_color(self, is_dark: bool):
        """
        Update Windows title bar color using DWM API.
        Works on Windows 10 (build 17763+) and Windows 11.
        """
        if sys.platform != 'win32':
            return
            
        try:
            import ctypes

            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            
            hwnd = int(self.winId())
            
            # Create a boolean attribute
            attribute = ctypes.c_int(1 if is_dark else 0)
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(attribute), 
                ctypes.sizeof(attribute)
            )
            # No self.repaint() — full theme apply already refreshes; forcing a
            # mid-switch repaint caused extra flicker on Dark/Light toggle.
        except Exception as e:
            print(f"Failed to set title bar color: {e}")

    def toggle_dark_mode(self):
        from smd.theme import THEME_DARK, THEME_LIGHT

        self.dark_mode_enabled = not self.dark_mode_enabled
        QSettings('SnapchatMemories', 'Downloader').setValue(
            'theme_mode', THEME_DARK if self.dark_mode_enabled else THEME_LIGHT
        )
        self._apply_current_theme()
