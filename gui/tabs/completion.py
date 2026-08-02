"""Post-run completion summary and duplicate-review mixin."""
from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QMessageBox

from gui.dialogs import DuplicateReviewDialog, SessionSummaryDialog
from gui.workers import (
    CompletionFinalizeWorker,
    DuplicateScanWorker,
    StagingVerifyWorker,
    VisualDuplicateScanWorker,
)


class CompletionMixin:
    """Mixin: completion summary, staging verify finalize, duplicate review."""

    def _maybe_copy_run_info(self, paths) -> None:
        """If Technical view + Add run info is on, snapshot logistics next to media."""
        if not hasattr(self, '_add_run_info_enabled') or not self._add_run_info_enabled():
            return
        try:
            from smd.account_layout import copy_run_info_into_library

            dest, copied = copy_run_info_into_library(paths)
            print(f"DEBUG: Copied run info → {dest} ({', '.join(copied)})")
        except Exception as exc:
            self._log_completion_error("copy run info into finished folder", exc, paths)

    def _show_completion_summary(self) -> None:
        """Kick off the post-run summary. The staging integrity check that
        this depends on ffprobes every video, which can take minutes on a
        large library - it now runs on a background thread (see
        StagingVerifyWorker) so the window stays responsive instead of
        looking frozen right after processing finishes."""
        account_name = self._account_name()
        try:
            paths = self._account_paths(account_name)
        except Exception as exc:
            self._log_completion_error("resolve account paths", exc, None)
            if hasattr(self, 'processing_shield'):
                self.processing_shield.hide()
            self._set_keep_awake(False)
            self._show_minimal_completion_message(account_name, None)
            return

        self._completion_account_name = account_name
        self._completion_paths = paths
        self._completion_stats = getattr(
            getattr(self, 'local_export_worker', None), 'run_stats', None
        )
        self._completion_keep_raw = self.save_raw_chk.isChecked()

        # Failsafe overlay until the summary dialog appears — avoids a silent
        # stall if verify/finalize is slow to emit progress. Progress bar still
        # updates underneath for anyone watching stage chrome.
        if hasattr(self, '_set_run_stage'):
            self._set_run_stage(6, 6, 'Finishing last touches')
        if hasattr(self, '_apply_status') and hasattr(self, 'status_label'):
            self._apply_status(
                self.status_label,
                'Double-checking saved files… almost done.',
                'info',
            )
        if hasattr(self, '_refresh_run_dashboard'):
            self._refresh_run_dashboard(
                pct=0,
                phase='Finishing last touches',
                status='Double-checking every saved file before the summary.',
                status_kind='info',
            )
        if hasattr(self, 'processing_shield'):
            self.processing_shield.set_hint(
                'Double-checking every saved file.\n'
                'Large libraries can take a few minutes.\n'
                'Your files are already saved — summary opens when this finishes.',
                title='Almost done…',
            )
            self.processing_shield.show_over()

        self._staging_verify_worker = StagingVerifyWorker(
            paths.account_dir, paths, self._completion_keep_raw
        )
        self._staging_verify_worker.finished_ok.connect(self._on_staging_verified)
        self._staging_verify_worker.error.connect(self._on_staging_verify_error)
        if hasattr(self, 'on_local_progress'):
            self._staging_verify_worker.progress.connect(self.on_local_progress)
        self._staging_verify_worker.start()

    def _on_staging_verify_error(self, message: str) -> None:
        self._log_completion_error(
            "verify staging", RuntimeError(message), self._completion_paths
        )
        self._finish_completion_summary(None)

    def _on_staging_verified(self, readiness) -> None:
        self._finish_completion_summary(readiness)

    def _finish_completion_summary(self, readiness) -> None:
        """Kick off background finalize (staging delete when safe + session report)."""
        paths = self._completion_paths
        stats = self._completion_stats
        keep_raw = self._completion_keep_raw

        if hasattr(self, '_apply_status') and hasattr(self, 'status_label'):
            self._apply_status(
                self.status_label,
                'Preparing your summary… (almost done)',
                'info',
            )
        if hasattr(self, '_refresh_run_dashboard'):
            self._refresh_run_dashboard(
                pct=90,
                phase='Finishing last touches',
                status='Preparing your summary — your files are already saved.',
                status_kind='info',
            )
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(90)
        if hasattr(self, 'processing_shield'):
            self.processing_shield.set_hint(
                'Preparing your summary.\n'
                'Your files are already saved.\n'
                'The results window opens next.',
                title='Almost done…',
            )
            self.processing_shield.show_over()

        self._stop_worker('completion_finalize_worker')
        self.completion_finalize_worker = CompletionFinalizeWorker(
            paths, stats, keep_raw, readiness
        )
        self.completion_finalize_worker.finished_ok.connect(self._on_completion_finalize_finished)
        self.completion_finalize_worker.error.connect(self._on_completion_finalize_error)
        if hasattr(self, 'on_local_progress'):
            self.completion_finalize_worker.progress.connect(self.on_local_progress)
        self.completion_finalize_worker.start()

    def _on_completion_finalize_finished(self, report) -> None:
        account_name = self._completion_account_name
        paths = self._completion_paths
        if hasattr(self, 'processing_shield'):
            self.processing_shield.hide()
        self._set_keep_awake(False)
        # Only now is the full run actually finished (verify + summary ready).
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(100)
            if hasattr(self, '_apply_status') and hasattr(self, 'status_label'):
                self._apply_status(
                    self.status_label,
                    'All done — your memories are ready.',
                    'ok',
                )
            if hasattr(self, 'stage_title_label'):
                self.stage_title_label.setText(
                    '<b>All stages complete</b> — your memories are ready.'
                )
            if hasattr(self, 'stage_overview_label'):
                self.stage_overview_label.setText(
                    '✓ Prepare&nbsp;&nbsp;✓ Extract&nbsp;&nbsp;✓ Match&nbsp;&nbsp;'
                    '✓ Save&nbsp;&nbsp;✓ Duplicates&nbsp;&nbsp;✓ Finish'
                )
            if hasattr(self, '_refresh_run_dashboard'):
                self._refresh_run_dashboard(
                    pct=100,
                    phase='Complete',
                    status='All done — your memories are ready.',
                    status_kind='ok',
                )
            from gui.common import play_happy_tone

            play_happy_tone()
        except Exception:
            pass
        self._maybe_copy_run_info(paths)
        try:
            dlg = SessionSummaryDialog(report, paths.library_root, paths.reports_dir, self)
            dlg.exec_()
        except Exception as exc:
            self._log_completion_error("show session summary", exc, paths)
            self._show_minimal_completion_message(account_name, paths)
        QTimer.singleShot(
            0,
            lambda an=account_name, p=paths, r=report: self._after_processing_summary(an, p, r),
        )

    def _on_completion_finalize_error(self, message: str) -> None:
        account_name = self._completion_account_name
        paths = self._completion_paths
        self._log_completion_error("build session summary", RuntimeError(message), paths)
        if hasattr(self, 'processing_shield'):
            self.processing_shield.hide()
        self._set_keep_awake(False)
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(100)
            if hasattr(self, '_apply_status') and hasattr(self, 'status_label'):
                self._apply_status(
                    self.status_label,
                    'Processing finished — summary had a problem; your files should still be saved.',
                    'warn',
                )
            if hasattr(self, 'stage_title_label'):
                self.stage_title_label.setText(
                    '<b>All stages complete</b> — summary could not be shown fully.'
                )
        except Exception:
            pass
        self._maybe_copy_run_info(paths)
        self._show_minimal_completion_message(account_name, paths)
        QTimer.singleShot(
            0,
            lambda an=account_name, p=paths, r=None: self._after_processing_summary(an, p, r),
        )

    def _show_minimal_completion_message(self, account_name: str, paths) -> None:
        """Fallback when the rich summary dialog cannot be built."""
        where = ''
        try:
            if paths is not None:
                where = f'\n\nYour memories are saved in:\n{paths.library_root}'
        except Exception:
            pass
        try:
            QMessageBox.information(
                self,
                'Processing complete',
                'Your Snapchat memories were processed successfully.' + where +
                '\n\nUse "Open finished folder" to view them. '
                '(Technical view → Review duplicates if you want to re-scan for extras.)',
            )
        except Exception:
            pass

    def _log_completion_error(self, stage: str, exc: Exception, paths) -> None:
        """Record a completion-stage error to disk and the run log."""
        import traceback
        tb = traceback.format_exc()
        print(f"Completion error ({stage}): {exc}\n{tb}")
        try:
            if paths is not None:
                paths.logs_dir.mkdir(parents=True, exist_ok=True)
                (paths.logs_dir / 'summary_error.log').write_text(
                    f"Stage: {stage}\n{tb}\n", encoding='utf-8'
                )
        except Exception:
            pass

    def _after_processing_summary(self, account_name: str, paths, report) -> None:
        """Refresh the main window after the session summary dialog closes."""
        try:
            self.show()
            self.raise_()
            self.activateWindow()
            if account_name:
                self.update_download_path_label(account_name)
        except Exception as exc:
            print(f"Post-summary refresh error: {exc}")
        if report and report.duplicate_groups > 0:
            self._open_duplicate_review_if_needed(account_name, paths, report.duplicate_groups)
        # exec_() above is modal, so this only runs once that dialog (if any) is closed.
        if report and getattr(report, 'visual_duplicate_groups', 0) > 0:
            self._open_visual_duplicate_review_if_needed(
                account_name, paths, report.visual_duplicate_groups
            )

    def _show_duplicate_review_dialog(self, account_name: str, paths, report) -> None:
        dlg = DuplicateReviewDialog(self, paths, account_name, report, dark=self.dark_mode_enabled)
        dlg.setModal(True)
        dlg.setAttribute(Qt.WA_QuitOnClose, False)
        dlg.exec_()

    def _open_duplicate_review_if_needed(self, account_name: str, paths, duplicate_groups: int) -> None:
        """Open duplicate review after a successful run when duplicates were found."""
        if duplicate_groups <= 0:
            return
        try:
            from smd.duplicates import load_cached_duplicate_report

            report = load_cached_duplicate_report(paths)
            if report and report.duplicate_groups:
                self._show_duplicate_review_dialog(account_name, paths, report)
                return

            self._duplicate_scan_account_name = account_name
            self._duplicate_scan_paths = paths
            self._duplicate_scan_auto_open = True
            self._stop_worker('duplicate_scan_worker')
            self.duplicate_scan_worker = DuplicateScanWorker(paths)
            self.duplicate_scan_worker.finished.connect(self.on_duplicate_scan_finished)
            self.duplicate_scan_worker.error.connect(self._on_post_run_duplicate_scan_error)
            self.duplicate_scan_worker.start()
        except Exception as exc:
            print(f"Duplicate review error: {exc}")
            QMessageBox.warning(
                self,
                'Review duplicates',
                'Could not open the leftovers check.\n\n'
                'Your finished photos and videos are already saved — this step is optional.',
            )

    def _on_post_run_duplicate_scan_error(self, message: str) -> None:
        self._duplicate_scan_auto_open = False
        print(f"Duplicate review error: {message}")

    def _open_visual_duplicate_review_if_needed(
        self, account_name: str, paths, visual_duplicate_groups: int
    ) -> None:
        """Open the deep-scan (same-content, different-bytes) review after a
        successful run when scan_visual_duplicates() found groups. Since that
        scan now runs as a normal part of every processing run (see
        DECISIONS.md 2026-07-19), the cache should already be on disk here -
        the worker fallback below only matters for older cached reports."""
        if visual_duplicate_groups <= 0:
            return
        try:
            from smd.duplicates import load_cached_visual_duplicate_report

            report = load_cached_visual_duplicate_report(paths)
            if report and report.duplicate_groups:
                self._show_duplicate_review_dialog(account_name, paths, report)
                return

            self._visual_scan_account_name = account_name
            self._visual_scan_paths = paths
            self._visual_scan_auto_open = True
            self._stop_worker('visual_scan_worker')
            self.visual_scan_worker = VisualDuplicateScanWorker(paths)
            self.visual_scan_worker.finished.connect(self.on_visual_scan_finished)
            self.visual_scan_worker.error.connect(self._on_post_run_visual_scan_error)
            self.visual_scan_worker.start()
        except Exception as exc:
            print(f"Deep scan review error: {exc}")
            QMessageBox.warning(
                self,
                'Deep scan',
                'Could not open the deep-scan duplicate review.\n\n'
                'Your finished photos and videos are already saved — this step is optional.',
            )

    def _on_post_run_visual_scan_error(self, message: str) -> None:
        self._visual_scan_auto_open = False
        print(f"Deep scan review error: {message}")

    def review_duplicates(self):
        if self.download_running:
            QMessageBox.information(
                self,
                'Review duplicates',
                'Wait until the current download/processing job finishes.',
            )
            return
        account_name = self._account_name()
        if not account_name:
            QMessageBox.information(self, 'Review duplicates', 'Choose an account first.')
            return
        paths = self._account_paths(account_name)

        # Processing already hashed merged/ once and saved the result to
        # technical/reports/duplicates_report.json. Trust that cache instead
        # of re-hashing everything on every click - it's kept in sync
        # whenever duplicates are deleted, and a full re-process (which
        # everyone runs after fixing a real bug) always regenerates it fresh.
        from smd.duplicates import load_cached_duplicate_report

        self._duplicate_scan_account_name = account_name
        self._duplicate_scan_paths = paths

        cached = load_cached_duplicate_report(paths)
        if cached is not None:
            self.on_duplicate_scan_finished(cached)
            return

        self.review_duplicates_btn.setEnabled(False)
        self._apply_status(self.status_label, 'Checking for duplicate files…', 'info')
        # No cache yet (first check on this account) - hashing every file in
        # merged/ can take a while on large libraries, so run it off the UI
        # thread rather than blocking the window.
        self._stop_worker('duplicate_scan_worker')
        self.duplicate_scan_worker = DuplicateScanWorker(paths)
        self.duplicate_scan_worker.progress.connect(self.on_duplicate_scan_progress)
        self.duplicate_scan_worker.finished.connect(self.on_duplicate_scan_finished)
        self.duplicate_scan_worker.error.connect(self.on_duplicate_scan_error)
        self.duplicate_scan_worker.start()

    def on_duplicate_scan_progress(self, message: str) -> None:
        self._apply_status(self.status_label, message, 'info')

    def _show_cached_visual_duplicates(self, account_name, paths) -> bool:
        """Surface any deep-scan (same content, different file bytes) results
        already cached from the automatic scan that runs at the end of every
        processing run - "Review duplicates" is now the one place both kinds
        of results show up (see DECISIONS.md, 2026-07-19). Returns True if a
        review dialog was shown."""
        if account_name is None or paths is None:
            return False
        try:
            from smd.duplicates import load_cached_visual_duplicate_report

            report = load_cached_visual_duplicate_report(paths)
        except Exception:
            return False
        if report and report.duplicate_groups:
            self._show_duplicate_review_dialog(account_name, paths, report)
            return True
        return False

    def on_duplicate_scan_finished(self, report) -> None:
        auto_open = getattr(self, '_duplicate_scan_auto_open', False)
        self._duplicate_scan_auto_open = False
        self._refresh_after_processing_actions()
        account_name = getattr(self, '_duplicate_scan_account_name', None)
        paths = getattr(self, '_duplicate_scan_paths', None)

        showed_byte = False
        if report.duplicate_groups and account_name and paths is not None:
            self._apply_status(self.status_label, 'Duplicates found - opening review.', 'info')
            self._show_duplicate_review_dialog(account_name, paths, report)
            showed_byte = True

        # exec_() above is modal, so this only runs once that dialog (if any) is closed.
        showed_visual = self._show_cached_visual_duplicates(account_name, paths)

        if not showed_byte and not showed_visual and not auto_open:
            self._apply_status(self.status_label, 'No leftover duplicates found.', 'ok')
            QMessageBox.information(
                self,
                'Review duplicates',
                f'Scanned {report.merged_scanned} files — nothing left to clean up '
                '(identical files or same picture/video).',
            )

    def on_duplicate_scan_error(self, message: str) -> None:
        self._refresh_after_processing_actions()
        self._apply_status(self.status_label, 'Duplicate check failed.', 'err')
        print(f"Duplicate review error: {message}")
        QMessageBox.warning(
            self,
            'Review duplicates',
            'Could not open the leftovers check.\n\n'
            'Your finished files are not affected — this step is optional.',
        )

    def on_visual_scan_progress(self, message: str) -> None:
        self._apply_status(self.status_label, message, 'info')

    def on_visual_scan_finished(self, report) -> None:
        auto_open = getattr(self, '_visual_scan_auto_open', False)
        self._visual_scan_auto_open = False
        self._refresh_after_processing_actions()
        account_name = getattr(self, '_visual_scan_account_name', None)
        paths = getattr(self, '_visual_scan_paths', None)
        if not report.duplicate_groups:
            if not auto_open:
                self._apply_status(self.status_label, 'No look-alike duplicates found.', 'ok')
                QMessageBox.information(
                    self,
                    'Deep scan',
                    f'Checked {report.merged_scanned} files - no look-alike duplicates found.',
                )
            return
        self._apply_status(
            self.status_label, 'Look-alike duplicates found - opening review.', 'info'
        )
        if account_name and paths is not None:
            self._show_duplicate_review_dialog(account_name, paths, report)

    def on_visual_scan_error(self, message: str) -> None:
        self._refresh_after_processing_actions()
        self._apply_status(self.status_label, 'Deep scan failed.', 'err')
        print(f"Deep scan error: {message}")
        QMessageBox.warning(
            self,
            'Deep scan',
            'Could not complete the deep scan.\n\n'
            'Your finished files are not affected — this step is optional.',
        )
