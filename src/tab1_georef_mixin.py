"""
/***************************************************************************
 PointerGeocoding Plugin - Tab 1 (Georeferencing) Mixin
 ***************************************************************************/

Stage B split (mechanical, logic-preserving): extracted from main_dock.py.
Provides Tab1GeorefMixin, mixed into MainDockWidget, containing all UI
construction and event handlers for Tab 1 (image addition, preview
canvas, reference point management, coordinate transformation & layer
export).
"""
# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

import os
import re
import math
from typing import Optional, List, Tuple

from qgis.core import (
    QgsProject,
    QgsPointXY,
    Qgis,
)
from qgis.gui import QgsFilterLineEdit
from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from .transform import CoordinateTransformer
from .style_helper import UIStyleHelper
from .core_logic import (
    to_survey_coords,
    from_survey_coords,
    update_point_layer_geometry,
    evaluate_residuals,
)
from .main_dock_constants import (
    UIConfig,
    UILabels,
    UIPlaceholders,
    UIDialogTitles,
    UIMessages,
    MAIN_RATIO,
)
from .main_dock_dialogs import PreviewDialog, GridInputDialog


class Tab1GeorefMixin:
    """Mixin providing Tab 1 (Image Addition & Pre-Georeferencing) behavior for MainDockWidget."""

    def _create_tab1_ui(self) -> QWidget:
        """Construct Tab 1: Image Addition & Pre-Georeferencing."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 16, 4)
        layout.setSpacing(12)

        # 1. Information Panel
        self.panel_tab1_info = QFrame(container)
        UIStyleHelper.set_status_panel(self.panel_tab1_info)
        panel_layout = QVBoxLayout(self.panel_tab1_info)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(4)
        
        # 1段目
        self.lbl_tab1_info_1 = QLabel(UILabels.TAB1_INFO_IMAGE_REF.format(
            name=UILabels.UNLOADED, count=0
        ), self.panel_tab1_info)
        self.lbl_tab1_info_1.setStyleSheet("font-weight: bold;")
        panel_layout.addWidget(self.lbl_tab1_info_1)
        
        # hr
        hr = QFrame(self.panel_tab1_info)
        hr.setFrameShape(QFrame.HLine)
        hr.setStyleSheet("border-top: 1px dashed palette(mid); background: transparent;")
        panel_layout.addWidget(hr)
        
        # 2段目
        self.lbl_tab1_info_2 = QLabel(UILabels.TRANSFORM_INIT_STATUS, self.panel_tab1_info)
        panel_layout.addWidget(self.lbl_tab1_info_2)
        
        # 3〜6段目
        self.lbl_tab1_info_3_6 = QLabel(UILabels.TAB1_INFO_RESIDUAL_INIT, self.panel_tab1_info)
        self.lbl_tab1_info_3_6.setWordWrap(True)
        self.lbl_tab1_info_3_6.setMinimumHeight(14 * 4) # Space for approx 4 lines
        panel_layout.addWidget(self.lbl_tab1_info_3_6)
        
        layout.addWidget(self.panel_tab1_info)

        # 2. Mode Toggle
        self.tab1_mode_container, self.tab1_mode_buttons = UIStyleHelper.build_segmented_toggle(
            ["新規追加", "編集削除"], default_index=0, parent=container
        )
        
        mode_row = UIStyleHelper.build_flex_row(
            main_label=None,
            child_configs=[(self.tab1_mode_container, 1)],
            main_ratio=(0, 10),
            row_height=UIConfig.ROW_HEIGHT
        )
        layout.addWidget(mode_row)
        
        self.tab1_mode_buttons[0].toggled.connect(lambda checked: self._on_tab1_mode_changed(0) if checked else None)
        self.tab1_mode_buttons[1].toggled.connect(lambda checked: self._on_tab1_mode_changed(1) if checked else None)

        # 3. Mode-specific inputs
        self.sec_image = QWidget(container)
        img_layout = QVBoxLayout(self.sec_image)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setSpacing(6)

        # 3a. Image File (New Mode)
        self.row_image_path = QWidget(self.sec_image)
        row_image_layout = QHBoxLayout(self.row_image_path)
        row_image_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_image_path = QLabel(UILabels.IMAGE_FILE, self.row_image_path)
        self.edit_image_path = QgsFilterLineEdit(self.row_image_path)
        self.edit_image_path.setPlaceholderText(UIPlaceholders.IMAGE_PATH)
        self.btn_browse_image = QPushButton(UILabels.BTN_BROWSE, self.row_image_path)
        self.btn_browse_image.clicked.connect(self._browse_image_file)
        row_image_layout.addWidget(self.lbl_image_path, 3)
        row_image_layout.addWidget(self.edit_image_path, 6)
        row_image_layout.addWidget(self.btn_browse_image, 1)
        img_layout.addWidget(self.row_image_path)

        # 3b. Edit Layer Selector (Edit Mode)
        self.lbl_edit_layer = QLabel("編集レイヤ:", self.sec_image)
        self.combo_edit_layer = QComboBox(self.sec_image)
        self.combo_edit_layer.currentIndexChanged.connect(self._on_edit_layer_changed)
        self.row_edit_layer = UIStyleHelper.build_flex_row(
            self.lbl_edit_layer, [(self.combo_edit_layer, 1)], main_ratio=MAIN_RATIO, row_height=UIConfig.ROW_HEIGHT
        )
        img_layout.addWidget(self.row_edit_layer)
        self.row_edit_layer.hide()

        # 3c. Layer Name (Both Modes)
        self.lbl_image_name = QLabel(UILabels.LAYER_NAME, self.sec_image)
        self.edit_image_name = QgsFilterLineEdit(self.sec_image)
        self.edit_image_name.setPlaceholderText(UIPlaceholders.IMAGE_NAME)
        row_image_name = UIStyleHelper.build_flex_row(
            self.lbl_image_name, [(self.edit_image_name, 1)], main_ratio=MAIN_RATIO, row_height=UIConfig.ROW_HEIGHT
        )
        img_layout.addWidget(row_image_name)

        # 3d. Actions: Confirm & Delete
        actions_btn_layout = QHBoxLayout()
        self.btn_confirm_image = QPushButton("確定", self.sec_image)
        UIStyleHelper.set_primary_button(self.btn_confirm_image)
        self.btn_confirm_image.clicked.connect(self._on_confirm_image_clicked)
        
        self.btn_delete_layer = QPushButton("レイヤ削除", self.sec_image)
        self.btn_delete_layer.setEnabled(False)
        self.btn_delete_layer.clicked.connect(self._on_delete_layer_clicked)

        actions_btn_layout.addWidget(self.btn_confirm_image, 1)
        actions_btn_layout.addWidget(self.btn_delete_layer, 1)
        img_layout.addLayout(actions_btn_layout)

        # 4. Reference Points Table
        self.table_ref_points = QTableWidget(0, 4, self.sec_image)
        self.table_ref_points.setHorizontalHeaderLabels(UILabels.REF_TABLE_HEADERS)
        self.table_ref_points.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_ref_points.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_ref_points.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_ref_points.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_ref_points.setMinimumHeight(130)
        self.table_ref_points.cellChanged.connect(self._on_ref_table_cell_changed)
        img_layout.addWidget(self.table_ref_points)

        layout.addWidget(self.sec_image)

        # 5. Coordinate Transformation & Placement
        self.sec_transform = QWidget(container)
        trans_layout = QVBoxLayout(self.sec_transform)
        trans_layout.setContentsMargins(0, 0, 0, 0)
        trans_layout.setSpacing(6)

        trans_btn_layout = QHBoxLayout()
        self.btn_transform = QPushButton(UILabels.BTN_TRANSFORM, self.sec_transform)
        UIStyleHelper.set_primary_button(self.btn_transform)
        self.btn_transform.setEnabled(False)
        self.btn_transform.clicked.connect(self._on_transform_clicked)

        self.btn_export_layer = QPushButton(UILabels.BTN_EXPORT_LAYER, self.sec_transform)
        UIStyleHelper.set_accent_button(self.btn_export_layer)
        self.btn_export_layer.setEnabled(False)
        self.btn_export_layer.clicked.connect(self._on_export_layer_clicked)

        trans_btn_layout.addWidget(self.btn_transform, 1)
        trans_btn_layout.addWidget(self.btn_export_layer, 1)
        trans_layout.addLayout(trans_btn_layout)

        layout.addWidget(self.sec_transform)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _on_tab1_mode_changed(self, mode_index: int) -> None:
        """Handle Tab 1 mode switch between New Add (0) and Edit/Delete (1)."""
        if mode_index == 0:
            self.row_image_path.show()
            self.row_edit_layer.hide()
            self.btn_delete_layer.setEnabled(False)
            self.edit_image_path.clear()
            self.edit_image_name.clear()
            self.confirmed_layer_name = None
            self.ref_points_data.clear()
            self._refresh_ref_points_table_and_markers()
        else:
            self.row_image_path.hide()
            self.row_edit_layer.show()
            self.btn_delete_layer.setEnabled(True)
            self._refresh_edit_layer_combo()
            self._on_edit_layer_changed()

    def _refresh_edit_layer_combo(self) -> None:
        self.combo_edit_layer.blockSignals(True)
        self.combo_edit_layer.clear()
        meta = self.layer_manager.load_image_metadata()
        for layer_name in meta.keys():
            self.combo_edit_layer.addItem(layer_name)
        self.combo_edit_layer.blockSignals(False)

    def _on_edit_layer_changed(self) -> None:
        layer_name = self.combo_edit_layer.currentText()
        if not layer_name:
            self.edit_image_name.clear()
            self.ref_points_data.clear()
            self._refresh_ref_points_table_and_markers()
            return

        self.edit_image_name.setText(layer_name)
        self.confirmed_layer_name = layer_name
        
        meta = self.layer_manager.load_image_metadata()
        layer_meta = meta.get(layer_name, {})
        self.current_copied_image_path = layer_meta.get("file_path", "")
        
        self.ref_points_data = []
        for r in layer_meta.get("ref_points", []):
            self.ref_points_data.append({
                "name": r.get("name", ""),
                "pixel_x": r.get("pixel_x", 0.0),
                "pixel_y": r.get("pixel_y", 0.0),
                "real_x": r.get("real_x", 0.0),
                "real_y": r.get("real_y", 0.0),
            })
        self._refresh_ref_points_table_and_markers()

    def _on_delete_layer_clicked(self) -> None:
        layer_name = self.combo_edit_layer.currentText()
        if not layer_name:
            return
            
        reply = QMessageBox.question(
            self, "レイヤ削除", f"レイヤ '{layer_name}' を削除しますか？\n関連するファイルやメタデータも削除されます。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        # Warning if points exist for this drawing
        if self.point_layer and self.point_layer.isValid() and "drawing_name" in self.point_layer.fields().names():
            has_points = False
            for f in self.point_layer.getFeatures():
                if str(f["drawing_name"] or "").strip() == layer_name:
                    has_points = True
                    break
            if has_points:
                pts_reply = QMessageBox.question(
                    self, "ポイントが存在します",
                    f"この図面に関連づけられた打刻点が存在します。\n削除を続行すると、これらの点の対象図面はクリアされグローバル点になります。\n続行しますか？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if pts_reply != QMessageBox.Yes:
                    return
                
                self.point_layer.startEditing()
                idx = self.point_layer.fields().indexFromName("drawing_name")
                for f in self.point_layer.getFeatures():
                    if str(f["drawing_name"] or "").strip() == layer_name:
                        self.point_layer.changeAttributeValue(f.id(), idx, "")
                self.point_layer.commitChanges()

        # Remove from QGIS Project first to release file locks
        project = QgsProject.instance()
        for tree_layer in project.layerTreeRoot().findLayers():
            l = tree_layer.layer()
            if l and l.name() == layer_name:
                project.removeMapLayer(l.id())
                break

        # Delete metadata and file
        meta = self.layer_manager.load_image_metadata()
        if layer_name in meta:
            file_path = meta[layer_name].get("file_path", "")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                    
            # Also remove world files if exist
            base, _ = os.path.splitext(file_path)
            for ext in [".tfw", ".jgw", ".pgw", ".bpw", ".wld"]:
                if os.path.exists(base + ext):
                    try:
                        os.remove(base + ext)
                    except Exception:
                        pass
            
            self.layer_manager.delete_image_metadata(layer_name)

        QMessageBox.information(self, "削除完了", f"レイヤ '{layer_name}' を削除しました。")
        self._refresh_edit_layer_combo()
        self._on_edit_layer_changed()

    # =========================================================================
    # Tab 1: Image Addition, Preview Canvas & Georeferencing Handlers
    # =========================================================================

    def _browse_image_file(self) -> None:
        """Open file dialog to select an analog drawing image."""
        start_dir = self.layers_dict.get("session_dir", os.path.expanduser("~"))
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            UIDialogTitles.BROWSE_IMAGE,
            start_dir,
            UIDialogTitles.IMAGE_FILTER,
        )
        if filepath:
            norm_path = os.path.normpath(filepath)
            self.edit_image_path.setText(norm_path)
            base_name, ext = os.path.splitext(os.path.basename(norm_path))
            self.edit_image_name.setText(base_name)
            self.confirmed_layer_name = None

    def _on_confirm_image_clicked(self) -> None:
        """Handle layer confirm: integrate image load and preview. In Edit mode, handle rename."""
        layer_name = self.edit_image_name.text().strip()

        if not layer_name:
            QMessageBox.warning(
                self,
                UIMessages.ERR_TITLE_INPUT,
                UIMessages.ERR_REQUIRED_IMAGE_NAME,
            )
            self.edit_image_name.setFocus()
            return

        if re.search(self.INVALID_CHARS_PATTERN, layer_name):
            QMessageBox.warning(
                self,
                UIMessages.ERR_TITLE_INPUT,
                UIMessages.ERR_INVALID_IMAGE_NAME,
            )
            self.edit_image_name.setFocus()
            return

        is_edit_mode = self.tab1_mode_buttons[1].isChecked()

        if not is_edit_mode:
            src_path = self.edit_image_path.text().strip()
            if not src_path or not os.path.isfile(src_path):
                QMessageBox.warning(
                    self,
                    UIMessages.ERR_TITLE_INPUT,
                    UIMessages.ERR_INVALID_IMAGE,
                )
                self.edit_image_path.setFocus()
                return

            _, ext = os.path.splitext(src_path)
            target_filename = f"{layer_name}{ext}"

            # Copy image to session
            success, msg, dest_path = self.layer_manager.copy_image_to_session(src_path, target_filename)
            if not success:
                if dest_path and os.path.isfile(dest_path):
                    pass
                else:
                    QMessageBox.warning(self, UIMessages.ERR_TITLE_FILE, msg)
                    return
            
            self.confirmed_layer_name = layer_name
            self.current_copied_image_path = dest_path

            # Clear old reference points for newly added image
            self.ref_points_data.clear()
            self.calculated_affine_params = None
            self._refresh_ref_points_table_and_markers()
            if self.preview_dialog:
                self.preview_dialog.clear_markers()
                self.preview_dialog.set_ref_points_data([])
                
        else:
            old_name = self.combo_edit_layer.currentText()
            if old_name != layer_name:
                # Handle rename
                meta = self.layer_manager.load_image_metadata()
                if old_name in meta:
                    layer_meta = meta[old_name]
                    old_path = layer_meta.get("file_path", "")
                    
                    if old_path and os.path.exists(old_path):
                        base, ext = os.path.splitext(old_path)
                        new_base = os.path.join(os.path.dirname(old_path), layer_name)
                        new_path = new_base + ext
                        try:
                            # Rename file
                            os.rename(old_path, new_path)
                            self.current_copied_image_path = new_path
                            layer_meta["file_path"] = new_path
                            
                            # Rename world files
                            for w_ext in [".tfw", ".jgw", ".pgw", ".bpw", ".wld"]:
                                if os.path.exists(base + w_ext):
                                    os.rename(base + w_ext, new_base + w_ext)
                        except Exception as e:
                            QMessageBox.warning(self, "Rename Error", f"ファイルの名称変更に失敗しました:\n{e}")
                            return

                    # Update metadata key
                    meta[layer_name] = layer_meta
                    del meta[old_name]
                    self.layer_manager.save_image_metadata(meta)
                    self.confirmed_layer_name = layer_name

                    # Update point attributes
                    if self.point_layer and self.point_layer.isValid() and "drawing_name" in self.point_layer.fields().names():
                        self.point_layer.startEditing()
                        idx = self.point_layer.fields().indexFromName("drawing_name")
                        for f in self.point_layer.getFeatures():
                            if str(f["drawing_name"] or "").strip() == old_name:
                                self.point_layer.changeAttributeValue(f.id(), idx, layer_name)
                        self.point_layer.commitChanges()
                        
                    # Update QGIS layer name if it exists in project
                    project = QgsProject.instance()
                    for tree_layer in project.layerTreeRoot().findLayers():
                        l = tree_layer.layer()
                        if l and l.name() == old_name:
                            l.setName(layer_name)

                    self._refresh_edit_layer_combo()
                    index = self.combo_edit_layer.findText(layer_name)
                    if index >= 0:
                        self.combo_edit_layer.setCurrentIndex(index)

        self.lbl_tab1_info_1.setText(
            UILabels.TAB1_INFO_IMAGE_REF.format(
                name=layer_name, count=len(self.ref_points_data)
            )
        )
        
        # Automatically show preview canvas
        if self.preview_dialog and self.preview_dialog.raster_layer is not None:
            self.preview_dialog.set_ref_points_data(self.ref_points_data)
            self.preview_dialog.show()
            self.preview_dialog.raise_()
            self.preview_dialog.activateWindow()
        else:
            self._create_preview_canvas(self.current_copied_image_path)


    def _create_preview_canvas(self, image_path: str) -> bool:
        """Create or update modeless PreviewDialog with preview raster."""
        if self.preview_dialog is None:
            self.preview_dialog = PreviewDialog(self)

        success, msg, raster_layer = self.layer_manager.load_preview_raster(image_path)
        if not success or raster_layer is None:
            QMessageBox.critical(
                self,
                UIMessages.ERR_TITLE_LOAD,
                UIMessages.ERR_PREVIEW_FAILED.format(msg=msg),
            )
            return False

        self.preview_dialog.setup_raster(
            raster_layer,
            self._on_preview_canvas_point_clicked,
            self.ref_points_data,
        )
        self.preview_dialog.show()
        self.preview_dialog.raise_()
        self.preview_dialog.activateWindow()

        return True

    def _destroy_preview_canvas(self) -> None:
        """Safely clean up preview dialog and canvas resources."""
        if self.preview_dialog is not None:
            self.preview_dialog.clean_up()
            self.preview_dialog.close()

    def _on_setup_ref_points_clicked(self) -> None:
        """Open or raise the modeless preview dialog for setting reference points."""
        if not self.current_copied_image_path or not os.path.isfile(self.current_copied_image_path):
            QMessageBox.information(
                self,
                UIMessages.MSG_TITLE_INFO,
                UIMessages.MSG_CONFIRM_IMAGE_FIRST,
            )
            return

        if self.preview_dialog and self.preview_dialog.raster_layer is not None:
            self.preview_dialog.set_ref_points_data(self.ref_points_data)
            self.preview_dialog.show()
            self.preview_dialog.raise_()
            self.preview_dialog.activateWindow()
        else:
            self._create_preview_canvas(self.current_copied_image_path)

    @pyqtSlot(float, float)
    def _on_preview_canvas_point_clicked(self, pixel_x: float, pixel_y: float) -> None:
        """Handle reference point click on preview canvas with 15px snap detection and GridInputDialog."""
        snapped_index: Optional[int] = None

        # 1. Snap test against existing reference points within 15 screen pixels
        if (
            self.preview_dialog
            and self.preview_dialog.raster_layer
            and self.preview_dialog.georef_tool
        ):
            tool = self.preview_dialog.georef_tool
            rlayer = self.preview_dialog.raster_layer
            extent = rlayer.extent()
            w = float(rlayer.width())
            h = float(rlayer.height())

            if w > 0 and h > 0 and extent.width() > 0 and extent.height() > 0:
                click_map_x = extent.xMinimum() + (pixel_x / w) * extent.width()
                click_map_y = extent.yMaximum() - (pixel_y / h) * extent.height()
                click_screen = tool.toCanvasCoordinates(QgsPointXY(click_map_x, click_map_y))

                min_dist = float("inf")
                for idx, rdata in enumerate(self.ref_points_data):
                    rx = float(rdata["pixel_x"])
                    ry = float(rdata["pixel_y"])
                    r_map_x = extent.xMinimum() + (rx / w) * extent.width()
                    r_map_y = extent.yMaximum() - (ry / h) * extent.height()
                    r_screen = tool.toCanvasCoordinates(QgsPointXY(r_map_x, r_map_y))
                    dist = math.hypot(
                        click_screen.x() - r_screen.x(), click_screen.y() - r_screen.y()
                    )
                    if dist <= 15.0 and dist < min_dist:
                        min_dist = dist
                        snapped_index = idx

        # 2. Case: Snapped to existing point -> Edit / Delete modal
        if snapped_index is not None:
            existing_point = self.ref_points_data[snapped_index]
            other_names = [
                r["name"] for i, r in enumerate(self.ref_points_data) if i != snapped_index
            ]
            dlg = GridInputDialog(
                self.layer_manager,
                existing_point=existing_point,
                existing_names=other_names,
                parent=self.preview_dialog or self,
            )
            if dlg.exec_() == QDialog.Accepted:
                if dlg.dialog_action == "delete":
                    del self.ref_points_data[snapped_index]
                    self.calculated_affine_params = None
                    self._refresh_ref_points_table_and_markers()
                elif dlg.dialog_action == "confirm":
                    existing_point["name"] = dlg.result_grid_name
                    existing_point["real_x"] = dlg.result_real_x
                    existing_point["real_y"] = dlg.result_real_y
                    self.calculated_affine_params = None
                    self._refresh_ref_points_table_and_markers()
            return

        # 3. Case: New point clicked -> Add new modal
        if len(self.ref_points_data) >= 4:
            QMessageBox.information(
                self,
                UIMessages.MSG_TITLE_LIMIT,
                UIMessages.MSG_LIMIT_REFS,
            )
            return

        other_names = [r["name"] for r in self.ref_points_data]
        dlg = GridInputDialog(
            self.layer_manager,
            existing_point=None,
            existing_names=other_names,
            parent=self.preview_dialog or self,
        )
        if dlg.exec_() == QDialog.Accepted and dlg.dialog_action == "confirm":
            pt_entry = {
                "name": dlg.result_grid_name,
                "pixel_x": pixel_x,
                "pixel_y": pixel_y,
                "real_x": dlg.result_real_x,
                "real_y": dlg.result_real_y,
            }
            self.ref_points_data.append(pt_entry)
            self.calculated_affine_params = None
            self._refresh_ref_points_table_and_markers()

    def _on_ref_table_cell_changed(self, row: int, column: int) -> None:
        """Handle coordinate manual entry in reference points table."""
        if row >= len(self.ref_points_data):
            return

        item_x = self.table_ref_points.item(row, 2)
        item_y = self.table_ref_points.item(row, 3)
        text_x = item_x.text().strip() if item_x else ""
        text_y = item_y.text().strip() if item_y else ""

        if column in (2, 3):
            sx: Optional[float] = None
            sy: Optional[float] = None
            if text_x:
                try:
                    sx = float(text_x)
                except ValueError:
                    sx = None
            if text_y:
                try:
                    sy = float(text_y)
                except ValueError:
                    sy = None

            if sx is not None and sy is not None:
                # User entered survey coordinates (column 2=X(North), column 3=Y(East))
                # Convert to internal mathematical coordinates
                math_x, math_y = from_survey_coords(sx, sy)
                self.ref_points_data[row]["real_x"] = math_x
                self.ref_points_data[row]["real_y"] = math_y
            else:
                self.ref_points_data[row]["real_x"] = None
                self.ref_points_data[row]["real_y"] = None

            self.calculated_affine_params = None
            self._update_ref_points_status()

    def _update_ref_points_status(self) -> None:
        """Refresh reference point UI state and validate button enabling."""
        count = len(self.ref_points_data)
        fname = (
            self.confirmed_layer_name
            if self.confirmed_layer_name
            else (
                os.path.basename(self.current_copied_image_path)
                if self.current_copied_image_path
                else UILabels.UNLOADED
            )
        )
        self.lbl_tab1_info_1.setText(
            UILabels.TAB1_INFO_IMAGE_REF.format(name=fname, count=count)
        )
        self.lbl_tab1_info_3_6.setText("")

        # Check if at least 2 points exist and all have valid coordinates
        all_coords_valid = False
        if count >= 2:
            all_coords_valid = all(
                r["real_x"] is not None and r["real_y"] is not None
                for r in self.ref_points_data
            )

        if count < 2:
            self.btn_transform.setEnabled(False)
            self.btn_export_layer.setEnabled(False)
            self.calculated_affine_params = None
            UIStyleHelper.update_status_panel(
                self.panel_tab1_info,
                self.lbl_tab1_info_2,
                UILabels.STATUS_NEED_MORE_REFS.format(count=count),
                status_type="warning",
            )
        elif not all_coords_valid:
            self.btn_transform.setEnabled(False)
            self.btn_export_layer.setEnabled(False)
            self.calculated_affine_params = None
            UIStyleHelper.update_status_panel(
                self.panel_tab1_info,
                self.lbl_tab1_info_2,
                UILabels.STATUS_INPUT_COORDS.format(count=count),
                status_type="info",
            )
        else:
            self.btn_transform.setEnabled(True)
            mode_str = (
                UILabels.TRANSFORM_HELMERT
                if count == 2
                else UILabels.TRANSFORM_AFFINE.format(count=count)
            )
            if self.calculated_affine_params is None:
                self.btn_export_layer.setEnabled(False)
                UIStyleHelper.update_status_panel(
                    self.panel_tab1_info,
                    self.lbl_tab1_info_2,
                    UILabels.STATUS_READY_TRANSFORM.format(
                        count=count, mode=mode_str
                    ),
                    status_type="info",
                )
            else:
                self.btn_export_layer.setEnabled(True)

    def _on_delete_selected_ref_point(self) -> None:
        """Delete selected reference point from list and table."""
        current_row = self.table_ref_points.currentRow()
        if current_row < 0 or current_row >= len(self.ref_points_data):
            QMessageBox.information(
                self,
                UIMessages.MSG_TITLE_INFO,
                UIMessages.MSG_SELECT_REF_ROW,
            )
            return

        del self.ref_points_data[current_row]
        self.calculated_affine_params = None
        self._refresh_ref_points_table_and_markers()

    def _on_clear_all_refs(self) -> None:
        """Clear all reference points."""
        self.ref_points_data.clear()
        self.calculated_affine_params = None
        self._refresh_ref_points_table_and_markers()

    def _refresh_ref_points_table_and_markers(self) -> None:
        """Re-render table and vertex markers based on current ref_points_data."""
        if self.preview_dialog:
            self.preview_dialog.clear_markers()
            self.preview_dialog.set_ref_points_data(self.ref_points_data)

        self.table_ref_points.blockSignals(True)
        self.table_ref_points.setRowCount(0)

        for i, rdata in enumerate(self.ref_points_data):
            self.table_ref_points.insertRow(i)

            name_item = QTableWidgetItem(rdata["name"])
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_ref_points.setItem(i, 0, name_item)

            pix_item = QTableWidgetItem(f"({rdata['pixel_x']:.1f}, {rdata['pixel_y']:.1f})")
            pix_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_ref_points.setItem(i, 1, pix_item)

            if rdata["real_x"] is not None and rdata["real_y"] is not None:
                sx, sy = to_survey_coords(float(rdata["real_x"]), float(rdata["real_y"]))
                rx_str = f"{sx:.3f}"
                ry_str = f"{sy:.3f}"
            else:
                rx_str = ""
                ry_str = ""
            self.table_ref_points.setItem(i, 2, QTableWidgetItem(rx_str))
            self.table_ref_points.setItem(i, 3, QTableWidgetItem(ry_str))

            if self.preview_dialog:
                self.preview_dialog.add_marker(rdata["pixel_x"], rdata["pixel_y"], rdata["name"])

        self.table_ref_points.blockSignals(False)
        self._update_ref_points_status()

    def _on_transform_clicked(self) -> None:
        """Compute transformation parameters and evaluate residuals without writing files or placing layers.
        # 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。
        """
        if len(self.ref_points_data) < 2:
            QMessageBox.warning(
                self,
                UIMessages.ERR_TITLE_GENERIC,
                UIMessages.ERR_MIN_2_REFS,
            )
            return

        local_pts: List[Tuple[float, float]] = []
        real_pts: List[Tuple[float, float]] = []

        for rdata in self.ref_points_data:
            if rdata["real_x"] is None or rdata["real_y"] is None:
                QMessageBox.warning(
                    self,
                    UIMessages.ERR_TITLE_INPUT,
                    UIMessages.ERR_INPUT_REAL_COORDS.format(name=rdata["name"]),
                )
                return
            local_pts.append((float(rdata["pixel_x"]), float(rdata["pixel_y"])))
            # Standard mathematical coordinates: (math_x=East, math_y=North)
            real_pts.append((float(rdata["real_x"]), float(rdata["real_y"])))

        affine_params = CoordinateTransformer.compute_affine_points(
            local_pts, real_pts, parent=self
        )
        if affine_params is None:
            return

        self.calculated_affine_params = affine_params

        # Evaluate transformation indicators using core_logic
        rotation_deg, aspect_ratio_pct = evaluate_residuals(self.ref_points_data, affine_params)
        mode_str = (
            UILabels.TRANSFORM_HELMERT
            if len(local_pts) == 2
            else UILabels.TRANSFORM_AFFINE.format(count=len(local_pts))
        )

        res_summary = (
            f"【{mode_str} 計算完了】\n"
            f"画像の回転角度: {rotation_deg:.2f} 度\n"
            f"アスペクト比(縦/横): {aspect_ratio_pct:.2f} %"
        )
        self.lbl_tab1_info_3_6.setText(res_summary)
        
        UIStyleHelper.update_status_panel(
            self.panel_tab1_info,
            self.lbl_tab1_info_2,
            UILabels.TAB1_INFO_TRANSFORM_DONE,
            status_type="success",
        )

        self.btn_export_layer.setEnabled(True)
        self.iface.messageBar().pushMessage(
            UIMessages.MSG_TITLE_INFO,
            UILabels.MSG_TRANSFORM_SUCCESS,
            level=Qgis.MessageLevel.Success,
            duration=4,
        )

        # Show transformation results dialog
        info_dialog_msg = (
            f"座標変換パラメータの計算が完了しました。\n\n"
            f"画像の回転角度: {rotation_deg:.2f} 度\n"
            f"アスペクト比(縦/横): {aspect_ratio_pct:.2f} %"
        )
        QMessageBox.information(
            self,
            "座標変換完了",
            info_dialog_msg,
        )

    def _on_export_layer_clicked(self) -> None:
        """Write world file, update metadata, update points, and load to canvas."""
        if self.calculated_affine_params is None:
            QMessageBox.warning(
                self,
                UIMessages.ERR_TITLE_GENERIC,
                UILabels.ERR_TRANSFORM_NOT_CALCULATED,
            )
            return

        layer_name = self.confirmed_layer_name or self.edit_image_name.text().strip()
        if not self.current_copied_image_path or not os.path.isfile(self.current_copied_image_path):
            session_img_dir = self.layer_manager.session_image_dir
            if session_img_dir and os.path.exists(session_img_dir):
                candidates = [
                    os.path.join(session_img_dir, f)
                    for f in os.listdir(session_img_dir)
                    if os.path.splitext(f)[0] == layer_name
                ]
                if candidates:
                    self.current_copied_image_path = candidates[0]

        if not self.current_copied_image_path or not os.path.isfile(self.current_copied_image_path):
            QMessageBox.critical(
                self,
                UIMessages.ERR_TITLE_FILE,
                "対象画像ファイルが見つかりません。",
            )
            return

        # 1. Write world file
        success, msg, _ = self.layer_manager.write_world_file(
            self.current_copied_image_path, self.calculated_affine_params
        )
        if not success:
            QMessageBox.critical(
                self,
                UIMessages.ERR_TITLE_GENERIC,
                UIMessages.ERR_WORLDFILE_FAILED.format(msg=msg),
            )
            return

        # 2. Persist reference points and affine params into JSON metadata
        self.layer_manager.update_image_metadata(
            layer_name,
            self.current_copied_image_path,
            self.ref_points_data,
            self.calculated_affine_params
        )

        # 3. Batch update coordinates and geometry for matching points
        if self.point_layer and self.point_layer.isValid():
            update_point_layer_geometry(
                self.point_layer,
                self.calculated_affine_params,
                drawing_name=layer_name,
            )

        # 4. Load georeferenced raster to main canvas with specified layer name
        success, msg, raster_layer = self.layer_manager.load_georeferenced_raster(
            self.current_copied_image_path, custom_layer_name=layer_name
        )
        if not success or raster_layer is None:
            QMessageBox.critical(
                self,
                UIMessages.ERR_TITLE_GENERIC,
                UIMessages.ERR_CANVAS_PLACEMENT_FAILED.format(msg=msg),
            )
            return

        self.canvas.setExtent(raster_layer.extent())
        self.canvas.refresh()

        # 5. Clean up dynamic preview canvas
        self._destroy_preview_canvas()

        # 6. Dynamically refresh target drawing combo & multi-selector in Tab 2 and select new layer
        self._update_drawing_combo()
        if layer_name:
            idx = self.combo_drawing_name.findText(layer_name)
            if idx >= 0:
                self.combo_drawing_name.setCurrentIndex(idx)
            self._ensure_drawing_visible(layer_name)

        self.iface.messageBar().pushMessage(
            UIMessages.MSG_GEOREF_COMPLETE_TITLE,
            UIMessages.MSG_GEOREF_COMPLETE,
            level=Qgis.MessageLevel.Success,
            duration=6,
        )

        # Clear UI state if in new add mode
        if self.tab1_mode_buttons[0].isChecked():
            self.edit_image_path.clear()
            self.edit_image_name.clear()
            self.ref_points_data.clear()
            self.calculated_affine_params = None
            self.confirmed_layer_name = None
            self._refresh_ref_points_table_and_markers()

        # 7. Automatically switch to Tab 2
        self.tab_widget.setCurrentIndex(1)

