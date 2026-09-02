#!/usr/bin/env python3
"""Regression tests for the outer-loop process-tree safety guard."""

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import harness.run_game as run_game
from harness.run_game import _process_group_rss_kb, run_guarded_session


class SessionGuardTests(unittest.TestCase):
    def assert_process_gone(self, pid: int) -> None:
        for _ in range(100):
            state = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(pid)],
                capture_output=True, text=True, check=False,
            ).stdout.strip()
            if not state or state.startswith("Z"):
                return
            time.sleep(0.02)
        self.fail(f"process {pid} remained live after process-group termination")

    def test_process_group_rss_reads_root(self) -> None:
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            start_new_session=True,
        )
        try:
            rss_kb = _process_group_rss_kb(child.pid)
            self.assertIsNotNone(rss_kb)
            self.assertGreater(rss_kb, 0)
        finally:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)

    def test_memory_limit_stops_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pid_file = tmp_path / "child.pid"
            cmd = [
                sys.executable,
                "-c",
                (
                    "import pathlib, subprocess, sys, time; "
                    "p=subprocess.Popen([sys.executable, '-c', "
                    "'import time; payload=bytearray(64*1024*1024); time.sleep(30)']); "
                    f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid)); "
                    "time.sleep(30)"
                ),
            ]
            result = run_guarded_session(
                cmd, cwd=tmp_path, stdout=subprocess.DEVNULL,
                timeout_seconds=5, memory_limit_kb=32 * 1024, poll_seconds=0.01,
            )
            self.assertEqual(result.reason, "memory")
            self.assertGreater(result.peak_rss_kb, 32 * 1024)
            self.assertTrue(pid_file.exists())
            self.assert_process_gone(int(pid_file.read_text()))

    def test_timeout_stops_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pid_file = tmp_path / "root.pid"
            cmd = [
                sys.executable,
                "-c",
                f"import pathlib, os, time; pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(30)",
            ]
            result = run_guarded_session(
                cmd, cwd=tmp_path, stdout=subprocess.DEVNULL,
                timeout_seconds=0.1, memory_limit_kb=1024 * 1024,
                poll_seconds=0.01,
            )
            self.assertEqual(result.reason, "timeout")
            self.assertTrue(pid_file.exists())
            self.assert_process_gone(int(pid_file.read_text()))

    def test_monitor_failure_stops_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            run_game, "_process_group_rss_kb", return_value=None,
        ):
            result = run_guarded_session(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                cwd=Path(tmp), stdout=subprocess.DEVNULL,
                timeout_seconds=5, memory_limit_kb=1024 * 1024,
                poll_seconds=0.01,
            )
            self.assertEqual(result.reason, "monitor-error")

    def test_normal_exit_cleans_background_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pid_file = tmp_path / "background.pid"
            cmd = [
                sys.executable,
                "-c",
                (
                    "import pathlib, subprocess, sys; "
                    "p=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
                    f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid))"
                ),
            ]
            result = run_guarded_session(
                cmd, cwd=tmp_path, stdout=subprocess.DEVNULL,
                timeout_seconds=5, memory_limit_kb=1024 * 1024,
                poll_seconds=0.01,
            )
            self.assertEqual(result.reason, "exited")
            self.assertEqual(result.returncode, 0)
            self.assertTrue(pid_file.exists())
            self.assert_process_gone(int(pid_file.read_text()))


if __name__ == "__main__":
    unittest.main()
