"""SMK must not treat random Desktop folders as accounts (USB2 bug)."""
from __future__ import annotations

import json
from pathlib import Path

from smd.account_layout import (
    ACCOUNT_IDENTITY_NAME,
    RUN_INFO_DIRNAME,
    TECHNICAL_DIRNAME,
    is_smk_account_dir,
    is_smk_account_name,
    rename_simple_mode_account,
    resolve_existing_account_layout,
    save_account_layout_info,
)


def test_usb_dump_folder_is_not_smk_owned(tmp_path: Path, monkeypatch):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    usb = desktop / "USB2"
    usb.mkdir()
    (usb / "DCIM").mkdir()
    (usb / "photo.jpg").write_bytes(b"not-smk")

    monkeypatch.setattr(
        "smd.account_layout.AccountPaths.user_desktop_dir",
        classmethod(lambda cls, name: desktop / name),
    )
    monkeypatch.setattr(
        "smd.account_layout.AccountPaths.internal_accounts_root",
        classmethod(lambda cls: tmp_path / "internal"),
    )

    assert not is_smk_account_dir(usb)
    assert not is_smk_account_name("USB2")
    assert rename_simple_mode_account("USB2", "USB2-memories") == []
    assert usb.is_dir()
    assert not (desktop / "USB2-memories").exists()


def test_owned_account_with_identity_is_recognized(tmp_path: Path, monkeypatch):
    desktop = tmp_path / "Desktop"
    internal = tmp_path / "internal"
    desktop.mkdir()
    account = desktop / "Las-memories"
    account.mkdir()
    tech = internal / "Las-memories" / TECHNICAL_DIRNAME
    tech.mkdir(parents=True)
    (tech / ACCOUNT_IDENTITY_NAME).write_text(
        json.dumps({"layout": "simple", "account_name": "Las-memories"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "smd.account_layout.AccountPaths.user_desktop_dir",
        classmethod(lambda cls, name: desktop / name),
    )
    monkeypatch.setattr(
        "smd.account_layout.AccountPaths.internal_accounts_root",
        classmethod(lambda cls: internal),
    )

    assert is_smk_account_name("Las-memories")
    assert is_smk_account_dir(internal / "Las-memories")


def test_run_info_on_library_counts_as_owned(tmp_path: Path):
    lib = tmp_path / "Mary-memories"
    run = lib / RUN_INFO_DIRNAME
    run.mkdir(parents=True)
    (run / "ABOUT.txt").write_text("SMK run info\n", encoding="utf-8")
    assert is_smk_account_dir(lib)


def test_resolve_existing_ignores_unrelated_desktop_folder(tmp_path: Path, monkeypatch):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    (desktop / "USB2").mkdir()
    (desktop / "USB2" / "file.txt").write_text("x", encoding="utf-8")

    monkeypatch.setattr(
        "smd.account_layout.AccountPaths.user_desktop_dir",
        classmethod(lambda cls, name: desktop / name),
    )
    monkeypatch.setattr(
        "smd.account_layout.AccountPaths.internal_accounts_root",
        classmethod(lambda cls: tmp_path / "internal"),
    )

    assert resolve_existing_account_layout("USB2", tmp_path / "base") is None


def test_rename_simple_moves_owned_desktop_when_internal_has_markers(
    tmp_path: Path, monkeypatch
):
    desktop = tmp_path / "Desktop"
    internal = tmp_path / "internal"
    desktop.mkdir()
    old_desk = desktop / "Las"
    old_desk.mkdir()
    (old_desk / "photo.jpg").write_bytes(b"media")
    old_int = internal / "Las"
    save_account_layout_info(old_int, layout="simple", keep_raw=False)

    monkeypatch.setattr(
        "smd.account_layout.AccountPaths.user_desktop_dir",
        classmethod(lambda cls, name: desktop / name),
    )
    monkeypatch.setattr(
        "smd.account_layout.AccountPaths.internal_accounts_root",
        classmethod(lambda cls: internal),
    )

    actions = rename_simple_mode_account("Las", "Las-memories")
    assert actions
    assert (desktop / "Las-memories").is_dir()
    assert not old_desk.exists()
    assert (internal / "Las-memories" / TECHNICAL_DIRNAME / ACCOUNT_IDENTITY_NAME).is_file()
