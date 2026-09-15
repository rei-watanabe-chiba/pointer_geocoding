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
the preview_* backward-compatible properties, _init_ui, _on_panel_changed
(formerly _on_tab_changed; see T-0020 note below), _save_project,
closeEvent, and update_symbology_opacity (shared by Tab 2's Focus Mode and
Tab 3's settings-apply flow).

Stage E split (logic-preserving relocation): update_symbology_opacity()'s
expression-construction and renderer-mutation logic now lives in
SymbologyMixin (symbology_mixin.py) as build_opacity_expression()/
apply_opacity_expression(), reached here via self.layer_manager (which
mixes SymbologyMixin in). update_symbology_opacity() itself remains as a
thin delegator that only gathers current UI state, so its name/signature
and all call sites (tab2_digitizing_mixin.py, and _on_panel_changed below)
are unchanged.

T-0020 (UI restructure): the former QTabWidget (Tab1/Tab2/Tab3) has been
replaced with a left icon rail + collapsible side panel layout. Tab 1
(図面管理) and Tab 3 (設定) now live inside a fixed-width side panel
(self.side_panel / self.side_stack) toggled open/closed by checkable nav
buttons (self.nav_btn_drawing / self.nav_btn_settings) on a left icon rail,
VSCode-activity-bar style: clicking a nav button opens its panel, clicking
the already-open panel's button closes it, and opening one panel
automatically closes the other. Tab 2 (遺物点作成) is no longer a tab at
all; its container is always visible as the main area. The former
_on_tab_changed(index) QTabWidget.currentChanged handler is replaced by
_on_panel_changed(), driven by self._active_panel ("drawing" / "settings"
/ None), which is invoked whenever the open side panel changes (including
once at __init__ time, matching the old initial currentChanged fire).
self.tab1_container / self.tab2_container / self.tab3_container attribute
names are kept unchanged for backward compatibility with tab*_mixin.py.
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
    QHBoxLayout,
    QPushButton,
    QToolButton,
    QButtonGroup,
    QStackedWidget,
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

        # Initial panel state (T-0020): both side panels start closed, so the
        # digitizing main area (former Tab 2) is shown by default. This
        # mirrors the old QTabWidget.currentChanged() initial fire that used
        # to run once at startup, now driven explicitly since there is no
        # tab-change signal to trigger it.
        self._on_panel_changed()

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

    # T-0020: fixed pixel widths for the left icon rail and the collapsible
    # side panel it toggles open/closed (VSCode activity-bar style).
    ICON_RAIL_WIDTH = 52
    SIDE_PANEL_WIDTH = 300

    def _init_ui(self) -> None:
        """Construct the entire dock interface programmatically using native PyQt classes."""
        root_widget = QWidget(self)
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        # No side panel open by default; the digitizing main area (former
        # Tab 2) is shown on its own until a nav button opens one.
        self._active_panel: Optional[str] = None

        # 1. Permanent Save Button Header
        self.btn_save_project = QPushButton(UILabels.BTN_SAVE_PROJECT, root_widget)
        UIStyleHelper.set_success_button(self.btn_save_project)
        self.btn_save_project.clicked.connect(self._save_project)
        root_layout.addWidget(self.btn_save_project)

        # 2. Content row: left icon rail + collapsible side panel + main area
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(6)
        root_layout.addLayout(content_row)

        # 2a. Icon rail: nav buttons toggling the side panel open/closed
        icon_rail = QWidget(root_widget)
        icon_rail.setFixedWidth(self.ICON_RAIL_WIDTH)
        icon_rail_layout = QVBoxLayout(icon_rail)
        icon_rail_layout.setContentsMargins(2, 4, 2, 4)
        icon_rail_layout.setSpacing(4)

        self.nav_btn_drawing = QToolButton(icon_rail)
        self.nav_btn_drawing.setObjectName("navBtnDrawing")
        self.nav_btn_drawing.setText(UILabels.NAV_DRAWING)
        self.nav_btn_drawing.setToolTip(UILabels.TAB_1_TITLE)
        self.nav_btn_drawing.setCheckable(True)
        self.nav_btn_drawing.setFixedHeight(48)
        UIStyleHelper.set_nav_button(self.nav_btn_drawing)
        icon_rail_layout.addWidget(self.nav_btn_drawing)

        self.nav_btn_settings = QToolButton(icon_rail)
        self.nav_btn_settings.setObjectName("navBtnSettings")
        self.nav_btn_settings.setText(UILabels.NAV_SETTINGS)
        self.nav_btn_settings.setToolTip(UILabels.TAB_3_TITLE)
        self.nav_btn_settings.setCheckable(True)
        self.nav_btn_settings.setFixedHeight(48)
        UIStyleHelper.set_nav_button(self.nav_btn_settings)
        icon_rail_layout.addWidget(self.nav_btn_settings)

        icon_rail_layout.addStretch()

        # QButtonGroup provides the "opening one panel closes the other"
        # exclusivity. Re-clicking the already-open panel's button to close
        # it is handled explicitly in _on_nav_button_clicked(), since an
        # exclusive QButtonGroup does not let its checked button become
        # unchecked purely by clicking it again.
        self.nav_button_group = QButtonGroup(icon_rail)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.nav_btn_drawing)
        self.nav_button_group.addButton(self.nav_btn_settings)

        self.nav_btn_drawing.clicked.connect(lambda: self._on_nav_button_clicked("drawing"))
        self.nav_btn_settings.clicked.connect(lambda: self._on_nav_button_clicked("settings"))

        content_row.addWidget(icon_rail)

        # 2b. Side panel: 図面管理 (Tab 1) / 設定 (Tab 3), hidden by default
        self.side_panel = QWidget(root_widget)
        self.side_panel.setFixedWidth(self.SIDE_PANEL_WIDTH)
        side_panel_layout = QVBoxLayout(self.side_panel)
        side_panel_layout.setContentsMargins(0, 0, 0, 0)
        side_panel_layout.setSpacing(0)

        self.side_stack = QStackedWidget(self.side_panel)
        side_panel_layout.addWidget(self.side_stack)

        # 図面管理 (former Tab 1: Image Add & Pre-Georeferencing)
        self.tab1_container = self._create_tab1_ui()
        self.side_stack.addWidget(self.tab1_container)

        # 設定 (former Tab 3: Settings)
        self.tab3_container = self._create_tab3_ui()
        self.side_stack.addWidget(self.tab3_container)

        self.side_panel.hide()
        content_row.addWidget(self.side_panel)

        # 2c. Main area: 遺物点作成 (former Tab 2), always visible, no tab chrome
        self.tab2_container = self._create_tab2_ui()
        content_row.addWidget(self.tab2_container, 1)

        self.setWidget(root_widget)

    def _on_nav_button_clicked(self, panel: str) -> None:
        """Handle a click on a left icon-rail nav button (図面管理/設定).

        Clicking a closed panel's button opens it (and, via the exclusive
        QButtonGroup, closes the other one automatically). Clicking the
        already-open panel's button closes it, returning to the default
        state where only the main digitizing area is shown.

        :param panel: Which nav button was clicked ("drawing" or "settings").
        :type panel: str
        """
        if self._active_panel == panel:
            button = self.nav_btn_drawing if panel == "drawing" else self.nav_btn_settings
            button.setChecked(False)
            self._active_panel = None
        else:
            self._active_panel = panel
        self._on_panel_changed()

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
        Tab3's settings-apply flow (via _on_panel_changed) need no changes.
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


    def _on_panel_changed(self) -> None:
        """Handle a change in which side panel is open (T-0020).

        Driven by self._active_panel: "drawing" (former Tab 1 open),
        "settings" (former Tab 3 open), or None (both closed, main
        digitizing area shown - the default state). Replaces the old
        QTabWidget.currentChanged()-driven _on_tab_changed(index).
        """
        if self._active_panel == "drawing":
            # 図面管理 side panel open: unset main map tool
            self.side_panel.show()
            self.side_stack.setCurrentWidget(self.tab1_container)
            self.canvas.unsetMapTool(self.map_tool)
        elif self._active_panel == "settings":
            # 設定 side panel open: unset main map tool, refresh settings UI
            self.side_panel.show()
            self.side_stack.setCurrentWidget(self.tab3_container)
            self.canvas.unsetMapTool(self.map_tool)
            self.update_settings_ui_from_dict()
        else:
            # Both panels closed: main digitizing area (former Tab 2) is
            # active. Activate main digitizing tool and refresh drawings.
            self.side_panel.hide()
            self._update_drawing_combo()
            self.canvas.setMapTool(self.map_tool)
            self._reset_point_selection()
            if self.is_focus_mode_active():
                self.update_symbology_opacity()

    def _close_side_panel(self) -> None:
        """Close any open side panel (図面管理/設定), returning to the
        default view where only the main digitizing area is shown.

        Replaces the old self.tab_widget.setCurrentIndex(1) auto-switch to
        Tab 2, e.g. after 図面管理's "レイヤ出力" (coordinate transform +
        layer export) completes (see tab1_georef_mixin.py).
        """
        self.nav_btn_drawing.setChecked(False)
        self.nav_btn_settings.setChecked(False)
        self._active_panel = None
        self._on_panel_changed()

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
