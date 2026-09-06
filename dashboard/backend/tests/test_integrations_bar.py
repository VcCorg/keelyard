"""Integration status bar contract.

gcloud/ADC covers Vertex + Gemini, so we don't ship a separate Gemini chip.
Also pins the chip order the UI expects: backend, gcloud, devin, mcp.

The bar renders the ``platform`` group only. An optional integration nobody
connected would otherwise sit there as a permanent grey dot, teaching people to
ignore the one widget that is supposed to tell them the backend is down — so the
group is part of this contract, not a cosmetic field.
"""

from src.services import integrations_service


def test_no_gemini_chip():
    keys = {i.key for i in integrations_service.get_integrations().integrations}
    assert "gemini" not in keys, "gcloud/ADC covers Gemini — the Gemini chip was removed"


def test_expected_chip_order():
    keys = [i.key for i in integrations_service.get_integrations().integrations
            if i.group == "platform"]
    assert keys == ["backend", "gcloud", "devin", "mcp"]


def test_hubs_are_optional_and_stay_out_of_the_bar():
    hubs = {i.key: i for i in integrations_service.get_integrations().integrations
            if i.key in ("huggingface", "kaggle")}
    assert set(hubs) == {"huggingface", "kaggle"}
    for item in hubs.values():
        assert item.group == "optional"
        # Every hub state names the command that changes it; a status with no
        # remedy is just a red dot.
        assert item.docs_command


def test_hub_status_never_carries_a_credential_value(monkeypatch, tmp_path):
    """The panel reports where a credential lives, never what it is."""
    kaggle_dir = tmp_path / ".kaggle"
    kaggle_dir.mkdir()
    (kaggle_dir / "kaggle.json").write_text(
        '{"username": "example-user", "key": "kaggle-key-placeholder-never-read"}'
    )
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(kaggle_dir))
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)

    item = next(i for i in integrations_service.get_integrations().integrations
                if i.key == "kaggle")
    blob = item.model_dump_json()
    assert "kaggle-key-placeholder-never-read" not in blob
