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

from PyQt5.QtCore import Qt, QSize, QTimer, QEvent
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
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
        self.setMinimumSize(QSize(120, 40))
        # precompute band mapping: first 5 green, next 3 yellow, last 2 red
        # this allows precise control over colors per LED
        self._bands = (['green'] * 5) + (['yellow'] * 3) + (['red'] * 2)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

    def sizeHint(self) -> QSize:  # pragma: no cover - GUI helper
        return QSize(200, 60)

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
        seg_w = max(6, (available_w - (self._segments - 1) * gap) / self._segments)
        led_h = max(6, min(14, h - 2 * margin))
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


class MainWindow(QMainWindow):
    """Main application window composing the VU meter and TX/RX controls."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyMeter - VU Meter with TX/RX LEDs")
        central = QWidget()
        self.setCentralWidget(central)

        self.meter = VUMeter(segments=10)
        # single toggle button starting in RX state (0)
        self.tr = LedButton("RX")
        # TUNE button below it
        self.tune = TuneButton("TUNE")

        # Ready label + LED placed above the meter
        ready_row = QHBoxLayout()
        # make spacing minimal so the LED sits very close to the text
        ready_row.setSpacing(0)
        ready_row.setContentsMargins(0, 0, 0, 0)
        self.ready_label = QLabel("Offline")
        # remove extra label padding/margins so LED can sit next to the text
        self.ready_label.setStyleSheet("font-weight: bold; margin: 0px; padding-right: 0px;")
        # make ready LED slightly smaller to sit closer to the text
        self.ready_led = LedIndicator(diameter=6)
        # ready: on color lime, off color dark green, start off
        self.ready_led.set_color_on((0, 255, 0))
        self.ready_led.set_color_off((0, 100, 0))
        self.ready_led.set_on(False)
        ready_row.addWidget(self.ready_label)
        ready_row.addWidget(self.ready_led)
        ready_row.setAlignment(self.ready_label, Qt.AlignVCenter)
        ready_row.setAlignment(self.ready_led, Qt.AlignVCenter)

        # Layout
        # Create a grid so corresponding rows align vertically across columns
        from PyQt5.QtWidgets import QGridLayout

        grid = QGridLayout(central)
        grid.setContentsMargins(12, 4, 12, 4)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        # row 0: ready label+led (left) and TR button (right)
        grid.addLayout(ready_row, 0, 0)
        grid.addWidget(self.tr, 0, 1, Qt.AlignVCenter)
        # row 1: meter (left) and tune button (right)
        grid.addWidget(self.meter, 1, 0)
        grid.addWidget(self.tune, 1, 1, Qt.AlignVCenter)
        # ensure meter row expands
        grid.setRowStretch(1, 1)

        main_layout = grid
        # Example: connect button click to print state
        self.tr._button.clicked.connect(lambda: print(f"TR state: {self.tr.get_state()}"))
  
        self.resize(360, 100)

    # Programmatic control methods
    def set_meter(self, value: int) -> None:
        """Set meter value in 0..255."""
        self.meter.set_value(value)

    def set_tr(self, value: int) -> None:
        """Set toggle indicator to 0 (RX) or 1 (TX)."""
        self.tr.set_state(value)

    def set_ready(self, enabled: bool) -> None:
        """Programmatically set the Ready LED: True -> lime on (Online), False -> dark green off (Offline)."""
        try:
            if enabled:
                self.ready_led.set_color_on((0, 255, 0))
                self.ready_led.set_on(True)
                self.ready_label.setText("Online")
            else:
                # off uses the dark green off color defined earlier
                self.ready_led.set_on(False)
                self.ready_label.setText("Offline")
        except Exception:
            # ignore if ready widget not present
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
            win.set_meter(val)

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
        ready_timer.start(2000)
        win._ready_timer = ready_timer

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
