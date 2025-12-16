"""PyControl GUI application.

This application composes UI widgets developed in PyMeter/PyMeter.py (VU meter,
buttons, indicators) to provide a simple control console. It imports the
necessary widget definitions from the repository's PyMeter module while
avoiding platform-specific COM initialization when possible.

Run: python PyControl.py [--test]
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
import argparse
import importlib.util
from typing import Any

# Allow running on Linux/headless systems by passing --linux; when present
# create proper dummy module objects for pythoncom and win32com.client so
# importing PyMeter.py does not fail. If --linux is provided it will be
# removed from sys.argv so later argument parsing works normally.
linux_flag = '--linux' in sys.argv
if linux_flag:
    try:
        sys.argv.remove('--linux')
    except ValueError:
        pass

    from types import ModuleType

    if 'pythoncom' not in sys.modules:
        mod = ModuleType('pythoncom')
        mod.Empty = None
        mod.PumpWaitingMessages = lambda: None
        mod.CoInitialize = lambda: None
        sys.modules['pythoncom'] = mod

    if 'win32com' not in sys.modules:
        winmod = ModuleType('win32com')
        clientmod = ModuleType('win32com.client')

        def _dispatch_with_events(*a, **k):
            # return dummy object with minimal Rig placeholders
            from types import SimpleNamespace

            return SimpleNamespace(Rig1=SimpleNamespace(), Rig2=SimpleNamespace())

        clientmod.DispatchWithEvents = _dispatch_with_events
        # register both package and submodule
        sys.modules['win32com'] = winmod
        sys.modules['win32com.client'] = clientmod
else:
    # do not inject dummies; allow real win32com/pythoncom to be used on Windows
    pass

# Locate the PyMeter.py file in the repository (assumes script lives in PyControl/)
repo_root = Path(__file__).resolve().parents[1]
pym_path = repo_root / 'PyMeter' / 'PyMeter.py'
if not pym_path.exists():
    raise FileNotFoundError(f"PyMeter.py not found at expected location: {pym_path}")

spec = importlib.util.spec_from_file_location('pymeter_module', str(pym_path))
_pym = importlib.util.module_from_spec(spec)  # type: ignore
assert spec and spec.loader
spec.loader.exec_module(_pym)  # type: ignore

# Import PyQt5 lazily to provide clearer error messages if missing.
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel

# Extract commonly used widget classes from PyMeter module (fall back to safe names).
VUMeter = getattr(_pym, 'VUMeter')
LedButton = getattr(_pym, 'LedButton')
LedIndicator = getattr(_pym, 'LedIndicator')
TuneButton = getattr(_pym, 'TuneButton')
VFOButton = getattr(_pym, 'VFOButton')
SwapButton = getattr(_pym, 'SwapButton')


def build_window() -> QWidget:
    """Build a compact control window reusing widgets from PyMeter."""
    win = QWidget()
    win.setWindowTitle('PyControl - Remote Console')
    layout = QVBoxLayout(win)
    # reduce vertical spacing so elements sit tightly
    layout.setSpacing(2)
    layout.setContentsMargins(8, 6, 8, 6)

    # label above the meter (tighter margins)
    label_signal = QLabel("Signal")
    label_signal.setContentsMargins(0, 0, 0, 2)
    layout.addWidget(label_signal)

    # meter (placed close below the label)
    meter = VUMeter(segments=10)
    meter.setContentsMargins(0, 0, 0, 2)
    layout.addWidget(meter)

    # Two-row table with headers: '', rig, name, status, freq, mode
    from PyQt5.QtWidgets import QGridLayout, QRadioButton, QButtonGroup
    from PyQt5.QtCore import Qt

    grid = QGridLayout()
    # tighten spacing so table is close to meter
    grid.setContentsMargins(0, 2, 0, 2)
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(4)

    headers = ['', 'rig', 'name', 'status', 'freq', 'mode']
    for c, h in enumerate(headers):
        lbl = QLabel(f"<b>{h}</b>") if h else QLabel('')
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid.addWidget(lbl, 0, c)

    # Row 1: rig1
    rig1_radio = QRadioButton()
    rig2_radio = QRadioButton()
    rig_group = QButtonGroup(win)
    rig_group.addButton(rig1_radio)
    rig_group.addButton(rig2_radio)
    rig1_radio.setChecked(True)

    rig1_label = QLabel('rig1')
    rig1_name = QLabel('ICOM-706')
    rig1_name.setMinimumWidth(120)
    rig1_led = LedIndicator(diameter=10)
    # initial off (gray)
    rig1_led.set_color_off((120, 120, 120))
    rig1_led.set_color_on((120, 120, 120))
    rig1_led.set_on(False)

    # frequency label formatted as integer (Hz) with thousands sep, up to 435000000
    rig1_freq_value = 14070000  # Hz as integer
    rig1_freq = QLabel(f"{rig1_freq_value:,d}")
    rig1_freq.setMinimumWidth(110)
    rig1_mhz = QLabel('MHz')
    rig1_mode = QLabel('USB')

    # place rig1 widgets
    grid.addWidget(rig1_radio, 1, 0, alignment=Qt.AlignCenter)
    grid.addWidget(rig1_label, 1, 1, alignment=Qt.AlignLeft | Qt.AlignVCenter)
    grid.addWidget(rig1_name, 1, 2, alignment=Qt.AlignLeft | Qt.AlignVCenter)
    grid.addWidget(rig1_led, 1, 3, alignment=Qt.AlignCenter)

    # frequency displayed as single right-aligned label with one space before 'MHz'
    rig1_freq = QLabel(f"{rig1_freq_value:,d} MHz")
    rig1_freq.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    rig1_freq.setMinimumWidth(120)
    grid.addWidget(rig1_freq, 1, 4, alignment=Qt.AlignRight | Qt.AlignVCenter)
    grid.addWidget(rig1_mode, 1, 5, alignment=Qt.AlignLeft | Qt.AlignVCenter)

    # Row 2: rig2
    rig2_label = QLabel('rig2')
    rig2_name = QLabel('FT-2000')
    rig2_name.setMinimumWidth(120)
    rig2_led = LedIndicator(diameter=10)
    rig2_led.set_color_off((120, 120, 120))
    rig2_led.set_color_on((120, 120, 120))
    rig2_led.set_on(False)

    rig2_freq_value = 7200000  # Hz as integer
    rig2_freq = QLabel(f"{rig2_freq_value:,d} MHz")
    rig2_freq.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    rig2_freq.setMinimumWidth(120)
    rig2_mode = QLabel('LSB')

    grid.addWidget(rig2_radio, 2, 0, alignment=Qt.AlignCenter)
    grid.addWidget(rig2_label, 2, 1, alignment=Qt.AlignLeft | Qt.AlignVCenter)
    grid.addWidget(rig2_name, 2, 2, alignment=Qt.AlignLeft | Qt.AlignVCenter)
    grid.addWidget(rig2_led, 2, 3, alignment=Qt.AlignCenter)
    grid.addWidget(rig2_freq, 2, 4, alignment=Qt.AlignRight | Qt.AlignVCenter)
    grid.addWidget(rig2_mode, 2, 5, alignment=Qt.AlignLeft | Qt.AlignVCenter)

    # connect rig selection event
    def _on_rig_selected(button) -> None:
        try:
            if rig1_radio.isChecked():
                sel = 'rig1'
            elif rig2_radio.isChecked():
                sel = 'rig2'
            else:
                sel = 'unknown'
            print(f"Rig selected: {sel}")
        except Exception:
            pass

    rig_group.buttonClicked.connect(_on_rig_selected)

    # ensure columns align by setting minimum widths for key columns
    # name column (2) and freq column (4)
    # Add grid to main layout
    layout.addLayout(grid)

    # Power control row immediately below the rig table
    from PyQt5.QtWidgets import QSlider, QPushButton
    from PyQt5.QtCore import Qt

    power_row = QHBoxLayout()
    power_row.setContentsMargins(0, 4, 0, 4)
    power_row.setSpacing(6)

    power_label = QLabel('Power')
    power_label.setMinimumWidth(50)
    power_slider = QSlider(Qt.Horizontal)
    power_slider.setRange(0, 255)
    power_slider.setValue(0)
    power_slider.setFixedWidth(220)
    power_value = QLabel('0')
    power_value.setMinimumWidth(30)
    set_btn = QPushButton('Set')

    def _on_power_change(v: int) -> None:
        try:
            power_value.setText(str(int(v)))
            print(f"Power slider changed: {int(v)}")
        except Exception:
            pass

    power_slider.valueChanged.connect(_on_power_change)
    # connect Set button to emit a simple console event with current slider value
    set_btn.clicked.connect(lambda _=False, s=power_slider: print(f"Set button pressed: power={s.value()}"))

    power_row.addWidget(power_label)
    power_row.addWidget(power_slider)
    power_row.addWidget(power_value)
    power_row.addWidget(set_btn)

    layout.addLayout(power_row)

    # Volume control row directly below Power
    volume_row = QHBoxLayout()
    volume_row.setContentsMargins(0, 4, 0, 4)
    volume_row.setSpacing(6)

    volume_label = QLabel('Volume')
    volume_label.setMinimumWidth(50)
    volume_slider = QSlider(Qt.Horizontal)
    volume_slider.setRange(0, 255)
    volume_slider.setValue(0)
    volume_slider.setFixedWidth(220)
    volume_value = QLabel('0')
    volume_value.setMinimumWidth(30)
    volume_set_btn = QPushButton('Set')

    def _on_volume_change(v: int) -> None:
        try:
            volume_value.setText(str(int(v)))
            print(f"Volume slider changed: {int(v)}")
        except Exception:
            pass

    volume_slider.valueChanged.connect(_on_volume_change)
    volume_set_btn.clicked.connect(lambda _=False, s=volume_slider: print(f"Set button pressed: volume={s.value()}"))

    volume_row.addWidget(volume_label)
    volume_row.addWidget(volume_slider)
    volume_row.addWidget(volume_value)
    volume_row.addWidget(volume_set_btn)

    layout.addLayout(volume_row)

    # Three radio groups row (between sliders and buttons)
    from PyQt5.QtWidgets import QRadioButton, QButtonGroup, QGroupBox, QComboBox
    from PyQt5.QtCore import Qt

    groups_row = QHBoxLayout()
    groups_row.setContentsMargins(0, 4, 0, 4)
    groups_row.setSpacing(6)

    # Left group: vertical SWR / Power / Signal
    left_box = QGroupBox()
    left_layout = QVBoxLayout()
    rb_swr = QRadioButton('SWR')
    rb_power = QRadioButton('Power')
    rb_signal = QRadioButton('Signal')
    left_group = QButtonGroup(left_box)
    left_group.addButton(rb_swr)
    left_group.addButton(rb_power)
    left_group.addButton(rb_signal)
    rb_signal.setChecked(True)
    left_layout.addWidget(rb_swr)
    left_layout.addWidget(rb_power)
    left_layout.addWidget(rb_signal)
    left_box.setLayout(left_layout)

    def _on_left_changed(button) -> None:
        try:
            print(f"Left group selected: {button.text()}")
        except Exception:
            pass

    left_group.buttonClicked.connect(_on_left_changed)

    # Middle group: Antenna 1 / 2
    mid_box = QGroupBox()
    mid_layout = QVBoxLayout()
    rb_ant1 = QRadioButton('ant 1')
    rb_ant2 = QRadioButton('ant 2')
    mid_group = QButtonGroup(mid_box)
    mid_group.addButton(rb_ant1)
    mid_group.addButton(rb_ant2)
    rb_ant1.setChecked(True)
    mid_layout.addWidget(rb_ant1)
    mid_layout.addWidget(rb_ant2)
    mid_box.setLayout(mid_layout)

    def _on_mid_changed(button) -> None:
        try:
            print(f"Antenna selected: {button.text()}")
        except Exception:
            pass

    mid_group.buttonClicked.connect(_on_mid_changed)

    # Right group: VFO A / VFO B
    right_box = QGroupBox()
    right_layout = QVBoxLayout()
    rb_vfoa = QRadioButton('VFO A')
    rb_vfob = QRadioButton('VFO B')
    right_group = QButtonGroup(right_box)
    right_group.addButton(rb_vfoa)
    right_group.addButton(rb_vfob)
    rb_vfoa.setChecked(True)
    right_layout.addWidget(rb_vfoa)
    right_layout.addWidget(rb_vfob)
    right_box.setLayout(right_layout)

    def _on_right_changed(button) -> None:
        try:
            print(f"VFO selected: {button.text()}")
        except Exception:
            pass

    right_group.buttonClicked.connect(_on_right_changed)

    # Mode selector to the right of VFO group (compact)
    mode_selector = QComboBox()
    mode_selector.addItems(["CW", "USB", "LSB", "AM", "FM", "DIG-U", "DIG-L", "CW-R"])
    mode_selector.setFixedWidth(110)
    mode_selector.setCurrentIndex(0)
    mode_selector.currentTextChanged.connect(lambda t: print(f"Mode selector changed: {t}"))

    # assemble groups row compactly so dialog width doesn't increase
    groups_row.addWidget(left_box)
    groups_row.addWidget(mid_box)
    groups_row.addWidget(right_box)
    groups_row.addWidget(mode_selector, alignment=Qt.AlignVCenter)

    layout.addLayout(groups_row)

    # small row of buttons (keep previous functionality)
    from PyQt5.QtWidgets import QFrame

    btn_row = QHBoxLayout()
    tr = LedButton('RX')
    mute = LedButton('Mute')
    tune = TuneButton('Tune')
    # provide TuneButton with a reference to the main window so its _on_clicked can use self.win
    try:
        getattr(tune, '_setMainWindow', lambda w: None)(win)
    except Exception:
        pass
    split = SwapButton('Split')

    # Set sensible defaults
    tr.set_state(0)
    try:
        mute.set_state(0)
    except Exception:
        pass
    try:
        # ensure Tune label uses requested capitalization
        tune._button.setText('Tune')
    except Exception:
        pass

    btn_row.addWidget(tr)
    btn_row.addWidget(mute)
    btn_row.addWidget(split)
    btn_row.addWidget(tune)

    # Override button actions: disconnect any existing handlers and replace with simple console log
    def _bind_simple(btn_obj, name: str):
        try:
            # attempt to access underlying QPushButton
            qbtn = getattr(btn_obj, '_button', None) or getattr(btn_obj, 'button', None) or btn_obj
            try:
                qbtn.clicked.disconnect()
            except Exception:
                pass
            qbtn.clicked.connect(lambda checked=False, n=name: print(f"Button event: {n}"))
        except Exception:
            # fallback: print on exception
            try:
                btn_obj.clicked.disconnect()
                btn_obj.clicked.connect(lambda checked=False, n=name: print(f"Button event: {n}"))
            except Exception:
                pass

    _bind_simple(tr, 'RX')
    _bind_simple(mute, 'Mute')
    _bind_simple(split, 'Split')
    _bind_simple(tune, 'Tune')

    # container frame to hold the button row
    frame = QFrame()
    frame.setLayout(btn_row)
    layout.addWidget(frame)

    # attach small helper methods for programmatic control
    def set_meter(val: int) -> None:
        try:
            meter.set_value(int(val))
        except Exception:
            pass

    def set_tr_state(v: int) -> None:
        try:
            tr.set_state(int(v))
        except Exception:
            pass

    # expose onto widget for external use
    setattr(win, 'set_meter', set_meter)
    setattr(win, 'set_tr', set_tr_state)
    setattr(win, 'meter', meter)
    setattr(win, 'tr', tr)
    setattr(win, 'tune', tune)
    setattr(win, 'mute', mute)
    setattr(win, 'split', split)

    # expose the rig table widgets for external manipulation
    setattr(win, 'rig_group', rig_group)
    setattr(win, 'rig1_radio', rig1_radio)
    setattr(win, 'rig2_radio', rig2_radio)
    setattr(win, 'rig1_name', rig1_name)
    setattr(win, 'rig2_name', rig2_name)
    setattr(win, 'rig1_led', rig1_led)
    setattr(win, 'rig2_led', rig2_led)
    setattr(win, 'rig1_freq_label', rig1_freq)
    setattr(win, 'rig2_freq_label', rig2_freq)
    setattr(win, 'rig1_mode', rig1_mode)
    setattr(win, 'rig2_mode', rig2_mode)

    return win


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='PyControl GUI (reusing PyMeter widgets)')
    parser.add_argument('--test', action='store_true', help='Animate meter for testing')
    args = parser.parse_args(argv)

    app = QApplication(sys.argv if argv is None else argv)
    win = build_window()
    win.show()

    # initial state
    if hasattr(win, 'set_meter'):
        win.set_meter(0)
    if hasattr(win, 'set_tr'):
        win.set_tr(0)

    # optional test animation
    if args.test:
        from PyQt5.QtCore import QTimer

        val = 0
        direction = 1

        def tick() -> None:
            nonlocal val, direction
            val += 8 * direction
            if val >= 255:
                val = 255
                direction = -1
            elif val <= 0:
                val = 0
                direction = 1
            try:
                win.set_meter(val)
            except Exception:
                pass

        timer = QTimer()
        timer.timeout.connect(tick)
        timer.start(50)
        win._test_timer = timer

    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
