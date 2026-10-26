import os
import sys
from importlib.util import find_spec
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

ICON_PATH = Path(__file__).resolve().parent / "resources" / "tasjeel.ico"


def _resolve_cuda_bin(module_name: str) -> Path | None:
    try:
        spec = find_spec(module_name)
    except ModuleNotFoundError:
        return None
    if not spec:
        return None
    base = None
    if spec.origin and spec.origin != "namespace":
        base = Path(spec.origin).parent
    elif spec.submodule_search_locations:
        base = Path(next(iter(spec.submodule_search_locations)))
    if base is None:
        return None
    candidate = base / "bin"
    return candidate if candidate.exists() else None


def _register_cuda_libraries():
    for module in ("nvidia.cudnn", "nvidia.cublas"):
        cuda_bin = _resolve_cuda_bin(module)
        if cuda_bin and hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(cuda_bin))
            os.environ["PATH"] = f"{cuda_bin}{os.pathsep}{os.environ['PATH']}"


def _set_windows_app_id():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Tasjeel.Desktop")


def main():
    _register_cuda_libraries()
    _set_windows_app_id()
    from tasjeel.core.app import VoiceTranscriptionApp

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Tasjeel")
        app.setApplicationVersion("2.0.0")
        app.setStyle("Fusion")
        app.setWindowIcon(QIcon(str(ICON_PATH)))
        window = VoiceTranscriptionApp()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
