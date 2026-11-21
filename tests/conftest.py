from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _hermetic_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every Git subprocess independent of the machine running the tests.

    A clean CI runner has no global Git identity, and a developer machine may
    carry a global `core.hooksPath`, commit signing, or a default branch name.
    Either would change what these tests observe, so the suite supplies its own
    identity and ignores user- and system-level Git configuration.
    """
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test Author")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "author@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test Committer")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "committer@example.invalid")
