"""
/***************************************************************************
 PointerGeocoding Plugin - Tab 3 (Settings) Mixin
 ***************************************************************************/

Stage B split (mechanical, logic-preserving): extracted from main_dock.py.
Provides Tab3SettingsMixin, mixed into MainDockWidget, containing UI
construction and event handlers for Tab 3 (display & symbol settings).
"""

from typing import Optional, Dict, Any, Tuple

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QFrame,
    QSpinBox,
    QDoubleSpinBox,
    QColorDialog,
)

from .style_helper import UIStyleHelper
from .main_dock_constants import UIConfig, UILabels


class Tab3SettingsMixin:
    """Mixin providing Tab 3 (Display & Symbol Settings) behavior for MainDockWidget."""

    # ───────────────────────────────────────────────────────────────────────────
    # Tab 3: Settings
    # ───────────────────────────────────────────────────────────────────────────

    def _create_tab3_ui(self) -> QWidget:
        """Construct Tab 3: Display & Symbol Settings."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        def _create_color_button(color_hex: str, handler) -> QPushButton:
            btn = QPushButton("")
            btn.setStyleSheet(f"background-color: {color_hex}; color: white; border-radius: 4px;")
            btn.clicked.connect(handler)
            return btn

        # ── Section: 基準点 ─────────────────────────────────────────────
        layout.addWidget(UIStyleHelper.build_section_header(UILabels.TAB3_SECTION_REF_SYMBOL))

        self.spin_ref_sym_size = QDoubleSpinBox()
        self.spin_ref_sym_size.setRange(0.5, 20.0)
        self.spin_ref_sym_size.setSingleStep(0.5)
        self.spin_ref_sym_size.setValue(4.0)

        self.spin_ref_sym_linewidth = QDoubleSpinBox()
        self.spin_ref_sym_linewidth.setRange(0.1, 5.0)
        self.spin_ref_sym_linewidth.setSingleStep(0.1)
        self.spin_ref_sym_linewidth.setValue(1.2)

        ref_row1 = QHBoxLayout()
        ref_row1.addWidget(UIStyleHelper.build_form_row(UILabels.TAB3_LBL_SIZE, self.spin_ref_sym_size), 1)
        ref_row1.addWidget(UIStyleHelper.build_form_row(UILabels.TAB3_LBL_LINEWIDTH, self.spin_ref_sym_linewidth), 1)
        ref_row1.addStretch(1)
        layout.addLayout(ref_row1)

        self._settings_ref_line_color = "#D32F2F"
        self.btn_ref_line_color = _create_color_button(
            self._settings_ref_line_color,
            lambda: self._on_color_pick("ref_line")
        )

        ref_row2 = QHBoxLayout()
        ref_row2.addWidget(UIStyleHelper.build_form_row(UILabels.TAB3_LBL_LINECOLOR, self.btn_ref_line_color), 1)
        ref_row2.addStretch(2)
        layout.addLayout(ref_row2)

        # ── Section: 遺物点 ─────────────────────────────────────────────
        layout.addWidget(UIStyleHelper.build_section_header(UILabels.TAB3_SECTION_POINT_SYMBOL))

        self.spin_point_sym_size = QDoubleSpinBox()
        self.spin_point_sym_size.setRange(0.5, 20.0)
        self.spin_point_sym_size.setSingleStep(0.5)
        self.spin_point_sym_size.setValue(6.0)

        self.spin_point_sym_linewidth = QDoubleSpinBox()
        self.spin_point_sym_linewidth.setRange(0.1, 5.0)
        self.spin_point_sym_linewidth.setSingleStep(0.1)
        self.spin_point_sym_linewidth.setValue(0.9)

        point_row1 = QHBoxLayout()
        point_row1.addWidget(UIStyleHelper.build_form_row(UILabels.TAB3_LBL_SIZE, self.spin_point_sym_size), 1)
        point_row1.addWidget(UIStyleHelper.build_form_row(UILabels.TAB3_LBL_LINEWIDTH, self.spin_point_sym_linewidth), 1)
        point_row1.addStretch(1)
        layout.addLayout(point_row1)

        self._settings_point_line_color = "#E53935"
        self.btn_point_line_color = _create_color_button(
            self._settings_point_line_color,
            lambda: self._on_color_pick("point_line")
        )

        point_fill_widget = QWidget()
        point_fill_layout = QHBoxLayout(point_fill_widget)
        point_fill_layout.setContentsMargins(0, 0, 0, 0)
        self.radio_point_fill_on  = QRadioButton(UILabels.TAB3_POINT_FILL_ON)
        self.radio_point_fill_off = QRadioButton(UILabels.TAB3_POINT_FILL_OFF)
        self.radio_point_fill_off.setChecked(True)
        point_fill_layout.addWidget(self.radio_point_fill_on)
        point_fill_layout.addWidget(self.radio_point_fill_off)

        point_row2 = QHBoxLayout()
        point_row2.addWidget(UIStyleHelper.build_form_row(UILabels.TAB3_LBL_LINECOLOR, self.btn_point_line_color), 1)
        point_row2.addWidget(point_fill_widget, 2)
        layout.addLayout(point_row2)

        # ── Section: ラベル ──────────────────────────────────────────────
        layout.addWidget(UIStyleHelper.build_section_header(UILabels.TAB3_SECTION_LABEL_SYMBOL))

        self.spin_lbl_size = QSpinBox()
        self.spin_lbl_size.setRange(6, 36)
        self.spin_lbl_size.setValue(UIConfig.LABEL_SIZE_REF)

        self.spin_lbl_offset = QDoubleSpinBox()
        self.spin_lbl_offset.setRange(0.0, 20.0)
        self.spin_lbl_offset.setSingleStep(0.5)
        self.spin_lbl_offset.setValue(1.0)

        lbl_row1 = QHBoxLayout()
        lbl_row1.addWidget(UIStyleHelper.build_form_row(UILabels.TAB3_LBL_SIZE, self.spin_lbl_size), 1)
        lbl_row1.addWidget(UIStyleHelper.build_form_row(UILabels.TAB3_LABEL_OFFSET, self.spin_lbl_offset), 1)
        lbl_row1.addStretch(1)
        layout.addLayout(lbl_row1)

        halo_widget = QWidget()
        halo_layout = QHBoxLayout(halo_widget)
        halo_layout.setContentsMargins(0, 0, 0, 0)
        self.radio_halo_on  = QRadioButton(UILabels.TAB3_LABEL_HALO_ON)
        self.radio_halo_off = QRadioButton(UILabels.TAB3_LABEL_HALO_OFF)
        self.radio_halo_on.setChecked(True)
        halo_layout.addWidget(self.radio_halo_on)
        halo_layout.addWidget(self.radio_halo_off)

        lbl_row2 = QHBoxLayout()
        lbl_row2.addWidget(halo_widget, 2)
        lbl_row2.addStretch(1)
        layout.addLayout(lbl_row2)

        # ── Section: 表示縮尺 ────────────────────────────────────────────
        layout.addWidget(UIStyleHelper.build_section_header(UILabels.TAB3_SECTION_SCALE))

        def _make_scale_controls(
            label_text: str, default_always: bool, default_scale: int
        ) -> Tuple[QWidget, QRadioButton, QRadioButton, QSpinBox]:
            """Build radio buttons widget and spinbox for grid scale settings."""
            radio_always  = QRadioButton(UILabels.TAB3_SCALE_ALWAYS)
            radio_specify = QRadioButton(UILabels.TAB3_SCALE_SPECIFY)
            spin = QSpinBox()
            spin.setRange(1, 99999)
            spin.setValue(default_scale)
            spin.setEnabled(not default_always)
            radio_always.setChecked(default_always)
            radio_specify.setChecked(not default_always)
            radio_always.toggled.connect(lambda chk: spin.setEnabled(not chk))

            radio_widget = QWidget()
            radio_layout = QHBoxLayout(radio_widget)
            radio_layout.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label_text)
            radio_layout.addWidget(lbl)
            radio_layout.addWidget(radio_always)
            radio_layout.addWidget(radio_specify)

            return radio_widget, radio_always, radio_specify, spin

        major_radio_w, self.radio_major_always, self.radio_major_specify, self.spin_major_scale = (
            _make_scale_controls(UILabels.TAB3_SCALE_MAJOR, True, 500)
        )
        scale_row1 = QHBoxLayout()
        scale_row1.addWidget(major_radio_w, 2)
        scale_row1.addWidget(self.spin_major_scale, 1)
        layout.addLayout(scale_row1)

        minor_radio_w, self.radio_minor_always, self.radio_minor_specify, self.spin_minor_scale = (
            _make_scale_controls(UILabels.TAB3_SCALE_MINOR, False, UIConfig.SCALE_THRESHOLD)
        )
        scale_row2 = QHBoxLayout()
        scale_row2.addWidget(minor_radio_w, 2)
        scale_row2.addWidget(self.spin_minor_scale, 1)
        layout.addLayout(scale_row2)

        # ── Apply button ─────────────────────────────────────────────────
        self.btn_settings_apply = QPushButton(UILabels.TAB3_BTN_APPLY, container)
        UIStyleHelper.set_primary_button(self.btn_settings_apply)
        self.btn_settings_apply.clicked.connect(self._on_settings_apply_clicked)
        layout.addWidget(self.btn_settings_apply)

        layout.addStretch()
        scroll.setWidget(container)

        return scroll

    def _on_color_pick(self, target: str) -> None:
        """Unified color picker handler."""
        current_color_hex = ""
        btn_ref = None

        if target == "ref_line":
            current_color_hex = self._settings_ref_line_color
            btn_ref = self.btn_ref_line_color
        elif target == "point_line":
            current_color_hex = self._settings_point_line_color
            btn_ref = self.btn_point_line_color

        if not current_color_hex or current_color_hex == "transparent":
            current_color_hex = "#FFFFFF"

        color = QColorDialog.getColor(QColor(current_color_hex), self, UILabels.TAB3_BTN_COLOR)
        if color.isValid():
            new_color = color.name()
            if target == "ref_line":
                self._settings_ref_line_color = new_color
            elif target == "point_line":
                self._settings_point_line_color = new_color

            if btn_ref:
                btn_ref.setStyleSheet(f"background-color: {new_color}; color: white; border-radius: 4px;")

    def update_settings_ui_from_dict(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Update Tab 3 setting widgets from loaded settings dictionary."""
        if settings is None:
            if self.layer_manager and hasattr(self.layer_manager, "load_settings"):
                settings = self.layer_manager.load_settings()
            else:
                return

        ref_size = float(settings.get("ref_symbol_size", 4.0))
        ref_lw   = float(settings.get("ref_symbol_line_width", 1.2))
        ref_line = str(settings.get("ref_symbol_line_color", settings.get("ref_symbol_color", "#D32F2F")))

        pt_size  = float(settings.get("point_symbol_size", 6.0))
        pt_lw    = float(settings.get("point_symbol_line_width", 0.9))
        pt_fill_enabled = bool(settings.get("point_symbol_fill_enabled", False))
        pt_line  = str(settings.get("point_symbol_line_color", settings.get("point_symbol_color", "#E53935")))

        lbl_sz   = int(settings.get("label_size", UIConfig.LABEL_SIZE_REF))
        lbl_halo = bool(settings.get("label_halo", True))
        lbl_off  = float(settings.get("label_offset", 1.0))

        sc_maj   = int(settings.get("scale_major_grid", -1))
        sc_min   = int(settings.get("scale_minor_grid", UIConfig.SCALE_THRESHOLD))

        if hasattr(self, "spin_ref_sym_size"):
            self.spin_ref_sym_size.setValue(ref_size)
        if hasattr(self, "spin_ref_sym_linewidth"):
            self.spin_ref_sym_linewidth.setValue(ref_lw)
        if hasattr(self, "btn_ref_line_color"):
            self._settings_ref_line_color = ref_line
            self.btn_ref_line_color.setStyleSheet(f"background-color: {ref_line}; color: white; border-radius: 4px;")

        if hasattr(self, "spin_point_sym_size"):
            self.spin_point_sym_size.setValue(pt_size)
        if hasattr(self, "spin_point_sym_linewidth"):
            self.spin_point_sym_linewidth.setValue(pt_lw)
        if hasattr(self, "btn_point_line_color"):
            self._settings_point_line_color = pt_line
            self.btn_point_line_color.setStyleSheet(f"background-color: {pt_line}; color: white; border-radius: 4px;")
        if hasattr(self, "radio_point_fill_on") and hasattr(self, "radio_point_fill_off"):
            self.radio_point_fill_on.setChecked(pt_fill_enabled)
            self.radio_point_fill_off.setChecked(not pt_fill_enabled)

        if hasattr(self, "spin_lbl_size"):
            self.spin_lbl_size.setValue(lbl_sz)
        if hasattr(self, "radio_halo_on") and hasattr(self, "radio_halo_off"):
            self.radio_halo_on.setChecked(lbl_halo)
            self.radio_halo_off.setChecked(not lbl_halo)
        if hasattr(self, "spin_lbl_offset"):
            self.spin_lbl_offset.setValue(lbl_off)

        if hasattr(self, "radio_major_always") and hasattr(self, "radio_major_specify"):
            if sc_maj <= 0:
                self.radio_major_always.setChecked(True)
            else:
                self.radio_major_specify.setChecked(True)
                self.spin_major_scale.setValue(sc_maj)

        if hasattr(self, "radio_minor_always") and hasattr(self, "radio_minor_specify"):
            if sc_min <= 0:
                self.radio_minor_always.setChecked(True)
            else:
                self.radio_minor_specify.setChecked(True)
                self.spin_minor_scale.setValue(sc_min)

    def _on_settings_apply_clicked(self) -> None:
        """Collect UI values and persist them to settings.json.

        Step3-B: symbology re-application and canvas refresh no longer happen
        here directly — they are handled by _on_layer_manager_settings_changed,
        which is connected to LayerManager.settings_changed and fires once
        save_settings() actually persists the change.
        """
        if not self.layer_manager or not self.layer_manager.session_dir:
            return

        # Gather values from UI
        scale_major = -1 if self.radio_major_always.isChecked() else self.spin_major_scale.value()
        scale_minor = -1 if self.radio_minor_always.isChecked() else self.spin_minor_scale.value()

        new_settings = {
            "ref_symbol_size":           self.spin_ref_sym_size.value(),
            "ref_symbol_line_width":     self.spin_ref_sym_linewidth.value(),
            "ref_symbol_line_color":     self._settings_ref_line_color,
            "point_symbol_size":         self.spin_point_sym_size.value(),
            "point_symbol_line_width":   self.spin_point_sym_linewidth.value(),
            "point_symbol_fill_enabled": self.radio_point_fill_on.isChecked(),
            "point_symbol_line_color":   self._settings_point_line_color,
            "label_size":                self.spin_lbl_size.value(),
            "label_halo":                self.radio_halo_on.isChecked(),
            "label_offset":              self.spin_lbl_offset.value(),
            "scale_major_grid":          scale_major,
            "scale_minor_grid":          scale_minor,
        }

        # Persist (LayerManager.save_settings emits settings_changed on success,
        # which triggers _on_layer_manager_settings_changed below)
        self.layer_manager.ensure_json_dir()
        self.layer_manager.save_settings(new_settings)

    def _on_layer_manager_settings_changed(self, new_settings: dict) -> None:
        """Re-apply symbology and refresh the canvas after settings are persisted.

        Connected to LayerManager.settings_changed (Step3-B). Consolidates logic
        that previously ran inline at the end of _on_settings_apply_clicked.

        :param new_settings: The settings dict that was just saved.
        :type new_settings: dict
        """
        # Re-apply ref_points symbology
        ref_layer = self.layer_manager.ref_point_layer
        if ref_layer and ref_layer.isValid():
            self.layer_manager.apply_ref_point_symbology(ref_layer, new_settings)

        # Re-apply point layer symbology (grid color + symbol size + line width)
        # T-0017: symbology construction moved from CanvasDigitizingTool
        # (map_tool.py) to SymbologyMixin.apply_point_symbology, reached via
        # self.layer_manager for consistency with apply_ref_point_symbology above.
        point_layer = self.layer_manager.point_layer
        if point_layer and point_layer.isValid():
            self.layer_manager.apply_point_symbology(point_layer, new_settings)

        # Refresh canvas
        if hasattr(self, "canvas") and self.canvas:
            self.canvas.refresh()

