from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseExporter(ABC):
    KEY = "base"
    LABEL = "Base Exporter"
    FILE_FILTER = "All files (*.*)"

    @abstractmethod
    def export(self, file_path: str, data: Dict[str, Any]) -> None:
        pass

    @classmethod
    def check_dependencies(cls) -> bool:
        return True
