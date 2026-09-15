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
/ tab2_digitizing_mixin.py already build (_create_tab3_ui / _create_output_ui).
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
from typing import Optional, Dict, Any, List, Callable

from qgis.core import QgsRasterLayer, QgsVectorLayer
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

# T-0027: SP属性専用の点名QLineEditで使用する入力バリデータ。PyQt5/PyQt6両対応
# パターンは tab2_digitizing_mixin.py (T-0022導入分) を踏襲する。
try:
    from qgis.PyQt.QtGui import QRegularExpressionValidator
    from qgis.PyQt.QtCore import QRegularExpression
    HAS_QT_REGEX = True
except ImportError:
    HAS_QT_REGEX = False

from .map_tool import ImageGeorefTool
from .style_helper import UIStyleHelper
from .core_logic import (
    to_survey_coords,
    check_duplicate_and_build_message,
    ExcavationType,
    AttributeType,
)
from .main_dock_constants import UILabels, UIMessages, UIPlaceholders, UIDialogSizes


class ModelessSectionDialog(QDialog):
    """Generic modeless dialog hosting a single pre-built content widget (T-0024).

    Used for the 設定 (settings) and 出力 (CSV export) dialogs: the dialog
    itself owns no business logic, it simply presents a content widget built
    by the corresponding tab mixin (tab3_settings_mixin.py's
    ``_create_tab3_ui`` / tab2_digitizing_mixin.py's ``_create_output_ui``)
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
        layout.setContentsMargins(6, 6, 6, 6)
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
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

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
        # Tier 3: [確定] [キャンセル] ボタン (centered, equal width; see
        # UIStyleHelper.build_centered_button_row / StartDialog's OK/Cancel
        # row for the shared pattern)
        # -------------------------------------------------------------
        self.btn_confirm = QPushButton(UILabels.BTN_CONFIRM, self)
        UIStyleHelper.set_primary_button(self.btn_confirm)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._on_confirm_clicked)

        self.btn_cancel = QPushButton(UILabels.BTN_CANCEL, self)
        self.btn_cancel.clicked.connect(self.reject)

        btn_action_layout = UIStyleHelper.build_centered_button_row(
            [self.btn_confirm, self.btn_cancel]
        )
        layout.addLayout(btn_action_layout)

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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(QLabel(UILabels.NEW_FEATURE_NAME, self))

        self.edit_name = QLineEdit(self)
        self.edit_name.setPlaceholderText(UIPlaceholders.NEW_FEATURE)
        layout.addWidget(self.edit_name)

        self.lbl_error = QLabel("", self)
        self.lbl_error.setStyleSheet("color: #C62828;")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        layout.addWidget(self.lbl_error)

        self.btn_ok = QPushButton(UILabels.BTN_CONFIRM, self)
        UIStyleHelper.set_primary_button(self.btn_ok)
        self.btn_ok.clicked.connect(self._on_ok_clicked)

        self.btn_cancel = QPushButton(UILabels.BTN_CANCEL, self)
        self.btn_cancel.clicked.connect(self.reject)

        layout.addLayout(UIStyleHelper.build_centered_button_row([self.btn_ok, self.btn_cancel]))

    def _on_ok_clicked(self) -> None:
        """Validate the entered feature name and accept the dialog if non-empty."""
        text = self.edit_name.text().strip()
        if not text:
            self.lbl_error.setText(UIMessages.ERR_NEW_FEATURE_REQUIRED)
            self.lbl_error.show()
            return
        self.result_text = text
        self.accept()


class PointRenameDialog(QDialog):
    """T-0027: Modal dialog for renaming (point number + branch number) an
    existing digitized point, replacing the former inline "番号修正を確定"
    button (Tab2DigitizingMixin._on_correct_point_number, now removed).

    Unlike new-point digitizing, no auto-numbering is applied here: the
    point-name/branch-number inputs start pre-filled with the point's
    current values, and OK only performs a duplicate check (via
    core_logic.check_duplicate_and_build_message(), excluding the point
    itself) before writing the updated attributes directly to the layer
    and closing. On duplicate, an inline red error label is shown and the
    dialog stays open (T-0027 requirement: no QMessageBox for this case).
    """

    def __init__(
        self,
        point_layer: QgsVectorLayer,
        feature_id: int,
        attribute_type: str,
        excavation_type: str,
        feature_name: str,
        drawing_name: str,
        point_name: str,
        branch_no: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the point rename dialog.

        :param point_layer: Vector layer containing the digitized point.
        :type point_layer: QgsVectorLayer
        :param feature_id: Feature id of the point being renamed (excluded from the duplicate check).
        :type feature_id: int
        :param attribute_type: Current attribute_type value ('S'/'P'/'C'/'SP'); determines
            whether the point-name input is a QSpinBox (S/P/C) or a free-text QLineEdit (SP).
        :type attribute_type: str
        :param excavation_type: Current excavation_type value (immutable while renaming).
        :type excavation_type: str
        :param feature_name: Current feature_name value (immutable while renaming).
        :type feature_name: str
        :param drawing_name: Current drawing_name value (immutable while renaming).
        :type drawing_name: str
        :param point_name: Current point_name value to pre-fill.
        :type point_name: str
        :param branch_no: Current branch_no value to pre-fill.
        :type branch_no: str
        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)
        self.point_layer = point_layer
        self.feature_id = feature_id
        self.attribute_type = attribute_type
        self.excavation_type = excavation_type
        self.feature_name = feature_name
        self.drawing_name = drawing_name

        self.setWindowTitle(UILabels.RENAME_POINT_DIALOG_TITLE)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        is_sp = attribute_type == AttributeType.SP.value

        layout.addWidget(QLabel(UILabels.POINT_NAME, self))
        self.spin_point_name = UIStyleHelper.create_spinbox(1, 999999, 1, self)
        self.spin_point_name.setVisible(not is_sp)

        self.edit_point_name_sp = QLineEdit(self)
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
        self.edit_point_name_sp.setVisible(is_sp)

        if is_sp:
            self.edit_point_name_sp.setText(point_name)
        else:
            try:
                self.spin_point_name.setValue(int(point_name or 1))
            except ValueError:
                self.spin_point_name.setValue(1)

        layout.addWidget(self.spin_point_name)
        layout.addWidget(self.edit_point_name_sp)

        layout.addWidget(QLabel(UILabels.BRANCH_NO, self))
        self.edit_branch_no = QLineEdit(self)
        self.edit_branch_no.setPlaceholderText(UIPlaceholders.BRANCH_NO)
        self.edit_branch_no.setText(branch_no)
        layout.addWidget(self.edit_branch_no)

        self.lbl_error = QLabel("", self)
        self.lbl_error.setStyleSheet("color: #C62828;")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        layout.addWidget(self.lbl_error)

        self.btn_ok = QPushButton(UILabels.BTN_CONFIRM, self)
        UIStyleHelper.set_primary_button(self.btn_ok)
        self.btn_ok.clicked.connect(self._on_ok_clicked)

        self.btn_cancel = QPushButton(UILabels.BTN_CANCEL, self)
        self.btn_cancel.clicked.connect(self.reject)

        layout.addLayout(UIStyleHelper.build_centered_button_row([self.btn_ok, self.btn_cancel]))

    def _show_error(self, message: str) -> None:
        """Display an inline red error message and keep the dialog open."""
        self.lbl_error.setText(message)
        self.lbl_error.show()

    def _on_ok_clicked(self) -> None:
        """Validate input, duplicate-check, write attributes, and close on success."""
        is_sp = self.attribute_type == AttributeType.SP.value
        point_name = (
            self.edit_point_name_sp.text().strip()
            if is_sp
            else str(self.spin_point_name.value())
        )
        branch_no = self.edit_branch_no.text().strip()

        if not point_name:
            self._show_error(UIMessages.ERR_POINT_NAME_REQUIRED)
            return

        # T-0027: reuse the same duplicate-check + message-building logic as
        # new-point digitizing (core_logic.check_duplicate_and_build_message),
        # excluding this point itself.
        ident = check_duplicate_and_build_message(
            self.point_layer,
            self.excavation_type,
            self.feature_name,
            point_name,
            branch_no,
            self.drawing_name,
            exclude_feature_id=self.feature_id,
        )
        if ident:
            self._show_error(UIMessages.MSG_DUPLICATE_POINT.format(ident=ident))
            return

        field_names = self.point_layer.fields().names()
        pname_idx = field_names.index("point_name")
        branch_idx = field_names.index("branch_no")

        self.point_layer.startEditing()
        self.point_layer.changeAttributeValue(self.feature_id, pname_idx, point_name)
        self.point_layer.changeAttributeValue(self.feature_id, branch_idx, branch_no)
        self.point_layer.commitChanges()
        self.point_layer.triggerRepaint()

        self.accept()
