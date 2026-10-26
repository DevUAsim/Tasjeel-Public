from .base_exporter import BaseExporter
from typing import Any, Dict
import time

RTL_LANGUAGES = ["Arabic", "Persian", "Urdu"]
DOCUMENT_TITLE = "Voice Transcription"
SPACER_HEIGHT_SMALL = 6
SPACER_HEIGHT_MEDIUM = 12
SPACER_HEIGHT_LARGE = 20

class PdfExporter(BaseExporter):
    KEY = "pdf"
    LABEL = "PDF Document (.pdf)"
    FILE_FILTER = "PDF files (*.pdf)"

    @classmethod
    def check_dependencies(cls) -> bool:
        try:
            import reportlab
            return True
        except ImportError:
            return False

    def export(self, file_path: str, data: Dict[str, Any]) -> None:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT

        doc = SimpleDocTemplate(file_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        story.append(Paragraph(DOCUMENT_TITLE, styles["h1"]))
        story.append(Spacer(1, SPACER_HEIGHT_MEDIUM))
        story.append(
            Paragraph(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"])
        )
        story.append(
            Paragraph(f"Language: {data.get('language', 'Unknown')}", styles["Normal"])
        )
        story.append(Spacer(1, SPACER_HEIGHT_LARGE))

        alignment = (
            TA_RIGHT
            if data.get("language") in RTL_LANGUAGES
            else TA_LEFT
        )
        content_style = ParagraphStyle(
            name="Content", parent=styles["Normal"], alignment=alignment
        )

        for para_text in data.get("text", "").split("\n"):
            story.append(Paragraph(para_text, content_style))
            story.append(Spacer(1, SPACER_HEIGHT_SMALL))

        doc.build(story)
