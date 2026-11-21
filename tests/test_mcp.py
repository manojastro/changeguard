import pytest

from changeguard import mcp_tools


def test_get_change_missing_returns_none(monkeypatch):
    monkeypatch.setattr(mcp_tools, "load_history", lambda p: [])
    assert mcp_tools.get_change("CH-0001") is None
    assert mcp_tools.list_change_collisions("CH-0001") == []


def test_add_note_requires_approval():
    with pytest.raises(PermissionError):
        mcp_tools.add_change_note("CH-0001", "hi")
    assert mcp_tools.add_change_note("CH-0001", "cab ok", approved=True).startswith("note recorded")
    assert "cab ok" in mcp_tools.get_notes("CH-0001")
