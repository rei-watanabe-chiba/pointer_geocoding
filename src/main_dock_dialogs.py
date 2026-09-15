"""
/***************************************************************************
 PointerGeocoding Plugin - Main Dock Standalone Dialog Classes
 ***************************************************************************/

Stage B split (mechanical, logic-preserving): extracted from main_dock.py.
Contains the independent dialog/widget classes used by MainDockWidget's
Tab 1 (georeferencing) workflow: PreviewDialog, TwoDigitSpinBox and
GridInputDialog.
"""
# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

import re
from typing import Optional, Dict, Any, List

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

from .map_tool import ImageGeorefTool
from .style_helper import UIStyleHelper
from .core_logic import to_survey_coords
from .main_dock_constants import UILabels, UIMessages


class PreviewDialog(QDialog):
    """Modeless dialog displaying the temporary georeferencing raster preview canvas."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize preview dialog.

        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)
        self.setWindowTitle(UILabels.PREVIEW_DIALOG_TITLE)
        self.resize(750, 580)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.canvas = QgsMapCanvas(self)
        self.canvas.setMinimumSize(400, 300)
        layout.addWidget(self.canvas)

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

    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event by hiding to allow reopening without reload."""
        self.hide()
        event.accept()


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
        self.setMinimumWidth(380)

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
        # Tier 3: [確定] [キャンセル] ボタン
        # -------------------------------------------------------------
        btn_action_layout = QHBoxLayout()
        btn_action_layout.setContentsMargins(0, 0, 0, 0)
        btn_action_layout.setSpacing(8)

        self.btn_confirm = QPushButton(UILabels.BTN_CONFIRM, self)
        UIStyleHelper.set_primary_button(self.btn_confirm)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._on_confirm_clicked)

        self.btn_cancel = QPushButton(UILabels.BTN_CANCEL, self)
        self.btn_cancel.clicked.connect(self.reject)

        btn_action_layout.addWidget(self.btn_confirm, 1)
        btn_action_layout.addWidget(self.btn_cancel, 1)
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
            "この基準点を削除しますか？",
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
