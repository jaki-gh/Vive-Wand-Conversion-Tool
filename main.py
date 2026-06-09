#!/usr/bin/env python3
"""
Vive Controller to Tracker Converter
==================================================
Converts or restores a Vive Wand controller config using SteamVR's internal tools.

Requirements:
  - Python 3.9+  (tkinter is included with most Python distributions)
  - lighthouse_console.exe (auto-detected or manually selected).
"""

import json
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, Tk


# ── Palette & fonts ───────────────────────────────────────────────────────────

BG       = "#000000"
SURFACE  = "#161920"
CARD     = "#1c2030"
BORDER   = "#2a2f42"
ACCENT   = "#4f8ef7"
ACCENT2  = "#7c5cfc"
SUCCESS  = "#3ecf8e"
WARNING  = "#f5a623"
DANGER   = "#f25c54"
FG       = "#e8ecf5"
FG_DIM   = "#7a84a0"

FONT_MONO  = ("Consolas", 10)
FONT_BODY  = ("Segoe UI", 10)
FONT_LABEL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI Semibold", 18)


# Steam / lighthouse_console auto-detection

# Relative path inside a SteamVR install
LH_REL = Path("steamapps/common/SteamVR/tools/lighthouse/bin/win64/lighthouse_console.exe")

# Common Steam root locations on Windows
STEAM_ROOTS = [
    Path("C:/Program Files (x86)/Steam"),
    Path("C:/Program Files/Steam"),
]

def find_lh_exe() -> Path | None:
    """Return the first lighthouse_console.exe found in Steam, or None."""
    # Next to this script first
    local = Path(__file__).resolve().parent / "lighthouse_console.exe"
    if local.exists():
        return local

    for root in STEAM_ROOTS:
        candidate = root / LH_REL
        if candidate.exists():
            return candidate

    return None


# Organised config folder

def config_dir(base: Path, serial: str) -> Path:
    """Return and create base/configs/<serial>/"""
    d = base / "configs" / serial
    d.mkdir(parents=True, exist_ok=True)
    return d


# Device-type detection

def is_hmd(config: dict) -> bool:
    """
    Return True only if device_class explicitly marks this as a headset.
    """
    return str(config.get("device_class", "")).lower() == "hmd"


# Config transform helpers

def patch_config(original: dict) -> dict:
    patched = dict(original)
    patched["device_class"]           = "generic_tracker"
    patched["model_number"]           = "Vive. Tracker PVT"
    patched["render_model"]           = "vr_tracker_vive_1_0"
    patched["tracked_controller_role"] = ""
    return patched


def restore_config(backup: dict) -> dict:
    restored = dict(backup)
    restored.pop("tracked_controller_role", None)
    restored["device_class"] = "controller"
    restored["model_number"] = "Vive Controller MV"
    restored["render_model"] = "vr_controller_vive_1_5"
    return restored


# lighthouse_console wrapper

def run_lh(lh_exe: Path, commands: list[str], timeout: int = 30) -> str:
    input_text = "\n".join(commands) + "\nexit\n"
    result = subprocess.run(
        [str(lh_exe)],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(lh_exe.parent),
    )
    return result.stdout + result.stderr


def detect_serial_from_lh(lh_exe: Path) -> str | None:
    try:
        output = run_lh(lh_exe, [], timeout=10)
    except Exception:
        return None
    m = re.search(r'\b(LHR-[0-9A-Fa-f]{8})\b', output)
    return m.group(1) if m else None


# Main GUI application

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vive Wand Conversion Tool  |  v1.0")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.lh_path = tk.StringVar()
        self.serial  = tk.StringVar()
        self.status  = tk.StringVar(value="Ready.")
        self._busy   = False

        self._set_icon()
        self._build_ui()
        self._try_autodetect_lh()

    def _set_icon(self):
        ico = Path(__file__).resolve().parent / "vwct.ico"
        if ico.exists():
            try:
                self.iconbitmap(str(ico))
            except Exception:
                pass

    # Layout
    def _build_ui(self):
        # Title
        header = tk.Frame(self, bg=BG, pady=18)
        header.pack(fill="x", padx=28)
        tk.Label(header, text="Vive Wand Conversion Tool", font=FONT_TITLE,
                 bg=BG, fg=ACCENT).pack(side="left")
        tk.Label(header, text="v1.0  |  XR Studios ©2026", font=FONT_LABEL,
                 bg=BG, fg=FG_DIM).pack(side="right", pady=(6, 0))

        self._divider()

        # lighthouse_console.exe
        self._section("LIGHTHOUSE CONSOLE EXECUTABLE")
        lh_row = tk.Frame(self, bg=BG)
        lh_row.pack(fill="x", padx=28, pady=(0, 12))
        self._entry(lh_row, self.lh_path, width=44).pack(side="left")
        self._button(lh_row, "Browse…",     self._browse_lh,
                     width=9).pack(side="left", padx=(8, 0))
        self._button(lh_row, "Auto-detect", self._auto_detect_lh,
                     width=11, accent=False).pack(side="left", padx=(8, 0))

        # Serial number
        self._section("DEVICE SERIAL NUMBER")
        ser_row = tk.Frame(self, bg=BG)
        ser_row.pack(fill="x", padx=28, pady=(0, 16))
        self._entry(ser_row, self.serial, width=22,
                    placeholder="e.g. LHR-FFB57F42").pack(side="left")
        self._button(ser_row, "Detect serial", self._auto_detect_serial,
                     width=14, accent=False).pack(side="left", padx=(8, 0))

        # Action buttons
        self._divider()
        btn_frame = tk.Frame(self, bg=BG, pady=14)
        btn_frame.pack(fill="x", padx=28)
        self._button(btn_frame, "⬇  Convert to Tracker",
                     self._do_convert, width=22, big=True).pack(side="left", padx=(0, 10))
        self._button(btn_frame, "↩  Restore Controller",
                     self._do_restore, width=22, big=True,
                     color=WARNING).pack(side="left")

        # Log
        self._divider()
        self._section("LOG")
        log_frame = tk.Frame(self, bg=CARD, bd=0,
                             highlightbackground=BORDER, highlightthickness=1)
        log_frame.pack(fill="x", padx=28, pady=(0, 10))
        self.log = scrolledtext.ScrolledText(
            log_frame, font=FONT_MONO, bg=CARD, fg=FG,
            insertbackground=FG, relief="flat", bd=0,
            height=12, width=70, state="disabled", wrap="word",
        )
        self.log.pack(padx=2, pady=2)
        self.log.tag_config("ok",      foreground=SUCCESS)
        self.log.tag_config("warn",    foreground=WARNING)
        self.log.tag_config("err",     foreground=DANGER)
        self.log.tag_config("info",    foreground=ACCENT)
        self.log.tag_config("dim",     foreground=FG_DIM)
        self.log.tag_config("section", foreground=ACCENT2)

        # Status bar
        status_bar = tk.Frame(self, bg=SURFACE, height=28)
        status_bar.pack(fill="x", side="bottom")
        tk.Label(status_bar, textvariable=self.status, font=FONT_LABEL,
                 bg=SURFACE, fg=FG_DIM, anchor="w", padx=14).pack(fill="x", pady=4)

    # Widget helpers
    def _divider(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=0, pady=4)

    def _section(self, text):
        tk.Label(self, text=text, font=("Segoe UI Semibold", 8),
                 bg=BG, fg=FG_DIM, anchor="w", padx=28).pack(fill="x", pady=(6, 2))

    def _entry(self, parent, var, width=30, placeholder=""):
        e = tk.Entry(parent, textvariable=var, font=FONT_BODY,
                     bg=CARD, fg=FG, insertbackground=FG,
                     relief="flat", bd=0, width=width,
                     highlightbackground=BORDER, highlightthickness=1,
                     highlightcolor=ACCENT)
        if placeholder and not var.get():
            e.insert(0, placeholder)
            e.config(fg=FG_DIM)
            def _fi(ev):
                if e.get() == placeholder:
                    e.delete(0, "end"); e.config(fg=FG)
            def _fo(ev):
                if not e.get():
                    e.insert(0, placeholder); e.config(fg=FG_DIM)
            e.bind("<FocusIn>",  _fi)
            e.bind("<FocusOut>", _fo)
        return e

    def _button(self, parent, text, cmd, width=10, big=False,
                accent=True, color=None):
        bg_col = color or (ACCENT if accent else BORDER)
        fg_col = BG if (accent or color) else FG
        font   = ("Segoe UI Semibold", 10) if big else FONT_BODY
        btn = tk.Button(parent, text=text, command=cmd, font=font,
                        bg=bg_col, fg=fg_col, activebackground=ACCENT2,
                        activeforeground=FG, relief="flat", bd=0,
                        cursor="hand2", width=width,
                        padx=14 if big else 8, pady=8 if big else 4)
        btn.bind("<Enter>", lambda _: btn.config(bg=ACCENT2 if accent else ACCENT))
        btn.bind("<Leave>", lambda _: btn.config(bg=bg_col))
        return btn

    # Logging
    def _log(self, msg: str, tag: str = ""):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _log_clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _log_section(self, title: str):
        self._log(f"\n── {title} {'─' * max(0, 40 - len(title))}", "section")

    def _set_status(self, msg: str):
        self.status.set(msg)

    # ── Input validation ──────────────────────────────────────────────────────
    def _get_lh(self) -> Path | None:
        p = self.lh_path.get().strip()
        if not p or not Path(p).exists():
            messagebox.showerror(
                "Not found",
                "lighthouse_console.exe not found.\n"
                "Use 'Browse…' or 'Auto-detect' to locate it."
            )
            return None
        return Path(p)

    def _get_serial(self) -> str | None:
        s = self.serial.get().strip().upper()
        if not s or s == "E.G. LHR-FFB57F42":
            messagebox.showerror("Serial required",
                                 "Enter a device serial number first.")
            return None
        return s

    # ── Auto-detection: exe ───────────────────────────────────────────────────
    def _try_autodetect_lh(self):
        found = find_lh_exe()
        if found:
            self.lh_path.set(str(found))
            self._log(f"Auto-found lighthouse_console.exe:", "dim")
            self._log(f"  {found}", "ok")

    def _auto_detect_lh(self):
        """Button handler — re-run exe detection and report result."""
        self._set_status("Searching for lighthouse_console.exe…")
        found = find_lh_exe()
        if found:
            self.lh_path.set(str(found))
            self._log(f"Found: {found}", "ok")
            self._set_status("lighthouse_console.exe located.")
        else:
            self._log(
                "Could not find lighthouse_console.exe automatically.\n"
                "It is normally at:\n"
                "  Steam/steamapps/common/SteamVR/tools/lighthouse/bin/win64/\n"
                "Use 'Browse…' to locate it manually.",
                "warn"
            )
            self._set_status("Auto-detect failed — use Browse.")

    def _browse_lh(self):
        path = filedialog.askopenfilename(
            title="Select lighthouse_console.exe",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.lh_path.set(path)
            self._log(f"Selected: {path}", "info")

    # ── Auto-detection: serial ────────────────────────────────────────────────
    def _auto_detect_serial(self):
        lh = self._get_lh()
        if not lh:
            return
        self._set_status("Detecting serial…")
        self._log("Probing for connected device…", "dim")

        def _run():
            s = detect_serial_from_lh(lh)
            if s:
                self.serial.set(s)
                self._log(f"Detected serial: {s}", "ok")
                self._set_status(f"Detected: {s}")
            else:
                self._log(
                    "Could not detect serial automatically.\n"
                    "Make sure the Wand is connected over USB and SteamVR is closed.",
                    "warn"
                )
                self._set_status("Detection failed — enter serial manually.")

        threading.Thread(target=_run, daemon=True).start()

    # ── HMD safety check ──────────────────────────────────────────────────────
    def _check_not_hmd(self, config: dict, serial: str) -> bool:
        """
        Returns True if it is safe to proceed (not an HMD).
        Shows a blocking warning and returns False if it looks like a headset.
        """
        if is_hmd(config):
            messagebox.showerror(
                "⚠ Headset detected — operation aborted",
                f"The device {serial} appears to be a VR headset (HMD), not a Wand.\n\n"
                "Flashing a headset with this tool will BRICK it.\n\n"
                "Make sure:\n"
                "  • Your headset is UNPLUGGED\n"
                "  • Only the Vive Wand is connected over USB\n\n"
                "The operation has been cancelled."
            )
            self._log(
                f"ABORTED — {serial} looks like an HMD ("
                f"class='{config.get('device_class', '?')}').",
                "err"
            )
            return False
        return True

    # Convert
    def _do_convert(self):
        if self._busy:
            return
        lh     = self._get_lh()
        serial = self._get_serial()
        if not lh or not serial:
            return
        if not messagebox.askyesno(
            "Confirm conversion",
            f"Convert {serial} from a Controller into a Tracker?\n\n"
            "A backup of the original config will be saved automatically.\n\n"
            "Make sure SteamVR is CLOSED and ONLY this Wand is connected over USB.\n\n"
            "Continue?"
        ):
            return
        self._run_task(self._task_convert, lh, serial)

    def _task_convert(self, lh: Path, serial: str):
        cfg_dir      = config_dir(lh.parent, serial)
        backup_path  = cfg_dir / f"{serial}-BKP.json"
        # lighthouse_console writes to its own working directory, then we move it
        lh_backup    = lh.parent / f"{serial}-BKP.json"
        lh_patched   = lh.parent / f"{serial}.json"

        # Download
        self._log_section("STEP 1 — Download original config")
        if backup_path.exists():
            self._log(f"Backup already exists: configs/{serial}/{backup_path.name}", "warn")
            self._log("Skipping download — using existing backup.", "dim")
        else:
            self._log(f"Running: downloadconfig {lh_backup.name}", "dim")
            try:
                run_lh(lh, [f"downloadconfig {lh_backup.name}"])
            except Exception as e:
                self._log(f"ERROR: {e}", "err")
                return
            if not lh_backup.exists():
                self._log(
                    "downloadconfig ran but no file was created.\n"
                    "Check: only the Wand is connected, SteamVR is closed, "
                    "and the serial is correct.",
                    "err"
                )
                return
            # Move into organised folder
            lh_backup.replace(backup_path)
            self._log(f"Saved: configs/{serial}/{backup_path.name}", "ok")

        # Load & HMD-check
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                original = json.load(f)
        except Exception as e:
            self._log(f"Failed to read backup JSON: {e}", "err")
            return

        if not self._check_not_hmd(original, serial):
            self._set_status("Aborted — HMD detected.")
            return

        # Patch
        self._log_section("STEP 2 — Patch config")
        patched = patch_config(original)
        changed = {k: (original.get(k), patched.get(k))
                   for k in patched if original.get(k) != patched.get(k)}
        for field, (old, new) in changed.items():
            self._log(f"  {field}:  '{old}'  →  '{new}'", "info")

        patched_stored = cfg_dir / f"{serial}-tracker.json"
        try:
            # Write to lh working dir for upload, and also save a copy in configs/
            with open(lh_patched, "w", encoding="utf-8") as f:
                json.dump(patched, f, indent=4)
            with open(patched_stored, "w", encoding="utf-8") as f:
                json.dump(patched, f, indent=4)
            self._log(f"Saved: configs/{serial}/{patched_stored.name}", "ok")
        except Exception as e:
            self._log(f"Failed to write patched JSON: {e}", "err")
            return

        # Upload
        self._log_section("STEP 3 — Upload patched config")
        self._log(f"Running: uploadconfig {lh_patched.name}", "dim")
        try:
            run_lh(lh, [f"uploadconfig {lh_patched.name}"])
        except Exception as e:
            self._log(f"ERROR during upload: {e}", "err")
            return

        self._log_section("DONE")
        self._log("✔ Conversion complete!", "ok")
        self._log(
            f"Configs saved to: configs/{serial}/\n\n"
            "Next steps:\n"
            "  1. Unplug the Wand from USB.\n"
            "  2. Plug in your VR headset.\n"
            "  3. Start SteamVR and the Wand should appear as a Tracker.",
            "dim"
        )
        self._set_status(f"✔ {serial} converted to Tracker.")

    # Restore
    def _do_restore(self):
        if self._busy:
            return
        lh     = self._get_lh()
        serial = self._get_serial()
        if not lh or not serial:
            return

        # Look in organised folder first, then lh working dir, then ask
        cfg_dir_path = config_dir(lh.parent, serial)
        backup_path  = cfg_dir_path / f"{serial}-BKP.json"
        if not backup_path.exists():
            fallback = lh.parent / f"{serial}-BKP.json"
            if fallback.exists():
                backup_path = fallback
            else:
                self._log(
                    f"No backup found in configs/{serial}/.\n"
                    "Please select the backup JSON file manually.",
                    "warn"
                )
                chosen = filedialog.askopenfilename(
                    title=f"Select backup JSON for {serial}",
                    initialdir=str(cfg_dir_path),
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                if not chosen:
                    self._log("Restore cancelled — no backup file selected.", "warn")
                    return
                backup_path = Path(chosen)

        if not messagebox.askyesno(
            "Confirm restore",
            f"Restore {serial} back to a standard Controller?\n\n"
            f"Using backup: {backup_path.name}\n\n"
            "Make sure SteamVR is CLOSED and ONLY this Wand is connected over USB.\n\n"
            "Continue?"
        ):
            return

        self._run_task(self._task_restore, lh, serial, backup_path)

    def _task_restore(self, lh: Path, serial: str, backup_path: Path):
        cfg_dir_path  = config_dir(lh.parent, serial)
        lh_restore    = lh.parent / f"{serial}.json"
        restore_store = cfg_dir_path / f"{serial}-controller.json"

        # Load backup
        self._log_section("STEP 1 — Read backup")
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                backup = json.load(f)
            self._log(f"Loaded: {backup_path.name}", "ok")
        except Exception as e:
            self._log(f"Failed to read backup: {e}", "err")
            return

        if not self._check_not_hmd(backup, serial):
            self._set_status("Aborted — HMD detected.")
            return

        # Build restore config
        self._log_section("STEP 2 — Build restore config")
        restored = restore_config(backup)
        changed = {
            k: (backup.get(k), restored.get(k))
            for k in set(list(backup) + list(restored))
            if backup.get(k) != restored.get(k)
        }
        if changed:
            for field, (old, new) in changed.items():
                if new is None:
                    self._log(f"  Removed: {field}  (was '{old}')", "info")
                else:
                    self._log(f"  {field}:  '{old}'  →  '{new}'", "info")
        else:
            self._log("  Config already matches controller format.", "warn")

        try:
            with open(lh_restore, "w", encoding="utf-8") as f:
                json.dump(restored, f, indent=4)
            with open(restore_store, "w", encoding="utf-8") as f:
                json.dump(restored, f, indent=4)
            self._log(f"Saved: configs/{serial}/{restore_store.name}", "ok")
        except Exception as e:
            self._log(f"Failed to write restore JSON: {e}", "err")
            return

        # Upload
        self._log_section("STEP 3 — Upload restore config")
        self._log(f"Running: uploadconfig {lh_restore.name}", "dim")
        try:
            run_lh(lh, [f"uploadconfig {lh_restore.name}"])
        except Exception as e:
            self._log(f"ERROR during upload: {e}", "err")
            return

        self._log_section("DONE")
        self._log("✔ Restore complete — Wand is a Controller again.", "ok")
        self._log(
            f"Configs saved to: configs/{serial}/\n\n"
            "Next steps:\n"
            "  1. Unplug the Wand from USB.\n"
            "  2. Start SteamVR and it should appear as a Controller.",
            "dim"
        )
        self._set_status(f"✔ {serial} restored to Controller.")

    # Threading wrapper
    def _run_task(self, fn, *args):
        self._busy = True
        self._log_clear()
        self._set_status("Working…")

        def _wrapper():
            try:
                fn(*args)
            except Exception as e:
                self._log(f"Unexpected error: {e}", "err")
                self._set_status("Error — see log.")
            finally:
                self._busy = False

        threading.Thread(target=_wrapper, daemon=True).start()


# Entry point

if __name__ == "__main__":
    app = App()
    app.mainloop()
