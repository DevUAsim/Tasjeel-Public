def get_stylesheet() -> str:
    return """
        QWidget {
            font-family: 'Segoe UI', sans-serif;
            color: #f5f5f5;
            font-size: 14px;
        }
        QMainWindow { background: transparent; }
        QDialog, QMessageBox, QInputDialog, QProgressDialog { background-color: #0a0a0a; }
        QToolTip {
            background-color: #161616; color: #f5f5f5;
            border: 1px solid #2a2a2a; border-radius: 8px;
            padding: 6px 10px; font-size: 12px;
        }
        QLabel { background: transparent; }
        QLabel#wordmark { color: #ffffff; }
        QLabel#statusText { color: #f5f5f5; font-size: 13px; font-weight: 500; }
        QLabel#modelText, QLabel#mutedText { color: #8f8f8f; font-size: 12px; }
        QLabel#sectionTitle { color: #f5f5f5; font-size: 13px; font-weight: 600; }
        QLabel#sheetTitle { color: #f5f5f5; font-size: 16px; font-weight: 600; }
        QLabel#sectionLabel { color: #8f8f8f; }
        QLabel#fieldLabel { color: #d4d4d4; font-size: 13px; }
        QLabel#noteText { color: #8f8f8f; font-size: 12px; }
        QLabel#emptyTitle { color: #f5f5f5; font-size: 18px; font-weight: 600; }
        QLabel#emptySubtitle { color: #8f8f8f; font-size: 14px; }
        QLabel#emptyIcon {
            background-color: #0d0d0d; border: 1px solid #1f1f1f; border-radius: 16px;
        }
        QFrame#hairline { background-color: #161616; border: none; }
        QFrame#vDivider { background-color: #1f1f1f; border: none; }
        QFrame#sheetPanel {
            background-color: #0a0a0a;
            border-left: 1px solid #1f1f1f;
            border-top-right-radius: 23px;
            border-bottom-right-radius: 23px;
        }
        QPushButton {
            background-color: #161616; color: #f5f5f5;
            border: 1px solid #2a2a2a; border-radius: 10px;
            padding: 8px 16px; font-weight: 500;
        }
        QPushButton:hover { background-color: #1f1f1f; border-color: #3a3a3a; }
        QPushButton:disabled { color: #4a4a4a; border-color: #1a1a1a; }
        QPushButton:focus { border-color: #5a5a5a; }
        QPushButton#primaryButton {
            background-color: #f5f5f5; color: #000000; border: 1px solid #f5f5f5;
            border-radius: 10px; padding: 8px 20px; font-weight: 600;
        }
        QPushButton#primaryButton:hover { background-color: #ffffff; }
        QPushButton#primaryButton:focus { border-color: #f5f5f5; }
        QPushButton#dangerButton {
            background-color: #ff453a; color: #ffffff; border: 1px solid #ff453a;
            border-radius: 10px; padding: 8px 20px; font-weight: 600;
        }
        QPushButton#dangerButton:hover { background-color: #ff5b52; }
        QPushButton#secondaryButton {
            background: transparent; color: #d4d4d4; border: 1px solid #2a2a2a;
            border-radius: 10px; padding: 8px 18px; font-weight: 500;
        }
        QPushButton#secondaryButton:hover { background-color: #161616; color: #ffffff; }
        QLabel#dialogBrand { color: #ffffff; font-size: 14px; font-weight: 700; }
        QLabel#dialogTitle { color: #f5f5f5; font-size: 17px; font-weight: 600; }
        QLabel#dialogText { color: #a3a3a3; font-size: 14px; }
        QLabel#dialogDetail { color: #8f8f8f; font-size: 12px; }
        QPushButton#iconButton {
            background: transparent; border: 1px solid transparent;
            border-radius: 10px; padding: 0;
        }
        QPushButton#iconButton:hover { background-color: #161616; border-color: #262626; }
        QPushButton#iconButton:focus { border-color: #5a5a5a; }
        QPushButton#iconButton:disabled { background: transparent; border-color: transparent; }
        QPushButton#roundButton {
            background-color: #0f0f0f; border: 1px solid #2a2a2a;
            border-radius: 26px; padding: 0;
        }
        QPushButton#roundButton:hover { background-color: #1a1a1a; border-color: #3a3a3a; }
        QPushButton#roundButton:focus { border-color: #ffffff; }
        QPushButton#ghostButton {
            background: transparent; border: 1px solid transparent; color: #d4d4d4;
            border-radius: 10px; padding: 0 14px; font-weight: 500;
        }
        QPushButton#ghostButton:hover { background-color: #141414; color: #ffffff; }
        QPushButton#ghostButton:focus { border-color: #5a5a5a; }
        QPushButton#ghostButton:disabled { color: #4a4a4a; }
        QFrame#segmentGroup {
            background-color: #000000; border: 1px solid #242424; border-radius: 10px;
        }
        QPushButton#segment {
            background: transparent; border: none; border-radius: 8px;
            color: #8f8f8f; padding: 7px 10px; font-size: 13px;
        }
        QPushButton#segment:hover { color: #f5f5f5; }
        QPushButton#segment:checked { background-color: #1c1c1c; color: #f5f5f5; }
        QComboBox, QLineEdit, QPlainTextEdit {
            background-color: #000000; color: #f5f5f5;
            border: 1px solid #242424; border-radius: 10px;
            padding: 8px 10px; font-size: 13px;
            selection-background-color: #ff453a; selection-color: #ffffff;
        }
        QComboBox:hover, QLineEdit:hover, QPlainTextEdit:hover { border-color: #333333; }
        QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus { border-color: #5a5a5a; }
        QComboBox::drop-down { border: none; width: 26px; }
        QComboBox QAbstractItemView {
            background-color: #0d0d0d; color: #f5f5f5;
            border: 1px solid #242424; outline: 0; padding: 4px;
            selection-background-color: #1f1f1f;
        }
        QCheckBox { color: #d4d4d4; font-size: 13px; spacing: 10px; }
        QCheckBox::indicator {
            width: 16px; height: 16px; border-radius: 5px;
            border: 1px solid #3a3a3a; background-color: #000000;
        }
        QCheckBox::indicator:checked { background-color: #ff453a; border-color: #ff453a; }
        QTextEdit#transcript {
            background: transparent; border: none;
            color: #ececec; font-size: 17px;
            selection-background-color: #ff453a; selection-color: #ffffff;
        }
        QStackedWidget, QScrollArea { background: transparent; border: none; }
        QScrollArea > QWidget > QWidget { background: transparent; }
        QScrollBar:vertical { background: transparent; width: 8px; margin: 4px 0; }
        QScrollBar::handle:vertical { background-color: #262626; border-radius: 4px; min-height: 32px; }
        QScrollBar::handle:vertical:hover { background-color: #3a3a3a; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        QMenu {
            background-color: #0d0d0d; border: 1px solid #242424;
            border-radius: 10px; padding: 6px;
        }
        QMenu::item { padding: 8px 18px; border-radius: 6px; color: #f5f5f5; }
        QMenu::item:selected { background-color: #1f1f1f; }
        QMenu::item:disabled { color: #4a4a4a; }
        QProgressBar {
            border: none; background-color: #161616;
            border-radius: 4px; height: 8px; color: transparent;
        }
        QProgressBar::chunk { background-color: #ff453a; border-radius: 4px; }
    """
