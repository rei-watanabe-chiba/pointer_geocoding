"""
/***************************************************************************
 PointerGeocoding Plugin - Custom Map Digitizing and Georeferencing Tools
 ***************************************************************************/
"""
# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

import math
from typing import Optional, Any, Dict, List, Tuple

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
    QgsFeatureRequest,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsMarkerSymbol,
    QgsSimpleMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsCoordinateReferenceSystem,
    QgsSpatialIndex,
    QgsProperty,
    QgsSymbol,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
    Qgis,
)
from qgis.gui import (
    QgsMapTool,
    QgsMapCanvas,
    QgsMapMouseEvent,
    QgsVertexMarker,
    QgsMapCanvasItem,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QRectF
from qgis.PyQt.QtGui import QColor, QCursor, QFont, QPainter
from qgis.PyQt.QtWidgets import QInputDialog, QWidget

from .symbology_mixin import SymbologyMixin

class PreviewTextItem(QgsMapCanvasItem):
    """Temporary canvas item to display text labels for reference points."""
    def __init__(self, canvas: QgsMapCanvas, map_pt: QgsPointXY, text: str, font_size: int = 10):
        super().__init__(canvas)
        self.map_pt = map_pt
        self.text = text
        self.font = QFont("sans-serif", font_size)
        self.font.setBold(True)
        self.setPos(self.toCanvasCoordinates(self.map_pt))

    def paint(self, painter: QPainter, option: Any = None, widget: Optional[QWidget] = None) -> None:
        painter.setFont(self.font)
        painter.setPen(QColor("#D32F2F"))
        # Offset to top right
        painter.drawText(10, -10, self.text)

    def boundingRect(self) -> QRectF:
        return QRectF(0, -30, 150, 40)

    def updatePosition(self) -> None:
        self.setPos(self.toCanvasCoordinates(self.map_pt))


class ImageGeorefTool(QgsMapTool):
    """Custom QgsMapTool for picking reference points on the temporary preview canvas.

    Translates preview canvas coordinates into image pixel coordinates (X, Y)
    where (0, 0) is the top-left of the image. Provides 15px hover snap detection and visual box marker.
    """

    point_clicked = pyqtSignal(float, float)  # Emits (pixel_x, pixel_y)

    def __init__(self, canvas: QgsMapCanvas, raster_layer: QgsRasterLayer) -> None:
        """Initialize preview georeferencing tool.

        :param canvas: Preview map canvas instance.
        :type canvas: QgsMapCanvas
        :param raster_layer: The unreferenced raster layer being previewed.
        :type raster_layer: QgsRasterLayer
        """
        super().__init__(canvas)
        self.canvas = canvas
        self.raster_layer = raster_layer
        self.markers: List[QgsVertexMarker] = []
        self.text_items: List[PreviewTextItem] = []
        self.ref_points_data: List[Dict[str, Any]] = []

        # Highlight marker for snapping on hover
        self.snap_marker = QgsVertexMarker(self.canvas)
        self.snap_marker.setIconType(QgsVertexMarker.ICON_BOX)
        self.snap_marker.setColor(QColor("#D32F2F"))
        self.snap_marker.setPenWidth(2)
        self.snap_marker.setIconSize(14)
        self.snap_marker.hide()

    def set_ref_points_data(self, ref_points_data: List[Dict[str, Any]]) -> None:
        """Update reference points list for hover snapping.

        :param ref_points_data: List of reference point dicts.
        :type ref_points_data: List[Dict[str, Any]]
        """
        self.ref_points_data = ref_points_data

    def activate(self) -> None:
        """Called when tool is activated on the preview canvas."""
        super().activate()
        self.setCursor(Qt.CrossCursor)

    def deactivate(self) -> None:
        """Called when tool is deactivated."""
        if self.snap_marker:
            self.snap_marker.hide()
        super().deactivate()

    def canvasMoveEvent(self, event: QgsMapMouseEvent) -> None:
        """Highlight nearby reference points within 15px with visual box marker on hover."""
        if not self.raster_layer or not self.raster_layer.isValid() or not self.ref_points_data:
            if self.snap_marker:
                self.snap_marker.hide()
            self.setCursor(Qt.CrossCursor)
            return

        extent = self.raster_layer.extent()
        w = float(self.raster_layer.width())
        h = float(self.raster_layer.height())
        if w <= 0 or h <= 0 or extent.width() <= 0 or extent.height() <= 0:
            if self.snap_marker:
                self.snap_marker.hide()
            self.setCursor(Qt.CrossCursor)
            return

        mouse_screen = event.pos()
        snapped_pt: Optional[QgsPointXY] = None
        min_dist = float("inf")

        for rdata in self.ref_points_data:
            rx = float(rdata.get("pixel_x", 0.0))
            ry = float(rdata.get("pixel_y", 0.0))
            r_map_x = extent.xMinimum() + (rx / w) * extent.width()
            r_map_y = extent.yMaximum() - (ry / h) * extent.height()
            r_screen = self.toCanvasCoordinates(QgsPointXY(r_map_x, r_map_y))

            dist = math.hypot(
                mouse_screen.x() - r_screen.x(),
                mouse_screen.y() - r_screen.y(),
            )
            if dist <= 15.0 and dist < min_dist:
                min_dist = dist
                snapped_pt = QgsPointXY(r_map_x, r_map_y)

        if snapped_pt is not None:
            self.snap_marker.setCenter(snapped_pt)
            self.snap_marker.show()
            self.setCursor(Qt.PointingHandCursor)
        else:
            if self.snap_marker:
                self.snap_marker.hide()
            self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event: QgsMapMouseEvent) -> None:
        """Process mouse release event on the preview canvas to emit pixel coordinates."""
        if event.button() != Qt.LeftButton:
            return

        map_point = self.toMapCoordinates(event.pos())
        if not self.raster_layer or not self.raster_layer.isValid():
            self.point_clicked.emit(map_point.x(), abs(map_point.y()))
            return

        extent = self.raster_layer.extent()
        w = float(self.raster_layer.width())
        h = float(self.raster_layer.height())

        if extent.width() > 0 and extent.height() > 0 and w > 0 and h > 0:
            pixel_x = (map_point.x() - extent.xMinimum()) / (extent.width() / w)
            pixel_y = (extent.yMaximum() - map_point.y()) / (extent.height() / h)
        else:
            pixel_x = map_point.x()
            pixel_y = abs(map_point.y())

        # Clamp within pixel bounds
        pixel_x = max(0.0, min(w, pixel_x))
        pixel_y = max(0.0, min(h, pixel_y))

        self.point_clicked.emit(pixel_x, pixel_y)

    def add_point_marker(self, pixel_x: float, pixel_y: float, name: str = "") -> None:
        """Place a visual vertex marker on the preview canvas at the given pixel location.

        :param pixel_x: X pixel coordinate.
        :type pixel_x: float
        :param pixel_y: Y pixel coordinate.
        :type pixel_y: float
        :param name: Label text for the point.
        :type name: str
        """
        if not self.raster_layer or not self.raster_layer.isValid():
            return

        extent = self.raster_layer.extent()
        w = float(self.raster_layer.width())
        h = float(self.raster_layer.height())
        if w <= 0 or h <= 0:
            return

        map_x = extent.xMinimum() + (pixel_x / w) * extent.width()
        map_y = extent.yMaximum() - (pixel_y / h) * extent.height()
        map_pt = QgsPointXY(map_x, map_y)

        # Import UIConfig lazily to avoid circular imports if any, or directly if okay.
        # Actually it's easier to just use hardcoded default or import.
        from .main_dock import UIConfig

        marker = QgsVertexMarker(self.canvas)
        marker.setIconType(QgsVertexMarker.ICON_CROSS)
        marker.setColor(QColor("#D32F2F"))
        marker.setPenWidth(2)
        # Convert mm to approx pixels or use fixed size, here UIConfig says 4.0 but that's for QgsSymbol.
        # Let's use 12 for canvas vertex marker.
        marker.setIconSize(12)
        marker.setCenter(map_pt)
        marker.show()
        self.markers.append(marker)

        if name:
            label = PreviewTextItem(self.canvas, map_pt, name, font_size=UIConfig.LABEL_SIZE_REF)
            self.text_items.append(label)

    def clear_markers(self) -> None:
        """Remove all visual vertex markers from the preview canvas scene."""
        for m in self.markers:
            try:
                self.canvas.scene().removeItem(m)
            except Exception:
                pass
        self.markers.clear()
        
        for t in self.text_items:
            try:
                self.canvas.scene().removeItem(t)
            except Exception:
                pass
        self.text_items.clear()
        self.markers.clear()

    def clean_up(self) -> None:
        """Clean up map tool markers."""
        self.clear_markers()
        if self.snap_marker:
            try:
                self.canvas.scene().removeItem(self.snap_marker)
            except Exception:
                pass
            self.snap_marker = None


class CanvasDigitizingTool(QgsMapTool):
    """Custom QgsMapTool for continuous artifact point digitizing on the main canvas.

    Integrates QgsSpatialIndex for high-performance hover snapping,
    supports Focus Mode category filtering, and records canvas/real-world coordinates.
    """

    # Step3: canvas_clicked notifies the dock of a plain click (no existing point hit).
    # Feature validation/construction/layer writes are handled by
    # MainDockWidget._on_canvas_clicked, not by this tool.
    canvas_clicked = pyqtSignal(QgsPointXY)
    existing_point_selected = pyqtSignal(dict)

    def __init__(
        self,
        canvas: QgsMapCanvas,
        point_layer: QgsVectorLayer,
        dock_widget: Optional[QWidget] = None,
        layer_manager: Optional[Any] = None,
    ) -> None:
        """Initialize the digitizing map tool.

        :param canvas: Main map canvas instance.
        :type canvas: QgsMapCanvas
        :param point_layer: Vector layer for digitized points.
        :type point_layer: QgsVectorLayer
        :param dock_widget: Reference to the main dock widget for state synchronization.
        :type dock_widget: Optional[QWidget]
        :param layer_manager: Optional LayerManager instance with spatial index and caches.
        :type layer_manager: Optional[Any]
        """
        super().__init__(canvas)
        self.canvas = canvas
        self.point_layer = point_layer
        self.dock_widget = dock_widget
        self.layer_manager = layer_manager or (
            getattr(dock_widget, "layer_manager", None) if dock_widget else None
        )

        # Highlight vertex marker on hover
        self.hover_marker = QgsVertexMarker(self.canvas)
        self.hover_marker.setIconType(QgsVertexMarker.ICON_BOX)
        self.hover_marker.setColor(QColor("#D32F2F"))
        self.hover_marker.setPenWidth(2)
        self.hover_marker.setIconSize(14)
        self.hover_marker.hide()

        # Focus mode state cache, pushed one-way from MainDockWidget via
        # update_focus_state() (Step3: replaces pulling dock_widget getters).
        self._focus_active: bool = False
        self._focus_filter: Dict[str, str] = {}

        # Initialize categorised symbology for point layer
        current_settings = (
            self.layer_manager.load_settings()
            if self.layer_manager and hasattr(self.layer_manager, "load_settings")
            else None
        )
        self.setup_point_layer_symbology(self.point_layer, current_settings)

    def activate(self) -> None:
        """Called when the map tool becomes active."""
        super().activate()
        self.setCursor(Qt.CrossCursor)

    def deactivate(self) -> None:
        """Called when the map tool is deactivated."""
        if self.hover_marker:
            self.hover_marker.hide()
        super().deactivate()

    def update_focus_state(self, active: bool, filters: Dict[str, str]) -> None:
        """Receive Focus Mode state pushed from MainDockWidget and cache it locally.

        Called by MainDockWidget whenever the focus toggle or any of the four
        category selectors (drawing/excavation/feature/attribute) changes, so
        this tool never needs to call back into the dock widget to read UI state.

        :param active: Whether Focus Mode is currently active.
        :type active: bool
        :param filters: Dict with keys 'drawing_name', 'excavation_type',
            'feature_name', 'attribute_type'.
        :type filters: Dict[str, str]
        """
        self._focus_active = bool(active)
        self._focus_filter = dict(filters) if filters else {}

    @staticmethod
    def setup_point_layer_symbology(
        layer: QgsVectorLayer,
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Apply categorical symbology for attribute types S, P, C, and SP.

        - S: Single circle (○).
        - P: Diamond (◇).
        - C: Triangle (△).
        - SP: Double concentric circle (◎).
        - Stroke color: Configurable via settings["point_symbol_line_color"] for グリッド,
          color_code for 遺構 via data-defined override.
        - Fill color: Matches stroke color if point_symbol_fill_enabled is True, else transparent.

        :param layer: Target point vector layer.
        :type layer: QgsVectorLayer
        :param settings: Optional settings dict (from settings.json). Uses point_symbol_* keys.
        :type settings: Optional[Dict[str, Any]]
        """
        if not layer or not layer.isValid():
            return

        # Resolve fill enabled flag, line color, symbol size, and line width from settings or fallback
        fill_enabled = bool((settings or {}).get("point_symbol_fill_enabled", False))
        grid_line_color = str(
            (settings or {}).get("point_symbol_line_color", (settings or {}).get("point_symbol_color", (settings or {}).get("symbol_color", "#E53935")))
        )
        sym_size = float(
            (settings or {}).get("point_symbol_size", (settings or {}).get("symbol_size", 6.0))
        )
        line_width = float(
            (settings or {}).get("point_symbol_line_width", (settings or {}).get("symbol_line_width", 0.9))
        )
        initial_fill_color = grid_line_color if fill_enabled else "transparent"

        categories: List[QgsRendererCategory] = []
        color_expr = (
            f"CASE WHEN \"excavation_type\" = 'グリッド' THEN '{grid_line_color}' "
            "ELSE coalesce(\"color_code\", '#FF5722') END"
        )
        prop_color = QgsProperty.fromExpression(color_expr)

        # Get stroke color property key
        prop_stroke = getattr(QgsSimpleMarkerSymbolLayer, "PropertyStrokeColor", None)
        if prop_stroke is None:
            prop_stroke = getattr(QgsSymbolLayer, "PropertyStrokeColor", None)
        if prop_stroke is None and hasattr(QgsSymbolLayer, "Property"):
            prop_stroke = getattr(QgsSymbolLayer.Property, "PropertyStrokeColor", None)
        if prop_stroke is None:
            prop_stroke = 2  # Standard QgsSymbolLayer::PropertyStrokeColor enum value

        # Get fill color property key
        prop_fill = getattr(QgsSimpleMarkerSymbolLayer, "PropertyFillColor", None)
        if prop_fill is None:
            prop_fill = getattr(QgsSymbolLayer, "PropertyFillColor", None)
        if prop_fill is None and hasattr(QgsSymbolLayer, "Property"):
            prop_fill = getattr(QgsSymbolLayer.Property, "PropertyFillColor", None)
        if prop_fill is None:
            prop_fill = 1  # Standard QgsSymbolLayer::PropertyFillColor enum value

        # Determine fill property: line color expression if fill enabled, else transparent
        if fill_enabled:
            prop_fill_val = prop_color
        else:
            prop_fill_val = QgsProperty.fromValue("transparent")

        # Standard hollow/filled single shapes: S (丸), P (ダイヤ), C (三角)
        std_specs = [
            ("S", "S (丸)",    "circle",   str(sym_size)),
            ("P", "P (ダイヤ)", "diamond",  str(sym_size)),
            ("C", "C (三角)",  "triangle", str(sym_size)),
        ]

        for val, label, shape, size in std_specs:
            sym_layer = QgsSimpleMarkerSymbolLayer.create({
                "name": shape,
                "color": initial_fill_color,
                "outline_color": "#FF5722",
                "outline_width": str(line_width),
                "size": size,
            })
            sym_layer.setDataDefinedProperty(prop_stroke, prop_color)
            sym_layer.setDataDefinedProperty(prop_fill, prop_fill_val)
            symbol = QgsMarkerSymbol()
            symbol.changeSymbolLayer(0, sym_layer)
            categories.append(QgsRendererCategory(val, symbol, label))

        # SP: Double concentric circle (◎)
        sp_outer = QgsSimpleMarkerSymbolLayer.create({
            "name": "circle",
            "color": initial_fill_color,
            "outline_color": "#FF5722",
            "outline_width": str(line_width),
            "size": str(sym_size + 1.0),
        })
        sp_outer.setDataDefinedProperty(prop_stroke, prop_color)
        sp_outer.setDataDefinedProperty(prop_fill, prop_fill_val)

        sp_inner = QgsSimpleMarkerSymbolLayer.create({
            "name": "circle",
            "color": initial_fill_color,
            "outline_color": "#FF5722",
            "outline_width": str(line_width),
            "size": str(max(sym_size - 2.2, 1.5)),
        })
        sp_inner.setDataDefinedProperty(prop_stroke, prop_color)
        sp_inner.setDataDefinedProperty(prop_fill, prop_fill_val)

        sp_symbol = QgsMarkerSymbol()
        sp_symbol.changeSymbolLayer(0, sp_outer)
        sp_symbol.appendSymbolLayer(sp_inner)
        categories.append(QgsRendererCategory("SP", sp_symbol, "SP (二重丸)"))

        renderer = QgsCategorizedSymbolRenderer("attribute_type", categories)
        layer.setRenderer(renderer)

        # Configure point layer labeling synchronized with symbol stroke color
        lbl_size   = int(  (settings or {}).get("label_size",   10))
        lbl_halo   = bool( (settings or {}).get("label_halo",   True))
        lbl_offset = float((settings or {}).get("label_offset", 1.0))

        pal = QgsPalLayerSettings()
        pal.fieldName = (
            "CASE WHEN \"excavation_type\" = '遺構' THEN \"feature_name\" || '_' ELSE '' END "
            "|| \"point_name\" "
            "|| CASE WHEN \"branch_no\" IS NOT NULL AND \"branch_no\" != '' THEN '-' || \"branch_no\" ELSE '' END"
        )
        pal.isExpression = True
        pal.placement = Qgis.LabelPlacement.OverPoint
        pal.xOffset = lbl_offset
        pal.yOffset = -lbl_offset

        SymbologyMixin.apply_above_right_label_quadrant(pal)

        text_format = QgsTextFormat()
        text_format.setSize(lbl_size)
        text_format.setColor(QColor(grid_line_color))

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(lbl_halo)
        buffer.setSize(1.0)
        buffer.setColor(QColor("white"))
        text_format.setBuffer(buffer)

        pal.setFormat(text_format)

        # Synchronize label font color with point symbol color via data-defined property
        prop_lbl_color = getattr(QgsPalLayerSettings, "Color", None)
        if prop_lbl_color is None and hasattr(QgsPalLayerSettings, "Property"):
            prop_lbl_color = getattr(QgsPalLayerSettings.Property, "Color", None)
        if prop_lbl_color is None:
            prop_lbl_color = 4

        pal.dataDefinedProperties().setProperty(prop_lbl_color, prop_color)

        labeling = QgsVectorLayerSimpleLabeling(pal)
        layer.setLabelsEnabled(True)
        layer.setLabeling(labeling)

        layer.triggerRepaint()

    @staticmethod
    def setup_ref_point_layer_symbology(layer: QgsVectorLayer) -> None:
        """Apply a cross symbol style for reference points.

        :param layer: Target reference point layer.
        :type layer: QgsVectorLayer
        """
        if not layer or not layer.isValid():
            return

        sym_layer = QgsSimpleMarkerSymbolLayer.create({
            "name": "cross",
            "color": "#D32F2F",
            "outline_color": "#D32F2F",
            "outline_width": "1.2",
            "size": "7.0",
        })
        symbol = QgsMarkerSymbol()
        symbol.changeSymbolLayer(0, sym_layer)

        from qgis.core import QgsSingleSymbolRenderer
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        layer.triggerRepaint()

    @staticmethod
    def update_attribute_transparency(layer: QgsVectorLayer, selected_attribute: str) -> None:
        """Set unselected attribute category symbols to 50% opacity and selected category to 100%.

        :param layer: Point layer with QgsCategorizedSymbolRenderer.
        :type layer: QgsVectorLayer
        :param selected_attribute: Current confirmed attribute type ('S', 'P', 'C', 'SP').
        :type selected_attribute: str
        """
        if not layer or not layer.isValid():
            return

        renderer = layer.renderer()
        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            return

        for category in renderer.categories():
            sym = category.symbol().clone()
            if category.value() == selected_attribute:
                sym.setOpacity(1.0)
            else:
                sym.setOpacity(0.5)
            category.setSymbol(sym)

        layer.triggerRepaint()

    def find_nearest_feature_id(
        self, map_point: QgsPointXY
    ) -> Optional[Tuple[int, float]]:
        """Find closest feature ID to map_point within 15px using QgsSpatialIndex.

        Applies focus mode category filtering using the state most recently pushed
        via update_focus_state(), falling back to overall nearest point within 15px
        if no filtered match is found.

        :param map_point: Target point in map canvas coordinates.
        :type map_point: QgsPointXY
        :return: Tuple of (feature_id, distance) if found within tolerance, None otherwise.
        :rtype: Optional[Tuple[int, float]]
        """
        lm = self.layer_manager or (
            getattr(self.dock_widget, "layer_manager", None) if self.dock_widget else None
        )
        if lm is None or lm.spatial_index is None:
            return None

        radius = 15.0 * self.canvas.mapUnitsPerPixel()
        search_rect = QgsRectangle(
            map_point.x() - radius,
            map_point.y() - radius,
            map_point.x() + radius,
            map_point.y() + radius,
        )

        # 1. Fast bounding box intersection query via QgsSpatialIndex
        candidate_ids = lm.spatial_index.intersects(search_rect)
        if not candidate_ids:
            return None

        # 2. Focus mode filtering (state pushed one-way from the dock via update_focus_state)
        is_focus_active = self._focus_active
        focus_filter: Dict[str, str] = self._focus_filter if is_focus_active else {}

        req_drawing = focus_filter.get("drawing_name", "").strip()
        req_excavation = focus_filter.get("excavation_type", "").strip()
        req_feature = focus_filter.get("feature_name", "").strip()
        req_attribute = focus_filter.get("attribute_type", "").strip()

        valid_ids: List[int] = []
        attr_cache = getattr(lm, "attr_cache", {})
        
        if is_focus_active:
            for fid in candidate_ids:
                cached = attr_cache.get(fid)
                if cached is not None:
                    c_drawing = cached.get("drawing_name", "").strip()
                    c_excavation = cached.get("excavation_type", "").strip()
                    c_feature = cached.get("feature_name", "").strip()
                    c_attribute = cached.get("attribute_type", "").strip()

                    if (
                        c_drawing == req_drawing
                        and c_excavation == req_excavation
                        and c_feature == req_feature
                        and c_attribute == req_attribute
                    ):
                        valid_ids.append(fid)

        # 3. Calculate exact Euclidean distance for candidates and select nearest
        pt_geom = QgsGeometry.fromPointXY(map_point)
        geom_cache = getattr(lm, "geom_cache", {})
        
        def find_best(fids: List[int]) -> Optional[Tuple[int, float]]:
            best_fid = None
            min_dist = float("inf")
            for fid in fids:
                geom = geom_cache.get(fid)
                if geom is None and self.point_layer and self.point_layer.isValid():
                    f = self.point_layer.getFeature(fid)
                    if f.isValid():
                        geom = f.geometry()
                if geom and geom.type() == 0:
                    dist = geom.distance(pt_geom)
                    if dist < min_dist:
                        min_dist = dist
                        best_fid = fid
            if best_fid is not None and min_dist <= radius:
                return best_fid, min_dist
            return None

        # First try to find among valid_ids (focused)
        if is_focus_active and valid_ids:
            best = find_best(valid_ids)
            if best is not None:
                return best

        # Fallback to all candidate_ids if not focused or no focused items found
        return find_best(candidate_ids)

    def find_nearest_feature(
        self, layer: QgsVectorLayer, map_point: QgsPointXY
    ) -> Optional[Tuple[QgsFeature, float]]:
        """Backward-compatible helper returning (QgsFeature, distance).

        :param layer: Target vector layer.
        :type layer: QgsVectorLayer
        :param map_point: Coordinate in canvas map coordinates.
        :type map_point: QgsPointXY
        :return: (QgsFeature, distance) if found, None otherwise.
        :rtype: Optional[Tuple[QgsFeature, float]]
        """
        nearest = self.find_nearest_feature_id(map_point)
        if nearest is not None and layer and layer.isValid():
            fid, dist = nearest
            feat = layer.getFeature(fid)
            if feat.isValid():
                return feat, dist
        return None

    def canvasMoveEvent(self, event: QgsMapMouseEvent) -> None:
        """Handle mouse movement: highlight nearby points within 15px tolerance using QgsSpatialIndex."""
        map_point = self.toMapCoordinates(event.pos())
        nearest = self.find_nearest_feature_id(map_point)

        if nearest is not None:
            fid, _ = nearest
            lm = self.layer_manager or (
                getattr(self.dock_widget, "layer_manager", None) if self.dock_widget else None
            )
            geom = getattr(lm, "geom_cache", {}).get(fid) if lm else None
            if geom is None and self.point_layer and self.point_layer.isValid():
                f = self.point_layer.getFeature(fid)
                if f.isValid():
                    geom = f.geometry()

            if geom and geom.type() == 0:  # Point geometry
                pt = geom.asPoint()
                self.hover_marker.setCenter(pt)
                self.hover_marker.show()
                self.setCursor(Qt.PointingHandCursor)
                return

        self.hover_marker.hide()
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event: QgsMapMouseEvent) -> None:
        """Handle mouse button release: route to continuous digitizing logic."""
        if event.button() != Qt.LeftButton:
            return

        map_point = self.toMapCoordinates(event.pos())
        self._handle_digitize_click(map_point)

    def _handle_digitize_click(self, map_point: QgsPointXY) -> None:
        """Process click event on main georeferenced canvas."""
        if not self.dock_widget:
            return

        # 1. Check for existing point selection within 15px tolerance (filtered by focus mode if active)
        nearest = self.find_nearest_feature_id(map_point)
        if nearest is not None:
            fid, _ = nearest
            feat = self.point_layer.getFeature(fid)
            if feat.isValid():
                data = {
                    "point_id": feat["point_id"],
                    "drawing_name": (
                        feat["drawing_name"]
                        if "drawing_name" in feat.fields().names()
                        else ""
                    ),
                    "excavation_type": feat["excavation_type"],
                    "feature_name": feat["feature_name"],
                    "color_code": feat["color_code"],
                    "attribute_type": feat["attribute_type"],
                    "point_name": feat["point_name"],
                    "branch_no": feat["branch_no"],
                    "canvas_x": feat["canvas_x"],
                    "canvas_y": feat["canvas_y"],
                    "feature_id": feat.id(),
                }
                self.existing_point_selected.emit(data)
                return

        # 2. No existing point hit: this is a plain canvas click. Input validation,
        # duplicate checking, feature construction and the layer write are all
        # handled by MainDockWidget._on_canvas_clicked (Step3: event-driven
        # decoupling — this tool no longer reads dock_widget state or touches
        # point_layer directly).
        self.canvas_clicked.emit(map_point)

    def clean_up(self) -> None:
        """Remove canvas vertex markers safely."""
        if self.hover_marker:
            try:
                self.canvas.scene().removeItem(self.hover_marker)
            except Exception:
                pass
            self.hover_marker = None
