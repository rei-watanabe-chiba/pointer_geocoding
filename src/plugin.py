"""
/***************************************************************************
 PointerGeocoding Plugin - Main Plugin Lifecycle Module
 ***************************************************************************/
"""
import os
from typing import Optional, Dict, Any

from qgis.core import QgsProject, Qgis
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QPixmap, QColor, QPainter
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QToolBar

from .start_dialog import StartDialog
from .layer_manager import LayerManager


class PointerGeocodingPlugin:
    """Main plugin entry class managing lifecycle, UI integration, and session orchestration."""

    def __init__(self, iface: QgisInterface) -> None:
        """Initialize the plugin instance.

        :param iface: QGIS interface reference.
        :type iface: QgisInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action: Optional[QAction] = None
        self.toolbar: Optional[QToolBar] = None
        self.menu_name = "&点群座標取得"
        self.layer_manager = LayerManager(iface)
        self.dock_widget: Optional[Any] = None

    def _get_icon(self) -> QIcon:
        """Obtain the plugin icon from SVG/PNG file or generate a fallback icon dynamically.

        Prioritizes vector icon.svg for High DPI displays.

        :return: QIcon instance.
        :rtype: QIcon
        """
        # 1. Prioritize icon.svg for crisp High DPI scaling
        svg_path = os.path.join(self.plugin_dir, "icon.svg")
        if os.path.exists(svg_path):
            return QIcon(svg_path)

        # 2. Check icon.png
        png_path = os.path.join(self.plugin_dir, "icon.png")
        if os.path.exists(png_path):
            return QIcon(png_path)

        # 3. Generate a dynamic fallback icon if both files are missing
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1976D2"))
        painter.drawEllipse(2, 2, 28, 28)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "点")
        painter.end()
        return QIcon(pixmap)

    def initGui(self) -> None:
        """Initialize and register plugin actions directly under pluginMenu and in dedicated toolbar."""
        icon = self._get_icon()
        self.action = QAction(icon, "点群座標取得", self.iface.mainWindow())
        self.action.setObjectName("pointerGeocodingAction")
        self.action.setStatusTip("アナログ図面上の連続打刻・座標変換・CSV出力を実行します")
        self.action.triggered.connect(self.run)

        # 1. Add action directly under the "プラグイン" menu (no sub-menu)
        if self.iface.pluginMenu() is not None:
            self.iface.pluginMenu().addAction(self.action)

        # 2. Add dedicated independent toolbar for this plugin
        self.toolbar = self.iface.addToolBar("点群座標取得ツール")
        self.toolbar.setObjectName("PointerGeocodingToolbar")
        self.toolbar.addAction(self.action)

    def unload(self) -> None:
        """Remove GUI elements, unregister menus and toolbars, and close active docks."""
        if self.action is not None:
            if self.iface.pluginMenu() is not None:
                self.iface.pluginMenu().removeAction(self.action)

        if self.toolbar is not None:
            if self.action is not None:
                self.toolbar.removeAction(self.action)
            del self.toolbar
            self.toolbar = None

        if self.action is not None:
            del self.action
            self.action = None

        self._teardown_dock_widget()

    def _teardown_dock_widget(self) -> None:
        """Unregister and dispose of the main dock widget and its left dock (T-0021).

        self.dock_widget (Qt.RightDockWidgetArea) and its left dock
        (self.dock_widget.left_dock, Qt.LeftDockWidgetArea) are two
        independent QDockWidget instances; Qt's parent-child auto-cleanup
        does not reach left_dock since it is registered as its own top-level
        dock rather than as a child widget of self.dock_widget. Both must
        therefore be explicitly removed/deleted here.
        """
        if self.dock_widget is None:
            return

        left_dock = getattr(self.dock_widget, "left_dock", None)
        if left_dock is not None:
            self.iface.removeDockWidget(left_dock)
            left_dock.deleteLater()

        self.iface.removeDockWidget(self.dock_widget)
        self.dock_widget.deleteLater()
        self.dock_widget = None

    def run(self) -> None:
        """Execute the plugin launch sequence: check dirty state, show start dialog, and initialize session."""
        # 1. Protect unsaved changes in current QGIS project
        if QgsProject.instance().isDirty():
            reply = QMessageBox.question(
                self.iface.mainWindow(),
                "未保存の変更",
                "現在のQGISプロジェクトに変更が加えられています。\n保存せずに新しいセッションを開始すると、未保存のデータは破棄されます。\n続行しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # 2. Display the session startup dialog
        dialog = StartDialog(self.iface.mainWindow())
        if dialog.exec_() != StartDialog.Accepted:
            return

        session_data = dialog.get_session_data()

        # 3. Process session based on type
        if session_data["session_type"] == "NEW":
            success, message, layers_dict = self.layer_manager.setup_new_session(
                parent_dir=session_data["parent_dir_path"],
                session_name=session_data["session_name"],
                image_file_path=session_data["image_file_path"],
                grid_config=session_data.get("grid_config"),
            )
        else:
            success, message, layers_dict = self.layer_manager.load_existing_session(
                session_dir=session_data["session_dir_path"],
                grid_config=session_data.get("grid_config"),
            )

        if not success:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "セッションエラー",
                f"セッションの初期化に失敗しました:\n{message}",
            )
            return

        # Notify success on QGIS message bar
        self.iface.messageBar().pushMessage(
            "点群座標取得",
            message,
            level=Qgis.MessageLevel.Success,
            duration=5,
        )

        # 4. Initialize and show MainDockWidget if available (Step 2 integration)
        self._setup_dock_widget(layers_dict)

    def _setup_dock_widget(self, layers_dict: Optional[Dict[str, Any]]) -> None:
        """Instantiate and attach the main dock widget (and its left dock) to QGIS interface.

        Gracefully notifies if MainDockWidget is not yet created (during Step 1).

        T-0021: MainDockWidget now spans two independent QDockWidget
        instances: self.dock_widget itself (Qt.RightDockWidgetArea; save
        button + main digitizing area) and self.dock_widget.left_dock
        (Qt.LeftDockWidgetArea; icon rail + collapsible 図面管理/設定 side
        panel), which MainDockWidget builds internally. Both are registered
        here so the QGIS map canvas is exposed between them.

        :param layers_dict: Dictionary containing session and layer references.
        :type layers_dict: Optional[Dict[str, Any]]
        """
        try:
            from .main_dock import MainDockWidget

            self._teardown_dock_widget()

            self.dock_widget = MainDockWidget(
                self.iface, self.layer_manager, layers_dict
            )
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget.left_dock)
            self.dock_widget.left_dock.show()
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
            self.dock_widget.show()

        except ImportError:
            # Step 1 environment: main_dock.py has not been generated yet
            self.iface.messageBar().pushMessage(
                "点群座標取得",
                "Step 1（セッション管理基盤）の準備が完了しました。ドックパネルモジュール (Step 2) を待機しています。",
                level=Qgis.MessageLevel.Info,
                duration=7,
            )
