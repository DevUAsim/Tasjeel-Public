from .base_exporter import BaseExporter
from typing import Any, Dict

DEFAULT_HTML_ENCODING = "utf-8"
RTL_LANGUAGES = ["Arabic", "Persian", "Urdu"]
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" dir="{direction}">
<head>
<meta charset="UTF-8">
<title>Voice Transcription</title>
<style>
body {{ font-family: sans-serif; line-height: 1.6; margin: 40px; }}
pre {{ white-space: pre-wrap; word-wrap: break-word; }}
</style>
</head>
<body>
<h1>Voice Transcription</h1>
<p><b>Language:</b> {lang}</p>
<hr>
<pre>{text}</pre>
</body>
</html>"""

class HtmlExporter(BaseExporter):
    KEY = "html"
    LABEL = "HTML Document (.html)"
    FILE_FILTER = "HTML files (*.html)"

    def export(self, file_path: str, data: Dict[str, Any]) -> None:
        text = data.get("text", "")
        lang = data.get("language", "English")
        direction = "rtl" if lang in RTL_LANGUAGES else "ltr"

        html_content = HTML_TEMPLATE.format(
            direction=direction,
            lang=lang,
            text=text
        )

        with open(file_path, "w", encoding=DEFAULT_HTML_ENCODING) as f:
            f.write(html_content)
