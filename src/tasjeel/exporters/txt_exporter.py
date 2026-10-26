from .base_exporter import BaseExporter
from typing import Any, Dict

DEFAULT_TEXT_ENCODING = "utf-8"

class TxtExporter(BaseExporter):
    KEY = "txt"
    LABEL = "Plain Text (.txt)"
    FILE_FILTER = "Text files (*.txt)"

    def export(self, file_path: str, data: Dict[str, Any]) -> None:
        with open(file_path, "w", encoding=DEFAULT_TEXT_ENCODING) as f:
            f.write(data.get("text", ""))
