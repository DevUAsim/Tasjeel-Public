import json

from tasjeel.exporters import HtmlExporter, JsonExporter, TxtExporter

SAMPLE = {
    "text": "Assalam o alaikum. This is a test transcript.",
    "language": "English",
    "metadata": {"provider": "Whisper (Local)", "speakers": "1 Speaker"},
}


def test_txt_export_writes_plain_text(tmp_path):
    target = tmp_path / "out.txt"
    TxtExporter().export(str(target), SAMPLE)
    assert target.read_text(encoding="utf-8") == SAMPLE["text"]


def test_json_export_keeps_metadata(tmp_path):
    target = tmp_path / "out.json"
    JsonExporter().export(str(target), SAMPLE)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["transcription"] == SAMPLE["text"]
    assert payload["language"] == "English"
    assert payload["metadata"]["provider"] == "Whisper (Local)"


def test_html_export_contains_transcript(tmp_path):
    target = tmp_path / "out.html"
    HtmlExporter().export(str(target), SAMPLE)
    assert "This is a test transcript." in target.read_text(encoding="utf-8")
