from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_STROKE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)
_FILL = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">{body}</svg>'

_ICONS = {
    "quill": (
        _STROKE,
        '<path d="M20.5 3C12.5 3.6 7.6 9.2 7 16.5h1.6C15.6 16 20 10.4 20.5 3z"/>'
        '<path d="M20.5 3L5.2 19.3"/>'
        '<path d="M5.2 19.3L3.5 21"/>'
        '<path d="M9.6 13.2h3.6"/>'
        '<path d="M12.9 9.4h3.4"/>',
    ),
    "sliders": (
        _STROKE,
        '<line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/>'
        '<line x1="4" y1="18" x2="20" y2="18"/><circle cx="9" cy="6" r="2" fill="#000"/>'
        '<circle cx="15" cy="12" r="2" fill="#000"/><circle cx="8" cy="18" r="2" fill="#000"/>',
    ),
    "minus": (_STROKE, '<line x1="5" y1="12" x2="19" y2="12"/>'),
    "close": (_STROKE, '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>'),
    "copy": (_STROKE, '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/>'),
    "export": (_STROKE, '<path d="M12 4v11"/><path d="M7 10l5 5 5-5"/><path d="M5 20h14"/>'),
    "trash": (_STROKE, '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/>'),
    "upload": (_STROKE, '<path d="M12 15V4"/><path d="M7 9l5-5 5 5"/><path d="M5 20h14"/>'),
    "plus": (_STROKE, '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'),
    "mic": (
        _STROKE,
        '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/>'
        '<line x1="12" y1="18" x2="12" y2="21"/>',
    ),
    "pause": (_FILL, '<rect x="6" y="5" width="4" height="14" rx="1.5"/><rect x="14" y="5" width="4" height="14" rx="1.5"/>'),
    "play": (_FILL, '<path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/>'),
}


def svg_pixmap(name: str, color: str, size: int, stroke_width: float = 1.8, ratio: float = 2.0) -> QPixmap:
    template, body = _ICONS[name]
    svg = template.format(color=color, width=stroke_width, body=body)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size * ratio, size * ratio))
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def svg_icon(name: str, color: str, size: int, stroke_width: float = 1.8) -> QIcon:
    return QIcon(svg_pixmap(name, color, size, stroke_width))
