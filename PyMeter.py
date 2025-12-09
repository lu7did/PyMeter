"""
Simple Qt5 application providing a LED VU-meter (0..255) and two buttons
with LED indicators named TX and RX. Buttons accept programmatic 0/1 values
and toggle their state when clicked.

Designed following the style rules in CONTEXT.md: Python 3.12, OOP,
separation of presentation and logic, basic error handling and type hints.
"""
from __future__ import annotations

from typing import Tuple
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QSize, QTimer, QEvent
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QRadioButton,
    QButtonGroup,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QSizePolicy,
)


class VUMeter(QWidget):
    """Widget that displays a VU meter using a row of LED-like segments.

    Value range: 0..255 (0 -> none lit, 255 -> all lit).
    """

    def __init__(self, segments: int = 10, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if segments <= 0:
            raise ValueError("segments must be > 0")
        self._segments = segments
        self._value = 0  # 0..255
        self.setMinimumSize(QSize(240, 40))
        # precompute band mapping: first 5 green, next 3 yellow, last 2 red
        # this allows precise control over colors per LED
        self._bands = (['green'] * 5) + (['yellow'] * 3) + (['red'] * 2)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        # whether the meter is enabled (online). When disabled, all LEDs show off colors
        self._enabled = True

    def sizeHint(self) -> QSize:  # pragma: no cover - GUI helper
        return QSize(320, 80)

    def set_value(self, value: int) -> None:
        """Set meter value in 0..255 and refresh display."""
        try:
            v = int(value)
        except Exception:
            return
        v = max(0, min(255, v))
        if v != self._value:
            self._value = v
            self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - painting
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        margin = 4
        # horizontal layout: compute per-segment width and a small LED height
        available_w = w - 2 * margin
        gap = 4
        seg_w = max(10, (available_w - (self._segments - 1) * gap) / self._segments)
        led_h = max(8, min(20, h - 2 * margin))
        y = int((h - led_h) / 2)
        lit_count = int(round((self._value / 255.0) * self._segments))

        for i in range(self._segments):
            left = margin + i * (seg_w + gap)
            rect_w = int(seg_w)
            rect_h = int(led_h)
            x = int(left)
            frac = i / max(1, self._segments - 1)
            # determine band from explicit mapping to ensure 5/3/2 distribution
            band = self._bands[i] if i < len(self._bands) else ("green" if frac < 0.4 else ("yellow" if frac < 0.75 else "red"))
            on_color, off_color = self._colors_for_band(band)
            # If meter is disabled (offline) always show off colors
            if not getattr(self, "_enabled", True):
                brush_color = off_color
            else:
                brush_color = on_color if i < lit_count else off_color
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(brush_color)
            painter.drawRoundedRect(x, y, rect_w, rect_h, 3, 3)

    @staticmethod
    def _colors_for_fraction(frac: float) -> tuple[QColor, QColor]:
        """Return (on_color, off_color) for the given fractional position.

        On colors are bright; off colors are dim (tenue/obscuro) as requested.
        """
        if frac < 0.4:
            # low band: dark green -> lime
            return QColor(0, 255, 0), QColor(0, 100, 0)
        if frac < 0.75:
            # mid band: dim yellow -> bright yellow
            return QColor(255, 255, 0), QColor(120, 120, 0)
        # high band: dim red -> bright red
        return QColor(255, 0, 0), QColor(120, 0, 0)

    def _colors_for_band(self, band: str) -> tuple[QColor, QColor]:
        """Return (on_color, off_color) given a named band: green/yellow/red."""
        if band == "green":
            return QColor(0, 255, 0), QColor(0, 100, 0)
        if band == "yellow":
            return QColor(255, 255, 0), QColor(120, 120, 0)
        return QColor(255, 0, 0), QColor(120, 0, 0)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the meter display. When disabled all LEDs show off colors."""
        self._enabled = bool(enabled)
        self.update()


class LedIndicator(QWidget):
    """Simple circular LED indicator. Use set_on(True/False)."""

    def __init__(self, diameter: int = 8, color_on: Tuple[int, int, int] = (0, 255, 0), parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on = False
        self._diameter = diameter
        self._color_on = QColor(*color_on)
        # default off color is neutral gray; can be changed with set_color_off
        self._color_off = QColor(80, 80, 80)
        self.setFixedSize(QSize(diameter + 4, diameter + 4))

    def set_on(self, state: bool) -> None:
        self._on = bool(state)
        self.update()

    def is_on(self) -> bool:
        return self._on

    def set_color_on(self, color: Tuple[int, int, int]) -> None:
        """Change the 'on' color for the indicator and refresh."""
        self._color_on = QColor(*color)
        self.update()

    def set_color_off(self, color: Tuple[int, int, int]) -> None:
        """Change the 'off' (dim) color for the indicator and refresh."""
        self._color_off = QColor(*color)
        self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - painting
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = 2
        d = self._diameter
        x = r
        y = r
        brush = self._color_on if self._on else self._color_off
        pen = QPen(Qt.black, 1)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawEllipse(x, y, d, d)


class LedButton(QWidget):
    """Composite widget: a QPushButton with a small LedIndicator beside it.

    The button click toggles the indicator state. Methods set_state(0|1)
    and get_state() are provided for programmatic control.
    """

    def __init__(self, label: str, color_on: Tuple[int, int, int] = (0, 255, 0), parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = 0
        self._button = QPushButton(label)
        # make button slightly wider so text and LED are separated (slightly smaller now)
        self._button.setMinimumWidth(90)
        self._button.setStyleSheet("background-color: #d3d3d3;")
        self._led = LedIndicator(color_on=color_on, diameter=8)
        self._button.clicked.connect(self._on_clicked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._button)
        # place LED inside the button as a child and keep it positioned
        self._led.setParent(self._button)
        self._button.installEventFilter(self)
        self._place_led()
        # ensure initial visual state and label and LED color
        self._state = 0
        # keep the provided label (e.g., "RX" or "TUNE")
        self._button.setText(label)
        self._led.set_color_on((0, 255, 0))
        self._led.set_on(True)

    def _on_clicked(self) -> None:
        # toggle state on user click
        self.set_state(0 if self._state else 1)

    def set_state(self, value: int) -> None:
        """Set state to 0 or 1. Non-zero values are treated as 1. Updates LED color and label.

        When 0 -> RX label and green LED off; when 1 -> TX label and red LED on.
        """
        s = 1 if int(value) else 0
        if s != self._state:
            self._state = s
            if self._state:
                # TX: vivid red and ON
                self._led.set_color_on((255, 0, 0))
                self._button.setText("TX")
                self._led.set_on(True)
            else:
                # RX: lime green and ON
                self._led.set_color_on((0, 255, 0))
                self._button.setText("RX")
                self._led.set_on(True)

    def get_state(self) -> int:
        return self._state

    def eventFilter(self, obj: object, event: "QEvent") -> bool:
        """Handle button resize events to reposition the embedded LED."""
        if obj is self._button and event.type() == QEvent.Resize:
            self._place_led()
        return super().eventFilter(obj, event)

    def _place_led(self) -> None:
        """Position the LED inside the button at the right side, centered vertically."""
        try:
            bw = self._button.width()
            bh = self._button.height()
            lw = self._led.width()
            lh = self._led.height()
            margin = 6
            x = max(2, bw - lw - margin)
            y = max(0, (bh - lh) // 2)
            self._led.move(x, y)
        except Exception:
            # on some early init calls sizes may be zero; ignore safely
            pass


class TuneButton(LedButton):
    """Momentary button: turns LED vivid red for 2s on click then returns to green."""

    def __init__(self, label: str = "TUNE", parent: QWidget | None = None) -> None:
        super().__init__(label, parent=parent)

    def _on_clicked(self) -> None:
        # set vivid red and schedule restore
        self._led.set_color_on((255, 0, 0))
        self._led.set_on(True)
        self._button.setEnabled(False)
        QTimer.singleShot(2000, self._restore)

    def _restore(self) -> None:
        # return to green lime
        self._led.set_color_on((0, 255, 0))
        self._led.set_on(True)
        self._button.setEnabled(True)


class VFOButton(LedButton):
    """Toggle between VFOA and VFOB labels, with LED showing green for A and red for B."""

    def __init__(self, label: str = "VFOA", parent: QWidget | None = None) -> None:
        super().__init__(label, parent=parent)

    def set_state(self, value: int) -> None:
        s = 1 if int(value) else 0
        if s != self._state:
            self._state = s
            if self._state:
                # VFOB
                self._led.set_color_on((255, 0, 0))
                self._button.setText("VFOB")
                self._led.set_on(True)
            else:
                # VFOA
                self._led.set_color_on((0, 255, 0))
                self._button.setText("VFOA")
                self._led.set_on(True)


class SwapButton(LedButton):
    """Momentary action button for swapping VFOs: blinks red and emits swap event."""

    def __init__(self, label: str = "A<>B", parent: QWidget | None = None) -> None:
        super().__init__(label, parent=parent)

    def _on_clicked(self) -> None:
        # emit a swap message and blink red briefly
        try:
            print("Swap VFO requested: A<->B")
            # show red briefly
            self._led.set_color_on((255, 0, 0))
            self._led.set_on(True)
            self._button.setEnabled(False)
            QTimer.singleShot(600, self._restore)
        except Exception:
            pass

    def _restore(self) -> None:
        # return led to green
        try:
            self._led.set_color_on((0, 255, 0))
            self._led.set_on(True)
            self._button.setEnabled(True)
        except Exception:
            pass


class MainWindow(QMainWindow):
    """Main application window composing the VU meter and TX/RX controls."""

    def __init__(self) -> None:
        super().__init__()
        self._config_path: Path | None = None
        self.setWindowTitle("PyMeter - VU Meter with TX/RX LEDs")
        central = QWidget()
        self.setCentralWidget(central)

        self.meter = VUMeter(segments=10)
        # single toggle button starting in RX state (0)
        self.tr = LedButton("RX")
        # make TR button slightly narrower (closer to right edge)
        try:
            self.tr._button.setMinimumWidth(70)
        except Exception:
            pass
        # TUNE button below it
        self.tune = TuneButton("TUNE")
        try:
            self.tune._button.setMinimumWidth(70)
        except Exception:
            pass
        # VFO toggle button under TUNE
        self.vfo = VFOButton("VFOA")
        try:
            self.vfo._button.setMinimumWidth(70)
        except Exception:
            pass

        # Ready label + LED placed above the meter
        ready_row = QHBoxLayout()
        # make spacing minimal so the LED sits very close to the text
        ready_row.setSpacing(0)
        ready_row.setContentsMargins(0, 0, 0, 0)
        self.ready_label = QLabel("Offline")
        # remove extra label padding/margins so LED can sit next to the text
        self.ready_label.setStyleSheet("font-weight: bold; margin: 0px; padding-left: 2px;")
        # make ready LED slightly smaller to sit closer to the text
        self.ready_led = LedIndicator(diameter=6)
        # ready: on color lime, off color dark green, start off
        self.ready_led.set_color_on((0, 255, 0))
        self.ready_led.set_color_off((0, 100, 0))
        self.ready_led.set_on(False)
        ready_row.addWidget(self.ready_led)
        ready_row.addWidget(self.ready_label)
        # rig name display to the right of Online/Offline in parentheses
        self.ready_rig_label = QLabel("")
        self.ready_rig_label.setStyleSheet("margin-left:4px; color: #333;")
        ready_row.addWidget(self.ready_rig_label)
        ready_row.setAlignment(self.ready_led, Qt.AlignVCenter)
        ready_row.setAlignment(self.ready_label, Qt.AlignVCenter)
        ready_row.setAlignment(self.ready_rig_label, Qt.AlignVCenter)

        # Layout
        # Create a grid so corresponding rows align vertically across columns
        from PyQt5.QtWidgets import QGridLayout

        grid = QGridLayout(central)
        grid.setContentsMargins(12, 4, 12, 4)
        # reduce vertical spacing so radio group sits immediately under the meter
        grid.setVerticalSpacing(0)
        grid.setRowMinimumHeight(2, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        # row 0: ready label+led (left) and TR area (right)
        grid.addLayout(ready_row, 0, 0)
        # create Swap button instance for right column
        self.swap = SwapButton("A<>B")
        try:
            self.swap._button.setMinimumWidth(70)
        except Exception:
            pass
        # right column: vertical stack with TR at top and TUNE at bottom, swap and vfo evenly spaced between
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.addWidget(self.tr, alignment=Qt.AlignRight)
        right_col.addStretch()
        # ensure swap is above VFO
        right_col.addWidget(self.swap, alignment=Qt.AlignRight)
        right_col.addWidget(self.vfo, alignment=Qt.AlignRight)
        right_col.addStretch()
        right_col.addWidget(self.tune, alignment=Qt.AlignRight)
        # place meter at row 1 left
        grid.addWidget(self.meter, 1, 0)
        # place right_col spanning rows 0..1 so the group sits between top and meter area
        grid.addLayout(right_col, 0, 1, 2, 1)
        # Signal/Power/SWR radio buttons immediately below the VUMeter (left column)
        radio_layout = QVBoxLayout()
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.setSpacing(0)
        self.rb_signal = QRadioButton("Signal")
        self.rb_power = QRadioButton("Power")
        self.rb_swr = QRadioButton("SWR")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_signal)
        self.mode_group.addButton(self.rb_power)
        self.mode_group.addButton(self.rb_swr)
        self.rb_signal.setChecked(True)
        radio_layout.addWidget(self.rb_signal)
        radio_layout.addWidget(self.rb_power)
        radio_layout.addWidget(self.rb_swr)
        # connect handler to selection changes
        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        grid.addLayout(radio_layout, 2, 0, Qt.AlignLeft)

        # Antenna selection immediately below Signal/Power/SWR
        ant_layout = QVBoxLayout()
        ant_layout.setContentsMargins(0, 6, 0, 0)
        ant_layout.setSpacing(2)
        self.rb_ant1 = QRadioButton("Ant 1")
        self.rb_ant2 = QRadioButton("Ant 2")
        self.ant_group = QButtonGroup(self)
        self.ant_group.addButton(self.rb_ant1)
        self.ant_group.addButton(self.rb_ant2)
        self.rb_ant1.setChecked(True)
        ant_layout.addWidget(self.rb_ant1)
        ant_layout.addWidget(self.rb_ant2)
        # connect antenna handler
        self.ant_group.buttonClicked.connect(self._on_ant_changed)
        grid.addLayout(ant_layout, 3, 0, Qt.AlignLeft)

        # rig selection controls stacked to the right aligned with Signal/Power/SWR
        rig_vlayout = QVBoxLayout()
        rig_vlayout.setContentsMargins(0, 0, 0, 0)
        rig_vlayout.setSpacing(2)
        # radio buttons should be labeled "rig1" and "rig2"
        self.rb_rig1 = QRadioButton("rig1")
        self.rb_rig2 = QRadioButton("rig2")
        self.rig_group = QButtonGroup(self)
        self.rig_group.addButton(self.rb_rig1)
        self.rig_group.addButton(self.rb_rig2)
        self.rb_rig1.setChecked(True)
        # labels showing the RigName next to each radio button (modifiable attribute)
        self.rig1_name = "Rig 1"
        self.rig2_name = "Rig 2"
        rig1_row = QHBoxLayout()
        rig1_row.setContentsMargins(0, 0, 0, 0)
        rig1_row.setSpacing(4)
        self.rig1_label = QLabel(self.rig1_name)
        # allow room for up to ~15 chars
        self.rig1_label.setMinimumWidth(150)
        self.rig1_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        rig1_row.addWidget(self.rb_rig1)
        rig1_row.addWidget(self.rig1_label)
        rig_vlayout.addLayout(rig1_row)
        rig2_row = QHBoxLayout()
        rig2_row.setContentsMargins(0, 0, 0, 0)
        rig2_row.setSpacing(4)
        self.rig2_label = QLabel(self.rig2_name)
        self.rig2_label.setMinimumWidth(150)
        self.rig2_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        rig2_row.addWidget(self.rb_rig2)
        rig2_row.addWidget(self.rig2_label)
        rig_vlayout.addLayout(rig2_row)
        # connect handler
        self.rig_group.buttonClicked.connect(self._on_rig_changed)
        grid.addLayout(rig_vlayout, 2, 1, Qt.AlignLeft)

        # Sliders placed in their own block below rig controls so they don't overlap
        from PyQt5.QtWidgets import QSlider
        slider_vlayout = QVBoxLayout()
        slider_vlayout.setContentsMargins(0, 6, 0, 0)
        slider_vlayout.setSpacing(6)

        # fixed label width so labels align left and sliders align vertically
        label_width = 60
        slider_width = 220

        self.slider_power_label = QLabel("Power")
        self.slider_power_label.setFixedWidth(label_width)
        self.slider_power = QSlider(Qt.Horizontal)
        self.slider_power.setRange(0, 255)
        self.slider_power.setValue(0)
        # connect power slider to isolated handler
        self.slider_power.valueChanged.connect(lambda v, s=self.slider_power: self._handle_slider_change('power', v, s))
        self.slider_power.setFixedWidth(slider_width)
        self.slider_power_value = QLabel("0")
        power_row = QHBoxLayout()
        power_row.setContentsMargins(0, 0, 0, 0)
        power_row.setSpacing(6)
        power_row.addWidget(self.slider_power_label)
        power_row.addWidget(self.slider_power)
        power_row.addWidget(self.slider_power_value)
        slider_vlayout.addLayout(power_row)

        self.slider_vol_label = QLabel("Volumen")
        self.slider_vol_label.setFixedWidth(label_width)
        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 255)
        self.slider_vol.setValue(0)
        # connect volume slider to isolated handler
        self.slider_vol.valueChanged.connect(lambda v, s=self.slider_vol: self._handle_slider_change('volume', v, s))
        self.slider_vol.setFixedWidth(slider_width)
        self.slider_vol_value = QLabel("0")
        vol_row = QHBoxLayout()
        vol_row.setContentsMargins(0, 0, 0, 0)
        vol_row.setSpacing(6)
        vol_row.addWidget(self.slider_vol_label)
        vol_row.addWidget(self.slider_vol)
        vol_row.addWidget(self.slider_vol_value)
        slider_vlayout.addLayout(vol_row)

        # place sliders below (row 4) to avoid overlapping with rig controls
        grid.addLayout(slider_vlayout, 4, 1, Qt.AlignLeft)

        # ensure meter row expands
        grid.setRowStretch(1, 1)

        # update ready rig label initially
        self._update_ready_rig_label()

        main_layout = grid
        # Example: connect button click to print state
        self.tr._button.clicked.connect(lambda: print(f"TR state: {self.tr.get_state()}"))
        # connect VFO change printing
        self.vfo._button.clicked.connect(lambda: self._on_vfo_changed(self.vfo.get_state()))
        # connect swap button
        self.swap._button.clicked.connect(lambda: self._on_swap())

        self.resize(360, 100)

    def load_config(self, path: str | Path) -> None:
        """Load config from file path (KEY=VALUE lines). Creates default if missing."""
        p = Path(path)
        self._config_path = p
        cfg = {}
        if p.exists():
            try:
                for line in p.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        cfg[k.strip()] = v.strip()
            except Exception:
                cfg = {}
        else:
            # create default
            cfg['SIGNAL'] = 'Signal'
            cfg['RIG'] = 'rig1'
            cfg['ANT'] = 'Ant 1'
            cfg['VFO'] = 'VFOA'
            cfg['POWER'] = '0'
            cfg['VOLUME'] = '0'
            try:
                p.write_text('\n'.join(f"{k}={v}" for k, v in cfg.items()) + '\n')
            except Exception:
                pass
        # apply to UI
        try:
            sig = cfg.get('SIGNAL', 'Signal')
            if sig == 'Signal':
                self.rb_signal.setChecked(True)
            elif sig == 'Power':
                self.rb_power.setChecked(True)
            elif sig == 'SWR':
                self.rb_swr.setChecked(True)
            rig = cfg.get('RIG', 'rig1')
            if rig == 'rig1':
                self.rb_rig1.setChecked(True)
            else:
                self.rb_rig2.setChecked(True)
            # antenna
            ant = cfg.get('ANT', 'Ant 1')
            if ant == 'Ant 2':
                self.rb_ant2.setChecked(True)
            else:
                self.rb_ant1.setChecked(True)
            # VFO
            vfo = cfg.get('VFO', 'VFOA')
            if vfo == 'VFOB':
                self.vfo.set_state(1)
            else:
                self.vfo.set_state(0)
            # Power / Volume
            try:
                if getattr(self, 'slider_power', None) is not None:
                    # set programmatically without triggering handlers
                    self.slider_power.blockSignals(True)
                    self.slider_power.setValue(int(cfg.get('POWER', '0')))
                    self.slider_power.blockSignals(False)
                    # update displayed numeric label using conversion formula
                    try:
                        valp = int(self.slider_power.value())
                        disp_p = self._power_display_from_slider(valp)
                        self.slider_power_value.setText(str(disp_p))
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                if getattr(self, 'slider_vol', None) is not None:
                    self.slider_vol.blockSignals(True)
                    self.slider_vol.setValue(int(cfg.get('VOLUME', '0')))
                    self.slider_vol.blockSignals(False)
                    try:
                        valv = int(self.slider_vol.value())
                        disp_v = self._volume_display_from_slider(valv)
                        self.slider_vol_value.setText(f"{disp_v:.1f}")
                    except Exception:
                        pass
            except Exception:
                pass

            # update ready label
            self._update_ready_rig_label()
        except Exception:
            pass

    def _write_config(self) -> None:
        """Write current SIGNAL and RIG selection to config path if known."""
        try:
            if not self._config_path:
                return
            p = Path(self._config_path)
            sig = 'Signal' if self.rb_signal.isChecked() else ('Power' if self.rb_power.isChecked() else 'SWR')
            rig = 'rig1' if self.rb_rig1.isChecked() else 'rig2'
            ant = 'Ant 1' if self.rb_ant1.isChecked() else 'Ant 2'
            vfo = 'VFOB' if self.vfo.get_state() else 'VFOA'
            power = str(int(self.slider_power.value())) if getattr(self, 'slider_power', None) else '0'
            volume = str(int(self.slider_vol.value())) if getattr(self, 'slider_vol', None) else '0'
            p.write_text(f"SIGNAL={sig}\nRIG={rig}\nANT={ant}\nVFO={vfo}\nPOWER={power}\nVOLUME={volume}\n")
        except Exception:
            pass

    # Programmatic control methods
    def set_meter(self, value: int) -> None:
        """Set meter value in 0..255."""
        self.meter.set_value(value)

    def set_tr(self, value: int) -> None:
        """Set toggle indicator to 0 (RX) or 1 (TX)."""
        self.tr.set_state(value)

    def set_ready(self, enabled: bool) -> None:
        """Programmatically set the Ready LED and toggle app online/offline behavior.

        When enabled is True the UI is Online: buttons enabled, LEDs show on colors and vumeter is active.
        When False the UI is Offline: buttons disabled, LEDs show off (dim) colors and vumeter shows only off colors.
        """
        try:
            self._online = bool(enabled)
            # update ready LED and label
            if self._online:
                self.ready_led.set_color_on((0, 255, 0))
                self.ready_led.set_on(True)
                self.ready_label.setText("Online")
            else:
                self.ready_led.set_on(False)
                self.ready_label.setText("Offline")

            # enable/disable controls
            self.tr._button.setEnabled(self._online)
            self.tune._button.setEnabled(self._online)
            # enable/disable sliders (Power and Volumen) when offline
            try:
                if getattr(self, 'slider_power', None) is not None:
                    self.slider_power.setEnabled(self._online)
                if getattr(self, 'slider_vol', None) is not None:
                    self.slider_vol.setEnabled(self._online)
            except Exception:
                pass

            # update TR (RX/TX) LED visuals according to mode and online state
            try:
                if self._online:
                    if self.tr.get_state():
                        # TX: vivid red on
                        self.tr._led.set_color_on((255, 0, 0))
                        self.tr._led.set_on(True)
                        self.tr._button.setText("TX")
                    else:
                        # RX: lime on
                        self.tr._led.set_color_on((0, 255, 0))
                        self.tr._led.set_on(True)
                        self.tr._button.setText("RX")
                else:
                    # offline -> force RX state and show dim green off LED
                    try:
                        # set logical state to RX
                        self.tr.set_state(0)
                        # ensure LED shows dim/off green
                        self.tr._led.set_color_off((0, 100, 0))
                        self.tr._led.set_on(False)
                        self.tr._button.setText("RX")
                    except Exception:
                        pass
            except Exception:
                pass

            # update TUNE visuals and VFO/SWAP buttons
            try:
                if self._online:
                    # TUNE
                    self.tune._led.set_color_on((0, 255, 0))
                    self.tune._led.set_on(True)
                    # VFO
                    if self.vfo.get_state():
                        self.vfo._led.set_color_on((255, 0, 0))
                    else:
                        self.vfo._led.set_color_on((0, 255, 0))
                    self.vfo._led.set_on(True)
                    self.vfo._button.setEnabled(True)
                    # SWAP
                    self.swap._led.set_color_on((0, 255, 0))
                    self.swap._led.set_on(True)
                    self.swap._button.setEnabled(True)
                else:
                    # TUNE
                    self.tune._led.set_color_off((0, 100, 0))
                    self.tune._led.set_on(False)
                    # VFO: show dim color based on logical state
                    try:
                        if self.vfo.get_state():
                            self.vfo._led.set_color_off((120, 0, 0))
                        else:
                            self.vfo._led.set_color_off((0, 100, 0))
                    except Exception:
                        # if vfo not present, fall back to neutral
                        self.vfo._led.set_color_off((80, 80, 80))
                    self.vfo._led.set_on(False)
                    self.vfo._button.setEnabled(False)
                    # SWAP
                    self.swap._led.set_color_off((0, 100, 0))
                    self.swap._led.set_on(False)
                    self.swap._button.setEnabled(False)
            except Exception:
                pass

            # enable/disable vumeter rendering
            try:
                self.meter.set_enabled(self._online)
            except Exception:
                pass

        except Exception:
            # ignore if ready widget not present
            pass

    def _on_mode_changed(self, button) -> None:
        """Handler called when one of the mode radio buttons is selected.

        Prints which radio button was selected; can be adapted to perform
        other logic based on the selected mode.
        """
        try:
            name = button.text() if hasattr(button, "text") else str(button)
            print(f"Mode selected: {name}")
        except Exception:
            pass
        # update config file
        try:
            self._write_config()
        except Exception:
            pass

    def _on_rig_changed(self, button) -> None:
        """Handler called when rig1/rig2 radio selection changes."""
        try:
            name = button.text() if hasattr(button, "text") else str(button)
            print(f"Rig selected: {name}")
        except Exception:
            pass
        # update ready-side label
        try:
            self._update_ready_rig_label()
        except Exception:
            pass
        # update config file
        try:
            self._write_config()
        except Exception:
            pass

    def _on_ant_changed(self, button) -> None:
        """Handler called when antenna selection changes."""
        try:
            name = button.text() if hasattr(button, "text") else str(button)
            print(f"Antenna selected: {name}")
        except Exception:
            pass
        # persist selection
        try:
            self._write_config()
        except Exception:
            pass

    def _on_vfo_changed(self, state: int) -> None:
        """Handler invoked when the VFO button is toggled; state is 0 for VFOA, 1 for VFOB."""
        try:
            label = "VFOB" if int(state) else "VFOA"
            print(f"VFO changed: {label}")
        except Exception:
            pass
        # persist VFO state
        try:
            self._write_config()
        except Exception:
            pass

    def _on_power_changed(self, value: int) -> None:
        """Legacy handler kept for compatibility. Use _handle_slider_change instead."""
        try:
            self._handle_slider_change('power', value, self.slider_power)
        except Exception:
            pass

    def _on_volume_changed(self, value: int) -> None:
        """Legacy handler kept for compatibility. Use _handle_slider_change instead."""
        try:
            self._handle_slider_change('volume', value, self.slider_vol)
        except Exception:
            pass

    def _power_display_from_slider(self, s: int) -> int:
        """Convert raw slider S (0..255) to displayed Power value using formula ((95*S/255)+5).
        Returns integer rounded value."""
        try:
            val = (95.0 * float(s) / 255.0) + 5.0
            return int(round(val))
        except Exception:
            return 0

    def _volume_display_from_slider(self, s: int) -> float:
        """Convert raw slider S (0..255) to displayed Volume using formula (10*S/255).
        Returns float rounded to one decimal."""
        try:
            val = 10.0 * float(s) / 255.0
            return round(val, 1)
        except Exception:
            return 0.0

    def _handle_slider_change(self, name: str, value: int, slider_obj) -> None:
        """Unified handler for sliders that updates only the specified control.

        name is 'power' or 'volume', value is new int, slider_obj is the QSlider that produced the event.
        This method strictly updates only the named slider and persists the value.
        """
        try:
            if name == 'power' and slider_obj is self.slider_power:
                disp = self._power_display_from_slider(int(value))
                self.slider_power_value.setText(str(disp))
                print(f"Power level (slider={int(value)}): {disp}")
            elif name == 'volume' and slider_obj is self.slider_vol:
                disp = self._volume_display_from_slider(int(value))
                self.slider_vol_value.setText(f"{disp:.1f}")
                print(f"Volume level (slider={int(value)}): {disp:.1f}")
            else:
                return
        except Exception:
            pass
        # persist only this value (write whole config)
        try:
            self._write_config()
        except Exception:
            pass

    def _on_swap(self) -> None:
        """Handler for swap button press - perform swap action/event."""
        try:
            print("Swap event: exchange VFO A <-> B")
        except Exception:
            pass

    def set_rig_name(self, index: int, name: str) -> None:
        """Set the display name for a rig label (index 1 or 2)."""
        if index == 1:
            self.rig1_name = str(name)
            self.rig1_label.setText(self.rig1_name)
        elif index == 2:
            self.rig2_name = str(name)
            self.rig2_label.setText(self.rig2_name)
        # refresh ready-side label
        try:
            self._update_ready_rig_label()
        except Exception:
            pass

    def _update_ready_rig_label(self) -> None:
        """Update the small label next to Online/Offline showing the selected rig name."""
        try:
            if getattr(self, 'rb_rig1', None) and self.rb_rig1.isChecked():
                name = self.rig1_label.text() if hasattr(self, 'rig1_label') else self.rig1_name
            elif getattr(self, 'rb_rig2', None) and self.rb_rig2.isChecked():
                name = self.rig2_label.text() if hasattr(self, 'rig2_label') else self.rig2_name
            else:
                name = ''
            if name:
                self.ready_rig_label.setText(f"({name})")
            else:
                self.ready_rig_label.setText('')
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    """Entry point for the GUI application."""
    app = QApplication(sys.argv if argv is None else argv)
    win = MainWindow()
    win.show()

    # initial states: meter at 0 and button in RX with green LED
    win.set_meter(0)
    win.set_tr(0)
    win.set_ready(False)

    # test mode: animate meter up/down if --test argument provided
    args = sys.argv[1:] if argv is None else (argv[1:] if len(argv) > 1 else [])
    # handle --config argument and --test
    args = sys.argv[1:] if argv is None else (argv[1:] if len(argv) > 1 else [])
    config_path = None
    for i, a in enumerate(args):
        if a.startswith("--config="):
            config_path = a.split("=", 1)[1]
        elif a == "--config" and i + 1 < len(args):
            config_path = args[i + 1]

    # set default config path if not provided
    if not config_path:
        config_path = "PyMeter.ini"

    # load/create config
    try:
        win.load_config(config_path)
    except Exception:
        pass
    # reapply ready state so controls (VFO/SWAP) reflect Online/Offline after config load
    try:
        win.set_ready(getattr(win, '_online', False))
    except Exception:
        pass

    if "--test" in args:
        step = 3
        val = 0
        direction = 1

        def tick() -> None:
            nonlocal val, direction
            val += step * direction
            if val >= 255:
                val = 255
                direction = -1
            elif val <= 0:
                val = 0
                direction = 1
            # only update display if online
            try:
                if getattr(win, "_online", False):
                    win.set_meter(val)
            except Exception:
                pass

        timer = QTimer()
        timer.timeout.connect(tick)
        timer.start(30)
        # keep a reference so it won't be GC'd
        win._test_timer = timer

        # blink ready LED every 2 seconds
        def blink_ready() -> None:
            try:
                win.set_ready(not win.ready_led.is_on())
            except Exception:
                pass

        ready_timer = QTimer()
        ready_timer.timeout.connect(blink_ready)
        ready_timer.start(5000)
        win._ready_timer = ready_timer

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
