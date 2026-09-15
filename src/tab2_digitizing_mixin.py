"""
/***************************************************************************
 PointerGeocoding Plugin - Tab 2 (Digitizing) Mixin
 ***************************************************************************/

Stage B split (mechanical, logic-preserving): extracted from main_dock.py.
Provides Tab2DigitizingMixin, mixed into MainDockWidget, containing all UI
construction and event handlers for Tab 2 (Master Focus Mode, continuous
artifact point digitizing, existing point editing/deletion, and CSV
export).
"""

import os
from typing import Dict, Any, List, Tuple

from qgis.core import (
    QgsProject,
    QgsPointXY,
    Qgis,
)
from qgis.gui import (
    QgsFilterLineEdit,
    QgsCollapsibleGroupBox,
)
from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QLabel,
    QPushButton,
    QComboBox,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QColorDialog,
    QFrame,
    QSlider,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
)

# T-0022: SP属性専用の点名QLineEditで使用する入力バリデータ。
# PyQt5/PyQt6両対応パターンは start_dialog.py (L31-38付近) を踏襲する。
try:
    from qgis.PyQt.QtGui import QRegularExpressionValidator
    from qgis.PyQt.QtCore import QRegularExpression
    HAS_QT_REGEX = True
except ImportError:
    from qgis.PyQt.QtGui import QRegExpValidator
    from qgis.PyQt.QtCore import QRegExp
    HAS_QT_REGEX = False

from .transform import export_points_to_csv
from .style_helper import UIStyleHelper
from .core_logic import (
    check_point_duplicate,
    get_next_point_number,
    get_next_point_id,
    build_digitized_feature,
    insert_feature_to_layer,
    pixel_from_affine,
    safe_get_str,
    ExcavationType,
    AttributeType,
)
from .main_dock_constants import (
    UIConfig,
    UILabels,
    UIPlaceholders,
    UIDialogTitles,
    UIMessages,
    MAIN_RATIO,
)


class Tab2DigitizingMixin:
    """Mixin providing Tab 2 (Master Focus Mode, Digitizing & CSV Export) behavior for MainDockWidget."""

    def _create_tab2_ui(self) -> QWidget:
        """Construct Tab 2: Master Focus Mode, Continuous Artifact Digitizing & CSV Export."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 16, 4)
        layout.setSpacing(8)

        # Status Panel (Flat design container with dynamic left border)
        # [EXCEPTION PROTECTION: Flat status panel preserved]
        self.panel_edit_status, self.lbl_edit_status = UIStyleHelper.create_status_panel(
            UILabels.EDIT_STATUS_INIT,
            status_type="info",
            parent=container,
        )
        edit_layout = self.panel_edit_status.layout()

        status_btn_layout = QHBoxLayout()
        self.btn_reset_selection = QPushButton(UILabels.BTN_RESET_SELECTION, self.panel_edit_status)
        self.btn_reset_selection.clicked.connect(self._reset_point_selection)

        self.btn_delete_point = QPushButton(UILabels.BTN_DELETE_POINT, self.panel_edit_status)
        self.btn_delete_point.clicked.connect(self._on_delete_selected_point)
        self.btn_delete_point.setEnabled(False)

        status_btn_layout.addWidget(self.btn_reset_selection)
        status_btn_layout.addWidget(self.btn_delete_point)
        status_btn_layout.addStretch()
        edit_layout.addLayout(status_btn_layout)

        layout.addWidget(self.panel_edit_status)

        # =============================================================
        # Section 1: Master Control Panel: Focus Mode & Drawing Multi-Selector
        # =============================================================
        self.group_focus = QgsCollapsibleGroupBox(UILabels.GROUP_FOCUS, container)
        focus_layout = QVBoxLayout(self.group_focus)
        focus_layout.setSpacing(6)

        # Row 1: Focus Mode ON/OFF Toggle Button
        self.btn_focus_mode = QPushButton(UILabels.BTN_FOCUS_OFF, self.group_focus)
        self.btn_focus_mode.setCheckable(True)
        self.btn_focus_mode.toggled.connect(self._on_focus_mode_toggled)
        focus_layout.addWidget(self.btn_focus_mode)

        # Row 2: Unselected Opacity Slider (0 - 100%)
        self.lbl_opacity = QLabel(UILabels.OPACITY_LABEL, self.group_focus)
        self.slider_opacity = QSlider(Qt.Horizontal, self.group_focus)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(20)
        self.slider_opacity.setSingleStep(5)
        self.lbl_opacity_val = QLabel("20%", self.group_focus)
        self.lbl_opacity_val.setMinimumWidth(36)
        self.lbl_opacity_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.slider_opacity.valueChanged.connect(self._on_slider_value_changed)
        self.slider_opacity.sliderReleased.connect(self._on_slider_released)

        row_opacity = UIStyleHelper.build_flex_row(
            self.lbl_opacity,
            [(self.slider_opacity, 3), (self.lbl_opacity_val, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        focus_layout.addWidget(row_opacity)

        # Row 3: Drawing Visibility Multi-Selector (図面表示マルチセレクタ)
        self.lbl_drawing_visibility = QLabel("図面表示切替 (マルチ選択):", self.group_focus)
        self.lbl_drawing_visibility.setStyleSheet("font-weight: bold; font-size: 8.5pt;")
        focus_layout.addWidget(self.lbl_drawing_visibility)

        self.list_drawing_visibility = QListWidget(self.group_focus)
        self.list_drawing_visibility.setMaximumHeight(90)
        self.list_drawing_visibility.itemChanged.connect(self._on_drawing_visibility_item_changed)
        focus_layout.addWidget(self.list_drawing_visibility)

        layout.addWidget(self.group_focus)

        # =============================================================
        # Section 2: Input Category Panel (Focus Target)
        # =============================================================
        self.group_category = QgsCollapsibleGroupBox(UILabels.GROUP_CATEGORY, container)
        cat_layout = QVBoxLayout(self.group_category)
        cat_layout.setSpacing(6)

        # Row 1: Target Drawing (対象図面)
        self.lbl_drawing_name = QLabel(UILabels.DRAWING_NAME, self.group_category)
        self.combo_drawing_name = QComboBox(self.group_category)
        self.combo_drawing_name.currentIndexChanged.connect(self._on_category_changed)
        row_drawing = UIStyleHelper.build_flex_row(
            self.lbl_drawing_name,
            [(self.combo_drawing_name, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        cat_layout.addWidget(row_drawing)

        # Row 2: Excavation Type (出土形態)
        self.lbl_excavation_type = QLabel(UILabels.EXCAVATION_TYPE, self.group_category)
        self.combo_excavation_type = QComboBox(self.group_category)
        self.combo_excavation_type.addItems(UILabels.EXCAVATION_OPTIONS)
        self.combo_excavation_type.currentIndexChanged.connect(self._on_excavation_type_changed)

        row_excavation = UIStyleHelper.build_flex_row(
            self.lbl_excavation_type,
            [(self.combo_excavation_type, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        cat_layout.addWidget(row_excavation)

        # Row 3: Feature Selector (遺構名セレクタ - 遺構選択時のみ表示)
        self.lbl_feature_selector = QLabel(UILabels.FEATURE_SELECTOR, self.group_category)
        self.combo_feature_name = QComboBox(self.group_category)
        self.combo_feature_name.addItem(UILabels.FEATURE_NEW_OPTION)
        self.combo_feature_name.currentTextChanged.connect(self._on_feature_combo_changed)

        self.row_feature_selector = UIStyleHelper.build_flex_row(
            self.lbl_feature_selector,
            [(self.combo_feature_name, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        cat_layout.addWidget(self.row_feature_selector)

        # Row 4: New Feature Name (新規遺構名入力)
        self.lbl_new_feature = QLabel(UILabels.NEW_FEATURE_NAME, self.group_category)
        self.edit_new_feature = QgsFilterLineEdit(self.group_category)
        self.edit_new_feature.setShowClearButton(True)
        self.edit_new_feature.setPlaceholderText(UIPlaceholders.NEW_FEATURE)
        self.edit_new_feature.textChanged.connect(self._on_new_feature_text_changed)

        self.row_new_feature = UIStyleHelper.build_flex_row(
            self.lbl_new_feature,
            [(self.edit_new_feature, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        cat_layout.addWidget(self.row_new_feature)

        # Row 5: Feature Color Picker Group
        self.group_color = QWidget(self.group_category)
        color_layout = QHBoxLayout(self.group_color)
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_color_picker = QPushButton(UILabels.BTN_COLOR_PICKER, self.group_color)
        self._update_color_picker_button()
        self.btn_color_picker.clicked.connect(self._pick_color)
        color_layout.addWidget(self.btn_color_picker)

        self.btn_apply_color = QPushButton(UILabels.BTN_APPLY_COLOR, self.group_color)
        self.btn_apply_color.clicked.connect(self._apply_feature_color_group)
        color_layout.addWidget(self.btn_apply_color)
        cat_layout.addWidget(self.group_color)

        # Initial visibility for feature-specific controls (default is グリッド)
        self.row_feature_selector.hide()
        self.row_new_feature.hide()
        self.group_color.hide()

        # Row 6: Attribute Code (属性記号)
        self.lbl_attribute = QLabel(UILabels.ATTRIBUTE_CODE, self.group_category)
        self.combo_attribute = QComboBox(self.group_category)
        self.combo_attribute.addItems(UILabels.ATTRIBUTE_OPTIONS)
        self.combo_attribute.currentIndexChanged.connect(self._on_category_changed)
        row_attribute = UIStyleHelper.build_flex_row(
            self.lbl_attribute,
            [(self.combo_attribute, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        cat_layout.addWidget(row_attribute)

        # Action button: Confirm Attribute (Focus mode trigger)
        self.btn_confirm_attribute = QPushButton(UILabels.BTN_CONFIRM_ATTRIBUTE, self.group_category)
        UIStyleHelper.set_primary_button(self.btn_confirm_attribute)
        self.btn_confirm_attribute.clicked.connect(self._confirm_attribute_transparency)
        cat_layout.addWidget(self.btn_confirm_attribute)

        layout.addWidget(self.group_category)

        # =============================================================
        # Section 3: Individual Input Panel (Non-focus Target)
        # =============================================================
        self.group_individual = QgsCollapsibleGroupBox(UILabels.GROUP_INDIVIDUAL, container)
        pt_layout = QVBoxLayout(self.group_individual)
        pt_layout.setSpacing(6)

        # Row 1: Point Name
        # [EXCEPTION PROTECTION: QSpinBox preserved for S/P/C attributes per
        # OSネイティブUI保護原則]. T-0022: SP属性選択時のみ、専用の自由入力
        # QLineEdit(半角英数字・ハイフン・アンダースコアのみ)をこれと並置し、
        # 表示/非表示を切り替える(QSpinBoxは変更しない)。
        self.lbl_point_name = QLabel(UILabels.POINT_NAME, self.group_individual)
        self.edit_point_name = UIStyleHelper.create_spinbox(1, 999999, 1, self.group_individual)

        self.edit_point_name_sp = QLineEdit(self.group_individual)
        self.edit_point_name_sp.setPlaceholderText(UIPlaceholders.POINT_NAME_SP)
        if HAS_QT_REGEX:
            self.edit_point_name_sp.setValidator(
                QRegularExpressionValidator(
                    QRegularExpression(r"^[A-Za-z0-9_-]+$"), self.edit_point_name_sp
                )
            )
        else:
            self.edit_point_name_sp.setValidator(
                QRegExpValidator(QRegExp(r"^[A-Za-z0-9_-]+$"), self.edit_point_name_sp)
            )
        self.edit_point_name_sp.hide()

        row_point_name = UIStyleHelper.build_flex_row(
            self.lbl_point_name,
            [(self.edit_point_name, 1), (self.edit_point_name_sp, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        pt_layout.addWidget(row_point_name)

        # Row 2: Branch Number
        self.lbl_branch_no = QLabel(UILabels.BRANCH_NO, self.group_individual)
        self.edit_branch_no = QgsFilterLineEdit(self.group_individual)
        self.edit_branch_no.setShowClearButton(True)
        self.edit_branch_no.setPlaceholderText(UIPlaceholders.BRANCH_NO)
        self.edit_branch_no.textChanged.connect(self._on_branch_text_changed)
        row_branch_no = UIStyleHelper.build_flex_row(
            self.lbl_branch_no,
            [(self.edit_branch_no, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        pt_layout.addWidget(row_branch_no)

        layout.addWidget(self.group_individual)

        # =============================================================
        # Section 4: CSV Export Group (Located at the bottom of Tab 2)
        # =============================================================
        csv_group = QgsCollapsibleGroupBox(UILabels.GROUP_CSV, container)
        csv_layout = QVBoxLayout(csv_group)
        csv_layout.setSpacing(6)

        self.lbl_encoding = QLabel(UILabels.ENCODING, csv_group)
        self.radio_utf8 = QRadioButton(UILabels.RADIO_UTF8, csv_group)
        self.radio_utf8.setChecked(True)
        self.radio_sjis = QRadioButton(UILabels.RADIO_SJIS, csv_group)
        row_encoding = UIStyleHelper.build_flex_row(
            self.lbl_encoding,
            [(self.radio_utf8, 1), (self.radio_sjis, 1), (None, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        csv_layout.addWidget(row_encoding)

        self.lbl_csv_path = QLabel(UILabels.CSV_DESTINATION, csv_group)
        self.edit_csv_path = QgsFilterLineEdit(csv_group)
        self.edit_csv_path.setShowClearButton(True)
        self.edit_csv_path.setPlaceholderText(UIPlaceholders.CSV_PATH)
        self.btn_browse_csv = QPushButton(UILabels.BTN_BROWSE, csv_group)
        self.btn_browse_csv.clicked.connect(self._browse_csv_path)
        row_csv = UIStyleHelper.build_flex_row(
            self.lbl_csv_path,
            [(self.edit_csv_path, 1), (self.btn_browse_csv, 0)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        csv_layout.addWidget(row_csv)

        self.btn_export_csv = QPushButton(UILabels.BTN_EXPORT_CSV, csv_group)
        UIStyleHelper.set_accent_button(self.btn_export_csv)
        self.btn_export_csv.clicked.connect(self._on_export_csv_clicked)
        csv_layout.addWidget(self.btn_export_csv)

        layout.addWidget(csv_group)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    # =========================================================================
    # Tab 2: Focus Mode, Artifact Digitizing & CSV Export Handlers
    # =========================================================================

    def _get_drawing_layers(self) -> List[Tuple[str, str, bool]]:
        """Extract valid raster layer information from the '画像ファイル' group in QGIS layer tree.

        :return: List of tuples (layer_name, layer_id, is_visible).
        :rtype: List[Tuple[str, str, bool]]
        """
        root = QgsProject.instance().layerTreeRoot()
        if not root:
            return []
        image_group = root.findGroup("画像ファイル")
        if not image_group:
            return []

        result: List[Tuple[str, str, bool]] = []
        for tree_layer in image_group.findLayers():
            layer = tree_layer.layer()
            if layer and layer.isValid():
                result.append((layer.name(), layer.id(), tree_layer.itemVisibilityChecked()))
        return result

    def _get_drawing_layer_names(self) -> List[str]:
        """Extract valid raster layer names from the '画像ファイル' group in QGIS layer tree.

        :return: List of raster layer names.
        :rtype: List[str]
        """
        return [info[0] for info in self._get_drawing_layers()]

    def _update_drawing_combo(self, *args: Any) -> None:
        """Dynamically refresh the target drawing combo box and drawing visibility multi-selector."""
        if not hasattr(self, "combo_drawing_name") or self.combo_drawing_name is None:
            return

        layers_info = self._get_drawing_layers()
        names = [info[0] for info in layers_info]

        # 1. Update combo_drawing_name
        UIStyleHelper.repopulate_combo_box(self.combo_drawing_name, names, preserve_current=True)

        # 2. Update list_drawing_visibility
        if hasattr(self, "list_drawing_visibility") and self.list_drawing_visibility is not None:
            entries = [(name, layer_id, is_vis) for name, layer_id, is_vis in layers_info]
            UIStyleHelper.repopulate_checkable_list(self.list_drawing_visibility, entries)

    def _on_drawing_visibility_item_changed(self, item: QListWidgetItem) -> None:
        """Toggle canvas visibility for the corresponding layer in '画像ファイル' group.

        :param item: QListWidgetItem whose check state was changed.
        :type item: QListWidgetItem
        """
        layer_id, is_checked = UIStyleHelper.get_checkable_item_state(item)
        root = QgsProject.instance().layerTreeRoot()
        if root and layer_id:
            image_group = root.findGroup("画像ファイル")
            if image_group:
                tree_layer = image_group.findLayer(layer_id)
                if tree_layer:
                    tree_layer.setItemVisibilityChecked(is_checked)
                    self.canvas.refresh()

    def _ensure_drawing_visible(self, drawing_name: str) -> None:
        """Ensure the specified drawing is checked ON in multi-selector and visible on canvas.

        :param drawing_name: Layer name to make visible.
        :type drawing_name: str
        """
        if not hasattr(self, "list_drawing_visibility") or self.list_drawing_visibility is None:
            return

        root = QgsProject.instance().layerTreeRoot()
        image_group = root.findGroup("画像ファイル") if root else None

        for i in range(self.list_drawing_visibility.count()):
            item = self.list_drawing_visibility.item(i)
            if item.text() == drawing_name:
                if item.checkState() != Qt.Checked:
                    self.list_drawing_visibility.blockSignals(True)
                    item.setCheckState(Qt.Checked)
                    self.list_drawing_visibility.blockSignals(False)

                    layer_id = item.data(Qt.UserRole)
                    if image_group and layer_id:
                        tree_layer = image_group.findLayer(layer_id)
                        if tree_layer:
                            tree_layer.setItemVisibilityChecked(True)
                    self.canvas.refresh()
                break

    def is_focus_mode_active(self) -> bool:
        """Return whether Focus Mode is currently active.

        :return: True if focus mode button is checked.
        :rtype: bool
        """
        return bool(hasattr(self, "btn_focus_mode") and self.btn_focus_mode.isChecked())

    def get_focus_category_filter(self) -> Dict[str, str]:
        """Return dictionary of the 4 category values for focus filtering.

        :return: Dict with keys 'drawing_name', 'excavation_type', 'feature_name', 'attribute_type'.
        :rtype: Dict[str, str]
        """
        d_name = (
            self.combo_drawing_name.currentText().strip()
            if hasattr(self, "combo_drawing_name")
            else ""
        )
        ex_type = (
            self.combo_excavation_type.currentText().strip()
            if hasattr(self, "combo_excavation_type")
            else ""
        )
        feat_name = (
            self.combo_feature_name.currentText().strip()
            if hasattr(self, "combo_feature_name")
            else ""
        )
        if (
            feat_name == UILabels.FEATURE_NEW_OPTION
            and hasattr(self, "edit_new_feature")
        ):
            feat_name = self.edit_new_feature.text().strip()

        attr_type = (
            self.combo_attribute.currentText().strip()
            if hasattr(self, "combo_attribute")
            else ""
        )

        return {
            "drawing_name": d_name,
            "excavation_type": ex_type,
            "feature_name": feat_name if ex_type == ExcavationType.FEATURE.value else "",
            "attribute_type": attr_type,
        }

    def _push_focus_state_to_tool(self) -> None:
        """Push current Focus Mode state to CanvasDigitizingTool (Step3: one-way push).

        Called whenever Focus Mode is toggled or any of the four category
        selectors change, so the map tool never needs to call back into this
        dock widget to read UI state (see CanvasDigitizingTool.update_focus_state).
        """
        if getattr(self, "map_tool", None) is not None:
            self.map_tool.update_focus_state(
                self.is_focus_mode_active(), self.get_focus_category_filter()
            )

    def _on_focus_mode_toggled(self, checked: bool) -> None:
        """Handle Focus Mode toggle button click.

        :param checked: True if toggled ON, False if OFF.
        :type checked: bool
        """
        if checked:
            self.btn_focus_mode.setText(UILabels.BTN_FOCUS_ON)
            self.btn_focus_mode.setStyleSheet(
                "background-color: #1976D2; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 4px;"
            )
        else:
            self.btn_focus_mode.setText(UILabels.BTN_FOCUS_OFF)
            self.btn_focus_mode.setStyleSheet("")

        self._push_focus_state_to_tool()
        self.update_symbology_opacity()

    def _on_slider_value_changed(self, val: int) -> None:
        """Update opacity label in real-time as slider is dragged.

        :param val: Slider value (0-100).
        :type val: int
        """
        self.lbl_opacity_val.setText(f"{val}%")

    def _on_slider_released(self) -> None:
        """Trigger symbology opacity update only on slider release event."""
        if self.is_focus_mode_active():
            self.update_symbology_opacity()

    def _on_category_changed(self, *args: Any) -> None:
        """Synchronize symbology opacity, drawing visibility, and point number when category changes.

        Triggered whenever attribute type (S/P/C/SP), excavation type, or
        feature name changes (see _on_excavation_type_changed /
        _on_feature_combo_changed below, both of which delegate here).
        """
        current_drawing = (
            self.combo_drawing_name.currentText().strip()
            if hasattr(self, "combo_drawing_name")
            else ""
        )
        if current_drawing:
            self._ensure_drawing_visible(current_drawing)

        self._apply_next_point_number()
        self._push_focus_state_to_tool()
        if self.is_focus_mode_active():
            self.update_symbology_opacity()

    def _on_excavation_type_changed(self, index: int) -> None:
        """Toggle feature name and color groups based on excavation type."""
        is_feature = self.combo_excavation_type.currentText() == ExcavationType.FEATURE.value
        self.row_feature_selector.setVisible(is_feature)
        self.group_color.setVisible(is_feature)

        if not is_feature:
            self.row_new_feature.hide()
            self.lbl_new_feature.hide()
            self.edit_new_feature.hide()
        else:
            is_new = self.combo_feature_name.currentText() == UILabels.FEATURE_NEW_OPTION
            self.row_new_feature.setVisible(is_new)
            self.lbl_new_feature.setVisible(is_new)
            self.edit_new_feature.setVisible(is_new)

        self._on_category_changed()

    def _on_feature_combo_changed(self, text: str) -> None:
        """Toggle new feature name input field when '新規作成' is selected."""
        is_new = text == UILabels.FEATURE_NEW_OPTION
        self.row_new_feature.setVisible(is_new)
        self.lbl_new_feature.setVisible(is_new)
        self.edit_new_feature.setVisible(is_new)

        self._on_category_changed()

    @pyqtSlot(str)
    def _on_new_feature_text_changed(self, text: str) -> None:
        """Update next point number and focus mode when typing a new feature name."""
        self._on_category_changed()

    def _restore_feature_names(self) -> None:
        """Extract existing unique feature names from points layer and populate combo box."""
        if not self.point_layer or not self.point_layer.isValid():
            return

        UIStyleHelper.populate_combo_from_layer_field(
            self.combo_feature_name,
            self.point_layer,
            "feature_name",
            leading_item=UILabels.FEATURE_NEW_OPTION,
            target_list=self.feature_name_list,
        )

    def register_new_feature_name(self, new_name: str) -> str:
        """Register a newly entered feature name into the combo box and select it."""
        clean_name = new_name.strip()
        idx = self.combo_feature_name.findText(clean_name)
        if idx >= 0:
            self.combo_feature_name.setCurrentIndex(idx)
        else:
            self.combo_feature_name.addItem(clean_name)
            self.feature_name_list.append(clean_name)
            self.combo_feature_name.setCurrentText(clean_name)

        self.edit_new_feature.clear()
        self.row_new_feature.hide()
        self.lbl_new_feature.hide()
        self.edit_new_feature.hide()
        return clean_name

    def _update_color_picker_button(self) -> None:
        """Reflect current feature color on the picker button."""
        self.btn_color_picker.setStyleSheet(
            f"background-color: {self.current_feature_color.name()}; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 4px;"
        )

    def _pick_color(self) -> None:
        """Open QColorDialog to select a feature group color."""
        color = QColorDialog.getColor(
            self.current_feature_color, self, UIDialogTitles.COLOR_PICKER
        )
        if color.isValid():
            self.current_feature_color = color
            self._update_color_picker_button()

    def _apply_feature_color_group(self) -> None:
        """Apply the selected color to all existing points belonging to the selected feature."""
        if not self.point_layer or not self.point_layer.isValid():
            return

        selected_feat = self.combo_feature_name.currentText()
        if selected_feat == UILabels.FEATURE_NEW_OPTION:
            QMessageBox.information(
                self,
                UIMessages.MSG_TITLE_INFO,
                UIMessages.MSG_SELECT_FEATURE_NAME,
            )
            return

        color_hex = self.current_feature_color.name()
        field_idx = self.point_layer.fields().indexFromName("color_code")

        updated_count = 0
        self.point_layer.startEditing()
        for feat in self.point_layer.getFeatures():
            if safe_get_str(feat, "feature_name") == selected_feat:
                self.point_layer.changeAttributeValue(feat.id(), field_idx, color_hex)
                updated_count += 1
        self.point_layer.commitChanges()
        self.point_layer.triggerRepaint()

        self.iface.messageBar().pushMessage(
            UIMessages.MSG_COLOR_APPLIED_TITLE,
            UIMessages.MSG_COLOR_APPLIED.format(
                feature=selected_feat, count=updated_count, color=color_hex
            ),
            level=Qgis.MessageLevel.Info,
            duration=4,
        )

    def _confirm_attribute_transparency(self) -> None:
        """Confirm selected attribute type and activate/update Focus Mode."""
        selected_attr = self.combo_attribute.currentText()
        if not self.is_focus_mode_active():
            self.btn_focus_mode.setChecked(True)
        else:
            self.update_symbology_opacity()

        self.iface.messageBar().pushMessage(
            UIMessages.MSG_ATTR_CONFIRM_TITLE,
            UIMessages.MSG_ATTR_CONFIRMED.format(attr=selected_attr),
            level=Qgis.MessageLevel.Info,
            duration=3,
        )

    def get_digitizing_input_state(self) -> Dict[str, Any]:
        """Collect current input parameters for digitizing validation."""
        d_name = (
            self.combo_drawing_name.currentText().strip()
            if hasattr(self, "combo_drawing_name")
            else ""
        )
        ex_type = self.combo_excavation_type.currentText()
        feat_name = self.combo_feature_name.currentText()
        is_new_feat = feat_name == UILabels.FEATURE_NEW_OPTION
        new_feat_name = self.edit_new_feature.text().strip()

        attr_type = self.combo_attribute.currentText()
        pname = (
            self.edit_point_name_sp.text().strip()
            if attr_type == AttributeType.SP.value
            else str(self.edit_point_name.value())
        )
        branch = self.edit_branch_no.text().strip()

        if not pname:
            return {
                "can_click": False,
                "error_message": UIMessages.ERR_POINT_NAME_REQUIRED,
            }

        if ex_type == ExcavationType.FEATURE.value and is_new_feat and not new_feat_name:
            return {
                "can_click": False,
                "error_message": UIMessages.ERR_NEW_FEATURE_REQUIRED,
            }

        return {
            "can_click": True,
            "drawing_name": d_name,
            "excavation_type": ex_type,
            "feature_name": new_feat_name if (ex_type == ExcavationType.FEATURE.value and is_new_feat) else feat_name,
            "is_new_feature": is_new_feat,
            "new_feature_name": new_feat_name,
            "color_code": self.current_feature_color.name(),
            "attribute_type": attr_type,
            "point_name": pname,
            "branch_no": branch,
        }

    def _is_sp_attribute(self) -> bool:
        """Return True when the currently selected attribute code is 'SP'.

        :return: True if combo_attribute is currently set to AttributeType.SP.value.
        :rtype: bool
        """
        return (
            hasattr(self, "combo_attribute")
            and self.combo_attribute.currentText() == AttributeType.SP.value
        )

    def _update_point_name_widget_visibility(self) -> None:
        """Show the widget matching the current attribute type, hide the other.

        S/P/C attributes use the QSpinBox (edit_point_name); SP uses the
        free-text QLineEdit (edit_point_name_sp). See T-0022.
        """
        is_sp = self._is_sp_attribute()
        self.edit_point_name.setVisible(not is_sp)
        self.edit_point_name_sp.setVisible(is_sp)

    def _get_next_point_number(self) -> int:
        """Calculate next point number based on current excavation type and feature name.

        Queries the point layer on-demand for the group matching the current
        excavation_type/feature_name selection (see core_logic.get_next_point_number
        for the "直前打刻追従型" (max point_id) numbering strategy).
        """
        ex_type = self.combo_excavation_type.currentText()
        feat_name = ""
        if ex_type == ExcavationType.FEATURE.value:
            feat_name = self.combo_feature_name.currentText()
            if feat_name == UILabels.FEATURE_NEW_OPTION:
                feat_name = self.edit_new_feature.text().strip()

        return get_next_point_number(
            self.point_layer,
            ex_type,
            feat_name,
        )

    def _apply_next_point_number(self) -> None:
        """Refresh the point-name entry widget(s) for the current attribute/category selection.

        For S/P/C attributes, auto-increments the QSpinBox using the
        "直前打刻追従型" numbering logic. For SP, auto-numbering is skipped
        entirely and the free-text QLineEdit is cleared, awaiting manual entry.
        """
        self._update_point_name_widget_visibility()
        if self._is_sp_attribute():
            self.edit_point_name_sp.clear()
        else:
            next_num = self._get_next_point_number()
            self.edit_point_name.setValue(next_num)

    @pyqtSlot(str)
    def _on_branch_text_changed(self, text: str) -> None:
        """Handle branch number cleared to increment point number if previously digitized with branch."""
        if not text.strip() and self._has_digitized_with_branch:
            self._apply_next_point_number()
            self._has_digitized_with_branch = False

    def _on_canvas_clicked(self, map_point: QgsPointXY) -> None:
        """Handle a plain (non-hit) click on the main canvas from CanvasDigitizingTool.

        Validates the current digitizing input state, resolves new-feature
        registration and duplicate checks, builds the feature via
        core_logic.build_digitized_feature(), and writes it to point_layer.
        This consolidates logic that previously lived in
        CanvasDigitizingTool._handle_digitize_click (Step3: event-driven
        decoupling — map_tool.py now only reports "canvas was clicked here").

        :param map_point: Click location in standard mathematical/canvas coordinates.
        :type map_point: QgsPointXY
        """
        if not self.point_layer or not self.point_layer.isValid():
            return

        # 1. Retrieve and validate current digitizing input state
        state = self.get_digitizing_input_state()
        if not state.get("can_click", False):
            QMessageBox.warning(
                self,
                "打刻エラー",
                state.get("error_message", "必須項目が未入力のため打刻できません。"),
            )
            return

        drawing_name = state.get("drawing_name", "")
        excavation_type = state["excavation_type"]
        feature_name = state["feature_name"]
        color_code = state["color_code"]
        attribute_type = state["attribute_type"]
        point_name = state["point_name"]
        branch_no = state["branch_no"]

        # 2. Pattern B: automatic feature registration if '新規作成'
        if excavation_type == ExcavationType.FEATURE.value and state.get("is_new_feature", False):
            new_feat_name = state.get("new_feature_name", "").strip()
            if not new_feat_name:
                QMessageBox.warning(self, "入力エラー", "新規遺構名を入力してください。")
                return
            feature_name = self.register_new_feature_name(new_feat_name)

        # 3. Duplicate check (including drawing_name)
        if check_point_duplicate(
            self.point_layer, excavation_type, feature_name, point_name, branch_no, drawing_name
        ):
            ident = (
                f"{feature_name}-{point_name}"
                if excavation_type == ExcavationType.FEATURE.value
                else f"{ExcavationType.GRID.value}-{point_name}"
            )
            if branch_no:
                ident += f" ({branch_no})"
            if drawing_name:
                ident = f"[{drawing_name}] {ident}"
            QMessageBox.warning(
                self,
                "重複打刻エラー",
                f"同じ点（{ident}）が既に登録されています。\n点名または枝番を変更してください。",
            )
            return

        # 4. Determine next point_id
        next_point_id = get_next_point_id(self.point_layer)

        # 5. Resolve pixel coordinates on the source drawing via the affine adapter
        pixel_coords = (0.0, 0.0)
        if drawing_name and self.layer_manager:
            meta = self.layer_manager.load_image_metadata()
            layer_meta = meta.get(drawing_name)
            affine_params = layer_meta.get("affine_params") if layer_meta else None
            pixel_coords = pixel_from_affine(affine_params, map_point)

        # 6. Build the feature (pre-georeferenced: canvas coords ARE real coords)
        new_feat = build_digitized_feature(
            self.point_layer,
            next_point_id,
            map_point,
            {
                "drawing_name": drawing_name,
                "excavation_type": excavation_type,
                "feature_name": feature_name if excavation_type == ExcavationType.FEATURE.value else "",
                "color_code": color_code if excavation_type == ExcavationType.FEATURE.value else "",
                "attribute_type": attribute_type,
                "point_name": point_name,
                "branch_no": branch_no,
            },
            pixel_coords=pixel_coords,
        )

        # 7. Write the new feature to the layer
        insert_feature_to_layer(self.point_layer, new_feat)

        # 8. Update UI (auto-increment point number / status panel)
        self._on_point_digitized({
            "point_id": next_point_id,
            "drawing_name": drawing_name,
            "point_name": point_name,
            "branch_no": branch_no,
            "excavation_type": excavation_type,
            "feature_name": feature_name,
        })

    def _on_point_digitized(self, data: dict) -> None:
        """Handle point digitization completion."""
        branch_no = data.get("branch_no", "")
        if branch_no:
            self._has_digitized_with_branch = True
        else:
            self._has_digitized_with_branch = False
            self._apply_next_point_number()

        UIStyleHelper.update_status_panel(
            self.panel_edit_status,
            self.lbl_edit_status,
            UILabels.STATUS_DIGITIZE_SUCCESS.format(
                id=data.get("point_id"), name=data.get("point_name")
            ),
            status_type="success",
        )

    @pyqtSlot(dict)
    def _on_existing_point_selected(self, data: dict) -> None:
        """Load an existing point's attributes into the dock widget for editing."""
        self.selected_edit_point_id = data.get("feature_id")

        # Select drawing if present
        d_name = str(data.get("drawing_name") or "").strip()
        if d_name and hasattr(self, "combo_drawing_name"):
            idx = self.combo_drawing_name.findText(d_name)
            if idx >= 0:
                self.combo_drawing_name.setCurrentIndex(idx)
            self._ensure_drawing_visible(d_name)

        ex_type = str(data.get("excavation_type") or ExcavationType.GRID.value)
        self.combo_excavation_type.setCurrentText(ex_type)

        if ex_type == ExcavationType.FEATURE.value:
            feat_name = str(data.get("feature_name") or "")
            self.register_new_feature_name(feat_name)
            color_code = str(data.get("color_code") or "#FF5722")
            self.current_feature_color = QColor(color_code)
            self._update_color_picker_button()

        # T-0022: attribute must be applied before the point-name value, since
        # changing combo_attribute triggers _on_category_changed ->
        # _apply_next_point_number() (auto-numbering side effect), which we
        # then override below with the actual loaded point_name value.
        attr_type = str(data.get("attribute_type") or AttributeType.S.value)
        self.combo_attribute.setCurrentText(attr_type)

        pname_raw = str(data.get("point_name") or "")
        if attr_type == AttributeType.SP.value:
            self.edit_point_name_sp.setText(pname_raw)
        else:
            try:
                p_val = int(pname_raw or 1)
            except ValueError:
                p_val = 1
            self.edit_point_name.setValue(p_val)
        self._update_point_name_widget_visibility()

        self.edit_branch_no.setText(str(data.get("branch_no") or ""))

        self.btn_delete_point.setEnabled(True)
        UIStyleHelper.update_status_panel(
            self.panel_edit_status,
            self.lbl_edit_status,
            UILabels.STATUS_EXISTING_POINT.format(
                id=data.get("point_id"), name=data.get("point_name")
            ),
            status_type="warning",
        )

    def _reset_point_selection(self) -> None:
        """Reset form back to new point creation mode."""
        self.selected_edit_point_id = None
        self.btn_delete_point.setEnabled(False)
        UIStyleHelper.update_status_panel(
            self.panel_edit_status,
            self.lbl_edit_status,
            UILabels.EDIT_STATUS_INIT,
            status_type="info",
        )

        self._apply_next_point_number()
        self.edit_branch_no.clear()
        self._has_digitized_with_branch = False

    def _on_delete_selected_point(self) -> None:
        """Delete the currently selected point from point layer."""
        if self.selected_edit_point_id is None or not self.point_layer:
            return

        reply = QMessageBox.question(
            self,
            UIMessages.MSG_CONFIRM_TITLE,
            UIMessages.MSG_DELETE_CONFIRM,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.point_layer.startEditing()
            self.point_layer.deleteFeature(self.selected_edit_point_id)
            self.point_layer.commitChanges()
            self.point_layer.triggerRepaint()

            self.iface.messageBar().pushMessage(
                UIMessages.MSG_DELETE_SUCCESS_TITLE,
                UIMessages.MSG_DELETE_SUCCESS,
                level=Qgis.MessageLevel.Success,
                duration=3,
            )
            self._reset_point_selection()

    def _browse_csv_path(self) -> None:
        """Browse destination path for CSV export."""
        default_dir = self.layers_dict.get("session_dir", os.path.expanduser("~"))
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            UIDialogTitles.BROWSE_CSV,
            default_dir,
            UIDialogTitles.CSV_FILTER,
        )
        if filepath:
            self.edit_csv_path.setText(os.path.normpath(filepath))

    def _on_export_csv_clicked(self) -> None:
        """Export digitized points directly to CSV."""
        filepath = self.edit_csv_path.text().strip()
        if not filepath:
            self._browse_csv_path()
            filepath = self.edit_csv_path.text().strip()
            if not filepath:
                return

        encoding = "utf-8-sig" if self.radio_utf8.isChecked() else "cp932"
        success, msg = export_points_to_csv(
            self.point_layer, filepath, encoding=encoding, parent=self
        )

        if success:
            self.iface.messageBar().pushMessage(
                UIMessages.MSG_EXPORT_CSV_TITLE,
                msg,
                level=Qgis.MessageLevel.Success,
                duration=5,
            )

