APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e24;
    color: #e6e6e6;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
}

QTabWidget::pane {
    border: 1px solid #33333d;
    background-color: #23232b;
    border-radius: 6px;
}

QTabBar::tab {
    background: #2b2b36;
    color: #a0a0b0;
    padding: 10px 24px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #383848;
    color: #ffffff;
    border-bottom: 2px solid #4daafc;
}

QTabBar::tab:hover {
    background: #333342;
    color: #ffffff;
}

QGroupBox {
    border: 1px solid #383848;
    border-radius: 8px;
    margin-top: 18px;
    padding: 16px;
    font-weight: 600;
    color: #b0b0c0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}

QPushButton {
    background-color: #3b3b4d;
    color: #ffffff;
    border: 1px solid #4a4a60;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #4a4a62;
    border-color: #5c5c78;
}

QPushButton:pressed {
    background-color: #2e2e3d;
}

QPushButton:disabled {
    background-color: #262630;
    color: #606070;
    border-color: #333340;
}

QPushButton#btn_record_start {
    background-color: #2e7d32;
    border-color: #388e3c;
    font-size: 16px;
    padding: 12px 24px;
}

QPushButton#btn_record_start:hover {
    background-color: #388e3c;
}

QPushButton#btn_record_stop {
    background-color: #c62828;
    border-color: #d32f2f;
    font-size: 16px;
    padding: 12px 24px;
}

QPushButton#btn_record_stop:hover {
    background-color: #d32f2f;
}

QPushButton#btn_alarm_stop {
    background-color: #e65100;
    border-color: #f57c00;
    font-size: 15px;
    font-weight: 700;
    animation: blink 1s;
}

QPushButton#btn_peek {
    background-color: #313142;
    border: 1px dashed #666680;
    color: #c0c0d8;
}

QPushButton#btn_peek:pressed {
    background-color: #454560;
    border-style: solid;
    color: #ffffff;
}

QLabel#timer_display {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 44px;
    font-weight: 700;
    color: #00e676;
    background-color: #16161b;
    border: 1px solid #2d2d38;
    border-radius: 8px;
    padding: 8px 16px;
    qproperty-alignment: AlignCenter;
}

QLabel#phone_timer_display {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 44px;
    font-weight: 700;
    color: #ffb74d;
    background-color: #16161b;
    border: 1px solid #2d2d38;
    border-radius: 8px;
    padding: 8px 16px;
    qproperty-alignment: AlignCenter;
}

QLabel#timer_display_hidden {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 38px;
    font-weight: 700;
    color: #616170;
    background-color: #141418;
    border: 1px dashed #30303c;
    border-radius: 8px;
    padding: 12px 16px;
    qproperty-alignment: AlignCenter;
}

QSlider::groove:horizontal {
    border: 1px solid #333342;
    height: 6px;
    background: #2a2a36;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #4daafc;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #4daafc;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #e0f0ff;
}

QComboBox, QSpinBox, QLineEdit {
    background-color: #2a2a36;
    border: 1px solid #3c3c4e;
    border-radius: 5px;
    padding: 6px 12px;
    color: #ffffff;
}

QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
    border-color: #55556e;
}

QComboBox::drop-down {
    border: 0px;
}

QScrollBar:vertical {
    border: none;
    background: #1e1e24;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3b3b4a;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #505064;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

DIFF_STYLES = {
    "similar": "background-color: #1b3820; border: 1px solid #2e7d32; border-radius: 6px; padding: 10px;",
    "moderate": "background-color: #2b2b36; border: 1px solid #3e3e50; border-radius: 6px; padding: 10px;",
    "different": "background-color: #3b1e22; border: 1px solid #c62828; border-radius: 6px; padding: 10px;",
    "missing": "background-color: #24242e; border: 1px dashed #48485a; border-radius: 6px; padding: 10px; color: #707080;",
}

PAUSE_BADGE_STYLE = (
    "background-color: #2e2619; color: #ffb74d; border: 1px solid #8c631e; "
    "border-radius: 4px; padding: 4px 8px; font-size: 12px; font-weight: 600;"
)

SPEECH_CARD_STYLE = (
    "background-color: #262632; border: 1px solid #38384a; border-radius: 6px; "
    "padding: 12px; margin-bottom: 8px;"
)

KPI_CARD_STYLE = (
    "background-color: #23232d; border: 1px solid #333342; border-radius: 8px; "
    "padding: 10px 8px; min-width: 80px;"
)

PHONE_TIMER_CARD_STYLE = (
    "background-color: #241c30; border: 1px solid #7e57c2; border-radius: 6px; "
    "padding: 8px 14px;"
)
