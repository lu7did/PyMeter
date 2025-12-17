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

    # configuration persistence helpers (PyControl.ini in this folder)
    cfg_path = Path(__file__).resolve().parent / 'PyControl.ini'

    def _read_cfg() -> dict:
        cfg = {}
        try:
            if cfg_path.exists():
                for line in cfg_path.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        cfg[k.strip()] = v.strip()
            else:
                # generate defaults
                cfg = {
                    'RIG': 'rig1',
                    'LEFT': 'Signal',
                    'ANT': 'ant 1',
                    'VFO': 'VFO A',
                    'MODE': 'CW',
                    'POWER': '0',
                    'VOLUME': '0'
                }
                _write_cfg(cfg)
        except Exception:
            pass
        return cfg

    def _write_cfg(cfg: dict) -> None:
        try:
            cfg_path.write_text('\n'.join(f"{k}={v}" for k, v in cfg.items()) + '\n')
        except Exception:
            pass

    def _save_key(key: str, value: str) -> None:
        try:
            cfg = _read_cfg()
            cfg[key] = str(value)
            _write_cfg(cfg)
        except Exception:
            pass

    # label + small LED above the meter (tighter margins)
    label_signal = QLabel("Signal")
    label_signal.setContentsMargins(0, 0, 0, 2)
    # LED placed immediately to the right of the label
    signal_led = LedIndicator(diameter=10)
    # start with dark green off (we'll toggle colors via timer)
    signal_led.set_color_on((0, 100, 0))
    signal_led.set_on(True)

    signal_row = QHBoxLayout()
    signal_row.setContentsMargins(0, 0, 0, 0)
    signal_row.setSpacing(6)
    signal_row.addWidget(label_signal)
    signal_row.addWidget(signal_led)
    signal_row.addStretch()
    layout.addLayout(signal_row)

    # Mode selector placed on the same row as the meter (right-aligned)
    from PyQt5.QtWidgets import QComboBox
    from PyQt5.QtCore import Qt

    mode_selector = QComboBox()
    mode_selector.addItems(["CW", "USB", "LSB", "AM", "FM", "DIG-U", "DIG-L", "CW-R"])
    mode_selector.setFixedWidth(110)
    mode_selector.setCurrentIndex(0)
    def _on_mode_changed(t: str) -> None:
        try:
            print(f"Mode selector changed: {t}")
            _save_key('MODE', t)
        except Exception:
            pass
    mode_selector.currentTextChanged.connect(_on_mode_changed)

    # meter row: meter at left, mode selector at right
    meter_row = QHBoxLayout()
    meter = VUMeter(segments=10)
    meter.setContentsMargins(0, 0, 0, 2)
    meter_row.addWidget(meter)
    meter_row.addStretch()
    meter_row.addWidget(mode_selector, alignment=Qt.AlignRight | Qt.AlignVCenter)
    layout.addLayout(meter_row)

    # timer to toggle the small signal LED once per second, alternate colors
    try:
        from PyQt5.QtCore import QTimer
        win._signal_led_state = False
        def _toggle_signal_led() -> None:
            try:
                if getattr(win, '_signal_led_state', False):
                    signal_led.set_color_on((0, 100, 0))
                else:
                    signal_led.set_color_on((0, 255, 0))
                signal_led.set_on(True)
                win._signal_led_state = not getattr(win, '_signal_led_state', False)
            except Exception:
                pass
        timer = QTimer()
        timer.timeout.connect(_toggle_signal_led)
        timer.start(1000)
        win._signal_timer = timer
    except Exception:
        pass

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
            _save_key('RIG', sel)
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
    # checkbox to toggle enabled state for the power control group
    from PyQt5.QtWidgets import QCheckBox
    power_enable_cb = QCheckBox()
    power_enable_cb.setChecked(True)
    power_slider = QSlider(Qt.Horizontal)
    power_slider.setRange(0, 255)
    power_slider.setValue(0)
    power_slider.setFixedWidth(220)
    power_value = QLabel('0')
    power_value.setMinimumWidth(30)
    set_btn = QPushButton('Set')

    def _on_power_change(v: int) -> None:
        try:
            # do nothing if controls are disabled
            if not getattr(win, '_power_enabled', True):
                return
            power_value.setText(str(int(v)))
            print(f"Power slider changed: {int(v)}")
        except Exception:
            pass

    power_slider.valueChanged.connect(_on_power_change)
    # connect Set button to emit a simple console event with current slider value and persist
    def _on_power_set(_=False):
        try:
            if not getattr(win, '_power_enabled', True):
                return
            val = int(power_slider.value())
            print(f"Set button pressed: power={val}")
            _save_key('POWER', str(val))
        except Exception:
            pass
    set_btn.clicked.connect(_on_power_set)

    # enable/disable helper for the power control group
    win._power_enabled = True
    def set_power_enabled(enabled: bool) -> None:
        try:
            en = bool(enabled)
            win._power_enabled = en
            power_slider.setEnabled(en)
            set_btn.setEnabled(en)
            power_enable_cb.setChecked(en)
            # gray out text when disabled
            if en:
                power_label.setStyleSheet("")
                power_value.setStyleSheet("")
            else:
                power_label.setStyleSheet("color: #888888;")
                power_value.setStyleSheet("color: #888888;")
        except Exception:
            pass

    set_power_enabled(True)
    set_btn.clicked.connect(_on_power_set)

    # wire checkbox to enable/disable
    try:
        power_enable_cb.stateChanged.connect(lambda s: set_power_enabled(s == 2))
    except Exception:
        pass

    power_row.addWidget(power_enable_cb)
    power_row.addWidget(power_label)
    power_row.addWidget(power_slider)
    power_row.addWidget(power_value)
    power_row.addWidget(set_btn)

    layout.addLayout(power_row)

    # expose power control enable API
    setattr(win, 'set_power_enabled', set_power_enabled)
    setattr(win, 'power_enabled', lambda: getattr(win, '_power_enabled', True))

    # Volume control row directly below Power
    volume_row = QHBoxLayout()
    volume_row.setContentsMargins(0, 4, 0, 4)
    volume_row.setSpacing(6)

    volume_label = QLabel('Volume')
    volume_label.setMinimumWidth(50)
    # checkbox controlling the Volume group enabled state
    volume_enable_cb = QCheckBox()
    volume_enable_cb.setChecked(True)
    volume_slider = QSlider(Qt.Horizontal)
    volume_slider.setRange(0, 255)
    volume_slider.setValue(0)
    volume_slider.setFixedWidth(220)
    volume_value = QLabel('0')
    volume_value.setMinimumWidth(30)
    volume_set_btn = QPushButton('Set')

    def _on_volume_change(v: int) -> None:
        try:
            if not getattr(win, '_volume_enabled', True):
                return
            volume_value.setText(str(int(v)))
            print(f"Volume slider changed: {int(v)}")
        except Exception:
            pass

    volume_slider.valueChanged.connect(_on_volume_change)
    def _on_volume_set(_=False):
        try:
            if not getattr(win, '_volume_enabled', True):
                return
            val = int(volume_slider.value())
            print(f"Set button pressed: volume={val}")
            _save_key('VOLUME', str(val))
        except Exception:
            pass
    volume_set_btn.clicked.connect(_on_volume_set)

    # enable/disable helper for the volume control group
    win._volume_enabled = True
    def set_volume_enabled(enabled: bool) -> None:
        try:
            en = bool(enabled)
            win._volume_enabled = en
            volume_slider.setEnabled(en)
            volume_set_btn.setEnabled(en)
            volume_enable_cb.setChecked(en)
            if en:
                volume_label.setStyleSheet("")
                volume_value.setStyleSheet("")
            else:
                volume_label.setStyleSheet("color: #888888;")
                volume_value.setStyleSheet("color: #888888;")
        except Exception:
            pass

    set_volume_enabled(True)
    # wire checkbox to enable/disable
    try:
        volume_enable_cb.stateChanged.connect(lambda s: set_volume_enabled(s == 2))
    except Exception:
        pass

    volume_row.addWidget(volume_enable_cb)
    volume_row.addWidget(volume_label)
    volume_row.addWidget(volume_slider)
    volume_row.addWidget(volume_value)
    volume_row.addWidget(volume_set_btn)

    layout.addLayout(volume_row)

    # expose volume control enable API
    setattr(win, 'set_volume_enabled', set_volume_enabled)
    setattr(win, 'volume_enabled', lambda: getattr(win, '_volume_enabled', True))

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
            txt = button.text()
            print(f"Left group selected: {txt}")
            _save_key('LEFT', txt)
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
            txt = button.text()
            print(f"Antenna selected: {txt}")
            _save_key('ANT', txt)
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
            txt = button.text()
            print(f"VFO selected: {txt}")
            _save_key('VFO', txt)
        except Exception:
            pass

    right_group.buttonClicked.connect(_on_right_changed)

    # assemble groups row compactly so dialog width doesn't increase
    # add small checkboxes (no labels) to control Enabled state per group
    from PyQt5.QtWidgets import QCheckBox
    left_enable_cb = QCheckBox()
    left_enable_cb.setChecked(True)
    mid_enable_cb = QCheckBox()
    mid_enable_cb.setChecked(True)
    right_enable_cb = QCheckBox()
    right_enable_cb.setChecked(True)

    groups_row.addWidget(left_enable_cb)
    groups_row.addWidget(left_box)
    groups_row.addStretch()
    groups_row.addWidget(mid_enable_cb)
    groups_row.addWidget(mid_box)
    groups_row.addStretch()
    groups_row.addWidget(right_enable_cb)
    groups_row.addWidget(right_box)

    layout.addLayout(groups_row)

    # helpers to enable/disable each radio group and gray out labels when disabled
    def set_left_enabled(enabled: bool) -> None:
        try:
            en = bool(enabled)
            for b in (rb_swr, rb_power, rb_signal):
                b.setEnabled(en)
                b.setStyleSheet("" if en else "color: #888888;")
            left_enable_cb.setChecked(en)
            # persist left enabled? not required
            setattr(win, '_left_enabled', en)
        except Exception:
            pass

    def set_mid_enabled(enabled: bool) -> None:
        try:
            en = bool(enabled)
            for b in (rb_ant1, rb_ant2):
                b.setEnabled(en)
                b.setStyleSheet("" if en else "color: #888888;")
            mid_enable_cb.setChecked(en)
            setattr(win, '_mid_enabled', en)
        except Exception:
            pass

    def set_right_enabled(enabled: bool) -> None:
        try:
            en = bool(enabled)
            for b in (rb_vfoa, rb_vfob):
                b.setEnabled(en)
                b.setStyleSheet("" if en else "color: #888888;")
            right_enable_cb.setChecked(en)
            setattr(win, '_right_enabled', en)
        except Exception:
            pass

    # wire checkboxes to helpers
    try:
        left_enable_cb.stateChanged.connect(lambda s: set_left_enabled(s == 2))
        mid_enable_cb.stateChanged.connect(lambda s: set_mid_enabled(s == 2))
        right_enable_cb.stateChanged.connect(lambda s: set_right_enabled(s == 2))
    except Exception:
        pass

    # expose APIs on window
    setattr(win, 'set_left_enabled', set_left_enabled)
    setattr(win, 'left_enabled', lambda: getattr(win, '_left_enabled', True))
    setattr(win, 'set_mid_enabled', set_mid_enabled)
    setattr(win, 'mid_enabled', lambda: getattr(win, '_mid_enabled', True))
    setattr(win, 'set_right_enabled', set_right_enabled)
    setattr(win, 'right_enabled', lambda: getattr(win, '_right_enabled', True))

    # Apply persisted configuration (if any) to initialize control states
    try:
        cfg = _read_cfg()
        # rig
        r = cfg.get('RIG', 'rig1')
        rig1_radio.blockSignals(True)
        rig2_radio.blockSignals(True)
        if r == 'rig2':
            rig2_radio.setChecked(True)
        else:
            rig1_radio.setChecked(True)
        rig1_radio.blockSignals(False)
        rig2_radio.blockSignals(False)
        # left group
        left_val = cfg.get('LEFT', 'Signal')
        for b in (rb_swr, rb_power, rb_signal):
            b.blockSignals(True)
            if b.text() == left_val:
                b.setChecked(True)
            b.blockSignals(False)
        # mid group (antenna)
        ant_val = cfg.get('ANT', 'ant 1')
        for b in (rb_ant1, rb_ant2):
            b.blockSignals(True)
            if b.text() == ant_val:
                b.setChecked(True)
            b.blockSignals(False)
        # right group (VFO)
        vfo_val = cfg.get('VFO', 'VFO A')
        for b in (rb_vfoa, rb_vfob):
            b.blockSignals(True)
            if b.text() == vfo_val:
                b.setChecked(True)
            b.blockSignals(False)
        # mode selector
        mode_val = cfg.get('MODE', 'CW')
        idx = mode_selector.findText(mode_val)
        if idx >= 0:
            mode_selector.blockSignals(True)
            mode_selector.setCurrentIndex(idx)
            mode_selector.blockSignals(False)
        # sliders initial values from cfg (do not persist on change)
        try:
            p = int(cfg.get('POWER', '0'))
            power_slider.blockSignals(True)
            power_slider.setValue(p)
            power_value.setText(str(p))
            power_slider.blockSignals(False)
        except Exception:
            pass
        try:
            v = int(cfg.get('VOLUME', '0'))
            volume_slider.blockSignals(True)
            volume_slider.setValue(v)
            volume_value.setText(str(v))
            volume_slider.blockSignals(False)
        except Exception:
            pass
    except Exception:
        pass

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

    # Set logical state to RX (0) for buttons if supported, then force LED visuals to "off" (dark green)
    try:
        tr.set_state(0)
    except Exception:
        pass
    try:
        mute.set_state(0)
    except Exception:
        pass
    try:
        split.set_state(0)
    except Exception:
        pass
    try:
        tune.set_state(0)
    except Exception:
        pass

    # Ensure LEDs show dark green off color and are turned off
    for b in (tr, mute, split, tune):
        try:
            led = getattr(b, '_led', None)
            if led is not None:
                try:
                    led.set_color_on((0, 255, 0))
                except Exception:
                    pass
                try:
                    led.set_color_off((0, 100, 0))
                except Exception:
                    pass
                try:
                    led.set_on(False)
                except Exception:
                    pass
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

    # helper methods to update rig row fields programmatically
    def set_rig_name(index: int, name: str) -> None:
        """Set the display name for rig row 1 or 2."""
        try:
            if int(index) == 1:
                rig1_name.setText(str(name))
            else:
                rig2_name.setText(str(name))
        except Exception:
            pass

    def set_rig_led_color(index: int, color_on: tuple[int, int, int] | list[int], on: bool = True) -> None:
        """Set the LED on-color for the rig status LED and optionally its on/off state."""
        try:
            if int(index) == 1:
                led = rig1_led
            else:
                led = rig2_led
            if color_on is not None:
                led.set_color_on(tuple(color_on))
            led.set_on(bool(on))
        except Exception:
            pass

    def set_rig_freq(index: int, hz: int) -> None:
        """Set the frequency label for the rig row. hz is an integer number of Hz.
        Display is formatted with thousands separators followed by a space and 'MHz'."""
        try:
            txt = f"{int(hz):,d} MHz"
            if int(index) == 1:
                rig1_freq.setText(txt)
            else:
                rig2_freq.setText(txt)
        except Exception:
            pass

    def set_rig_mode(index: int, mode: str) -> None:
        """Set the mode label for the rig row (e.g., USB, LSB)."""
        try:
            if int(index) == 1:
                rig1_mode.setText(str(mode))
            else:
                rig2_mode.setText(str(mode))
        except Exception:
            pass

    setattr(win, 'set_rig_name', set_rig_name)
    setattr(win, 'set_rig_led_color', set_rig_led_color)
    setattr(win, 'set_rig_freq', set_rig_freq)
    setattr(win, 'set_rig_mode', set_rig_mode)

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
