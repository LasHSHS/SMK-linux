"""Save memories tab mixin: setup, run lifecycle, dashboard, after-processing."""
from __future__ import annotations

import html
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QSettings, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QComboBox, QCheckBox, QProgressBar, QFileDialog, QDialog,
    QMessageBox, QSizePolicy, QMenu, QGraphicsOpacityEffect,
    QButtonGroup, QLineEdit, QInputDialog, QListView, QFrame,
)

from gui.common import ROOT, TAB_SAVE_MEMORIES
from gui.widgets import LiveRunDashboard
from gui.workers import (
    LocalExportWorker,
    TechnicalStorageWorker,
)


class SaveMemoriesTabMixin:
    """Mixin: Save memories tab (full processing run + after-processing actions)."""

    def _add_save_memories_tab(self) -> None:
        # --- Tab 2: Save memories ---
        from smd.theme import CONTROL_GAP, FIELD_GAP, SECTION_GAP

        download_tab = self._make_tab_page()
        download_tab_layout = QVBoxLayout(download_tab)
        download_tab_layout.setContentsMargins(0, 0, 0, 0)
        process_panel = QWidget()
        process_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        controls_layout = QVBoxLayout(process_panel)
        controls_layout.setSpacing(SECTION_GAP)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        account_box, account_lay = self._section('Account')
        self._active_account_name = ''
        # Same gold-border checkmark style as Run options (QCheckBox theme),
        # but exclusive via QButtonGroup so only one mode is selected at a time.
        self._account_mode_group = QButtonGroup(self)
        self._account_mode_group.setExclusive(True)
        account_mode_row = QHBoxLayout()
        account_mode_row.setContentsMargins(0, 0, 0, 0)
        account_mode_row.setSpacing(CONTROL_GAP * 2)
        self.new_account_radio = QCheckBox('New account')
        self.old_account_radio = QCheckBox('Existing account')
        self._account_mode_group.addButton(self.new_account_radio)
        self._account_mode_group.addButton(self.old_account_radio)
        self.new_account_radio.toggled.connect(self._on_account_mode_toggled)
        account_mode_row.addWidget(self.new_account_radio)
        account_mode_row.addWidget(self.old_account_radio)
        account_mode_row.addStretch(1)
        account_lay.addLayout(account_mode_row)

        new_account_row = QHBoxLayout()
        new_account_row.setContentsMargins(0, 0, 0, 0)
        new_account_row.setSpacing(FIELD_GAP)
        new_account_row.addWidget(QLabel('Name folder:'))
        self.new_account_name_edit = QLineEdit()
        self.new_account_name_edit.setPlaceholderText('e.g. your name or nickname')
        self.new_account_name_edit.setToolTip(
            'Folder name for this export. Created automatically when you Start processing.'
        )
        self.new_account_name_edit.textChanged.connect(self._on_new_account_name_changed)
        new_account_row.addWidget(self.new_account_name_edit, 1)
        account_lay.addLayout(new_account_row)

        self.new_account_preview_label = QLabel('')
        self.new_account_preview_label.setProperty('class', 'caption')
        account_lay.addWidget(self.new_account_preview_label)

        old_account_row = QHBoxLayout()
        old_account_row.setContentsMargins(0, 0, 0, 0)
        old_account_row.setSpacing(FIELD_GAP)
        self.old_account_label = QLabel('No previous accounts found yet.')
        self.old_account_label.setWordWrap(True)
        old_account_row.addWidget(self.old_account_label, 1)
        account_lay.addLayout(old_account_row)

        # Path banner + Change button side-by-side.
        active_account_row = QHBoxLayout()
        active_account_row.setContentsMargins(0, 0, 0, 0)
        active_account_row.setSpacing(FIELD_GAP)
        self.active_account_label = QLabel('No account selected yet.')
        self.active_account_label.setObjectName('infoBanner')
        self.active_account_label.setWordWrap(True)
        active_account_row.addWidget(self.active_account_label, 1)
        self.old_account_change_btn = QPushButton('Change output folder')
        self.old_account_change_btn.setObjectName('toolbarBtn')
        self.old_account_change_btn.setToolTip('Pick a different already-processed account folder')
        self.old_account_change_btn.clicked.connect(self._on_old_account_change)
        active_account_row.addWidget(self.old_account_change_btn, 0, Qt.AlignVCenter)
        account_lay.addLayout(active_account_row)

        setup_box, setup_lay = self._section('My Data – zip files')
        export_hint = QLabel(
            'Choose the folder with the ZIP file(s) from your Snapchat My Data download. '
            'If Snapchat sent several parts, keep them all in that same folder.'
        )
        export_hint.setProperty('class', 'caption')
        export_hint.setWordWrap(True)
        setup_lay.addWidget(export_hint)
        guide_link = QLabel(
            '<a href="smd://guide">Don\'t have your export yet? '
            'How to request your Snapchat data</a>'
        )
        guide_link.setTextFormat(Qt.RichText)
        guide_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        guide_link.setOpenExternalLinks(False)
        guide_link.setCursor(Qt.PointingHandCursor)
        guide_link.setWordWrap(True)
        guide_link.linkActivated.connect(
            lambda *_: self.tabs.setCurrentIndex(self._tab_guide)
        )
        setup_lay.addWidget(guide_link)
        zip_btn_row = QHBoxLayout()
        zip_btn_row.setContentsMargins(0, 0, 0, 0)
        zip_btn_row.setSpacing(FIELD_GAP)
        zip_folder_btn = QPushButton('Choose folder')
        zip_folder_btn.setObjectName('accentBtn')
        zip_folder_btn.setToolTip(
            'Pick the folder where you put every part of your My Data export - '
            'SMK finds all ZIP files in that folder automatically.'
        )
        zip_folder_btn.clicked.connect(self.select_export_folder)
        zip_btn_row.addWidget(zip_folder_btn)
        zip_btn_row.addStretch(1)
        setup_lay.addLayout(zip_btn_row)
        self.zip_label = QLabel('No file selected')
        self.zip_label.setProperty('class', 'muted')
        setup_lay.addWidget(self.zip_label)
        self.export_summary_label = QLabel(
            'After you choose a folder, a summary of the ZIP parts SMK found appears here.'
        )
        self.export_summary_label.setWordWrap(True)
        self.export_summary_label.setTextFormat(Qt.RichText)
        self.export_summary_label.setObjectName('infoBanner')
        setup_lay.addWidget(self.export_summary_label)

        perf_box, perf_lay = self._section('Performance')
        self.perf_mode_combo = QComboBox()
        # Custom list view avoids native Windows popup chrome (white bars).
        _perf_view = QListView()
        _perf_view.setFrameShape(QFrame.NoFrame)
        _perf_view.setUniformItemSizes(True)
        self.perf_mode_combo.setView(_perf_view)
        self.perf_mode_combo.setMaxVisibleItems(3)
        self.perf_mode_combo.addItems([
            'Maximum - fastest; PC may feel busy (more power)',
            'Balanced - good speed; light multitasking OK',
            'Eco - slower; easier multitasking / better on battery',
        ])
        self.perf_mode_combo.setToolTip(
            'How hard SMK works your PC while processing.\n'
            'Maximum: finishes sooner; other apps may stutter; uses more power.\n'
            'Balanced: solid speed; browsing or chatting is usually fine.\n'
            'Eco: slower; best when using other apps, or on battery.\n'
            '(On a plugged-in desktop, “battery” matters less — Eco still leaves '
            'more room for other programs.)'
        )
        self.perf_mode_combo.setCurrentIndex(0)
        self.perf_mode_combo.currentIndexChanged.connect(self.on_perf_mode_changed)

        cpu_cores = os.cpu_count() or 2
        self.cpu_info_label = QLabel(f'({cpu_cores} threads)')
        self.cpu_info_label.setProperty('class', 'caption')

        perf_lay.addWidget(self.perf_mode_combo)
        perf_lay.addWidget(self.cpu_info_label)
        self.system_profile_label = QLabel("")
        self.system_profile_label.setProperty('class', 'muted')
        self.system_profile_label.setWordWrap(True)
        perf_lay.addWidget(self.system_profile_label)
        self.estimate_time_label = QLabel(
            'Estimated time: choose a Snapchat export folder to see a rough estimate.'
        )
        self.estimate_time_label.setProperty('class', 'caption')
        self.estimate_time_label.setWordWrap(True)
        self.estimate_time_label.setToolTip(
            'Rough estimate for the selected performance mode. Large video-heavy '
            'exports take much longer; a full library can take several hours.'
        )
        perf_lay.addWidget(self.estimate_time_label)
        self.perf_section = perf_box

        output_hint = QLabel(
            'Snapchat filters included by default. Optionally keep plain originals too.'
        )
        output_hint.setWordWrap(True)
        output_hint.setProperty('class', 'caption')
        self.save_raw_chk = QCheckBox('Also save without filters')
        self.save_raw_chk.setChecked(False)
        self.save_raw_chk.setToolTip(
            'Keeps a second copy of each memory without filters, stickers, or text overlays. '
            'Useful if you want the clean photo or video underneath.'
        )
        self.save_raw_chk.stateChanged.connect(self._on_save_raw_changed)

        self.technical_view_chk = QCheckBox('Technical view')
        self.technical_view_chk.setToolTip(
            'Shows advanced settings and buttons for SMK working data '
            '(staging, JSON, reports, checkpoint, logs, quarantine, debug). '
            'Leave off for a simple Desktop folder with just your memories.'
        )
        stored_tv = QSettings('SnapchatMemories', 'Downloader').value('technical_view', False)
        self.technical_view_chk.setChecked(str(stored_tv).lower() in ('1', 'true', 'yes'))
        self.technical_view_chk.stateChanged.connect(self._on_technical_view_changed)

        self.technical_view_hint = QLabel(
            'Technical view: advanced settings and buttons for working data '
            '(staging, reports, logs) — not your finished photos/videos.'
        )
        self.technical_view_hint.setWordWrap(True)
        self.technical_view_hint.setProperty('class', 'caption')

        # Technical-only: copy logistics next to finished memories after a run.
        self.add_run_info_chk = QCheckBox('Add run info to finished folder')
        self.add_run_info_chk.setToolTip(
            'After processing, copy a small SMK-run-info folder next to your '
            'memories (JSON, reports, logs, README — not the large staging extract). '
            'Useful for support or keeping a record of the run.'
        )
        stored_run_info = QSettings('SnapchatMemories', 'Downloader').value(
            'add_run_info', False
        )
        self.add_run_info_chk.setChecked(
            str(stored_run_info).lower() in ('1', 'true', 'yes')
        )
        self.add_run_info_chk.stateChanged.connect(self._on_add_run_info_changed)

        # Technical-only: default remains auto-delete; this opts into Review duplicates.
        self.manual_duplicate_review_chk = QCheckBox('Keep duplicates for review')
        self.manual_duplicate_review_chk.setToolTip(
            'When on, SMK still finds identical and look-alike duplicates but does not '
            'delete them. After the run, use Review duplicates to choose what to keep. '
            'When off (default), extras are removed automatically and the oldest name '
            'in each group is kept.'
        )
        stored_manual = QSettings('SnapchatMemories', 'Downloader').value(
            'manual_duplicate_review', False
        )
        self.manual_duplicate_review_chk.setChecked(
            str(stored_manual).lower() in ('1', 'true', 'yes')
        )
        self.manual_duplicate_review_chk.stateChanged.connect(
            self._on_manual_duplicate_review_changed
        )

        run_box, run_lay = self._section('Run')
        run_body = QHBoxLayout()
        run_body.setContentsMargins(0, 0, 0, 0)
        run_body.setSpacing(CONTROL_GAP)
        self.download_btn = QPushButton('Start processing')
        self.download_btn.setObjectName('runAction')
        self.download_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.download_btn.setToolTip(
            'Extract, merge overlays, embed metadata, and show a summary report. '
            'Creates the account folder if this is a new name.'
        )
        self.download_btn.clicked.connect(self.on_download_button_clicked)

        run_options_col = QVBoxLayout()
        run_options_col.setContentsMargins(0, 0, 0, 0)
        run_options_col.setSpacing(FIELD_GAP)
        run_options_col.addWidget(output_hint)
        run_options_col.addWidget(self.save_raw_chk)
        run_options_col.addWidget(self.technical_view_chk)
        run_options_col.addWidget(self.technical_view_hint)
        run_options_col.addWidget(self.add_run_info_chk)
        run_options_col.addWidget(self.manual_duplicate_review_chk)
        # Technical storage sizes belong here (not in My Data) so toggling
        # Technical view doesn't shove the zip section around.
        self.technical_storage_label = QLabel('')
        self.technical_storage_label.setProperty('class', 'caption')
        self.technical_storage_label.setWordWrap(True)
        run_options_col.addWidget(self.technical_storage_label)
        self._run_options_host = QWidget()
        self._run_options_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._run_options_host.setLayout(run_options_col)
        run_body.addWidget(self._run_options_host, 1)
        run_body.addWidget(self.download_btn, 0, Qt.AlignTop | Qt.AlignRight)
        run_body_host = QWidget()
        run_body_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        run_body_host.setLayout(run_body)
        run_lay.addWidget(run_body_host)

        run_footer = QHBoxLayout()
        run_footer.setContentsMargins(0, 0, 0, 0)
        run_footer.setSpacing(CONTROL_GAP)
        self.action_header = QLabel('Ready to start?')
        self.action_header.setProperty('class', 'caption')
        run_footer.addWidget(self.action_header)
        self.step_status_label = QLabel('Steps: waiting for export selection')
        self.step_status_label.setProperty('class', 'caption')
        run_footer.addWidget(self.step_status_label, 1)
        run_lay.addLayout(run_footer)

        after_box, after_lay = self._section('After processing')
        after_hint = QLabel(
            'Acts on the account chosen above. With Technical view off you only see '
            'Open finished folder and Where are my files? — Review duplicates and '
            'Open debug appear when Technical view is on.'
        )
        after_hint.setProperty('class', 'caption')
        after_hint.setWordWrap(True)
        after_lay.addWidget(after_hint)
        after_grid = QGridLayout()
        after_grid.setContentsMargins(0, 0, 0, 0)
        after_grid.setHorizontalSpacing(FIELD_GAP)
        after_grid.setVerticalSpacing(FIELD_GAP)
        self.open_folder_btn = QPushButton('Open finished folder')
        self.open_folder_btn.setObjectName('toolbarBtn')
        self.open_folder_btn.setToolTip('Your finished photos and videos (with Snapchat filters)')
        self.open_folder_btn.clicked.connect(self.open_download_folder)

        self.show_save_location_btn = QPushButton('Where are my files?')
        self.show_save_location_btn.setObjectName('toolbarBtn')
        self.show_save_location_btn.setToolTip(
            'Shows the full path to your finished photos and videos for this account'
        )
        self.show_save_location_btn.clicked.connect(self.show_finished_folder_locations)

        # Technical view only. Pipeline auto-removes duplicates unless
        # "Keep duplicates for review" is on; this is the manual follow-up.
        # (Open technical / Verify staging removed: Add run info copies logistics
        # next to photos; staging cleanup runs automatically after a clean finish.)
        self.review_duplicates_btn = QPushButton('Review duplicates')
        self.review_duplicates_btn.setObjectName('toolbarBtn')
        self.review_duplicates_btn.setToolTip(
            'Look for duplicate copies still in your library (identical files or '
            'the same picture/video saved twice). Use after a run with '
            '"Keep duplicates for review" on, or to double-check.'
        )
        self.review_duplicates_btn.clicked.connect(self.review_duplicates)

        self.open_debug_btn = QPushButton('Open debug folder')
        self.open_debug_btn.setObjectName('toolbarBtn')
        self.open_debug_btn.setToolTip('Opens technical/debug/ - processing logs and failed items')
        self.open_debug_btn.clicked.connect(self.open_debug_folder)

        after_grid.addWidget(self.open_folder_btn, 0, 0)
        after_grid.addWidget(self.show_save_location_btn, 0, 1)
        # Technical-only row (hidden unless Technical view is on).
        after_grid.addWidget(self.review_duplicates_btn, 1, 0)
        after_grid.addWidget(self.open_debug_btn, 1, 1)
        after_lay.addLayout(after_grid)

        self._account_section = account_box
        self._setup_section = setup_box
        self._perf_section = perf_box
        self._run_section = run_box
        self._after_section = after_box
        self._process_controls_grid_host = QWidget()
        self._process_controls_grid_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._process_controls_grid = QGridLayout(self._process_controls_grid_host)
        self._process_controls_grid.setContentsMargins(0, 0, 0, 0)
        from smd.theme import CONTROL_GAP as _cg, SECTION_GAP as _sg
        self._process_controls_grid.setHorizontalSpacing(_cg)
        self._process_controls_grid.setVerticalSpacing(_sg)
        controls_layout.addWidget(self._process_controls_grid_host)
        self._rebuild_process_controls_grid()
        self._init_account_section()
        self._refresh_after_processing_actions()

        progress_box, progress_lay = self._section('Progress')
        progress_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.progress_section = progress_box

        # Always-visible run stages (independent of the live run dashboard).
        self._run_stage_num = 0
        self._run_stage_total = 6
        self.stage_title_label = QLabel('Stages appear here when you start processing.')
        self.stage_title_label.setWordWrap(True)
        self.stage_title_label.setTextFormat(Qt.RichText)
        progress_lay.addWidget(self.stage_title_label)
        self.stage_overview_label = QLabel('')
        self.stage_overview_label.setProperty('class', 'caption')
        self.stage_overview_label.setWordWrap(True)
        self.stage_overview_label.setTextFormat(Qt.RichText)
        progress_lay.addWidget(self.stage_overview_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat('%p%')
        self.progress_bar.setFixedHeight(28)
        progress_lay.addWidget(self.progress_bar)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(CONTROL_GAP)
        status_col = QVBoxLayout()
        status_col.setContentsMargins(0, 0, 0, 0)
        status_col.setSpacing(2)
        self.status_label = QLabel('Ready')
        self.status_label.setWordWrap(True)
        status_col.addWidget(self.status_label)
        self.mode_status_label = QLabel('Mode: waiting')
        self.mode_status_label.setProperty('class', 'caption')
        status_col.addWidget(self.mode_status_label)
        self.download_details = QLabel('Files: 0/0 | Speed: - | ETA: -')
        self.download_details.setProperty('class', 'caption')
        status_col.addWidget(self.download_details)
        status_row.addLayout(status_col, 1)
        # Avoid the word "dashboard" — Segoe UI Variable mis-kerns "oa" so
        # "dashboard" renders with overlapping o/a on Windows.
        self.debug_output_toggle = QCheckBox('Show live run panel')
        self.debug_output_toggle.setToolTip(
            'Shows a larger live panel with progress, time estimates, and activity messages during processing'
        )
        self.debug_output_toggle.setChecked(False)
        self.debug_output_toggle.stateChanged.connect(self.toggle_debug_output)
        status_row.addWidget(self.debug_output_toggle, 0, Qt.AlignTop | Qt.AlignRight)
        progress_lay.addLayout(status_row)

        self.live_run_dashboard = LiveRunDashboard()
        self.live_run_dashboard.setVisible(self.debug_output_toggle.isChecked())
        progress_lay.addWidget(self.live_run_dashboard, 0)
        self._apply_dashboard_visibility(self.debug_output_toggle.isChecked())
        self._run_phase = "Waiting"
        self._run_log_buffer: list[str] = []
        self._last_estimate_label: str | None = None
        controls_layout.addWidget(progress_box)
        # Absorb leftover vertical space so the last section (Progress) keeps its
        # natural height instead of stretching tall when the dashboard is hidden.
        controls_layout.addStretch(1)

        self.download_running = False
        download_tab_layout.addWidget(self._form_tab(process_panel))
        self.tabs.addTab(download_tab, TAB_SAVE_MEMORIES)


    def update_status_animation(self):
        """Animate status text with moving indicator"""
        if not self.status_animation_active:
            return
        
        # Create moving dots animation (8 frame cycle)
        indicators = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧']
        frame = indicators[self.status_animation_frame % len(indicators)]
        
        # Update status with animated frame
        animated_text = f"{frame} {self.status_base_text}"
        self.unified_status.setText(animated_text)
        self.status_animation_frame += 1

    def start_status_animation(self, base_text):
        """Start animated status display"""
        self.status_base_text = base_text
        self.status_animation_active = True
        self.status_animation_frame = 0
        self.status_animation_timer.start(100)  # Update every 100ms

    def stop_status_animation(self):
        """Stop animated status display"""
        self.status_animation_active = False
        self.status_animation_timer.stop()

    def refresh_system_profile(self):
        """Update PC / power labels and warn if power source changed."""
        from smd.system_profile import (
            compute_workers,
            get_system_profile,
        )

        profile = get_system_profile()
        settings = compute_workers(self.performance_mode, profile, task="export")

        self.system_profile_label.setText(
            f"{profile.summary()} • ~{settings.max_workers} parallel jobs"
        )
        self.cpu_info_label.setText(
            f"({profile.physical_cores} cores / {profile.logical_cpus} threads, {settings.max_workers} jobs)"
        )

        if self._last_power_on_battery is not None and profile.on_battery is not None:
            if profile.on_battery != self._last_power_on_battery:
                msg = (
                    "On battery - consider Balanced or Eco for the next run"
                    if profile.on_battery
                    else "Plugged in - Maximum is fine for the next run"
                )
                self._apply_status(self.status_label, msg, 'warn')
                if hasattr(self, 'unified_status'):
                    self._apply_status(self.unified_status, msg, 'warn')
        self._last_power_on_battery = profile.on_battery

    def apply_recommended_settings(self, silent: bool = False):
        """Apply hardware-based performance mode recommendation."""
        from smd.system_profile import mode_to_combo_index, recommend_settings

        rec = recommend_settings()
        self.performance_mode = rec.performance_mode
        self._persist_perf_mode()
        self.perf_mode_combo.blockSignals(True)
        self.perf_mode_combo.setCurrentIndex(mode_to_combo_index(rec.performance_mode))
        self.perf_mode_combo.blockSignals(False)
        self.refresh_system_profile()
        if not silent:
            msg = (
                f"Recommended: {rec.performance_mode.title()} "
                f"({rec.max_workers} parallel jobs - {rec.reason})"
            )
            self._apply_status(self.status_label, msg, 'info')

    def on_perf_mode_changed(self, index):
        """Handle performance mode change"""
        mode_map = {0: 'maximum', 1: 'balanced', 2: 'conservative'}
        self.performance_mode = mode_map.get(index, 'balanced')
        self._persist_perf_mode()
        self.refresh_system_profile()
        self._refresh_time_estimate()
        self.update_export_ui_mode()

    def _persist_perf_mode(self) -> None:
        """Remember the selected performance mode across launches."""
        try:
            self._perf_settings.setValue("performance_mode_v1", self.performance_mode)
        except Exception:
            pass

    def _account_name(self) -> str:
        """The one account the whole tab acts on - set via the Account
        section (New/Old account) and reused for both the next run and every
        'After processing' button. See DECISIONS.md (2026-07-19, inline
        Account toggle replaces the per-export dialog and the separate
        'Selected account folder' selector).

        In New account mode, a typed-but-not-yet-created name wins over any
        leftover active folder so Start cannot silently write into the
        previous account (e.g. typing Mary while Las was still active)."""
        pending = self._pending_new_account_name()
        if pending:
            return pending
        return getattr(self, '_active_account_name', '').strip()

    def _pending_new_account_name(self) -> str:
        """Folder name typed under New account, or '' if not applicable."""
        if not getattr(self, 'new_account_radio', None):
            return ''
        if not self.new_account_radio.isChecked():
            return ''
        raw = ''
        try:
            raw = self.new_account_name_edit.text().strip()
        except Exception:
            return ''
        if not raw or not self._is_valid_account_name(raw):
            return ''
        from smd.account_layout import ensure_memories_suffix

        return ensure_memories_suffix(raw)

    def _after_processing_account_name(self) -> str:
        """Kept as a thin alias - After processing always acts on the same
        active account as everything else now."""
        return self._account_name()

    def _list_known_accounts(self) -> list:
        """Account folders that already exist on disk - in either layout
        (Desktop/<name>/ simple, or <base_dir>/<name>/ technical) - so the
        Account section's 'Old account' list and After processing always
        have real accounts to offer, regardless of the live Technical view
        toggle."""
        from smd.account_layout import AccountPaths

        names: set[str] = set()
        base_dir_resolved = None
        try:
            base_dir = Path(self.get_download_base_dir())
            base_dir_resolved = base_dir.resolve()
            if base_dir.is_dir():
                names.update(
                    d.name
                    for d in base_dir.iterdir()
                    if d.is_dir() and not d.name.startswith('.')
                )
        except Exception:
            pass

        try:
            desktop = Path.home() / 'Desktop'
            internal_root = AccountPaths.internal_accounts_root()
            if desktop.is_dir():
                for d in desktop.iterdir():
                    if not d.is_dir() or d.name.startswith('.'):
                        continue
                    # The Technical-mode base dir (e.g. Desktop/Memories,
                    # containing real account subfolders like Las/, Mary/)
                    # commonly sits directly on the Desktop - it is a
                    # container, not an account itself, so it must never be
                    # offered as one just because it's a non-empty folder.
                    try:
                        if base_dir_resolved is not None and d.resolve() == base_dir_resolved:
                            continue
                    except OSError:
                        pass
                    internal = internal_root / d.name
                    if internal.is_dir() or any(d.iterdir()):
                        names.add(d.name)
        except Exception:
            pass

        return sorted(names, key=str.lower)

    def _init_account_section(self) -> None:
        """Pre-select a sensible Account section default at startup - the
        last-used account under Existing account if one exists, else New
        account. Existing account mode activates the shown folder automatically."""
        last_account = ''
        try:
            last_account = str(
                QSettings('SnapchatMemories', 'Downloader').value('last_account_name', '') or ''
            ).strip()
        except Exception:
            pass
        known = self._list_known_accounts()
        if last_account and last_account in known:
            self._old_account_candidate = last_account
            self.old_account_radio.setChecked(True)
        elif known:
            self._old_account_candidate = known[-1]
            self.old_account_radio.setChecked(True)
        else:
            self.new_account_radio.setChecked(True)
        self._on_account_mode_toggled()
        self._refresh_account_section()

    def _set_active_account(self, account_name: str, *, create: bool = False) -> bool:
        """Single point of truth for which account folder the whole tab acts
        on. Creates the folder immediately when *create* is True (new
        account, or confirming an old one), then refreshes every dependent
        widget (Account banner, After processing enablement, Start button)."""
        account_name = (account_name or '').strip()
        if not account_name or not self._is_valid_account_name(account_name):
            return False
        if create:
            try:
                self._account_paths(account_name, create=True)
            except Exception as exc:
                QMessageBox.warning(self, 'Account', f'Could not create that folder:\n{exc}')
                return False
        self._active_account_name = account_name
        try:
            QSettings('SnapchatMemories', 'Downloader').setValue('last_account_name', account_name)
        except Exception:
            pass
        self.update_download_path_label(account_name)
        self._refresh_account_section()
        self._refresh_after_processing_actions()
        self._update_run_readiness()
        if getattr(self, 'export_analysis', None):
            self.update_export_ui_mode()
        return True

    def _refresh_account_section(self) -> None:
        """Keep the Account section's banner and Existing account candidate in
        sync with the active account and what's actually on disk, without
        disturbing which radio the user has selected."""
        from smd.account_layout import ensure_memories_suffix

        active = self._account_name()
        if active:
            try:
                paths = self._account_paths(active, create=False)
                self.active_account_label.setText(
                    f'<b>Active account:</b> {html.escape(active)} - saved to '
                    f'{html.escape(str(paths.library_root))}'
                )
            except Exception:
                self.active_account_label.setText(f'<b>Active account:</b> {html.escape(active)}')
        else:
            self.active_account_label.setText(
                'No account selected yet - pick New account or Existing account above.'
            )

        known = self._list_known_accounts()
        if known:
            candidate = getattr(self, '_old_account_candidate', '') or active
            if candidate not in known:
                candidate = known[-1]
            self._old_account_candidate = candidate
            display_name = ensure_memories_suffix(candidate)
            self.old_account_label.setText(
                f'Your output folder is <b>{html.escape(display_name)}</b>'
            )
            # Beside the active-path banner — usable whenever prior accounts exist.
            self.old_account_change_btn.setEnabled(True)
        else:
            self._old_account_candidate = ''
            self.old_account_label.setText('No previous accounts found yet.')
            self.old_account_change_btn.setEnabled(False)

    def _on_account_mode_toggled(self, _checked: bool = False) -> None:
        is_new = self.new_account_radio.isChecked()
        self.new_account_name_edit.setEnabled(is_new)
        can_existing = bool(self._list_known_accounts())
        self.old_account_label.setEnabled(not is_new)
        self.old_account_change_btn.setEnabled(can_existing)
        if is_new:
            # Drop the previous Existing-account selection so a typed name
            # cannot be ignored while Start still writes into Las/etc.
            self._active_account_name = ''
            try:
                self.technical_storage_label.setText('')
            except Exception:
                pass
            self._refresh_account_section()
            self._refresh_after_processing_actions()
        self._on_new_account_name_changed(self.new_account_name_edit.text())
        if not is_new and can_existing:
            self._activate_existing_account_candidate(silent=True)
        else:
            self._update_run_readiness()

    def _on_new_account_name_changed(self, text: str) -> None:
        from smd.account_layout import ensure_memories_suffix

        name = (text or '').strip()
        if not getattr(self, 'new_account_radio', None) or not self.new_account_radio.isChecked():
            self.new_account_preview_label.setText('')
            self._update_run_readiness()
            return
        if not name:
            self.new_account_preview_label.setText(
                'Type a name — the folder is created when you Start processing.'
            )
        elif not self._is_valid_account_name(name):
            self.new_account_preview_label.setText('Name cannot contain \\ / : * ? " < > |')
        else:
            folder = ensure_memories_suffix(name)
            self.new_account_preview_label.setText(
                f'Will save to: {folder} (created when you Start processing)'
            )
        self._refresh_account_section()
        self._update_run_readiness()

    def _activate_existing_account_candidate(self, *, silent: bool = False) -> None:
        from smd.account_layout import (
            ensure_memories_suffix,
            rename_simple_mode_account,
            rename_technical_mode_account,
            resolve_existing_account_layout,
        )

        candidate = getattr(self, '_old_account_candidate', '') or self._account_name()
        if not candidate:
            if not silent:
                QMessageBox.information(
                    self, 'Existing account', 'No previous account folder yet.'
                )
            return
        final_name = ensure_memories_suffix(candidate)
        if final_name != candidate:
            base_dir = Path(self.get_download_base_dir())
            layout_info = resolve_existing_account_layout(candidate, base_dir)
            try:
                if layout_info and layout_info[0] == 'technical':
                    rename_technical_mode_account(layout_info[1] or base_dir, candidate, final_name)
                else:
                    rename_simple_mode_account(candidate, final_name)
            except Exception:
                final_name = candidate
        if self._set_active_account(final_name, create=False):
            self._old_account_candidate = final_name
            if not silent:
                self._apply_status(self.status_label, f'Using "{final_name}".', 'ok')

    def _on_old_account_change(self) -> None:
        known = self._list_known_accounts()
        if not known:
            QMessageBox.information(
                self, 'Change output folder', 'No previously processed accounts found yet.'
            )
            return
        current = getattr(self, '_old_account_candidate', '') or self._account_name()
        start_idx = known.index(current) if current in known else 0
        name, ok = QInputDialog.getItem(
            self, 'Change output folder', 'Choose an existing account:', known, start_idx, False
        )
        if ok and name:
            self._old_account_candidate = name
            self._refresh_account_section()
            self._activate_existing_account_candidate(silent=True)

    @staticmethod
    def _is_valid_account_name(name: str) -> bool:
        if not name or name in ('.', '..'):
            return False
        return not any(ch in name for ch in '<>:"/\\|?*')

    def _rebuild_process_controls_grid(self) -> None:
        """Stack sections in a single column so none of them ever has to share
        row width with a sibling - a 2-column layout here forced Run and After
        processing side by side, and their combined natural width couldn't
        shrink below ~1600px, wedging the whole tab wide no matter the window
        size. Stacking vertically works at any window width since the tab is
        already scrollable."""
        grid = self._process_controls_grid
        for section in (
            self._account_section,
            self._setup_section,
            self._perf_section,
            self._run_section,
            self._after_section,
        ):
            grid.removeWidget(section)
            section.setParent(self._process_controls_grid_host)

        # Performance is always visible — Technical view only gates staging/
        # reports/leftovers controls, not speed settings.
        self._perf_section.setVisible(True)
        row = 0
        grid.addWidget(self._account_section, row, 0)
        row += 1
        grid.addWidget(self._setup_section, row, 0)
        row += 1
        grid.addWidget(self._perf_section, row, 0)
        row += 1
        grid.addWidget(self._run_section, row, 0)
        row += 1
        grid.addWidget(self._after_section, row, 0)
        grid.setColumnStretch(0, 1)

    def _set_run_lockout(self, active: bool) -> None:
        """Dim and disable Setup/Performance/After-processing while a run is
        active. Keeps Start/Cancel clickable, but locks Run option checkboxes
        (Also save without filters / Technical view) so mid-run toggles cannot
        change layout expectations. Progress stays scrollable."""
        for section in (
            getattr(self, '_account_section', None),
            getattr(self, '_setup_section', None),
            getattr(self, '_perf_section', None),
            getattr(self, '_after_section', None),
        ):
            if section is None:
                continue
            section.setEnabled(not active)
            if active:
                effect = section.graphicsEffect()
                if not isinstance(effect, QGraphicsOpacityEffect):
                    effect = QGraphicsOpacityEffect(section)
                    section.setGraphicsEffect(effect)
                effect.setOpacity(0.4)
            else:
                section.setGraphicsEffect(None)
        options_host = getattr(self, '_run_options_host', None)
        if options_host is not None:
            options_host.setEnabled(not active)

    def _set_keep_awake(self, active: bool) -> None:
        """Prevent Windows from sleeping the system or display while a run
        (including the post-run verification/finalize passes) is in
        progress, then release it as soon as that work ends.

        Motivated by a user report: some AMD GPUs render at a fraction of
        normal speed for a while after the display wakes from sleep (a
        known driver quirk - Ctrl+Shift+Win+B, which restarts the graphics
        driver, is the common workaround). If SMK is mid-run when the
        monitor sleeps, that post-wake slowdown hits ffmpeg too. Keeping
        the display on for the run's duration avoids the wake cycle
        entirely instead of trying to detect/react to it. See
        agent-docs/DECISIONS.md, "Keep system/display awake during a run".
        """
        if sys.platform != 'win32':
            return
        try:
            import ctypes

            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED if active else 0)
            ctypes.windll.kernel32.SetThreadExecutionState(flags)
        except Exception:
            pass

    def _update_run_readiness(self) -> None:
        """Enable Start only when export is valid and account name is usable."""
        if getattr(self, 'download_running', False):
            self.download_btn.setEnabled(True)
            return

        analysis = getattr(self, 'export_analysis', None)
        bundled = bool(analysis and analysis.is_bundled)
        name = self._account_name()
        valid_name = self._is_valid_account_name(name)
        ready = bundled and valid_name

        self.download_btn.setEnabled(ready)
        if not analysis:
            tip = 'Select a Snapchat export ZIP or folder first.'
        elif not bundled:
            tip = 'This export has no media files. Request a new export from Snapchat.'
        elif not name:
            if getattr(self, 'new_account_radio', None) and self.new_account_radio.isChecked():
                tip = 'Type a new account name above — Start processing creates the folder.'
            else:
                tip = 'Choose New account or Existing account in the Account section above first.'
        elif not valid_name:
            tip = 'Folder name cannot contain \\ / : * ? " < > |'
        elif self._pending_new_account_name():
            tip = f'Start will create "{name}" and process into that folder.'
        else:
            tip = 'Extract, merge overlays, embed metadata, and show a summary report'
        self.download_btn.setToolTip(tip)

    def update_export_ui_mode(self):
        """Update summary and button labels based on detected export type."""
        from smd.system_profile import compute_workers, get_system_profile

        analysis = getattr(self, 'export_analysis', None)
        bundled = bool(analysis and analysis.is_bundled)

        if not analysis:
            self.download_btn.setText('Start processing')
            self.action_header.setText('Ready to start?')
            self._refresh_time_estimate()
            self._update_run_readiness()
            return

        self._refresh_time_estimate()
        settings = compute_workers(self.performance_mode, get_system_profile(), task='export')
        parts = len(analysis.zip_paths or [])
        technical = self._technical_view_enabled()

        if bundled:
            self.download_btn.setText('Start processing')
            self.action_header.setText('Ready to process?')
            from smd.media_types import format_bytes

            zip_n = parts
            zip_label = f"{zip_n} Snapchat export ZIP(s)" if zip_n != 1 else "1 Snapchat export ZIP"
            size_bit = (
                f" ({format_bytes(analysis.zip_bytes)})"
                if getattr(analysis, "zip_bytes", 0)
                else ""
            )
            year_bit = ""
            if analysis.year_min is not None and analysis.year_max is not None:
                if analysis.year_min == analysis.year_max:
                    year_bit = f" ({analysis.year_min})"
                else:
                    year_bit = f" ({analysis.year_min}–{analysis.year_max})"
            url_bit = (
                "Download URLs empty (bundled/offline - expected)."
                if analysis.rows_with_link == 0
                else f"{analysis.rows_with_link:,} JSON rows also list download URLs."
            )
            worker_line = (
                f"{settings.max_workers} parallel jobs • metadata, GPS, and overlays"
                if technical
                else "metadata, GPS, and Snapchat filters included"
            )
            self.export_summary_label.setText(
                f"✓ {zip_label} found{size_bit} — memories_history.json located inside. "
                f"ZIPs are extracted automatically when processing starts.<br>"
                f"✓ memories_history.json found — {analysis.json_rows:,} memories{year_bit}. "
                f"{url_bit}<br>"
                f"{worker_line}"
            )
            self.step_status_label.setText(
                'Steps on start: detect export → extract ZIPs → match JSON → '
                'merge overlays → embed metadata → summary report'
            )
            self.export_summary_label.setObjectName('infoBanner')
            self.export_summary_label.setStyleSheet('')
        else:
            self.download_btn.setText('Start processing')
            self.action_header.setText('Export not supported')
            detail = html.escape(analysis.message) if analysis.message else (
                'This export does not include media files.'
            )
            self.export_summary_label.setText(
                f"<b>This export does not include media files.</b><br>{detail}<br>"
                "Open the <b>Guide</b> tab for how to request a Memories export with media in the ZIP. "
                "SMK stays offline-only (no CDN downloads)."
            )
            self.export_summary_label.setObjectName('infoBanner')
            self.export_summary_label.setStyleSheet('')

        self._update_run_readiness()

    def _on_technical_view_changed(self, _state: int = 0) -> None:
        super()._on_technical_view_changed(_state)
        if getattr(self, 'export_analysis', None):
            self.update_export_ui_mode()

    def _on_add_run_info_changed(self, _state: int = 0) -> None:
        QSettings('SnapchatMemories', 'Downloader').setValue(
            'add_run_info',
            bool(
                getattr(self, 'add_run_info_chk', None)
                and self.add_run_info_chk.isChecked()
            ),
        )

    def _add_run_info_enabled(self) -> bool:
        """Copy SMK-run-info/ after a run when Technical view + this checkbox."""
        if not self._technical_view_enabled():
            return False
        chk = getattr(self, 'add_run_info_chk', None)
        return chk is not None and chk.isChecked()

    def _on_manual_duplicate_review_changed(self, _state: int = 0) -> None:
        QSettings('SnapchatMemories', 'Downloader').setValue(
            'manual_duplicate_review',
            bool(
                getattr(self, 'manual_duplicate_review_chk', None)
                and self.manual_duplicate_review_chk.isChecked()
            ),
        )

    def _auto_delete_duplicates_enabled(self) -> bool:
        """Auto-delete unless Technical view + Keep duplicates for review."""
        if not self._technical_view_enabled():
            return True
        chk = getattr(self, 'manual_duplicate_review_chk', None)
        return not (chk is not None and chk.isChecked())

    def _on_save_raw_changed(self, _state: int = 0) -> None:
        super()._on_save_raw_changed(_state)
        if getattr(self, 'export_analysis', None):
            self.update_export_ui_mode()

    def _export_default_dir(self) -> str:
        default_dir = str(Path.home() / 'Downloads')
        if not Path(default_dir).exists():
            default_dir = str(Path.home() / 'Pictures')
        if not Path(default_dir).exists():
            default_dir = str(Path.home())
        return default_dir

    @staticmethod
    def _suggested_new_account_name(seed, zip_paths) -> str:
        """Best-effort text to pre-fill the 'New account' name field - purely
        from how the user organized files on disk (selected folder / ZIP
        parent folder name), never from the export's own account info. SMK
        does not read or require Snapchat account/profile data for naming;
        the user names accounts themselves in the Account section."""
        from smd.export_detect import is_usable_account_folder_name

        if not isinstance(seed, list):
            folder = Path(seed)
            if folder.is_dir() and is_usable_account_folder_name(folder.name):
                return folder.name
        if zip_paths:
            parent_name = zip_paths[0].parent.name
            if is_usable_account_folder_name(parent_name):
                return parent_name
        return ''

    def _suggest_account_from_export(self, seed, zip_paths) -> None:
        """Non-blocking nudge after picking an export: if this exact export
        was already processed into a known account before (matched purely by
        the export's own mydata~ID - technical bookkeeping, not personal
        data - see DECISIONS.md), pre-select Existing account with that folder.
        The user still sees and confirms the choice in the Account section -
        nothing is created or renamed silently. Leaves the Account section
        alone if an account is already active."""
        from smd.export_detect import export_base_ids, find_existing_account_folder_name

        if self._active_account_name:
            return

        search_dirs: list[Path] = []
        desktop = Path.home() / 'Desktop'
        if desktop.is_dir():
            search_dirs.append(desktop)
        base_dir = Path(self.get_download_base_dir())
        if base_dir.is_dir() and base_dir not in search_dirs:
            search_dirs.append(base_dir)

        mydata_ids = export_base_ids(zip_paths)
        match = find_existing_account_folder_name(search_dirs, identity=None, mydata_ids=mydata_ids)
        known = self._list_known_accounts()
        if match and match in known:
            self._old_account_candidate = match
            self.old_account_radio.setChecked(True)
        elif not known:
            self.new_account_radio.setChecked(True)
            suggestion = self._suggested_new_account_name(seed, zip_paths)
            if suggestion and not self.new_account_name_edit.text().strip():
                self.new_account_name_edit.setText(suggestion)
        self._refresh_account_section()

    def _refresh_time_estimate(self) -> None:
        """Update the Performance section estimate label (no popup)."""
        label = getattr(self, 'estimate_time_label', None)
        if label is None:
            return
        analysis = getattr(self, "export_analysis", None)
        if not analysis or not analysis.is_bundled:
            label.setText(
                'Estimated time: choose a Snapchat export folder to see a rough estimate.'
            )
            self._last_estimate_label = None
            return
        from smd.system_profile import MODE_LABELS, get_system_profile
        from smd.time_estimate import estimate_bundled_processing

        # Prefer ZIP media count over JSON rows — JSON often lists more rows
        # than unique mains in the archive (Mary: 915 JSON vs 696 ZIP mains).
        file_count = analysis.main_file_count or analysis.json_rows or 1
        account_name = self._account_name()
        needs_extract = True
        staging_gb = 0.0
        if account_name:
            try:
                paths = self._account_paths(account_name)
                staging = paths.staging_dir
                if staging.is_dir():
                    mains = sum(
                        1
                        for p in staging.iterdir()
                        if p.is_file() and "-main." in p.name.lower()
                    )
                    needs_extract = mains < max(50, file_count // 20)
                    if not needs_extract:
                        staging_gb = sum(
                            p.stat().st_size for p in staging.rglob("*") if p.is_file()
                        ) / (1024**3)
            except Exception:
                pass

        overlay_fraction = 0.24
        if analysis.main_file_count and analysis.main_file_count > 0:
            overlay_fraction = min(
                1.0, max(0.0, (analysis.overlay_file_count or 0) / analysis.main_file_count)
            )

        # Default assumes a video-heavy export (Las was ~62% video). Under-defaulting
        # made old estimates look "minutes" when real runs took hours.
        video_fraction = 0.40
        try:
            import tempfile
            from smd.export_detect import extract_json_from_zips
            from smd.utils import load_memories

            zip_paths = analysis.zip_paths or []
            if zip_paths:
                est_json = Path(tempfile.gettempdir()) / "smd_estimate_memories_history.json"
                extract_json_from_zips(zip_paths, est_json)
                memories = load_memories(est_json)
                if memories:
                    videos = sum(1 for m in memories if (m.media_type or "").strip().lower() == "video")
                    video_fraction = min(1.0, max(0.0, videos / max(len(memories), 1)))
        except Exception:
            pass

        if needs_extract and staging_gb <= 0.0:
            try:
                zip_paths = analysis.zip_paths or []
                if zip_paths:
                    staging_gb = sum(p.stat().st_size for p in zip_paths) / (1024**3)
            except Exception:
                pass

        est = estimate_bundled_processing(
            file_count,
            profile=get_system_profile(),
            needs_zip_extract=needs_extract,
            staging_gb=staging_gb,
            overlay_fraction=overlay_fraction,
            video_fraction=video_fraction,
        )
        mode = self.performance_mode
        data = est.get(mode) or next(iter(est.values()), {})
        mode_label = MODE_LABELS.get(mode, mode)
        dur = str(data.get("label") or "?")
        self._last_estimate_label = dur
        extract_note = (
            "ZIP unpack included"
            if needs_extract
            else "staging already on disk (faster)"
        )
        label.setText(
            f"Estimated time ({mode_label}): about {dur} for ~{file_count:,} memories "
            f"({int(video_fraction * 100)}% video, {int(overlay_fraction * 100)}% with filters; "
            f"{extract_note}). Rough guide only — based on file count and filter mix, "
            f"not ZIP folder size (finished libraries are often smaller than the ZIPs)."
        )

    def select_export_folder(self):
        """Open folder picker for a directory containing all ZIP parts -
        the one place to point SMK at your export (see DECISIONS.md,
        2026-07-19, unifying 'Choose ZIP files'/'Choose folder')."""
        folder = QFileDialog.getExistingDirectory(
            self,
            'Select the folder with your Snapchat My Data ZIP file(s)',
            self._export_default_dir(),
        )
        if folder:
            self._set_export_selection(folder)

    def _set_export_selection(self, path: str):
        from smd.export_detect import analyze_zip_export, resolve_export_zip_paths

        p = Path(path)
        self.selected_zip = path
        zip_paths = resolve_export_zip_paths(p)

        analysis = analyze_zip_export(p)
        self.export_analysis = analysis
        part_txt = f"{len(zip_paths)} ZIP parts" if len(zip_paths) > 1 else "1 ZIP"
        if analysis.is_bundled:
            fmt = f"Bundled • {part_txt} • ~{analysis.main_file_count} main files"
        else:
            fmt = "No media in ZIP — request a new export from Snapchat"

        label_name = p.name + "/" if p.is_dir() else p.name
        self.zip_label.setText(f'{label_name} ({fmt})')
        from smd.theme import apply_status_property
        apply_status_property(self.zip_label, 'ok')
        if analysis.is_bundled:
            self._suggest_account_from_export(p, zip_paths)
        self.update_export_ui_mode()

    def get_default_base_dir(self):
        """Default to Desktop so accounts sit as Las-memories / Mary-memories."""
        desktop = Path.home() / 'Desktop'
        try:
            desktop.mkdir(parents=True, exist_ok=True)
            return str(desktop)
        except Exception:
            docs = Path.home() / 'Documents'
            docs.mkdir(parents=True, exist_ok=True)
            return str(docs)

    def get_download_base_dir(self):
        try:
            settings = QSettings('SnapchatMemories', 'Downloader')
            base_dir = settings.value('download_base_dir', None)
            if not base_dir:
                base_dir = self.get_default_base_dir()
                settings.setValue('download_base_dir', base_dir)
            from smd.account_layout import (
                is_legacy_desktop_accounts_wrapper,
                migrate_accounts_out_of_desktop_wrapper,
            )

            base_path = Path(str(base_dir))
            # Always retire Desktop/Memories and Desktop/SMD Media — even when
            # empty — otherwise mkdir(parents=True) for a new account recreates them.
            if is_legacy_desktop_accounts_wrapper(base_path):
                new_base, _actions = migrate_accounts_out_of_desktop_wrapper(base_path)
                settings.setValue('download_base_dir', str(new_base))
                return str(new_base)
            return str(base_path)
        except Exception:
            return self.get_default_base_dir()

    def _account_paths(self, account_name: str, *, create: bool = False):
        """
        Resolve where *account_name* actually lives on disk. For an existing
        account this always trusts what was persisted the first time it was
        created (simple vs technical layout, and keep_raw) - never today's
        live Technical view toggle - which is what used to make After
        processing (and re-runs) silently look in the wrong folder whenever
        the toggle didn't match how the account was originally made. See
        DECISIONS.md (2026-07-19, persisted per-account layout).

        A brand-new account (create=True, never seen before) picks up
        today's toggle + "Also save without filters" checkbox and persists
        that choice immediately, so every later call resolves consistently.
        """
        from smd.account_layout import (
            AccountPaths,
            migrate_account_layout,
            migrate_flat_accounts_root,
            migrate_flat_library_to_subfolders,
            normalize_account_dir,
            resolve_account_paths,
            resolve_existing_account_layout,
            save_account_layout_info,
        )

        live_keep_raw = self.save_raw_chk.isChecked() if hasattr(self, 'save_raw_chk') else False
        current_base_dir = Path(self.get_download_base_dir())

        existing = resolve_existing_account_layout(account_name, current_base_dir)
        if existing is not None:
            layout, base_dir, stored_keep_raw = existing
            # A fresh run may add raw copies going forward; a lookup (After
            # processing) trusts what's actually on disk over today's checkbox.
            keep_raw = (live_keep_raw or stored_keep_raw) if create else stored_keep_raw
        else:
            layout = 'technical' if self._technical_view_enabled() else 'simple'
            base_dir = current_base_dir if layout == 'technical' else None
            keep_raw = live_keep_raw

        if layout == 'technical':
            base_dir = Path(base_dir or current_base_dir)
            if create:
                migrate_flat_accounts_root(base_dir)
            account_dir = normalize_account_dir(base_dir / account_name)
            if create:
                paths = resolve_account_paths(
                    account_dir, migrate=True, create=True, keep_raw=keep_raw
                )
                if keep_raw:
                    migrate_flat_library_to_subfolders(paths.library_root)
                save_account_layout_info(
                    paths.account_dir, layout='technical', base_dir=str(base_dir), keep_raw=keep_raw
                )
            else:
                # create=False is still a read of a real, already-existing
                # account - run migration (safe/idempotent: renames only,
                # never invents folders) so a lookup made before the next
                # "Start processing" run still finds legacy-layout
                # files (old downloads/ name, old always-nested merged/).
                paths = resolve_account_paths(
                    account_dir, migrate=True, create=False, keep_raw=keep_raw
                )
            return paths

        paths = AccountPaths.for_user(account_name, keep_raw=keep_raw)
        if create:
            paths.ensure_user_dirs(keep_raw=keep_raw)
            migrate_account_layout(paths)
            if keep_raw:
                migrate_flat_library_to_subfolders(paths.library_root)
            save_account_layout_info(paths.account_dir, layout='simple', keep_raw=keep_raw)
        elif paths.account_dir.exists():
            migrate_account_layout(paths)
        return paths

    def update_download_path_label(
        self, account_name: str, *, create: bool = False, storage_scan: bool = True
    ) -> None:
        try:
            paths = self._account_paths(account_name, create=create)
            if not paths.account_dir.exists() and not create and not paths.library_root.exists():
                self.technical_storage_label.setText(
                    'Technical: (folder is created when you start processing)'
                )
                self._refresh_after_processing_actions()
                return
            if self._technical_view_enabled():
                if storage_scan:
                    self.technical_storage_label.setText('Technical: Calculating…')
                    self._pending_storage_account = account_name
                    self._run_technical_storage_scan()
            else:
                self.technical_storage_label.setText('')
        except Exception:
            self.technical_storage_label.setText('')
        self._refresh_after_processing_actions()

    def _run_technical_storage_scan(self) -> None:
        account_name = self._pending_storage_account or self._account_name()
        if not account_name or not self._technical_view_enabled():
            return
        try:
            paths = self._account_paths(account_name, create=False)
        except Exception:
            return
        self._storage_scan_generation += 1
        generation = self._storage_scan_generation
        self._stop_worker('technical_storage_worker')
        self.technical_storage_worker = TechnicalStorageWorker(paths, account_name)
        self.technical_storage_worker.finished_ok.connect(
            lambda name, rows, gen=generation: self._on_technical_storage_ready(name, rows, gen)
        )
        self.technical_storage_worker.error.connect(self._on_technical_storage_error)
        self.technical_storage_worker.start()

    def _on_technical_storage_ready(self, account_name: str, rows, generation: int) -> None:
        if generation != self._storage_scan_generation:
            return
        if self._account_name() != account_name or not self._technical_view_enabled():
            return
        try:
            from smd.account_layout import format_bytes

            paths = self._account_paths(account_name, create=False)
            staging_bytes = next((n for label, n in rows if label == 'staging'), 0)
            total_tech = sum(n for _, n in rows)
            parts = [f"staging {format_bytes(staging_bytes)}"]
            parts.extend(
                f"{label} {format_bytes(size)}"
                for label, size in rows
                if label != 'staging' and size > 0
            )
            self.technical_storage_label.setText(
                f"Technical: {paths.technical_dir} - {', '.join(parts)} "
                f"(total {format_bytes(total_tech)})"
            )
        except Exception:
            self.technical_storage_label.setText('Technical: (unavailable)')

    def _on_technical_storage_error(self, _message: str) -> None:
        if self._technical_view_enabled():
            self.technical_storage_label.setText('Technical: (size scan failed)')

    @staticmethod
    def _folder_has_files(folder: Path, *, min_files: int = 1) -> bool:
        if not folder.is_dir():
            return False
        try:
            found = 0
            for entry in folder.iterdir():
                if entry.is_file():
                    found += 1
                    if found >= min_files:
                        return True
            return found >= min_files
        except OSError:
            return False

    def _refresh_after_processing_actions(self) -> None:
        """Enable After processing buttons only when the relevant project data
        exists for the active account - independent of Technical view, which
        used to make these buttons resolve to the wrong folder entirely (see
        DECISIONS.md, 2026-07-19, persisted per-account layout)."""
        buttons = (
            self.open_folder_btn,
            self.show_save_location_btn,
            self.review_duplicates_btn,
            self.open_debug_btn,
        )
        busy = bool(getattr(self, 'download_running', False))
        account_name = self._account_name()

        def _disable_all() -> None:
            for btn in buttons:
                btn.setEnabled(False)

        if not account_name or busy:
            _disable_all()
            return

        try:
            paths = self._account_paths(account_name, create=False)
        except Exception:
            _disable_all()
            return

        has_merged = self._folder_has_files(paths.merged_dir)
        has_debug = self._folder_has_files(paths.debug_dir)

        self.open_folder_btn.setEnabled(has_merged)
        self.show_save_location_btn.setEnabled(bool(account_name) and not busy)
        self.review_duplicates_btn.setEnabled(has_merged)
        self.open_debug_btn.setEnabled(has_debug)

    def open_download_folder(self):
        try:
            account_name = self._after_processing_account_name()
            if not account_name:
                QMessageBox.information(self, 'Folder', 'Enter an account name first.'); return
            paths = self._account_paths(account_name)
            paths.library_root.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.library_root)))
        except Exception as e:
            try:
                QMessageBox.warning(self, 'Folder Error', f'Could not open folder:\n{e}')
            except Exception:
                pass

    def show_finished_folder_locations(self):
        """Tell the user where finished photos/videos live for the active account."""
        try:
            account_name = self._after_processing_account_name()
            if not account_name:
                QMessageBox.information(
                    self, 'Where are my files?', 'Choose an account first.'
                )
                return
            paths = self._account_paths(account_name, create=False)
            lines = [
                f'Account: {account_name}',
                '',
                'Your finished photos and videos (with Snapchat filters):',
                str(paths.merged_dir),
            ]
            # Only mention raw/ when it sits under the user library (keep_raw
            # on) - never the unused technical/raw_unused stub.
            raw = paths.raw_dir
            try:
                raw_under_library = raw != paths.merged_dir and (
                    raw == paths.library_root or paths.library_root in raw.parents
                    or raw.parent == paths.library_root
                )
            except Exception:
                raw_under_library = False
            if raw_under_library and raw.is_dir() and any(raw.iterdir()):
                lines.extend([
                    '',
                    'Also saved without filters (plain originals):',
                    str(raw),
                ])
            lines.extend([
                '',
                'Tip: use "Open finished folder" to open that location in File Explorer.',
            ])
            QMessageBox.information(self, 'Where are my files?', '\n'.join(lines))
        except Exception as e:
            try:
                QMessageBox.warning(
                    self, 'Where are my files?', f'Could not resolve the folder path:\n{e}'
                )
            except Exception:
                pass

    def open_debug_folder(self):
        """Open the debug folder for the current account"""
        try:
            account_name = self._after_processing_account_name()
            if not account_name:
                QMessageBox.information(self, 'Debug Folder', 'Enter an account name first.')
                return
            paths = self._account_paths(account_name)
            debug_dir = paths.debug_dir
            if not debug_dir.exists():
                debug_dir.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(debug_dir)))
        except Exception as e:
            try:
                QMessageBox.warning(self, 'Debug Folder Error', f'Could not open debug folder:\n{e}')
            except Exception:
                pass

    def _populate_support_menu(self, button: QPushButton) -> None:
        """Attach a menu with free and optional tip links."""
        from smd.support_links import support_options

        menu = QMenu(self)
        donate_opts = [o for o in support_options() if o.category == "donate"]
        free_opts = [o for o in support_options() if o.category == "free"]

        if donate_opts:
            for opt in donate_opts:
                action = menu.addAction(opt.label.replace("&", "&&"))
                action.setToolTip(opt.description)
                action.triggered.connect(
                    lambda _checked=False, url=opt.url: QDesktopServices.openUrl(QUrl(url))
                )
            if free_opts:
                menu.addSeparator()

        for opt in free_opts:
            action = menu.addAction(opt.label.replace("&", "&&"))
            action.setToolTip(opt.description)
            action.triggered.connect(
                lambda _checked=False, url=opt.url: QDesktopServices.openUrl(QUrl(url))
            )

        button.setMenu(menu)

    @staticmethod
    def _phase_from_log_message(message: str) -> str | None:
        low = message.lower()
        if "checking for duplicate" in low:
            return "Checking duplicates"
        if "duplicate check done" in low:
            return "Finishing up"
        if "extracting" in low and ".zip" in low:
            return "Extracting ZIPs"
        if "reusing" in low and "staged" in low:
            return "Loading staging"
        if "matched" in low and "json" in low:
            return "Matching to dates & GPS"
        if "parallel:" in low or "video encoding:" in low:
            return "Preparing workers"
        if "processing complete" in low:
            return "Complete"
        if "merging" in low or re.search(r"processing \d+/\d+", low):
            return "Merging & saving"
        if "loaded" in low and "json" in low:
            return "Reading export data"
        return None

    @staticmethod
    def _format_elapsed_short(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)} sec"
        if seconds < 3600:
            return f"{int(seconds // 60)} min {int(seconds % 60)} sec"
        return f"{int(seconds // 3600)} hr {int((seconds % 3600) // 60)} min"

    def _show_run_dashboard(self, *, reset: bool = False) -> None:
        if not hasattr(self, "live_run_dashboard"):
            return
        self.debug_output_toggle.setChecked(True)
        self.live_run_dashboard.setVisible(True)
        if reset:
            self.live_run_dashboard.reset(planned_estimate=self._last_estimate_label)
            for line in self._run_log_buffer:
                self.live_run_dashboard.log.appendPlainText(line)

    def _refresh_run_dashboard(
        self,
        *,
        pct: int | None = None,
        files_current: int | None = None,
        files_total: int | None = None,
        speed: str | None = None,
        eta: str | None = None,
        phase: str | None = None,
        status: str | None = None,
        status_kind: str = "info",
    ) -> None:
        if not hasattr(self, "live_run_dashboard"):
            return
        elapsed_str = None
        if getattr(self, "dl_start_time", None):
            import time as _t

            elapsed_str = self._format_elapsed_short(_t.time() - self.dl_start_time)
        self.live_run_dashboard.update_stats(
            pct=pct,
            files_current=files_current,
            files_total=files_total,
            speed=speed,
            eta=eta,
            elapsed=elapsed_str,
            phase=phase or self._run_phase,
            status=status,
            status_kind=status_kind,
        )

    def _apply_dashboard_visibility(self, visible: bool) -> None:
        """Show or fully collapse the live dashboard without stretching the Progress box."""
        if not hasattr(self, 'live_run_dashboard'):
            return
        dash = self.live_run_dashboard
        if visible:
            dash.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            dash.setMinimumHeight(0)
            dash.setMaximumHeight(16777215)
            dash.log.setMinimumHeight(320)
            dash.setVisible(True)
        else:
            dash.setVisible(False)
            dash.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            dash.log.setMinimumHeight(0)
            dash.setMinimumHeight(0)
            dash.setMaximumHeight(0)
        dash.updateGeometry()
        if hasattr(self, 'progress_section'):
            self.progress_section.adjustSize()
            self.progress_section.updateGeometry()

    def toggle_debug_output(self):
        """Toggle visibility of the live run dashboard."""
        visible = self.debug_output_toggle.isChecked()
        self._apply_dashboard_visibility(visible)
        if visible and not self.live_run_dashboard.log.toPlainText():
            self.live_run_dashboard.log.appendPlainText(
                f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Live run panel opened."
            )
            for line in self._run_log_buffer:
                self.live_run_dashboard.log.appendPlainText(line)

    def append_debug_message(self, message: str):
        """Append a message to the live dashboard log and update step hints.

        Kept in full (no in-memory cap) and also mirrored to a per-run log
        file on disk, so a run that lasts hours can still be scrolled back
        to the very start, and remains reviewable even after SMK closes."""
        if not hasattr(self, "live_run_dashboard"):
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        self._run_log_buffer.append(line)
        self._write_run_log_line(line)

        phase = self._phase_from_log_message(message)
        if phase:
            self._run_phase = phase

        if self.debug_output_toggle.isChecked():
            self.live_run_dashboard.log.appendPlainText(line)
            sb = self.live_run_dashboard.log.verticalScrollBar()
            sb.setValue(sb.maximum())

        short = message.strip()
        if short and not short.startswith("⏳"):
            self._refresh_run_dashboard(status=short[:240], phase=phase, status_kind="info")

    def _write_run_log_line(self, line: str) -> None:
        """Append one line to this run's on-disk activity log, if open."""
        path = getattr(self, '_run_log_path', None)
        if not path:
            return
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except OSError:
            self._run_log_path = None

    def remember_account_name(self, name):
        """Store account name in settings."""
        try:
            name = name.strip()
            if not name:
                return

            settings = QSettings('SnapchatMemories', 'Downloader')
            recent = settings.value('recent_accounts', [])
            if not isinstance(recent, list):
                recent = []
            if name in recent:
                recent.remove(name)
            recent.append(name)
            if len(recent) > 10:
                recent = recent[-10:]
            settings.setValue('recent_accounts', recent)
        except Exception:
            pass

        self.update_download_path_label(name)

    def start_download(self):
        # Validate inputs
        if not self.selected_zip:
            QMessageBox.warning(self, 'Error', 'Please select a Snapchat export ZIP or folder')
            return
        # New account with a typed name: create/select that folder now so we
        # never fall back to a previous Existing account (Las vs Mary bug).
        pending_new = self._pending_new_account_name()
        if pending_new:
            if not self._set_active_account(pending_new, create=True):
                return
            self.new_account_name_edit.clear()
        account_name = self._account_name()
        if not account_name:
            QMessageBox.warning(
                self,
                'Error',
                'No account selected.\n\n'
                'Use the Account section above: pick "New account" and type a '
                'name (Start processing creates the folder), or Existing account.',
            )
            return
        if not self._is_valid_account_name(account_name):
            QMessageBox.warning(
                self,
                'Error',
                'That account name is not valid for Windows '
                '(cannot contain \\ / : * ? " < > |). Re-select your export and pick a different name.',
            )
            return

        # Remember account name for future sessions
        self.remember_account_name(account_name)
        self.update_download_path_label(account_name)

        analysis = getattr(self, 'export_analysis', None)
        if analysis and analysis.zip_paths:
            # Remembers which export (by mydata~ID - a technical batch id, not
            # personal account data) populated this folder, so re-selecting
            # the same export later can default to "Continue" for it.
            try:
                from smd.account_layout import save_account_identity
                from smd.export_detect import export_base_ids

                paths = self._account_paths(account_name, create=True)
                save_account_identity(
                    paths.account_dir,
                    account_name=account_name,
                    mydata_ids=sorted(export_base_ids(analysis.zip_paths)),
                )
            except Exception:
                pass

        try:
            from smd.export_detect import analyze_zip_export, extract_json_from_zips, ExportFormat

            seed_path = Path(self.selected_zip)
            if not seed_path.exists():
                QMessageBox.warning(self, 'Error', 'Selected path does not exist')
                return
            if seed_path.is_file() and seed_path.suffix.lower() != '.zip':
                QMessageBox.warning(self, 'Error', 'Selected file must be a .zip (or choose a folder)')
                return

            analysis = getattr(self, 'export_analysis', None) or analyze_zip_export(seed_path)
            self.export_analysis = analysis

            is_bundled = analysis.format == ExportFormat.BUNDLED_LOCAL
            if not is_bundled:
                QMessageBox.warning(
                    self,
                    'Export not supported',
                    'This export does not include media files inside the ZIP.\n\n'
                    'Request a new Snapchat data export from Snapchat with memories included.',
                )
                return

            paths = self._account_paths(account_name, create=True)

            zip_bytes = int(getattr(analysis, "zip_bytes", 0) or 0)
            if zip_bytes <= 0 and analysis.zip_paths:
                try:
                    zip_bytes = sum(p.stat().st_size for p in analysis.zip_paths)
                except OSError:
                    zip_bytes = 0
            # Soft warn only (never hard-block). Snapchat ZIPs are barely
            # compressed (Las ~49 GB ZIPs ≈ 50.6 GB cloud; Mary ~6 GB ≈ library).
            # Finished filters-only ≈ ~1× ZIP; with “Also save without filters”
            # ≈ ~2× ZIP (Mary ~12 GB, Las ~97 GB). Staging (~1× ZIP) is temporary
            # and deleted after a clean finish — peak can briefly exceed the
            # finished size. +5 GB keeps Windows comfortable.
            _OS_HEADROOM = 5 * 1024 * 1024 * 1024
            _MIN_DISK_WARN_BYTES = 512 * 1024 * 1024
            keep_raw = bool(self.save_raw_chk.isChecked())
            copies = 2 if keep_raw else 1
            suggested = int(zip_bytes) * copies + _OS_HEADROOM
            if zip_bytes >= _MIN_DISK_WARN_BYTES:
                from smd.media_types import format_bytes

                def _free(path: Path) -> int | None:
                    try:
                        return shutil.disk_usage(str(path)).free
                    except OSError:
                        return None

                free = _free(paths.library_root)
                if free is None:
                    free = _free(paths.technical_dir)
                if free is not None and free < suggested:
                    box = QMessageBox(self)
                    box.setIcon(QMessageBox.Warning)
                    box.setWindowTitle('Low disk space')
                    box.setText(
                        'Free space on the output drive looks tight for this export.\n\n'
                        'SMK unpacks to a temporary staging folder (about the ZIP size), '
                        'then builds your finished library. Staging is removed after a '
                        'successful run. Windows also needs a few GB free to stay smooth.'
                    )
                    if keep_raw:
                        rule = (
                            f'about 2× ZIP + ~5 GB '
                            f'(filters copy + “without filters” copy + PC headroom)'
                        )
                        extra = (
                            '\n\n“Also save without filters” is on — that keeps a second '
                            'plain copy, so the finished folder is roughly twice the ZIP size.'
                        )
                    else:
                        rule = 'about ZIP size + ~5 GB (finished library + PC headroom)'
                        extra = (
                            '\n\nFilters-only libraries usually end up near the ZIP size. '
                            'Turn on “Also save without filters” only if you want a second copy.'
                        )
                    box.setInformativeText(
                        f'Export ZIPs: {format_bytes(zip_bytes)}\n'
                        f'Warn if under about: {format_bytes(suggested)} ({rule})\n'
                        f'Free on output drive: {format_bytes(free)}'
                        f'{extra}\n\n'
                        'You can continue anyway if staging is already on disk or you '
                        'will free space soon.'
                    )
                    continue_btn = box.addButton('Continue anyway', QMessageBox.AcceptRole)
                    box.addButton('Cancel', QMessageBox.RejectRole)
                    box.setDefaultButton(continue_btn)
                    box.exec_()
                    if box.clickedButton() is not continue_btn:
                        return

            dest_json = paths.json_path

            if analysis.zip_paths:
                extract_json_from_zips(analysis.zip_paths, dest_json)
            elif seed_path.is_dir():
                candidate = seed_path / 'json' / 'memories_history.json'
                if candidate.exists():
                    shutil.copy2(candidate, dest_json)
                else:
                    QMessageBox.critical(self, 'Error', 'memories_history.json not found in export.')
                    return
            else:
                temp_dir = ROOT / '.temp_import_gui'
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                temp_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(str(seed_path), 'r') as z:
                    mem_member = next((n for n in z.namelist() if n.lower().endswith('memories_history.json')), None)
                    if not mem_member:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        QMessageBox.critical(self, 'Error', 'memories_history.json is missing from export.')
                        return
                    z.extract(mem_member, str(temp_dir))
                    mem_json = (temp_dir / mem_member).resolve()
                shutil.copy2(mem_json, dest_json)
                shutil.rmtree(temp_dir, ignore_errors=True)

            self.tabs.setCurrentIndex(self._tab_process)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.download_log_lines = []
            self._run_log_buffer = []
            self._run_phase = "Starting"
            self.dl_start_time = None
            self.dl_total_files = 0
            try:
                paths.logs_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                self._run_log_path = paths.logs_dir / f'run_activity_{ts}.log'
            except OSError:
                self._run_log_path = None
            self._show_run_dashboard(reset=True)
            self.append_debug_message(
                f"Performance mode: {self.perf_mode_combo.currentText()}"
            )
            self.download_cancelled = False
            self.download_running = True
            self._refresh_after_processing_actions()
            self.download_btn.setText('Cancel')
            self.download_btn.setToolTip('Stop the current operation.')
            self._set_run_lockout(True)
            self._set_keep_awake(True)

            merge_overlays = True
            keep_raw = self.save_raw_chk.isChecked()

            self._apply_status(self.status_label, 'Bundled export detected. Processing locally (offline).', 'info')
            outputs = ['with filters']
            if keep_raw:
                outputs.append('originals without filters')
            self.mode_status_label.setText(
                f'Mode: Bundled local • outputs: {", ".join(outputs)} • metadata and GPS'
            )
            self._set_run_stage(1, 6, 'Preparing export and metadata')
            QApplication.processEvents()

            self.local_export_worker = LocalExportWorker(
                seed_path=seed_path,
                account_dir=paths.account_dir,
                json_path=dest_json,
                merge_overlays=merge_overlays,
                keep_raw=keep_raw,
                repair_videos=True,
                performance_mode=self.performance_mode,
                zip_paths=analysis.zip_paths,
                paths=paths,
                auto_delete_duplicates=self._auto_delete_duplicates_enabled(),
            )
            self.local_export_worker.limit = 0
            self.local_export_worker.output.connect(self.on_download_output)
            self.local_export_worker.progress.connect(self.on_local_progress)
            self.local_export_worker.stage.connect(self.on_local_stage)
            self.local_export_worker.finished.connect(self.on_download_finished)
            self.local_export_worker.start()
        except Exception as e:
            self.download_running = False
            self.download_btn.setText('Start processing')
            self._refresh_after_processing_actions()
            self._set_run_lockout(False)
            self._set_keep_awake(False)
            QMessageBox.critical(self, 'Error', str(e))

    # Short titles + one-line blurbs for the always-visible Progress stages.
    _RUN_STAGE_BLURBS = {
        1: 'Reading your My Data export and memory list',
        2: 'Unpacking photos and videos from the ZIP parts',
        3: 'Linking each file to its date, GPS, and metadata',
        4: 'Writing finished files with filters, dates, and GPS',
        5: 'Looking for duplicate copies of the same photo or video',
        6: 'Verifying files and preparing your summary',
    }

    def _set_run_stage(self, stage_num: int, stage_total: int, title: str) -> None:
        """Update always-visible stage chrome and reset the progress bar."""
        try:
            stage_num = max(1, int(stage_num))
            stage_total = max(stage_num, int(stage_total))
        except (TypeError, ValueError):
            return
        self._run_stage_num = stage_num
        self._run_stage_total = stage_total
        title = (title or '').strip() or f'Stage {stage_num}'
        blurb = self._RUN_STAGE_BLURBS.get(stage_num, '')
        self.stage_title_label.setText(
            f'<b>Stage {stage_num} of {stage_total}</b> — {html.escape(title)}'
            + (f'<br><span style="font-weight:normal">{html.escape(blurb)}</span>' if blurb else '')
        )
        parts = []
        short_names = {
            1: 'Prepare',
            2: 'Extract',
            3: 'Match',
            4: 'Save',
            5: 'Duplicates',
            6: 'Finish',
        }
        for n in range(1, stage_total + 1):
            short = short_names.get(n, str(n))
            if n < stage_num:
                parts.append(f'✓ {short}')
            elif n == stage_num:
                parts.append(f'<b>→ {short}</b>')
            else:
                parts.append(f'· {short}')
        self.stage_overview_label.setText('&nbsp;&nbsp;'.join(parts))
        if hasattr(self, 'step_status_label'):
            self.step_status_label.setText(f'Stage {stage_num} of {stage_total}: {title}')
        # Each stage owns the bar: always determinate 0% → 100%.
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('%p%')
        self.dl_start_time = None
        self._run_phase = title
        self._refresh_run_dashboard(pct=0, phase=title, status=title)

    def on_local_stage(self, stage_num: int, stage_total: int, title: str) -> None:
        self._set_run_stage(stage_num, stage_total, title)

    def on_local_progress(self, current, total):
        import time as _t

        try:
            total = int(total)
            current = int(current)
        except (TypeError, ValueError):
            return
        if total <= 0:
            return
        current = max(0, min(current, total))
        self.progress_bar.setRange(0, 100)
        pct = int(current / total * 100)
        if current >= total:
            pct = 100
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat('%p%')
        stage_n = getattr(self, '_run_stage_num', 0) or 4
        if stage_n == 4:
            status_txt = f'Saving… {current:,} of {total:,} ({pct}%)'
        elif stage_n == 5:
            status_txt = f'Checking duplicates… {current:,} of {total:,} ({pct}%)'
        elif stage_n == 2:
            status_txt = f'Extracting ZIP {current:,} of {total:,} ({pct}%)'
        elif stage_n == 6:
            status_txt = f'Finishing last touches… {pct}%'
        else:
            status_txt = f'{current:,} of {total:,} ({pct}%)'
        self._apply_status(self.status_label, status_txt, 'info')
        if self.dl_start_time is None and current > 0 and stage_n == 4:
            self.dl_start_time = _t.time()
            self.dl_total_files = total
        eta_str = '-'
        speed_str = '-'
        if self.dl_start_time and current > 0 and stage_n == 4:
            elapsed = _t.time() - self.dl_start_time
            rate = current / elapsed
            speed_str = f'{rate:.1f} files/s'
            remaining = max(total - current, 0)
            eta_sec = remaining / rate if rate > 0 else 0
            if eta_sec > 3600:
                eta_str = f'{int(eta_sec // 3600)} hr {int((eta_sec % 3600) // 60)} min'
            elif eta_sec > 60:
                eta_str = f'{int(eta_sec // 60)} min {int(eta_sec % 60)} sec'
            else:
                eta_str = f'{int(eta_sec)} sec'
        self.download_details.setText(
            f'Files: {current:,}/{total:,} | Speed: {speed_str} | ETA: {eta_str}'
        )
        self.mode_status_label.setText(
            f'Mode: Bundled local | Progress: {current:,}/{total:,} ({pct}%) | ETA: {eta_str}'
        )
        self._refresh_run_dashboard(
            pct=pct,
            files_current=current,
            files_total=total,
            speed=speed_str,
            eta=eta_str,
            phase=getattr(self, '_run_phase', 'Working') or 'Working',
            status=status_txt,
        )

    def on_download_output(self, line):
        """Append worker log lines to the live dashboard."""
        try:
            self.download_log_lines.append(line)
            if len(self.download_log_lines) > 50:
                self.download_log_lines.pop(0)
            self.append_debug_message(line)
        except Exception:
            pass

    def on_download_finished(self, return_code):
        """Handle download/completion"""
        self.download_running = False
        self.update_export_ui_mode()
        self._refresh_after_processing_actions()
        self._set_run_lockout(False)
        self.download_btn.setText('Start processing')
        self.download_btn.setToolTip("Runs extract, merge, metadata, and reports in one flow")
        bundled = getattr(self, 'export_analysis', None) and getattr(self.export_analysis, 'is_bundled', False)
        if return_code == 0:
            # Files are saved, but verify/summary can still take a while -
            # never tell the user "done" until that tidying finishes.
            self._set_run_stage(6, 6, 'Finishing last touches')
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat('%p%')
            msg = (
                'Tidying up — verifying your files and preparing the summary. '
                'Your memories are already saved; this last step can take a bit.'
            )
            self._apply_status(self.status_label, msg, 'info')
            self._refresh_run_dashboard(
                pct=0,
                phase='Finishing last touches',
                status=msg,
                status_kind='info',
            )
            self._show_completion_summary()
        else:
            # Success continues into verification/finalize below, which still
            # needs the display kept awake - only release it here on the
            # cancelled/failed path, where no further background work runs.
            self._set_keep_awake(False)
            if getattr(self, 'download_cancelled', False):
                self._apply_status(self.status_label, '⏹ Stopped. Click Start to resume with the same account name.', "warn")
            else:
                tail = '\n'.join(self.download_log_lines[-12:]) if self.download_log_lines else 'No output was captured.'
                tail_low = tail.lower()
                title = 'Processing Failed'

                if 'no space left' in tail_low or 'errno 28' in tail_low:
                    title = 'Out of disk space'
                    error_msg = (
                        'Your disk ran out of space while processing.\n\n'
                        'Free up space on the output drive - merged/, raw/, and '
                        'technical/staging/ can be very large for big exports - then click '
                        'Start again with the same project name. SMK resumes where it left '
                        'off and only processes the files that remain.'
                    )
                elif 'permission' in tail_low:
                    error_msg = 'The app does not have permission to access that folder.\n\nCheck Windows security settings and try again.'
                elif 'no module named' in tail_low or 'cannot import name' in tail_low:
                    error_msg = (
                        'Processing is not available in this copy of SMK.\n\n'
                        'Please install the latest version of Snapchat Memories Keeper.'
                    )
                else:
                    error_msg = (
                        'Processing failed.\n\n'
                        'Details from log:\n' + tail + '\n\n'
                        'Tips: free disk space on the output drive, close other heavy apps, '
                        'and try again with the same project name.'
                    )

                self._apply_status(self.status_label, 'Processing failed - see details in the log.', "err")
                try:
                    QMessageBox.critical(self, title, error_msg)
                except Exception:
                    pass

    def cancel_download(self):
        """Cancel the running processing job."""
        try:
            if hasattr(self, 'local_export_worker') and self.local_export_worker.isRunning():
                self.download_cancelled = True
                self.local_export_worker.cancel()
                self._apply_status(self.status_label, 'Cancelling processing...', "warn")
        except Exception:
            pass

    def _stop_worker(self, attr: str, timeout_ms: int = 3000) -> None:
        """Stop and detach a previous QThread worker before starting a replacement.

        Prevents stale threads from emitting into shared slots (double map
        renders, crossed progress updates) and shutdown crashes.
        """
        worker = getattr(self, attr, None)
        if worker is None:
            return
        try:
            if worker.isRunning():
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                elif hasattr(worker, 'cancelled'):
                    worker.cancelled = True
                worker.wait(timeout_ms)
            try:
                worker.disconnect()
            except TypeError:
                pass
        except RuntimeError:
            pass  # C++ object already deleted

    def on_download_button_clicked(self):
        """Unified Start/Cancel behavior on single button."""
        if not self.download_running:
            self.start_download()
        else:
            self.cancel_download()
