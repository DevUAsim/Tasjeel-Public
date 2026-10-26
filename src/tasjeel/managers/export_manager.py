from typing import Any, Callable, Dict, List, Type
from functools import partial

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog, QMenu

from tasjeel.ui import dialogs

from ..exporters import (
    BaseExporter,
    TxtExporter,
    DocxExporter,
    PdfExporter,
    JsonExporter,
    HtmlExporter,
)

NO_CONTENT_MESSAGE = "There is no transcription text to export."
EXPORT_SUCCESS_TITLE = "Export Successful"
EXPORT_ERROR_TITLE = "Export Error"
NO_CONTENT_TITLE = "No Content"
FILE_DIALOG_ALL_FILES = "All files (*.*)"

class ExportManager:
    def __init__(self, parent_window, get_data_callback: Callable[[], Dict[str, Any]]):
        self.parent = parent_window
        self.get_data_callback = get_data_callback
        self._exporters: List[Type[BaseExporter]] = [
            TxtExporter,
            JsonExporter,
            HtmlExporter,
            DocxExporter,
            PdfExporter,
        ]

    def show_export_context_menu(self, button):
        text = self.get_data_callback()
        if not text or not text.strip():
            dialogs.inform(self.parent, NO_CONTENT_TITLE, NO_CONTENT_MESSAGE, "warning")
            return

        export_data = {
            "text": text,
            "language": self.parent.get_transcription_parameters().get("language", "English"),
            "metadata": self.parent.get_transcription_parameters(),
        }

        context_menu = QMenu(self.parent)
        for exporter_class in self._exporters:
            action = QAction(exporter_class.LABEL, self.parent)
            if exporter_class.check_dependencies():
                handler = partial(
                    self._handle_export, exporter_class, export_data
                )
                action.triggered.connect(handler)
            else:
                action.setEnabled(False)
                action.setToolTip(
                    f"Required library for {exporter_class.KEY} is not installed."
                )
            context_menu.addAction(action)

        anchor = button.mapToGlobal(button.rect().bottomRight())
        context_menu.exec(anchor - QPoint(context_menu.sizeHint().width(), -6))

    def _handle_export(
        self, exporter_class: Type[BaseExporter], data: Dict[str, Any]
    ):
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            f"Save as {exporter_class.LABEL}",
            "",
            f"{exporter_class.FILE_FILTER};;{FILE_DIALOG_ALL_FILES}",
        )

        if not file_path:
            return

        try:
            exporter = exporter_class()
            exporter.export(file_path, data)
            dialogs.inform(self.parent, EXPORT_SUCCESS_TITLE, f"Saved to {file_path}", "success")
        except Exception as e:
            dialogs.inform(self.parent, EXPORT_ERROR_TITLE, f"Failed to export as {exporter_class.KEY}: {str(e)}", "error")
