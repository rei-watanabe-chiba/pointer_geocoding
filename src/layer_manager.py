"""
/***************************************************************************
 PointerGeocoding Plugin - Layer and Session Management Module
 ***************************************************************************/

Stage C split (mechanical, logic-preserving): the dataclasses/helper
functions and the various responsibility groups previously implemented
directly in this file have been extracted, without any logic changes,
into layer_manager_models.py (PluginSettings/RefPointMeta/ImageLayerMeta,
get_local_crs, suppress_crs_prompt) plus per-responsibility mixin modules
(settings_metadata_mixin.py, symbology_mixin.py, gpkg_cache_mixin.py,
grid_csv_mixin.py, session_io_mixin.py). LayerManager now mixes those
mixins in and keeps only the QObject signals, __init__, and the
session_image_dir/session_json_dir properties.
"""
# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

import os
from typing import Optional, Tuple, Dict, Any

from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsGeometry,
    QgsSpatialIndex,
)
from qgis.PyQt.QtCore import QObject, pyqtSignal

from .settings_metadata_mixin import SettingsMetadataMixin
from .symbology_mixin import SymbologyMixin
from .gpkg_cache_mixin import GpkgCacheMixin
from .grid_csv_mixin import GridCsvMixin
from .session_io_mixin import SessionIOMixin


class LayerManager(
    QObject,
    SettingsMetadataMixin,
    SymbologyMixin,
    GpkgCacheMixin,
    GridCsvMixin,
    SessionIOMixin,
):
    """Manages the creation, persistence, and loading of project layers and GeoPackage files.

    Handles local CRS assignment, relative path storage, schema migration,
    multiple raster layer retention, and Observer pattern synchronization using QgsSpatialIndex.
    # 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

    Step3-B: QObject化により、以下のシグナルで状態変化を通知できる（追加のみ、
    既存メソッドの引数・戻り値・処理内容は変更しない）:
        metadata_updated(str): 画像メタデータが保存された（save_image_metadata経由。
            対象レイヤ名が特定できない一括保存のケースでは空文字を渡す）。
        layer_deleted(str): 指定レイヤのメタデータが削除された。
        settings_changed(dict): プラグイン設定が保存された。
    """

    metadata_updated = pyqtSignal(str)
    layer_deleted = pyqtSignal(str)
    settings_changed = pyqtSignal(dict)

    def __init__(self, iface: Any = None) -> None:
        """Initialize LayerManager with an optional QgsInterface reference.

        :param iface: Optional QGIS interface instance.
        :type iface: QgisInterface
        """
        super().__init__()
        self.iface = iface
        self.session_dir: Optional[str] = None
        self.gpkg_path: Optional[str] = None
        self.qgz_path: Optional[str] = None
        self.point_layer: Optional[QgsVectorLayer] = None
        self.ref_point_layer: Optional[QgsVectorLayer] = None
        self.raster_layer: Optional[QgsRasterLayer] = None
        self.grid_csv_path: Optional[str] = None
        self.grid_data: Dict[Tuple[int, str, str], Tuple[float, float]] = {}
        self.max_gx: int = 0
        self.unique_gy: set = set()

        # Spatial index and cache properties (Observer pattern)
        self.spatial_index: Optional[QgsSpatialIndex] = None
        self.attr_cache: Dict[int, Dict[str, str]] = {}
        self.geom_cache: Dict[int, QgsGeometry] = {}
        self._signals_connected: bool = False

    @property
    def session_image_dir(self) -> Optional[str]:
        """Return path to the session image/ directory if session is initialized."""
        if self.session_dir:
            return os.path.join(self.session_dir, "image")
        return None

    @property
    def session_json_dir(self) -> Optional[str]:
        """Return path to the session json/ directory if session is initialized."""
        if self.session_dir:
            return os.path.join(self.session_dir, "json")
        return None
