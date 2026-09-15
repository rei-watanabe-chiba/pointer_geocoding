"""
/***************************************************************************
 PointerGeocoding Plugin - Symbology & Labeling Mixin
 ***************************************************************************/

Stage C split (mechanical, logic-preserving): extracted from
layer_manager.py. Provides SymbologyMixin, mixed into LayerManager,
containing digitized-point labeling and reference-point symbology/labeling.

Stage E: also mixed into MainDockWidget so that "symbology application"
(digitized-point labeling, reference-point symbology, and the Focus Mode
opacity override) is a single cohesive concern regardless of which widget
triggers it. build_opacity_expression()/apply_opacity_expression() were
moved here from main_dock.py's update_symbology_opacity() without changing
their expression/output semantics; main_dock.py keeps a same-named thin
delegator so Tab2/Tab3 call sites are unaffected.
"""
# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

from typing import Optional, Dict, Any

from qgis.core import (
    QgsVectorLayer,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsMarkerSymbol,
    QgsRuleBasedRenderer,
    QgsCategorizedSymbolRenderer,
    QgsProperty,
    QgsSymbol,
    Qgis,
)
from qgis.PyQt.QtGui import QColor


class SymbologyMixin:
    """Mixin providing point/reference-point symbology and labeling for LayerManager."""

    @staticmethod
    def apply_point_labeling(layer: QgsVectorLayer) -> None:
        """Apply dynamic expression-based labeling to the points layer."""
        settings = QgsPalLayerSettings()
        settings.fieldName = (
            "CASE WHEN \"excavation_type\" = '遺構' THEN \"feature_name\" || '_' ELSE '' END "
            "|| \"point_name\" "
            "|| CASE WHEN \"branch_no\" IS NOT NULL AND \"branch_no\" != '' THEN '-' || \"branch_no\" ELSE '' END"
        )
        settings.isExpression = True
        settings.placement = Qgis.LabelPlacement.OverPoint
        settings.yOffset = -5.0  # Slightly above the point

        text_format = QgsTextFormat()
        text_format.setSize(10)

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.0)
        text_format.setBuffer(buffer)

        settings.setFormat(text_format)

        labeling = QgsVectorLayerSimpleLabeling(settings)
        layer.setLabelsEnabled(True)
        layer.setLabeling(labeling)

    @staticmethod
    def apply_above_right_label_quadrant(pal: QgsPalLayerSettings) -> None:
        """Align label anchor so its bottom-left sits exactly at the insertion point.

        Sets the label quadrant to AboveRight (enum value 2) on the given
        QgsPalLayerSettings instance, in place. Shared by
        apply_ref_point_symbology (reference points) and
        CanvasDigitizingTool.setup_point_layer_symbology (digitized points, in
        map_tool.py), which both need identical label-anchor behavior.

        :param pal: Label settings object to mutate in place.
        :type pal: QgsPalLayerSettings
        """
        try:
            quad_val = 2
            if hasattr(Qgis, "LabelQuadrantPosition") and hasattr(Qgis.LabelQuadrantPosition, "QuadrantAboveRight"):
                quad_val = Qgis.LabelQuadrantPosition.QuadrantAboveRight
            elif hasattr(QgsPalLayerSettings, "QuadrantAboveRight"):
                quad_val = QgsPalLayerSettings.QuadrantAboveRight

            if hasattr(pal, "quadrantPosition"):
                pal.quadrantPosition = quad_val
            if hasattr(pal, "quadOffset"):
                pal.quadOffset = quad_val
        except Exception:
            pass

    @staticmethod
    def apply_ref_point_symbology(
        layer: QgsVectorLayer,
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Apply cross symbol style and rule-based rendering for reference points.

        :param layer: Target reference point layer (CSV Delimited Text).
        :type layer: QgsVectorLayer
        :param settings: Optional settings dict from settings.json. Falls back to UIConfig defaults.
        :type settings: Optional[Dict[str, Any]]
        """
        if not layer or not layer.isValid():
            return

        from .main_dock import UIConfig

        # Resolve display values from settings or UIConfig defaults
        sym_size    = float((settings or {}).get("ref_symbol_size",       (settings or {}).get("symbol_size", UIConfig.SYMBOL_SIZE_REF)))
        line_width  = float((settings or {}).get("ref_symbol_line_width",  (settings or {}).get("symbol_line_width", 1.2)))
        line_color  = str(  (settings or {}).get("ref_symbol_line_color",  (settings or {}).get("ref_symbol_color", "#D32F2F")))
        lbl_size    = int(  (settings or {}).get("label_size",             UIConfig.LABEL_SIZE_REF))
        lbl_halo    = bool( (settings or {}).get("label_halo",             True))
        lbl_offset  = float((settings or {}).get("label_offset",           1.0))
        scale_major = int(  (settings or {}).get("scale_major_grid",       -1))
        scale_minor = int(  (settings or {}).get("scale_minor_grid",       UIConfig.SCALE_THRESHOLD))

        symbol = QgsMarkerSymbol.createSimple({
            "name": "cross",
            "color": line_color,
            "outline_color": line_color,
            "outline_width": str(line_width),
            "size": str(sym_size),
        })

        root_rule = QgsRuleBasedRenderer.Rule(None)

        # Rule 1: Subgrid "00" — visibility controlled by scale_major_grid
        rule1 = QgsRuleBasedRenderer.Rule(symbol.clone())
        rule1.setLabel("Subgrid 00")
        rule1.setFilterExpression('"小グリッド" = \'00\'')
        if scale_major > 0:
            rule1.setMinimumScale(scale_major)
        root_rule.appendChild(rule1)

        # Rule 2: Subgrid != "00" — visibility controlled by scale_minor_grid
        rule2 = QgsRuleBasedRenderer.Rule(symbol.clone())
        rule2.setLabel("Subgrid non-00")
        rule2.setFilterExpression('"小グリッド" != \'00\'')
        if scale_minor > 0:
            rule2.setMinimumScale(scale_minor)
        root_rule.appendChild(rule2)

        renderer = QgsRuleBasedRenderer(root_rule)
        layer.setRenderer(renderer)

        pal = QgsPalLayerSettings()
        # Label format: [大グリッドＸ][大グリッドＹ]-[小グリッド]  e.g. "5C-00"
        pal.fieldName = '"大グリッドＸ" || "大グリッドＹ" || \'-\' || "小グリッド"'
        pal.isExpression = True
        pal.placement = Qgis.LabelPlacement.OverPoint

        # Quadrant placement - we don't use Quadrant enum to avoid missing constant issues.
        # Instead, we just offset the label X right and Y up (negative Y).
        pal.xOffset = lbl_offset
        pal.yOffset = -lbl_offset

        SymbologyMixin.apply_above_right_label_quadrant(pal)

        text_format = QgsTextFormat()
        text_format.setSize(lbl_size)
        text_format.setColor(QColor(line_color))

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(lbl_halo)
        buffer.setSize(1.0)
        buffer.setColor(QColor("white"))
        text_format.setBuffer(buffer)

        pal.setFormat(text_format)

        labeling = QgsVectorLayerSimpleLabeling(pal)
        layer.setLabelsEnabled(True)
        layer.setLabeling(labeling)
        layer.triggerRepaint()

    @staticmethod
    def build_opacity_expression(
        is_focus_on: bool,
        filters: Optional[Dict[str, str]],
        slider_val: int,
    ) -> str:
        """Build the QgsProperty expression string controlling per-category point opacity.

        Pure expression-construction half of the former
        MainDockWidget.update_symbology_opacity(): given Focus Mode state, the
        four current category filter values, and the opacity slider value,
        returns the CASE WHEN expression string (or the literal "100" when
        Focus Mode is off). Contains no QGIS layer/renderer mutation.

        :param is_focus_on: Whether Focus Mode is currently active.
        :type is_focus_on: bool
        :param filters: Dict with keys 'drawing_name', 'excavation_type',
            'feature_name', 'attribute_type' representing the currently
            selected category values (as shown in the Tab2 UI).
        :type filters: Optional[Dict[str, str]]
        :param slider_val: Opacity percentage (0-100) applied to non-matching points.
        :type slider_val: int
        :return: Expression string suitable for QgsProperty.fromExpression().
        :rtype: str
        """
        if not is_focus_on:
            return "100"

        filters = filters or {}
        d_name = filters.get("drawing_name", "").strip()
        ex_type = filters.get("excavation_type", "").strip()
        feat_name = filters.get("feature_name", "").strip()
        attr_type = filters.get("attribute_type", "").strip()

        def _escape_sql(s: str) -> str:
            return s.replace("'", "''")

        conditions = []
        if d_name:
            conditions.append(f"\"drawing_name\" = '{_escape_sql(d_name)}'")
        else:
            conditions.append("coalesce(\"drawing_name\", '') = ''")

        conditions.append(f"\"excavation_type\" = '{_escape_sql(ex_type)}'")

        if ex_type == "遺構":
            conditions.append(f"\"feature_name\" = '{_escape_sql(feat_name)}'")
        else:
            conditions.append("coalesce(\"feature_name\", '') = ''")

        conditions.append(f"\"attribute_type\" = '{_escape_sql(attr_type)}'")

        condition_str = " AND ".join(conditions)
        return f"CASE WHEN {condition_str} THEN 100 ELSE {slider_val} END"

    @staticmethod
    def apply_opacity_expression(layer: QgsVectorLayer, expr: str) -> None:
        """Apply a QgsProperty opacity expression to every category symbol of a layer.

        Mutation half of the former MainDockWidget.update_symbology_opacity():
        overrides each category symbol's opacity via a data-defined property
        built from ``expr`` (as produced by build_opacity_expression()), then
        re-sets the renderer on the layer and triggers a repaint. Does not
        refresh the map canvas itself (callers refresh the canvas afterwards,
        matching the previous behavior).

        :param layer: Point layer with QgsCategorizedSymbolRenderer.
        :type layer: QgsVectorLayer
        :param expr: Expression string evaluating to an opacity percentage (0-100).
        :type expr: str
        """
        if not layer or not layer.isValid():
            return

        renderer = layer.renderer()
        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            return

        prop = QgsProperty.fromExpression(expr)

        # Retrieve PropertyOpacity enum key safely
        prop_key = getattr(QgsSymbol, "PropertyOpacity", None)
        if prop_key is None and hasattr(QgsSymbol, "Property"):
            prop_key = getattr(QgsSymbol.Property, "PropertyOpacity", None)
        if prop_key is None:
            prop_key = 1

        for idx, category in enumerate(renderer.categories()):
            sym = category.symbol().clone()
            if sym:
                if prop_key is not None:
                    sym.setDataDefinedProperty(prop_key, prop)
                renderer.updateCategorySymbol(idx, sym)

        # Re-set modified renderer to layer and trigger canvas repaint
        layer.setRenderer(renderer.clone())
        layer.triggerRepaint()
