from .base_exporter import BaseExporter
from typing import Any, Dict
import json

DEFAULT_JSON_ENCODING = "utf-8"
JSON_INDENT_SIZE = 2

class JsonExporter(BaseExporter):
    KEY = "json"
    LABEL = "JSON Format (.json)"
    FILE_FILTER = "JSON files (*.json)"

    def export(self, file_path: str, data: Dict[str, Any]) -> None:
        export_data = {
            "transcription": data.get("text", ""),
            "metadata": data.get("metadata", {}),
            "language": data.get("language", "Unknown"),
        }
        with open(file_path, "w", encoding=DEFAULT_JSON_ENCODING) as f:
            json.dump(export_data, f, indent=JSON_INDENT_SIZE, ensure_ascii=False)
