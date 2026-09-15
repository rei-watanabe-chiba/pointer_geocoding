"""
/***************************************************************************
 PointerGeocoding Plugin - UI Style Helper (Material & High DPI Adaptation)
 ***************************************************************************/
"""
from typing import Optional, Tuple, List
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QSpinBox,
    QComboBox,
    QLineEdit,
    QButtonGroup,
    QMessageBox,
)


class UIStyleHelper:
    """Manages Material Design-inspired styling compatible with both QGIS light and dark themes.

    Uses QGIS system palette roles and relative font metrics without hardcoding fixed backgrounds.
    """

    @classmethod
    def get_style_sheet(cls) -> str:
        """Generate a theme-agnostic QSS stylesheet referencing Qt palette roles.

        :return: QSS stylesheet string.
        :rtype: str
        """
        return """
        /* General Widget Typography & Spacing */
        QWidget {
            font-size: 9pt;
        }

        /* Group Boxes - Collapsible and standard */
        QGroupBox, QgsCollapsibleGroupBox {
            font-weight: bold;
            border: none;
            margin-top: 10px;
            padding-top: 14px;
            padding-bottom: 6px;
            padding-left: 6px;
            padding-right: 6px;
        }

        QGroupBox::title, QgsCollapsibleGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 4px;
            color: palette(window-text);
        }

        /* Input Controls - Rounded, padded, base-palette responsive */
        QLineEdit, QgsFilterLineEdit, QComboBox {
            background-color: palette(base);
            color: palette(text);
            border: 1px solid palette(mid);
            border-radius: 4px;
            padding: 0px 8px;
            min-height: 28px;
            selection-background-color: palette(highlight);
            selection-color: palette(highlighted-text);
        }

        QLineEdit:focus, QgsFilterLineEdit:focus, QComboBox:focus {
            border: 1.5px solid palette(highlight);
        }


        /* Default Buttons */
        QPushButton {
            background-color: palette(button);
            color: palette(button-text);
            border: 1px solid palette(mid);
            border-radius: 4px;
            min-height: 28px;
        }

        QPushButton:hover {
            background-color: rgba(128, 128, 128, 0.15);
        }

        QPushButton:pressed {
            background-color: rgba(128, 128, 128, 0.28);
        }

        QPushButton:disabled {
            opacity: 0.5;
            color: palette(disabled-text);
        }

        /* Tab Widget Styling */
        QTabWidget::pane {
            border: 1px solid palette(mid);
            border-radius: 4px;
            top: -1px;
        }

        QTabBar::tab {
            background-color: palette(window);
            color: palette(window-text);
            border: 1px solid palette(mid);
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 14px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background-color: palette(base);
            border-bottom: 2px solid #1976D2;
            font-weight: bold;
        }

        QTabBar::tab:hover:!selected {
            background-color: rgba(128, 128, 128, 0.1);
        }

        /* Banner Labels (Themed with transparency) */
        QLabel[banner="info"] {
            background-color: rgba(2, 136, 209, 0.12);
            border: 1px solid rgba(2, 136, 209, 0.4);
            border-radius: 4px;
            padding: 6px 8px;
            color: palette(window-text);
            font-weight: bold;
        }

        QLabel[banner="success"] {
            background-color: rgba(46, 125, 50, 0.14);
            border: 1px solid rgba(46, 125, 50, 0.45);
            border-radius: 4px;
            padding: 6px 8px;
            color: palette(window-text);
            font-weight: bold;
        }

        QLabel[banner="warning"] {
            background-color: rgba(198, 40, 40, 0.14);
            border: 1px solid rgba(198, 40, 40, 0.45);
            border-radius: 4px;
            padding: 6px 8px;
            color: palette(window-text);
            font-weight: bold;
        }

        /* Status Panel (Flat design container with color-coded left border) */
        QFrame[statusPanel="true"] {
            background-color: rgba(128, 128, 128, 0.08);
            border-left: 3px solid palette(highlight);
            border-radius: 4px;
            border-top-left-radius: 0px;
            border-bottom-left-radius: 0px;
            padding: 6px 8px;
        }

        QFrame[statusType="info"] {
            border-left: 3px solid #1976D2;
            background-color: rgba(25, 118, 210, 0.08);
        }

        QFrame[statusType="success"] {
            border-left: 3px solid #2E7D32;
            background-color: rgba(46, 125, 50, 0.08);
        }

        QFrame[statusType="error"] {
            border-left: 3px solid #C62828;
            background-color: rgba(198, 40, 40, 0.08);
        }

        QFrame[statusType="warning"] {
            border-left: 3px solid #F57C00;
            background-color: rgba(245, 124, 0, 0.08);
        }

        /* Scroll Area without outer ugly borders */
        QScrollArea {
            border: none;
            background: transparent;
        }

        /* Segmented Toggle Container */
        QWidget[segmentedContainer="true"] {
            background-color: rgba(128, 128, 128, 0.15);
            border-radius: 6px;
        }

        /* Segmented Toggle Buttons */
        QPushButton[segmentedButton="true"] {
            background-color: transparent;
            color: palette(text);
            border: none;
            border-radius: 4px;
            min-height: 24px;
        }

        QPushButton[segmentedButton="true"]:hover {
            background-color: rgba(128, 128, 128, 0.1);
        }

        QPushButton[segmentedButton="true"]:checked {
            background-color: palette(base);
            color: palette(text);
            border: 1px solid rgba(0, 0, 0, 0.1);
            font-weight: bold;
        }
        """

    @staticmethod
    def show_error_dialog(parent: Optional[QWidget], title: str, message: str) -> None:
        """Thin wrapper around QMessageBox.critical() to consolidate error dialog presentation.

        :param parent: Parent QWidget for the dialog.
        :type parent: Optional[QWidget]
        :param title: Dialog title text.
        :type title: str
        :param message: Dialog message text.
        :type message: str
        """
        QMessageBox.critical(parent, title, message)

    @staticmethod
    def show_warning_dialog(parent: Optional[QWidget], title: str, message: str) -> None:
        """Thin wrapper around QMessageBox.warning() to consolidate warning dialog presentation.

        :param parent: Parent QWidget for the dialog.
        :type parent: Optional[QWidget]
        :param title: Dialog title text.
        :type title: str
        :param message: Dialog message text.
        :type message: str
        """
        QMessageBox.warning(parent, title, message)

    @classmethod
    def apply_theme(cls, widget: QWidget) -> None:
        """Apply theme-agnostic styling to the target widget and polish its hierarchy.

        :param widget: Target QWidget (e.g. QDialog or QDockWidget).
        :type widget: QWidget
        """
        if widget:
            widget.setStyleSheet(cls.get_style_sheet())

    @staticmethod
    def create_spinbox(
        min_val: int = 0,
        max_val: int = 999999,
        default_val: int = 0,
        parent: Optional[QWidget] = None,
    ) -> QSpinBox:
        """Factory method to create a standardized QSpinBox with native controls.

        :param min_val: Minimum spinbox value.
        :type min_val: int
        :param max_val: Maximum spinbox value.
        :type max_val: int
        :param default_val: Initial spinbox value.
        :type default_val: int
        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        :return: Configured QSpinBox instance.
        :rtype: QSpinBox
        """
        spin = QSpinBox(parent)
        spin.setRange(min_val, max_val)
        spin.setValue(default_val)
        return spin

    @staticmethod
    def create_status_panel(
        text: str = "",
        status_type: str = "info",
        parent: Optional[QWidget] = None,
    ) -> Tuple[QFrame, QLabel]:
        """Create a flat-design status container panel with a color-coded left border.

        :param text: Initial label text.
        :type text: str
        :param status_type: Status category ('info', 'success', 'error', 'warning').
        :type status_type: str
        :param parent: Optional parent widget.
        :type parent: Optional[QWidget]
        :return: Tuple containing (container QFrame, text QLabel).
        :rtype: Tuple[QFrame, QLabel]
        """
        frame = QFrame(parent)
        frame.setProperty("statusPanel", True)
        frame.setProperty("statusType", status_type)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        label = QLabel(text, frame)
        label.setWordWrap(True)
        layout.addWidget(label)

        frame.style().polish(frame)
        return frame, label

    @staticmethod
    def update_status_panel(
        frame: QFrame,
        label: QLabel,
        text: str,
        status_type: str = "info",
    ) -> None:
        """Update text and border status style for an existing status panel container.

        :param frame: Target container QFrame.
        :type frame: QFrame
        :param label: Target text QLabel inside container.
        :type label: QLabel
        :param text: New text to display.
        :type text: str
        :param status_type: Status category ('info', 'success', 'error', 'warning').
        :type status_type: str
        """
        label.setText(text)
        frame.setProperty("statusType", status_type)
        frame.style().unpolish(frame)
        frame.style().polish(frame)

    @staticmethod
    def set_primary_button(button: QPushButton) -> None:
        """Mark a QPushButton as a primary action button."""
        button.setProperty("primary", True)
        button.style().polish(button)

    @staticmethod
    def set_success_button(button: QPushButton) -> None:
        """Mark a QPushButton as a success/save action button."""
        button.setProperty("success", True)
        button.style().polish(button)

    @staticmethod
    def set_accent_button(button: QPushButton) -> None:
        """Mark a QPushButton as an accent/export action button."""
        button.setProperty("accent", True)
        button.style().polish(button)

    @staticmethod
    def set_banner_status(label: QLabel, status: str) -> None:
        """Set dynamic status property on a banner QLabel ('info', 'success', 'warning').

        :param label: Target QLabel.
        :param status: Status string ('info', 'success', 'warning').
        """
        label.setProperty("banner", status)
        label.style().polish(label)

    @staticmethod
    def set_status_panel(frame: QWidget) -> None:
        """Mark a QFrame as a status panel."""
        frame.setProperty("statusPanel", True)
        frame.style().polish(frame)

    @staticmethod
    def build_flex_row(
        main_label: Optional[QLabel],
        child_configs: list,
        main_ratio: Tuple[int, int] = (2, 8),
        row_height: int = 32,
    ) -> QWidget:
        """Build a standardized flexbox-style horizontal row widget with a main label and element container.

        :param main_label: Left-side label widget (can be None).
        :type main_label: Optional[QLabel]
        :param child_configs: List of tuples (widget or None, stretch_ratio) for up to 3 elements.
        :type child_configs: list
        :param main_ratio: Stretch ratio between main_label and element container. Default is (2, 8).
        :type main_ratio: Tuple[int, int]
        :param row_height: Fixed height for the row widget. Default is 32.
        :type row_height: int
        :return: Composite QWidget containing the row layout.
        :rtype: QWidget
        """
        row_widget = QWidget()
        row_widget.setMinimumHeight(row_height)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label_stretch, content_stretch = main_ratio
        if main_label is not None:
            row_layout.addWidget(main_label, label_stretch)
        else:
            row_layout.addStretch(label_stretch)

        content_widget = QWidget(row_widget)
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        for item in child_configs[:3]:
            widget, stretch = item
            if widget is not None:
                content_layout.addWidget(widget, stretch)
            else:
                content_layout.addStretch(stretch)

        row_layout.addWidget(content_widget, content_stretch)
        return row_widget

    @staticmethod
    def build_child_container(
        sub_label: Optional[QLabel],
        input_widget: QWidget,
    ) -> QWidget:
        """Build a sub-container pairing a sub-label with an input widget.

        :param sub_label: Sub-label displayed before the input widget.
        :type sub_label: Optional[QLabel]
        :param input_widget: Target input widget.
        :type input_widget: QWidget
        :return: Container QWidget holding the label and input.
        :rtype: QWidget
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        if sub_label is not None:
            layout.addWidget(sub_label, 0)
        layout.addWidget(input_widget, 1)

        return container

    @staticmethod
    def build_segmented_toggle(
        options: List[str], default_index: int = 0, parent: Optional[QWidget] = None
    ) -> Tuple[QWidget, List[QPushButton]]:
        """Build an iOS-style segmented toggle button group.
        
        :param options: List of string labels for the buttons.
        :type options: List[str]
        :param default_index: The index of the button to check initially. Default is 0.
        :type default_index: int
        :param parent: Optional parent widget.
        :type parent: Optional[QWidget]
        :return: Tuple containing the container QWidget and the list of QPushButton objects.
        :rtype: Tuple[QWidget, List[QPushButton]]
        """
        container = QWidget(parent)
        container.setProperty("segmentedContainer", True)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        button_group = QButtonGroup(container)
        button_group.setExclusive(True)
        
        buttons = []
        for i, option in enumerate(options):
            btn = QPushButton(option, container)
            btn.setProperty("segmentedButton", True)
            btn.setCheckable(True)
            btn.setSizePolicy(btn.sizePolicy().Policy.Expanding, btn.sizePolicy().Policy.Preferred)
            button_group.addButton(btn, i)
            layout.addWidget(btn)
            buttons.append(btn)
            
        if 0 <= default_index < len(buttons):
            buttons[default_index].setChecked(True)
            
        # Retain reference to button_group to prevent garbage collection
        container._button_group = button_group
        container.style().polish(container)
        
        return container, buttons

