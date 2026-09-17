"""
/***************************************************************************
 PointerGeocoding Plugin - Main Dock Standalone Dialog Classes
 ***************************************************************************/

Stage B split (mechanical, logic-preserving): extracted from main_dock.py.
Contains the independent dialog/widget classes used by MainDockWidget:
ModelessSectionDialog, ImageDialog, TwoDigitSpinBox and GridInputDialog.

T-0024 (UI restructure: left dock removal, top 4-button row + modeless
dialogs): the former left-dock icon rail + collapsible side panel (T-0020/
T-0021) has been replaced by three independent modeless dialogs opened from
buttons on the right dock's (MainDockWidget's) own top row: 画像 (image),
設定 (settings) and 出力 (CSV export). 設定/出力 are thin
ModelessSectionDialog wrappers around the content widgets tab3_settings_mixin.py
/ tab2_digitizing_mixin.py already build (_create_tab3_ui / _create_tab4_ui,
the latter renamed from _create_output_ui in T-0034).
画像 is the dedicated ImageDialog class below, which also absorbs the former
standalone PreviewDialog: the reference-point preview QgsMapCanvas (and its
setup_raster/add_marker/clear_markers/clean_up API, used by
tab1_georef_mixin.py) is now embedded directly inside the same window as the
画像管理 form, instead of opening as a second popup. All three dialogs are
modeless (multiple can be open at once) and report their show/close events
back to MainDockWidget via on_show/on_close callbacks, which it uses to
suspend/restore the main canvas digitizing tool (map_tool) while any of them
is open (see MainDockWidget._update_main_map_tool_state).
"""
# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

import re
from typing import Optional, Dict, Any, List, Callable, Tuple

from qgis.core import QgsRasterLayer
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import Qt, pyqtSlot, QRegExp
from qgis.PyQt.QtGui import QRegExpValidator
from qgis.PyQt.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QMessageBox,
)

from ..canvas.map_tool import ImageGeorefTool
from .style import UIStyleHelper
from ..logic.core import to_survey_coords, check_point_duplicate, build_point_ident
from .constants import UIConfig, UILabels, UIMessages, UIPlaceholders, UIDialogSizes
from .core import CoreUIBuilder
from .core.validators import RequiredValidator, DuplicateValidator, show_validation_error
from .schemas import (
    GRID_INPUT_ACTIONS_SPEC,
    FEATURE_CREATE_INPUT_SPEC,
    FEATURE_CREATE_ACTIONS_SPEC,
    POINT_NAME_ENTRY_SPEC,
    POINT_NAME_ENTRY_ACTIONS_SPEC,
)


class ModelessSectionDialog(QDialog):
    """Generic modeless dialog hosting a single pre-built content widget (T-0024).

    Used for the 設定 (settings) and 出力 (CSV export) dialogs: the dialog
    itself owns no business logic, it simply presents a content widget built
    by the corresponding tab mixin (tab3_settings_mixin.py's
    ``_create_tab3_ui`` / tab2_digitizing_mixin.py's ``_create_tab4_ui``,
    renamed from ``_create_output_ui`` in T-0034)
    and, since it is modeless and reopenable, notifies MainDockWidget of its
    show/close events via the optional ``on_show``/``on_close`` callbacks so
    the main canvas digitizing tool can be suspended while it is open and
    restored once no such dialog remains open.
    """

    def __init__(
        self,
        title: str,
        content_widget: QWidget,
        on_show: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the dialog.

        :param title: Window title.
        :type title: str
        :param content_widget: Pre-built content widget to embed.
        :type content_widget: QWidget
        :param on_show: Optional callback invoked after the dialog is shown.
        :type on_show: Optional[Callable[[], None]]
        :param on_close: Optional callback invoked after the dialog is hidden/closed.
        :type on_close: Optional[Callable[[], None]]
        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._on_show = on_show
        self._on_close = on_close

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
        )
        layout.addWidget(content_widget)

    def showEvent(self, event: Any) -> None:
        """Notify on_show after the dialog becomes visible."""
        super().showEvent(event)
        if self._on_show is not None:
            self._on_show()

    def closeEvent(self, event: Any) -> None:
        """Hide (rather than destroy) so the dialog can be reopened, then notify on_close."""
        self.hide()
        event.accept()
        if self._on_close is not None:
            self._on_close()


class ImageDialog(QDialog):
    """Modeless dialog hosting the 画像管理 (Tab 1) form, with the
    reference-point preview canvas embedded directly beside it (T-0024).

    Replaces the former separate PreviewDialog popup (see module docstring):
    the QgsMapCanvas preview and its setup_raster/add_marker/clear_markers/
    clean_up API now live on this class, alongside the 画像管理 form widget
    (tab1_georef_mixin.py's ``_create_tab1_ui``) passed in as
    ``content_widget``.
    """

    def __init__(
        self,
        content_widget: QWidget,
        on_show: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the image dialog.

        :param content_widget: Pre-built 画像管理 form widget (Tab 1 content).
        :type content_widget: QWidget
        :param on_show: Optional callback invoked after the dialog is shown.
        :type on_show: Optional[Callable[[], None]]
        :param on_close: Optional callback invoked after the dialog is hidden/closed.
        :type on_close: Optional[Callable[[], None]]
        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)
        self.setWindowTitle(UILabels.TAB_1_TITLE)
        self.resize(UIDialogSizes.IMAGE_DIALOG_WIDTH, UIDialogSizes.IMAGE_DIALOG_HEIGHT)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._on_show = on_show
        self._on_close = on_close

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
        )
        layout.setSpacing(UIConfig.DIALOG_MARGIN)

        # Left: 画像管理 form (image add/edit, reference point table, transform)
        layout.addWidget(content_widget, 1)

        # Right: embedded reference-point preview canvas (formerly PreviewDialog)
        preview_container = QWidget(self)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(4)

        lbl_hint = QLabel(UILabels.PREVIEW_HINT, preview_container)
        lbl_hint.setWordWrap(True)
        preview_layout.addWidget(lbl_hint)

        self.canvas = QgsMapCanvas(preview_container)
        self.canvas.setMinimumSize(400, 300)
        preview_layout.addWidget(self.canvas, 1)

        layout.addWidget(preview_container, 1)

        self.raster_layer: Optional[QgsRasterLayer] = None
        self.georef_tool: Optional[ImageGeorefTool] = None

    def setup_raster(
        self,
        raster_layer: QgsRasterLayer,
        point_clicked_callback: Any,
        ref_points_data: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Set up raster layer and georeferencing map tool on the preview canvas.

        :param raster_layer: Loaded temporary raster layer.
        :type raster_layer: QgsRasterLayer
        :param point_clicked_callback: Callback slot for point_clicked signal.
        :type point_clicked_callback: Any
        :param ref_points_data: Optional list of existing reference points for snap detection.
        :type ref_points_data: Optional[List[Dict[str, Any]]]
        """
        self.clean_up()

        self.raster_layer = raster_layer
        self.canvas.setLayers([self.raster_layer])
        self.canvas.setExtent(self.raster_layer.extent())
        self.canvas.refresh()

        self.georef_tool = ImageGeorefTool(self.canvas, self.raster_layer)
        if ref_points_data:
            self.georef_tool.set_ref_points_data(ref_points_data)
        self.canvas.setMapTool(self.georef_tool)
        self.georef_tool.point_clicked.connect(point_clicked_callback)

    def set_ref_points_data(self, ref_points_data: List[Dict[str, Any]]) -> None:
        """Update reference points list in georef tool for hover snap detection.

        :param ref_points_data: List of reference points.
        :type ref_points_data: List[Dict[str, Any]]
        """
        if self.georef_tool:
            self.georef_tool.set_ref_points_data(ref_points_data)

    def add_marker(self, pixel_x: float, pixel_y: float, name: str = "") -> None:
        """Add a vertex marker at given image pixel coordinate.

        :param pixel_x: Pixel X coordinate.
        :type pixel_x: float
        :param pixel_y: Pixel Y coordinate.
        :type pixel_y: float
        :param name: Label text for the point.
        :type name: str
        """
        if self.georef_tool:
            self.georef_tool.add_point_marker(pixel_x, pixel_y, name)

    def clear_markers(self) -> None:
        """Clear all vertex markers from preview canvas."""
        if self.georef_tool:
            self.georef_tool.clear_markers()

    def clean_up(self) -> None:
        """Clean up map tool and canvas layers."""
        if self.georef_tool is not None:
            self.georef_tool.clean_up()
            self.georef_tool = None
        if self.canvas is not None:
            self.canvas.setMapTool(None)
            self.canvas.setLayers([])
        self.raster_layer = None

    def showEvent(self, event: Any) -> None:
        """Notify on_show after the dialog becomes visible."""
        super().showEvent(event)
        if self._on_show is not None:
            self._on_show()

    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event by hiding to allow reopening without reload."""
        self.hide()
        event.accept()
        if self._on_close is not None:
            self._on_close()


class TwoDigitSpinBox(QSpinBox):
    """QSpinBox displaying two-digit integer numbers (00 to 99)."""

    def textFromValue(self, val: int) -> str:
        """Format integer value as two-digit string."""
        return f"{val:02d}"

    def valueFromText(self, text: str) -> int:
        """Parse two-digit string into integer."""
        try:
            return int(text)
        except ValueError:
            return 0


class GridInputDialog(QDialog):
    """Modal dialog for inputting and validating grid indices against PointGeo_grid.csv.
    # 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。
    """

    def __init__(
        self,
        layer_manager: Any,
        existing_point: Optional[Dict[str, Any]] = None,
        existing_names: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize grid input modal dialog.
        # 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

        :param layer_manager: LayerManager instance containing grid memory cache.
        :type layer_manager: Any
        :param existing_point: Optional reference point dictionary if editing an existing point.
        :type existing_point: Optional[Dict[str, Any]]
        :param existing_names: List of names of other existing points to prevent duplication.
        :type existing_names: Optional[List[str]]
        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.existing_point = existing_point
        self.existing_names = existing_names or []

        self.dialog_action: str = "cancel"  # "confirm", "delete", "cancel"
        self.result_grid_name: str = ""
        self.result_real_x: Optional[float] = None
        self.result_real_y: Optional[float] = None

        self.setWindowTitle(UILabels.GRID_DIALOG_TITLE)
        self.setModal(True)
        self.setMinimumWidth(UIDialogSizes.GRID_DIALOG_MIN_WIDTH)

        self._init_ui()
        UIStyleHelper.apply_theme(self)
        self._populate_initial_values()

    def _init_ui(self) -> None:
        """Construct the 4-tier dialog interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
        )
        layout.setSpacing(UIConfig.DIALOG_MARGIN)

        # -------------------------------------------------------------
        # Tier 1: [Xグリッド (数値SpinBox)] - [Yグリッド (英字のみテキスト入力)] - [小グリッド (00-99 数値SpinBox)]
        # -------------------------------------------------------------
        tier1_box = QWidget(self)
        tier1_vlayout = QVBoxLayout(tier1_box)
        tier1_vlayout.setContentsMargins(0, 0, 0, 0)
        tier1_vlayout.setSpacing(4)

        # Labels header row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        lbl_header_x = QLabel(UILabels.GRID_X_LABEL, tier1_box)
        lbl_header_x.setStyleSheet("font-weight: bold; font-size: 8.5pt;")
        lbl_header_x.setAlignment(Qt.AlignCenter)

        lbl_header_y = QLabel(UILabels.GRID_Y_LABEL, tier1_box)
        lbl_header_y.setStyleSheet("font-weight: bold; font-size: 8.5pt;")
        lbl_header_y.setAlignment(Qt.AlignCenter)

        lbl_header_sub = QLabel(UILabels.GRID_SUB_LABEL, tier1_box)
        lbl_header_sub.setStyleSheet("font-weight: bold; font-size: 8.5pt;")
        lbl_header_sub.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(lbl_header_x, 1)
        header_layout.addSpacing(16)
        header_layout.addWidget(lbl_header_y, 1)
        header_layout.addSpacing(16)
        header_layout.addWidget(lbl_header_sub, 1)
        tier1_vlayout.addLayout(header_layout)

        # Inputs row
        inputs_layout = QHBoxLayout()
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(4)

        max_gx = max(1, getattr(self.layer_manager, "max_gx", 100))
        self.spin_x = UIStyleHelper.create_spinbox(1, max_gx, 1, tier1_box)
        self.spin_x.setMinimumWidth(70)
        self.spin_x.valueChanged.connect(self._validate_and_lookup)

        lbl_sep1 = QLabel("-", tier1_box)
        lbl_sep1.setStyleSheet("font-weight: bold; padding: 0 4px;")
        lbl_sep1.setAlignment(Qt.AlignCenter)

        self.edit_y = QLineEdit(tier1_box)
        self.edit_y.setPlaceholderText("A")
        self.edit_y.setMaxLength(10)
        self.edit_y.setMinimumWidth(70)
        self.edit_y.setAlignment(Qt.AlignCenter)
        self.edit_y.setValidator(QRegExpValidator(QRegExp(r"[A-Za-z]+"), self.edit_y))
        self.edit_y.textChanged.connect(self._on_y_changed)

        lbl_sep2 = QLabel("-", tier1_box)
        lbl_sep2.setStyleSheet("font-weight: bold; padding: 0 4px;")
        lbl_sep2.setAlignment(Qt.AlignCenter)

        self.spin_sub = TwoDigitSpinBox(tier1_box)
        self.spin_sub.setRange(0, 99)
        self.spin_sub.setValue(0)
        self.spin_sub.setMinimumWidth(70)
        self.spin_sub.valueChanged.connect(self._validate_and_lookup)

        inputs_layout.addWidget(self.spin_x, 1)
        inputs_layout.addWidget(lbl_sep1, 0)
        inputs_layout.addWidget(self.edit_y, 1)
        inputs_layout.addWidget(lbl_sep2, 0)
        inputs_layout.addWidget(self.spin_sub, 1)
        tier1_vlayout.addLayout(inputs_layout)

        layout.addWidget(tier1_box)

        # -------------------------------------------------------------
        # Tier 2: [選択点を削除] ボタン（既存点選択時のみ表示/有効化）
        # -------------------------------------------------------------
        self.btn_delete_point = QPushButton(UILabels.BTN_DELETE_SELECTED_POINT, self)
        self.btn_delete_point.setStyleSheet(
            "background-color: #D32F2F; color: #FFFFFF; font-weight: bold; border-radius: 4px;"
        )
        self.btn_delete_point.clicked.connect(self._on_delete_point_clicked)
        if self.existing_point is None:
            self.btn_delete_point.setVisible(False)
        layout.addWidget(self.btn_delete_point)

        # -------------------------------------------------------------
        # Tier 3: [確定] [キャンセル] ボタン (T-0047: CoreUI BUTTON_ROW with
        # centered=True, replacing the former direct
        # UIStyleHelper.build_centered_button_row() call; see
        # GRID_INPUT_ACTIONS_SPEC in schemas.py).
        # -------------------------------------------------------------
        actions_panel = CoreUIBuilder.build(GRID_INPUT_ACTIONS_SPEC, parent=self)
        self._actions_panel = actions_panel
        self.btn_confirm = actions_panel.get("confirm")
        self.btn_cancel = actions_panel.get("cancel")
        actions_panel.bind("confirm_clicked", self._on_confirm_clicked)
        actions_panel.bind("cancel_clicked", self.reject)
        layout.addWidget(actions_panel.widget)

        # -------------------------------------------------------------
        # Tier 4: ステータス・エラー表示パネル
        # -------------------------------------------------------------
        self.panel_status, self.lbl_status = UIStyleHelper.create_status_panel(
            "", status_type="info", parent=self
        )
        layout.addWidget(self.panel_status)

    def _populate_initial_values(self) -> None:
        """Pre-populate inputs if editing an existing reference point."""
        if self.existing_point:
            name = str(self.existing_point.get("name", "")).strip()
            m = re.match(r"^(\d+)-?([A-Za-z]+)-?(\d{1,2})$", name)
            if m:
                self.spin_x.setValue(int(m.group(1)))
                self.edit_y.setText(m.group(2).upper())
                self.spin_sub.setValue(int(m.group(3)))
            else:
                self.edit_y.setText("A")
        else:
            default_y = "A"
            unique_gy = getattr(self.layer_manager, "unique_gy", set())
            if unique_gy:
                sorted_gy = sorted(list(unique_gy))
                if sorted_gy:
                    default_y = sorted_gy[0]
            self.edit_y.setText(default_y)

        self._validate_and_lookup()

    @pyqtSlot(str)
    def _on_y_changed(self, text: str) -> None:
        """Enforce uppercase on Y grid text input and trigger validation."""
        upper = text.upper()
        if upper != text:
            pos = self.edit_y.cursorPosition()
            self.edit_y.setText(upper)
            self.edit_y.setCursorPosition(pos)
        self._validate_and_lookup()

    def _validate_and_lookup(self) -> None:
        """Perform real-time lookup and validation against LayerManager's grid cache."""
        gx = self.spin_x.value()
        gy = self.edit_y.text().strip().upper()
        sub_grid = f"{self.spin_sub.value():02d}"
        grid_name = f"{gx}-{gy}-{sub_grid}"

        if not gy:
            UIStyleHelper.update_status_panel(
                self.panel_status,
                self.lbl_status,
                "大グリッドＹを入力してください (英字)。",
                status_type="info",
            )
            self.btn_confirm.setEnabled(False)
            return

        # Check duplicate name
        if grid_name in self.existing_names:
            UIStyleHelper.update_status_panel(
                self.panel_status,
                self.lbl_status,
                UILabels.ERR_GRID_DUPLICATE.format(grid=grid_name),
                status_type="error",
            )
            self.btn_confirm.setEnabled(False)
            return

        # Check unique_gy
        unique_gy = getattr(self.layer_manager, "unique_gy", set())
        if unique_gy and gy not in unique_gy:
            UIStyleHelper.update_status_panel(
                self.panel_status,
                self.lbl_status,
                UILabels.ERR_GY_NOT_FOUND.format(gy=gy),
                status_type="error",
            )
            self.btn_confirm.setEnabled(False)
            return

        # Lookup in grid_data
        grid_data = getattr(self.layer_manager, "grid_data", {})
        key = (gx, gy, sub_grid)

        if key in grid_data:
            math_x, math_y = grid_data[key]
            self.result_grid_name = grid_name
            self.result_real_x = float(math_x)
            self.result_real_y = float(math_y)

            # Apply to_survey_coords adapter for UI display in survey coordinate system
            survey_x, survey_y = to_survey_coords(math_x, math_y)
            msg = UILabels.STATUS_GRID_FOUND.format(
                grid=grid_name, rx=survey_x, ry=survey_y
            )
            UIStyleHelper.update_status_panel(
                self.panel_status,
                self.lbl_status,
                msg,
                status_type="success",
            )
            self.btn_confirm.setEnabled(True)
        else:
            UIStyleHelper.update_status_panel(
                self.panel_status,
                self.lbl_status,
                UILabels.ERR_GRID_NOT_FOUND.format(grid=grid_name),
                status_type="error",
            )
            self.btn_confirm.setEnabled(False)

    def _on_delete_point_clicked(self) -> None:
        """Handle deletion of the selected reference point."""
        reply = QMessageBox.question(
            self,
            UIMessages.MSG_CONFIRM_TITLE,
            UIMessages.MSG_CONFIRM_DELETE_REF,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.dialog_action = "delete"
            self.accept()

    def _on_confirm_clicked(self) -> None:
        """Handle confirmation and accept dialog."""
        self.dialog_action = "confirm"
        self.accept()


class FeatureCreateDialog(QDialog):
    """T-0027: Modal dialog for creating a new 遺構名 (feature name).

    Replaces the former always-visible ``edit_new_feature`` QLineEdit row in
    the 属性パネル/入力カテゴリ設定 group: the "作成" button in
    tab2_digitizing_mixin.py's 属性パネル opens this dialog instead. On OK,
    ``result_text`` holds the trimmed feature name for the caller
    (Tab2DigitizingMixin._on_create_feature_clicked) to register via
    ``register_new_feature_name()`` and then continue on to color selection.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the feature-name creation dialog.

        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)
        self.result_text: str = ""

        self.setWindowTitle(UILabels.FEATURE_CREATE_DIALOG_TITLE)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
        )
        layout.setSpacing(UIConfig.DIALOG_MARGIN)

        # T-0047: 遺構名 input + OK/キャンセル row built declaratively via
        # CoreUI (see FEATURE_CREATE_INPUT_SPEC / FEATURE_CREATE_ACTIONS_SPEC
        # in schemas.py); the former inline red-text lbl_error is dropped in
        # favor of the ui/core/validators.py Validator +
        # show_validation_error() pattern already used by tab1_image.py
        # (QMessageBox.warning() + setFocus()).
        input_panel = CoreUIBuilder.build(FEATURE_CREATE_INPUT_SPEC, parent=self)
        self._input_panel = input_panel
        self.edit_name = input_panel.get("feature_name")
        layout.addWidget(input_panel.widget)

        actions_panel = CoreUIBuilder.build(FEATURE_CREATE_ACTIONS_SPEC, parent=self)
        self._actions_panel = actions_panel
        self.btn_ok = actions_panel.get("ok")
        self.btn_cancel = actions_panel.get("cancel")
        actions_panel.bind("ok_clicked", self._on_ok_clicked)
        actions_panel.bind("cancel_clicked", self.reject)
        layout.addWidget(actions_panel.widget)

    def _on_ok_clicked(self) -> None:
        """Validate the entered feature name and accept the dialog if non-empty."""
        text = self.edit_name.text().strip()
        result = RequiredValidator(UIMessages.ERR_NEW_FEATURE_REQUIRED).validate(text)
        if not result.is_valid:
            show_validation_error(self, UIMessages.ERR_TITLE_INPUT, result, focus_widget=self.edit_name)
            return
        self.result_text = text
        self.accept()


class PointNameEntryDialog(QDialog):
    """T-0040: Modal dialog for entering a 点名/枝番 at click time while the
    新規モード点情報パネルの自動連番/解除トグル is set to 解除 (or while it is
    forced to 解除 by an SP attribute selection, see
    Tab2DigitizingMixin._update_autonum_toggle_for_sp).

    While 解除 is active, edit_point_name (QSpinBox) is left untouched by
    _apply_next_point_number and edit_point_name_sp is cleared for SP, so
    neither panel widget reliably holds the value the user actually wants
    at the moment of a canvas click. This dialog pops up at click time
    (positioned near the click via Tab2DigitizingMixin._on_canvas_clicked)
    to collect 点名/枝番 explicitly, following the same
    OK/キャンセル + red-text-above-buttons error pattern as
    FeatureCreateDialog. On OK, a duplicate check
    (core_logic.check_point_duplicate) is run against the panel's current
    出土形態/遺構名/対象図面 (passed in by the caller, unchanged by this
    dialog); a duplicate blocks acceptance and shows
    core_logic.build_point_ident()'s message in ``self.lbl_error`` instead.
    On success, ``result_point_name``/``result_branch_no`` hold the
    validated values for the caller to build the digitized feature with.
    """

    def __init__(
        self,
        point_layer,
        excavation_type: str,
        feature_name: str,
        drawing_name: str = "",
        is_sp_attribute: bool = False,
        parent: Optional[QWidget] = None,
        initial_point_name: str = "",
    ) -> None:
        """Initialize the point-name/branch-number entry dialog.

        :param point_layer: Vector layer to check for duplicate point identities against.
        :type point_layer: QgsVectorLayer
        :param excavation_type: ExcavationType.GRID.value or ExcavationType.FEATURE.value,
            taken from the 点情報パネル's current selection.
        :type excavation_type: str
        :param feature_name: Current 遺構名 selection (empty when excavation_type is グリッド).
        :type feature_name: str
        :param drawing_name: Current 対象図面 選択.
        :type drawing_name: str
        :param is_sp_attribute: True when the panel's currently selected 属性
            is SP (Tab2DigitizingMixin._is_sp_attribute()). SP点名は英数字の
            自由記述（edit_point_name_sp と同じバリデーション）で入力させ、
            それ以外は従来通り整数QSpinBoxで入力させる (see T-0040 followup
            fix: SP属性は解除モード固定のため、このダイアログ経由でしか
            SP点名を入力できない).
        :type is_sp_attribute: bool
        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        :param initial_point_name: T-0041: Preset value for the 点名 input
            (直前に作成した点名), typically obtained via
            Tab2DigitizingMixin._get_last_created_point_name(). For the
            QSpinBox (non-SP) case this must be a string parseable as an
            int; non-numeric/empty values are ignored and the spinbox keeps
            its default. Presetting a value that turns out to be a
            duplicate is allowed -- OK still runs the normal duplicate
            check and shows an error, leaving it to the user to edit the
            value.
        :type initial_point_name: str
        """
        super().__init__(parent)
        self._point_layer = point_layer
        self._excavation_type = excavation_type
        self._feature_name = feature_name
        self._drawing_name = drawing_name
        self._is_sp_attribute = is_sp_attribute
        self.result_point_name: str = ""
        self.result_branch_no: str = ""

        self.setWindowTitle(UILabels.POINT_NAME_ENTRY_DIALOG_TITLE)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
        )
        layout.setSpacing(UIConfig.DIALOG_MARGIN)

        # T-0047: 点名 (numeric or SP free-text)/枝番 inputs + OK/キャンセル
        # row built declaratively via CoreUI (see POINT_NAME_ENTRY_SPEC /
        # POINT_NAME_ENTRY_ACTIONS_SPEC in schemas.py). Both the numeric
        # "point_name" (SPINBOX_ROW) and free-text "point_name_sp"
        # (LINEEDIT_ROW) fields are always built; only the one matching
        # is_sp_attribute is shown, since CoreUI schemas stay static and this
        # choice is fixed per dialog instance.
        input_panel = CoreUIBuilder.build(POINT_NAME_ENTRY_SPEC, parent=self)
        self._input_panel = input_panel
        self.spin_point_name: QSpinBox = input_panel.get("point_name")
        self.edit_point_name_sp: QLineEdit = input_panel.get("point_name_sp")
        self.edit_branch_no: QLineEdit = input_panel.get("branch_no")

        if self._is_sp_attribute:
            # SP属性: edit_point_name_sp (tab2_digitizing_mixin.py) と同じ
            # 英数字・ハイフン・アンダースコアのみ許可のバリデータを踏襲する。
            self.edit_point_name_sp.setValidator(
                QRegExpValidator(QRegExp(r"^[A-Za-z0-9_-]+$"), self.edit_point_name_sp)
            )
            if initial_point_name:
                self.edit_point_name_sp.setText(initial_point_name)
            input_panel.get_row("point_name").hide()
        else:
            if initial_point_name and initial_point_name.isdigit():
                preset_value = int(initial_point_name)
                if self.spin_point_name.minimum() <= preset_value <= self.spin_point_name.maximum():
                    self.spin_point_name.setValue(preset_value)
            input_panel.get_row("point_name_sp").hide()

        layout.addWidget(input_panel.widget)

        actions_panel = CoreUIBuilder.build(POINT_NAME_ENTRY_ACTIONS_SPEC, parent=self)
        self._actions_panel = actions_panel
        self.btn_ok = actions_panel.get("ok")
        self.btn_cancel = actions_panel.get("cancel")
        actions_panel.bind("ok_clicked", self._on_ok_clicked)
        actions_panel.bind("cancel_clicked", self.reject)
        layout.addWidget(actions_panel.widget)

    def _get_point_name_text(self) -> str:
        """Return the currently entered 点名 as a string, regardless of which
        input widget (spin_point_name / edit_point_name_sp) is active for the
        current 属性 (SP or not, see __init__'s is_sp_attribute).

        :return: 点名 as a string (e.g. "123" for non-SP, "SP-1" for SP).
        :rtype: str
        """
        if self._is_sp_attribute:
            return self.edit_point_name_sp.text().strip()
        return str(self.spin_point_name.value())

    def _on_ok_clicked(self) -> None:
        """Validate (duplicate-check) the entered 点名/枝番 and accept if unique.

        T-0047: judgment now runs through ui/core/validators.py's Validator
        classes (RequiredValidator for the SP-required check,
        DuplicateValidator wrapping logic.core.check_point_duplicate), with
        show_validation_error() displaying the failure via QMessageBox.warning
        (replacing the former inline lbl_error red-text panel), matching
        tab1_image.py's existing adoption of the same pattern.
        """
        point_name = self._get_point_name_text()
        branch_no = self.edit_branch_no.text().strip()

        if self._is_sp_attribute:
            result = RequiredValidator(UIMessages.ERR_POINT_NAME_REQUIRED).validate(point_name)
            if not result.is_valid:
                show_validation_error(
                    self, UIMessages.ERR_TITLE_INPUT, result, focus_widget=self.edit_point_name_sp
                )
                return

        ident = build_point_ident(
            self._excavation_type,
            self._feature_name,
            point_name,
            branch_no,
            self._drawing_name,
        )
        result = DuplicateValidator(
            lambda v: check_point_duplicate(
                self._point_layer,
                self._excavation_type,
                self._feature_name,
                v,
                branch_no,
                self._drawing_name,
            ),
            message=UIMessages.ERR_POINT_NAME_DUPLICATE.format(ident=ident),
        ).validate(point_name)
        if not result.is_valid:
            show_validation_error(self, UIMessages.ERR_TITLE_DUPLICATE, result)
            return

        self.result_point_name = point_name
        self.result_branch_no = branch_no
        self.accept()

    def get_values(self) -> Tuple[str, str]:
        """Return the validated (point_name, branch_no) pair after an accepted dialog.

        :return: Tuple of (point_name, branch_no) strings.
        :rtype: Tuple[str, str]
        """
        return self.result_point_name, self.result_branch_no
