"""
/***************************************************************************
 PointerGeocoding Plugin - Main Operation Dock Panel
 ***************************************************************************/

Stage B split (mechanical, logic-preserving): the UI-construction and
event-handling code for each tab previously lived directly in this file.
It has been extracted, without any logic changes, into per-tab mixin
modules (tab1_georef_mixin.py, tab2_digitizing_mixin.py,
tab3_settings_mixin.py) plus shared constant/dialog modules
(main_dock_constants.py, main_dock_dialogs.py). MainDockWidget now mixes
those tab mixins in and keeps only the shared/common members: __init__,
the preview_* backward-compatible properties, _init_ui, _on_tab_changed,
_save_project, closeEvent, and update_symbology_opacity (shared by Tab 2's
Focus Mode and Tab 3's settings-apply flow).

Stage E split (logic-preserving relocation): update_symbology_opacity()'s
expression-construction and renderer-mutation logic now lives in
SymbologyMixin (symbology_mixin.py) as build_opacity_expression()/
apply_opacity_expression(), reached here via self.layer_manager (which
mixes SymbologyMixin in). update_symbology_opacity() itself remains as a
thin delegator that only gathers current UI state, so its name/signature
and all call sites (tab2_digitizing_mixin.py, and _on_tab_changed below)
are unchanged.
"""
# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

from typing import Optional, Dict, Any, List, Tuple

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    Qgis,
)
from qgis.gui import (
    QgisInterface,
    QgsMapCanvas,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTabWidget,
)

from .map_tool import CanvasDigitizingTool, ImageGeorefTool
from .style_helper import UIStyleHelper
# NOTE: UIConfig is not used directly in this module's own body, but is
# re-exported here (rather than only via main_dock_constants) because
# layer_manager.py and map_tool.py perform ``from .main_dock import UIConfig``
# at call time. Keeping this import preserves that existing cross-module
# contract unchanged after the Stage B mechanical split.
from .main_dock_constants import UIConfig, UILabels, UIMessages
from .main_dock_dialogs import PreviewDialog
from .tab1_georef_mixin import Tab1GeorefMixin
from .tab2_digitizing_mixin import Tab2DigitizingMixin
from .tab3_settings_mixin import Tab3SettingsMixin


class MainDockWidget(QDockWidget, Tab1GeorefMixin, Tab2DigitizingMixin, Tab3SettingsMixin):
    """Main dock widget hosting Tab 1 (Image Add & Pre-Georeferencing)
    and Tab 2 (Artifact Point Digitizing & CSV Export)."""

    INVALID_CHARS_PATTERN = r'[\\/:*?"<>|]'

    def __init__(
        self,
        iface: QgisInterface,
        layer_manager: Any,
        layers_dict: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the main dock widget.

        :param iface: QGIS interface reference.
        :type iface: QgisInterface
        :param layer_manager: LayerManager instance.
        :type layer_manager: Any
        :param layers_dict: Dictionary containing active layer references.
        :type layers_dict: Optional[Dict[str, Any]]
        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(UILabels.DOCK_TITLE, parent)
        self.iface = iface
        self.layer_manager = layer_manager
        self.layers_dict = layers_dict or {}

        self.point_layer: Optional[QgsVectorLayer] = self.layers_dict.get("point_layer")
        self.ref_point_layer: Optional[QgsVectorLayer] = self.layers_dict.get("ref_point_layer")
        self.canvas: QgsMapCanvas = self.iface.mapCanvas()

        # Tab 1: Georeferencing preview state
        self.preview_dialog: Optional[PreviewDialog] = None
        self.current_copied_image_path: Optional[str] = None
        self.confirmed_layer_name: Optional[str] = None
        self.calculated_affine_params: Optional[Tuple[float, float, float, float, float, float]] = None
        # Reference points in memory: [{'name': str, 'pixel_x': float, 'pixel_y': float, 'real_x': float, 'real_y': float}]
        self.ref_points_data: List[Dict[str, Any]] = []

        # Tab 2: Digitizing state
        self.current_feature_color = QColor("#FF5722")
        self.selected_edit_point_id: Optional[int] = None
        self.feature_name_list: List[str] = []
        self._has_digitized_with_branch: bool = False

        # Main digitizing tool for real-world canvas
        self.map_tool = CanvasDigitizingTool(
            self.canvas, self.point_layer, dock_widget=self, layer_manager=self.layer_manager
        )
        self.map_tool.canvas_clicked.connect(self._on_canvas_clicked)
        self.map_tool.existing_point_selected.connect(self._on_existing_point_selected)
        # Step3-B: react to LayerManager persisting settings, rather than the
        # settings-apply handler doing the UI refresh inline.
        self.layer_manager.settings_changed.connect(self._on_layer_manager_settings_changed)

        self._init_ui()
        UIStyleHelper.apply_theme(self)
        self._restore_feature_names()
        self._update_drawing_combo()
        self.update_settings_ui_from_dict()
        # Step3: push initial Focus Mode state now that the category widgets exist,
        # so map_tool's cache is valid before any canvas interaction.
        self._push_focus_state_to_tool()

        # Connect project layer additions/removals to dynamically update drawing combo box & list
        project = QgsProject.instance()
        if project is not None:
            project.layersAdded.connect(self._update_drawing_combo)
            project.layersRemoved.connect(self._update_drawing_combo)

        # Initial active tab handling
        if self.layer_manager.raster_layer is not None and self.layer_manager.raster_layer.isValid():
            self.tab_widget.setCurrentIndex(1)
            self.canvas.setMapTool(self.map_tool)
        else:
            self.tab_widget.setCurrentIndex(0)
            self.canvas.unsetMapTool(self.map_tool)

    @property
    def preview_canvas(self) -> Optional[QgsMapCanvas]:
        """Backward compatible preview canvas reference."""
        return self.preview_dialog.canvas if self.preview_dialog else None

    @property
    def preview_raster_layer(self) -> Optional[QgsRasterLayer]:
        """Backward compatible preview raster layer reference."""
        return self.preview_dialog.raster_layer if self.preview_dialog else None

    @property
    def georef_tool(self) -> Optional[ImageGeorefTool]:
        """Backward compatible preview georef tool reference."""
        return self.preview_dialog.georef_tool if self.preview_dialog else None

    def _init_ui(self) -> None:
        """Construct the entire dock interface programmatically using native PyQt classes."""
        root_widget = QWidget(self)
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        # 1. Permanent Save Button Header
        self.btn_save_project = QPushButton(UILabels.BTN_SAVE_PROJECT, root_widget)
        UIStyleHelper.set_success_button(self.btn_save_project)
        self.btn_save_project.clicked.connect(self._save_project)
        root_layout.addWidget(self.btn_save_project)

        # 2. Main Tab Widget Container [EXCEPTION PROTECTION: Full-width tab container]
        self.tab_widget = QTabWidget(root_widget)
        root_layout.addWidget(self.tab_widget)

        # Tab 1: Image Add & Pre-Georeferencing (画像管理)
        self.tab1_container = self._create_tab1_ui()
        self.tab_widget.addTab(self.tab1_container, UILabels.TAB_1_TITLE)

        # Tab 2: Artifact Point Digitizing
        self.tab2_container = self._create_tab2_ui()
        self.tab_widget.addTab(self.tab2_container, UILabels.TAB_2_TITLE)

        # Tab 3: Settings
        self.tab3_container = self._create_tab3_ui()
        self.tab_widget.addTab(self.tab3_container, UILabels.TAB_3_TITLE)

        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        self.setWidget(root_widget)

    def update_symbology_opacity(self) -> None:
        """Update point layer symbol opacity dynamically using QgsProperty expression override.

        When Focus Mode is ON:
            Points matching all 4 current category values (drawing_name, excavation_type,
            feature_name, attribute_type) have 100% opacity,
            while non-matching points have opacity equal to slider value (0-100%).
        When Focus Mode is OFF:
            All points have 100% opacity.

        Thin delegator (Stage E): gathers the current UI state (Focus Mode
        flag, category filter values, opacity slider value) and hands the
        expression construction and its application to the layer's renderer
        off to SymbologyMixin (via layer_manager), which owns both halves of
        this logic alongside apply_point_labeling/apply_ref_point_symbology.
        Kept under this same name/signature so Tab2's Focus Mode toggle and
        Tab3's settings-apply flow (via _on_tab_changed) need no changes.
        """
        if not self.point_layer or not self.point_layer.isValid():
            return

        is_focus_on = self.is_focus_mode_active()
        slider_val = self.slider_opacity.value()

        filters: Dict[str, str] = {}
        if is_focus_on:
            feat_name = self.combo_feature_name.currentText().strip()
            if feat_name == UILabels.FEATURE_NEW_OPTION:
                feat_name = self.edit_new_feature.text().strip()
            filters = {
                "drawing_name": self.combo_drawing_name.currentText().strip(),
                "excavation_type": self.combo_excavation_type.currentText().strip(),
                "feature_name": feat_name,
                "attribute_type": self.combo_attribute.currentText().strip(),
            }

        expr = self.layer_manager.build_opacity_expression(is_focus_on, filters, slider_val)
        self.layer_manager.apply_opacity_expression(self.point_layer, expr)

        if hasattr(self, "canvas") and self.canvas:
            self.canvas.refresh()


    def _on_tab_changed(self, index: int) -> None:
        """Handle switching between tabs."""
        if index == 1:
            # Tab 2: Activate main digitizing tool and refresh drawings
            self._update_drawing_combo()
            self.canvas.setMapTool(self.map_tool)
            self._reset_point_selection()
            if self.is_focus_mode_active():
                self.update_symbology_opacity()
        elif index == 2:
            # Tab 3: Settings tab
            self.canvas.unsetMapTool(self.map_tool)
            self.update_settings_ui_from_dict()
        else:
            # Tab 1: Unset main map tool
            self.canvas.unsetMapTool(self.map_tool)

    def _save_project(self) -> None:
        """Save project state through LayerManager and display notification."""
        success = self.layer_manager.save_project()
        if success:
            self.iface.messageBar().pushMessage(
                UIMessages.MSG_SAVE_TITLE,
                UIMessages.MSG_SAVE_SUCCESS,
                level=Qgis.MessageLevel.Success,
                duration=4,
            )
        else:
            self.iface.messageBar().pushMessage(
                UIMessages.MSG_SAVE_TITLE,
                UIMessages.MSG_SAVE_FAILED,
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )

    def closeEvent(self, event: Any) -> None:
        """Clean up map tools and canvases when dock is closed."""
        try:
            project = QgsProject.instance()
            if project is not None:
                project.layersAdded.disconnect(self._update_drawing_combo)
                project.layersRemoved.disconnect(self._update_drawing_combo)
        except (TypeError, RuntimeError):
            pass

        self._destroy_preview_canvas()
        if self.map_tool:
            self.map_tool.clean_up()
        super().closeEvent(event)
