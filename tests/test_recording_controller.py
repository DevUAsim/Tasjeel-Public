from tasjeel.utils import recording_controller as module
from tasjeel.utils.recording_controller import RecordingController


def test_format_duration():
    controller = RecordingController(None, None, None, None)
    assert controller._format_duration(0) == "00:00"
    assert controller._format_duration(75.9) == "01:15"
    assert controller._format_duration(3600) == "60:00"


def test_elapsed_time_excludes_pauses(monkeypatch):
    controller = RecordingController(None, None, None, None)
    clock = {"now": 1000.0}
    monkeypatch.setattr(module.time, "time", lambda: clock["now"])
    controller.start_time = 1000.0
    clock["now"] = 1030.0
    controller.pause_started = 1010.0
    assert controller._get_elapsed_time_str() == "00:10"
    controller.paused_total = 20.0
    controller.pause_started = None
    clock["now"] = 1045.0
    assert controller._get_elapsed_time_str() == "00:25"
