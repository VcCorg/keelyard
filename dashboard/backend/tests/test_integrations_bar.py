"""Integration status bar contract.

gcloud/ADC covers Vertex + Gemini, so we don't ship a separate Gemini chip.
Also pins the chip order the UI expects: backend, gcloud, devin, mcp.
"""

from src.services import integrations_service


def test_no_gemini_chip():
    keys = {i.key for i in integrations_service.get_integrations().integrations}
    assert "gemini" not in keys, "gcloud/ADC covers Gemini — the Gemini chip was removed"


def test_expected_chip_order():
    keys = [i.key for i in integrations_service.get_integrations().integrations]
    assert keys == ["backend", "gcloud", "devin", "mcp"]
