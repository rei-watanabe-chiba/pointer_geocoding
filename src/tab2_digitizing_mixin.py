"""
/***************************************************************************
 PointerGeocoding Plugin - Tab 2 (Digitizing) Mixin
 ***************************************************************************/

Stage B split (mechanical, logic-preserving): extracted from main_dock.py.
Provides Tab2DigitizingMixin, mixed into MainDockWidget, containing all UI
construction and event handlers for Tab 2 (Master Focus Mode, continuous
artifact point digitizing, existing point editing/deletion, and CSV
export).

T-0032 (large follow-up to T-0027): redesigns the 点情報パネル/属性パネル and
substantially expands existing-point editing:
- Existing-point editing unlocks nearly all category widgets (only
  combo_drawing_name stays locked, see _CATEGORY_LOCK_WIDGET_NAMES); the
  former PointRenameDialog is removed in favor of directly editing
  edit_point_name/edit_point_name_sp/edit_branch_no in-panel and committing
  via btn_rename_point, plus a new btn_update_attribute for committing
  出土形態/遺構名/属性記号 changes.

T-0033 (UI follow-up to T-0032, after in-QGIS review): 点情報パネル/属性パネル/
フォーカスモードパネルのQGroupBoxタイトルを廃止しHLine区切りに変更
(UIStyleHelper.build_separator); 点情報パネルは状態文言+出土形態+点名/枝番+
XY座標を1つの複数行QLabelにまとめ、start_dialog.pyのpanel_preview_statusと同じ
左ボーダー色分けフレーム(UIStyleHelper.create_status_panel/update_status_panel)
で表示する(新規点作成=info/既設点編集=warning/エラー=error)。点名/枝番の入力欄と
点名変更/削除ボタンはこのフレームの外(下)に配置。カラーボタンは無効時グレー表示
(_update_color_picker_button)。遺構名未指定/点名重複エラー時はそれぞれ
combo_feature_name/点名入力欄に赤枠を表示(_update_error_borders)。T-0032の
透明度「更新」ボタン(btn_update_opacity)は削除し、スライダーのリアルタイム反映
のみに戻した。
"""

import os
from typing import Dict, Any, List, Tuple, Optional

from qgis.core import (
    QgsProject,
    QgsPointXY,
    Qgis,
)
from qgis.gui import (
    QgsFilterLineEdit,
    QgsCollapsibleGroupBox,
)
from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QLabel,
    QPushButton,
    QComboBox,
    QGroupBox,
    QDialog,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QColorDialog,
    QFrame,
    QSlider,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
)

# T-0022: SP属性専用の点名QLineEditで使用する入力バリデータ。
# PyQt5/PyQt6両対応パターンは start_dialog.py (L31-38付近) を踏襲する。
try:
    from qgis.PyQt.QtGui import QRegularExpressionValidator
    from qgis.PyQt.QtCore import QRegularExpression
    HAS_QT_REGEX = True
except ImportError:
    from qgis.PyQt.QtGui import QRegExpValidator
    from qgis.PyQt.QtCore import QRegExp
    HAS_QT_REGEX = False

from .transform import export_points_to_csv
from .style_helper import UIStyleHelper
from .core_logic import (
    check_point_duplicate,
    build_point_ident,
    get_next_point_number,
    get_next_point_id,
    build_digitized_feature,
    insert_feature_to_layer,
    pixel_from_affine,
    safe_get_str,
    to_survey_coords,
    ExcavationType,
    AttributeType,
)
from .main_dock_constants import (
    UIConfig,
    UILabels,
    UIPlaceholders,
    UIDialogTitles,
    UIMessages,
    MAIN_RATIO,
)
from .main_dock_dialogs import FeatureCreateDialog


class Tab2DigitizingMixin:
    """Mixin providing Tab 2 (Master Focus Mode, Digitizing & CSV Export) behavior for MainDockWidget."""

    def _create_tab2_ui(self) -> QWidget:
        """Construct Tab 2: 4 always-expanded panels (T-0027, restructured T-0032/T-0033).

        ① 点情報パネル (group_point_info) — title-less, HLine区切り; 左ボーダー
           色分けフレーム内に状態文言(新規点作成/既設点編集/エラー)+出土形態・
           点名/枝番・XY座標をまとめた複数行テキストを表示。フレームの外(下)に
           editable 点名/枝番 inputs + 既設点のみの削除/点名変更(コミット)ボタン;
        ② 属性パネル (group_attribute_panel) — title-less、HLine区切り;
           属性→出土形態→遺構名→(作成・カラーの行)→対象図面、既設点編集時のみの
           属性変更ボタン;
        ③ フォーカスモードパネル (group_focus) — title-less、HLine区切り;
           ON/OFFトグルとスライダー(sliderReleased でリアルタイム反映、更新
           ボタンなし);
        ④ 図面選択リスト (group_drawing_list) — 図面表示マルチセレクタ(タイトル維持).
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            UIConfig.PANEL_CONTAINER_MARGIN_LEFT,
            UIConfig.PANEL_MARGIN,
            UIConfig.PANEL_CONTAINER_MARGIN_RIGHT,
            UIConfig.PANEL_MARGIN,
        )
        layout.setSpacing(UIConfig.PANEL_MARGIN)

        # =============================================================
        # Panel 1: 点情報パネル (T-0033: title removed; the status band +
        # 出土形態/点名+枝番/XY座標 summary is now a single flat multi-line
        # QLabel inside a left-border color-coded QFrame, matching
        # start_dialog.py's panel_preview_status style. The editable
        # point-name/branch inputs and existing-point-only action buttons
        # live below this frame, outside of it. T-0034: the leading HLine
        # separator that used to precede this panel was removed because
        # main_dock.py now places its own separator directly above
        # tab2_container, avoiding two adjacent separators.)
        # =============================================================
        self.group_point_info = QGroupBox(container)
        info_layout = QVBoxLayout(self.group_point_info)
        info_layout.setSpacing(UIConfig.PANEL_MARGIN)

        # T-0033: flat multi-line summary (status + 出土形態 + 点名+枝番 +
        # XY座標) inside a create_status_panel()-style left-border frame;
        # color-coded via _update_point_info_status() (新規点作成=info/blue,
        # 既設点編集=warning/orange, エラー=error/red -- reusing the same
        # QFrame[statusType=...] styles as start_dialog.py's
        # panel_preview_status, no dedicated "editing" style needed).
        self.panel_point_info, self.lbl_point_info_status = UIStyleHelper.create_status_panel(
            UILabels.STATUS_NEW_POINT, status_type="info", parent=self.group_point_info
        )
        info_layout.addWidget(self.panel_point_info)

        # 番号・枝番 (editable inputs, directly under the summary panel
        # above). T-0032: no longer force-disabled while an existing point
        # is selected (see _CATEGORY_LOCK_WIDGET_NAMES) -- editing them here
        # and pressing 点名変更 (btn_rename_point) now commits the value
        # directly to the selected feature, replacing the former
        # PointRenameDialog.
        # [EXCEPTION PROTECTION: QSpinBox preserved for S/P/C attributes per
        # OSネイティブUI保護原則]. T-0022: SP属性選択時のみ、専用の自由入力
        # QLineEdit(半角英数字・ハイフン・アンダースコアのみ)をこれと並置し、
        # 表示/非表示を切り替える(QSpinBoxは変更しない)。
        self.lbl_point_name = QLabel(UILabels.POINT_NAME, self.group_point_info)
        self.edit_point_name = UIStyleHelper.create_spinbox(1, 999999, 1, self.group_point_info)
        self.edit_point_name.valueChanged.connect(self._on_point_identity_changed)

        self.edit_point_name_sp = QLineEdit(self.group_point_info)
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
        self.edit_point_name_sp.hide()
        self.edit_point_name_sp.textChanged.connect(self._on_point_identity_changed)

        row_point_name = UIStyleHelper.build_flex_row(
            self.lbl_point_name,
            [(self.edit_point_name, 1), (self.edit_point_name_sp, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        info_layout.addWidget(row_point_name)

        self.lbl_branch_no = QLabel(UILabels.BRANCH_NO, self.group_point_info)
        self.edit_branch_no = QgsFilterLineEdit(self.group_point_info)
        self.edit_branch_no.setShowClearButton(True)
        self.edit_branch_no.setPlaceholderText(UIPlaceholders.BRANCH_NO)
        self.edit_branch_no.textChanged.connect(self._on_branch_text_changed)
        row_branch_no = UIStyleHelper.build_flex_row(
            self.lbl_branch_no,
            [(self.edit_branch_no, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        info_layout.addWidget(row_branch_no)

        # Existing-point-only actions: 削除 (immediate, no confirmation) /
        # 点名変更 (T-0032: commits the current edit_point_name(_sp)/edit_branch_no
        # values directly to the selected feature; no longer opens a dialog).
        self.row_existing_actions = QWidget(self.group_point_info)
        existing_actions_layout = QHBoxLayout(self.row_existing_actions)
        existing_actions_layout.setContentsMargins(0, 0, 0, 0)
        existing_actions_layout.setSpacing(8)

        self.btn_rename_point = QPushButton(UILabels.BTN_RENAME_POINT, self.row_existing_actions)
        self.btn_rename_point.clicked.connect(self._on_rename_point_clicked)
        existing_actions_layout.addWidget(self.btn_rename_point)

        self.btn_delete_point = QPushButton(UILabels.BTN_DELETE_POINT, self.row_existing_actions)
        self.btn_delete_point.clicked.connect(self._on_delete_selected_point)
        existing_actions_layout.addWidget(self.btn_delete_point)

        info_layout.addWidget(self.row_existing_actions)
        self.row_existing_actions.hide()

        layout.addWidget(self.group_point_info)

        # =============================================================
        # Panel 2: 属性パネル (T-0032 order: 属性→出土形態→遺構名→
        # (作成・カラーの行)→対象図面→(既設点編集時のみ)属性変更ボタン;
        # T-0033: title removed, replaced by an HLine separator)
        # =============================================================
        layout.addWidget(UIStyleHelper.build_separator(container))

        self.group_attribute_panel = QGroupBox(container)
        attr_layout = QVBoxLayout(self.group_attribute_panel)
        attr_layout.setSpacing(UIConfig.PANEL_MARGIN)

        # 属性 (T-0032: display-only labels "S:石器"/"P:土器"/"C:炭化物"/"SP";
        # the raw AttributeType value is stored as itemData and must be read
        # via _get_attribute_value()/set via _set_attribute_value()).
        self.lbl_attribute = QLabel(UILabels.ATTRIBUTE_CODE, self.group_attribute_panel)
        self.combo_attribute = QComboBox(self.group_attribute_panel)
        for value in UILabels.ATTRIBUTE_OPTIONS:
            self.combo_attribute.addItem(UILabels.ATTRIBUTE_DISPLAY_MAP.get(value, value), value)
        self.combo_attribute.currentIndexChanged.connect(self._on_category_changed)
        row_attribute = UIStyleHelper.build_flex_row(
            self.lbl_attribute,
            [(self.combo_attribute, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        attr_layout.addWidget(row_attribute)

        # 出土形態
        self.lbl_excavation_type = QLabel(UILabels.EXCAVATION_TYPE, self.group_attribute_panel)
        self.combo_excavation_type = QComboBox(self.group_attribute_panel)
        self.combo_excavation_type.addItems(UILabels.EXCAVATION_OPTIONS)
        self.combo_excavation_type.currentIndexChanged.connect(self._on_excavation_type_changed)
        row_excavation = UIStyleHelper.build_flex_row(
            self.lbl_excavation_type,
            [(self.combo_excavation_type, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        attr_layout.addWidget(row_excavation)

        # 遺構名 (selector only; 作成/カラーは別行に分離, see row_feature_actions).
        self.lbl_feature_selector = QLabel(UILabels.FEATURE_SELECTOR, self.group_attribute_panel)
        self.combo_feature_name = QComboBox(self.group_attribute_panel)
        self.combo_feature_name.addItem(UILabels.FEATURE_NEW_OPTION)
        self.combo_feature_name.currentTextChanged.connect(self._on_feature_combo_changed)

        self.row_feature_selector = UIStyleHelper.build_flex_row(
            self.lbl_feature_selector,
            [(self.combo_feature_name, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        attr_layout.addWidget(self.row_feature_selector)

        # 作成ボタン + カラーボタン (T-0032: separate row, 1:1 width ratio;
        # カラーボタンは常時表示、有効/無効のみ切り替える。ラベルなし).
        self.row_feature_actions = QWidget(self.group_attribute_panel)
        feature_actions_layout = QHBoxLayout(self.row_feature_actions)
        feature_actions_layout.setContentsMargins(0, 0, 0, 0)
        feature_actions_layout.setSpacing(8)

        self.btn_create_feature = QPushButton(UILabels.BTN_CREATE_FEATURE, self.row_feature_actions)
        self.btn_create_feature.clicked.connect(self._on_create_feature_clicked)
        feature_actions_layout.addWidget(self.btn_create_feature, 1)

        self.btn_color_picker = QPushButton(UILabels.BTN_COLOR_PICKER, self.row_feature_actions)
        self._update_color_picker_button()
        self.btn_color_picker.clicked.connect(self._pick_color)
        feature_actions_layout.addWidget(self.btn_color_picker, 1)

        attr_layout.addWidget(self.row_feature_actions)

        # 対象図面 (kept -- unchanged -- since drawing_name attribution is
        # still required by digitizing/CSV export/Focus Mode filtering, even
        # though T-0032 removes it from duplicate-check filtering).
        self.lbl_drawing_name = QLabel(UILabels.DRAWING_NAME, self.group_attribute_panel)
        self.combo_drawing_name = QComboBox(self.group_attribute_panel)
        self.combo_drawing_name.currentIndexChanged.connect(self._on_category_changed)
        row_drawing = UIStyleHelper.build_flex_row(
            self.lbl_drawing_name,
            [(self.combo_drawing_name, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        attr_layout.addWidget(row_drawing)

        # Initial visibility for feature-specific controls (default is グリッド)
        self.row_feature_selector.hide()

        # T-0032: 属性変更ボタン (既設点編集時のみ表示)。押下時に
        # 出土形態/遺構名/属性記号のみをフィーチャへコミットする
        # (点名/枝番はbtn_rename_point側で扱う)。
        self.btn_update_attribute = QPushButton(UILabels.BTN_UPDATE_ATTRIBUTE, self.group_attribute_panel)
        UIStyleHelper.set_primary_button(self.btn_update_attribute)
        self.btn_update_attribute.clicked.connect(self._on_update_attribute_clicked)
        self.btn_update_attribute.hide()
        attr_layout.addWidget(self.btn_update_attribute)

        layout.addWidget(self.group_attribute_panel)

        # =============================================================
        # Panel 3: フォーカスモードパネル (toggle + slider; drawing multi-
        # selector moved to Panel 4, see below; T-0033: title removed,
        # replaced by an HLine separator, and the T-0032 "更新" button is
        # removed -- opacity is refreshed via slider release only, as before
        # T-0032)
        # =============================================================
        layout.addWidget(UIStyleHelper.build_separator(container))

        self.group_focus = QGroupBox(container)
        focus_layout = QVBoxLayout(self.group_focus)
        focus_layout.setSpacing(UIConfig.PANEL_MARGIN)

        self.btn_focus_mode = QPushButton(UILabels.BTN_FOCUS_OFF, self.group_focus)
        self.btn_focus_mode.setCheckable(True)
        self.btn_focus_mode.toggled.connect(self._on_focus_mode_toggled)
        focus_layout.addWidget(self.btn_focus_mode)

        self.lbl_opacity = QLabel(UILabels.OPACITY_LABEL, self.group_focus)
        self.slider_opacity = QSlider(Qt.Horizontal, self.group_focus)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(20)
        self.slider_opacity.setSingleStep(5)
        self.lbl_opacity_val = QLabel("20%", self.group_focus)
        self.lbl_opacity_val.setMinimumWidth(36)
        self.lbl_opacity_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.slider_opacity.valueChanged.connect(self._on_slider_value_changed)
        self.slider_opacity.sliderReleased.connect(self._on_slider_released)

        # T-0033: the T-0032 "更新" button (btn_update_opacity) is removed;
        # slider:label width ratio restored to its pre-T-0032 3:1 split.
        row_opacity = UIStyleHelper.build_flex_row(
            self.lbl_opacity,
            [(self.slider_opacity, 3), (self.lbl_opacity_val, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        focus_layout.addWidget(row_opacity)

        layout.addWidget(self.group_focus)

        # =============================================================
        # Panel 4: 図面選択リスト (図面表示マルチセレクタ, fixed height)
        # =============================================================
        self.group_drawing_list = QGroupBox(UILabels.GROUP_DRAWING_LIST, container)
        drawing_list_layout = QVBoxLayout(self.group_drawing_list)
        drawing_list_layout.setSpacing(UIConfig.PANEL_MARGIN)

        self.list_drawing_visibility = QListWidget(self.group_drawing_list)
        self.list_drawing_visibility.setFixedHeight(UIConfig.DRAWING_LIST_HEIGHT)
        self.list_drawing_visibility.itemChanged.connect(self._on_drawing_visibility_item_changed)
        drawing_list_layout.addWidget(self.list_drawing_visibility)

        layout.addWidget(self.group_drawing_list)
        layout.addStretch()

        scroll.setWidget(container)

        # T-0032: initialize 点情報パネル error-tracking flag; the summary
        # panel itself already defaults to status_type="info" (新規点作成)
        # via create_status_panel() above.
        self._point_info_has_error = False

        # T-0033: sync 作成/カラー button enabled state (and the color
        # picker's gray-when-disabled styling) with the default 出土形態
        # selection (グリッド), since neither combo emits its
        # currentIndexChanged signal for the initial index-(-1)->0 transition
        # performed by addItems() above.
        self._update_feature_related_visibility()

        return scroll

    def _create_tab4_ui(self) -> QWidget:
        """Construct the 出力 (CSV export) dialog content (T-0024).

        Formerly Section 4 of Tab 2 (embedded at the bottom of the main
        digitizing area); split out into its own modeless dialog so the
        main digitizing area stays focused on continuous point entry. The
        widgets/handlers themselves (_browse_csv_path / _on_export_csv_clicked)
        are unchanged.

        T-0034: renamed from _create_output_ui() to _create_tab4_ui() to
        align with the tab1/tab2/tab3 naming pattern used by main_dock.py's
        self.tab1_container / self.tab2_container / self.tab3_container /
        self.tab4_container.
        """
        csv_group = QgsCollapsibleGroupBox(UILabels.GROUP_CSV)
        csv_layout = QVBoxLayout(csv_group)
        csv_layout.setContentsMargins(
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
            UIConfig.COMMON_MARGIN_LR,
            UIConfig.DIALOG_MARGIN,
        )
        csv_layout.setSpacing(UIConfig.DIALOG_MARGIN)

        self.lbl_encoding = QLabel(UILabels.ENCODING, csv_group)
        self.radio_utf8 = QRadioButton(UILabels.RADIO_UTF8, csv_group)
        self.radio_utf8.setChecked(True)
        self.radio_sjis = QRadioButton(UILabels.RADIO_SJIS, csv_group)
        row_encoding = UIStyleHelper.build_flex_row(
            self.lbl_encoding,
            [(self.radio_utf8, 1), (self.radio_sjis, 1), (None, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        csv_layout.addWidget(row_encoding)

        self.lbl_csv_path = QLabel(UILabels.CSV_DESTINATION, csv_group)
        self.edit_csv_path = QgsFilterLineEdit(csv_group)
        self.edit_csv_path.setShowClearButton(True)
        self.edit_csv_path.setPlaceholderText(UIPlaceholders.CSV_PATH)
        self.btn_browse_csv = QPushButton(UILabels.BTN_BROWSE, csv_group)
        self.btn_browse_csv.clicked.connect(self._browse_csv_path)
        row_csv = UIStyleHelper.build_flex_row(
            self.lbl_csv_path,
            [(self.edit_csv_path, 1), (self.btn_browse_csv, 0)],
            main_ratio=MAIN_RATIO,
            row_height=UIConfig.ROW_HEIGHT,
        )
        csv_layout.addWidget(row_csv)

        self.btn_export_csv = QPushButton(UILabels.BTN_EXPORT_CSV, csv_group)
        UIStyleHelper.set_accent_button(self.btn_export_csv)
        self.btn_export_csv.clicked.connect(self._on_export_csv_clicked)
        csv_layout.addWidget(self.btn_export_csv)

        return csv_group

    # =========================================================================
    # Tab 2: Focus Mode, Artifact Digitizing & CSV Export Handlers
    # =========================================================================

    def _get_drawing_layers(self) -> List[Tuple[str, str, bool]]:
        """Extract valid raster layer information from the '画像ファイル' group in QGIS layer tree.

        :return: List of tuples (layer_name, layer_id, is_visible).
        :rtype: List[Tuple[str, str, bool]]
        """
        root = QgsProject.instance().layerTreeRoot()
        if not root:
            return []
        image_group = root.findGroup("画像ファイル")
        if not image_group:
            return []

        result: List[Tuple[str, str, bool]] = []
        for tree_layer in image_group.findLayers():
            layer = tree_layer.layer()
            if layer and layer.isValid():
                result.append((layer.name(), layer.id(), tree_layer.itemVisibilityChecked()))
        return result

    def _get_drawing_layer_names(self) -> List[str]:
        """Extract valid raster layer names from the '画像ファイル' group in QGIS layer tree.

        :return: List of raster layer names.
        :rtype: List[str]
        """
        return [info[0] for info in self._get_drawing_layers()]

    def _update_drawing_combo(self, *args: Any) -> None:
        """Dynamically refresh the target drawing combo box and drawing visibility multi-selector."""
        if not hasattr(self, "combo_drawing_name") or self.combo_drawing_name is None:
            return

        layers_info = self._get_drawing_layers()
        names = [info[0] for info in layers_info]

        # 1. Update combo_drawing_name
        UIStyleHelper.repopulate_combo_box(self.combo_drawing_name, names, preserve_current=True)

        # 2. Update list_drawing_visibility
        if hasattr(self, "list_drawing_visibility") and self.list_drawing_visibility is not None:
            entries = [(name, layer_id, is_vis) for name, layer_id, is_vis in layers_info]
            UIStyleHelper.repopulate_checkable_list(self.list_drawing_visibility, entries)

    def _on_drawing_visibility_item_changed(self, item: QListWidgetItem) -> None:
        """Toggle canvas visibility for the corresponding layer in '画像ファイル' group.

        :param item: QListWidgetItem whose check state was changed.
        :type item: QListWidgetItem
        """
        layer_id, is_checked = UIStyleHelper.get_checkable_item_state(item)
        root = QgsProject.instance().layerTreeRoot()
        if root and layer_id:
            image_group = root.findGroup("画像ファイル")
            if image_group:
                tree_layer = image_group.findLayer(layer_id)
                if tree_layer:
                    tree_layer.setItemVisibilityChecked(is_checked)
                    self.canvas.refresh()

    def _ensure_drawing_visible(self, drawing_name: str) -> None:
        """Ensure the specified drawing is checked ON in multi-selector and visible on canvas.

        :param drawing_name: Layer name to make visible.
        :type drawing_name: str
        """
        if not hasattr(self, "list_drawing_visibility") or self.list_drawing_visibility is None:
            return

        root = QgsProject.instance().layerTreeRoot()
        image_group = root.findGroup("画像ファイル") if root else None

        for i in range(self.list_drawing_visibility.count()):
            item = self.list_drawing_visibility.item(i)
            if item.text() == drawing_name:
                if item.checkState() != Qt.Checked:
                    self.list_drawing_visibility.blockSignals(True)
                    item.setCheckState(Qt.Checked)
                    self.list_drawing_visibility.blockSignals(False)

                    layer_id = item.data(Qt.UserRole)
                    if image_group and layer_id:
                        tree_layer = image_group.findLayer(layer_id)
                        if tree_layer:
                            tree_layer.setItemVisibilityChecked(True)
                    self.canvas.refresh()
                break

    def is_focus_mode_active(self) -> bool:
        """Return whether Focus Mode is currently active.

        :return: True if focus mode button is checked.
        :rtype: bool
        """
        return bool(hasattr(self, "btn_focus_mode") and self.btn_focus_mode.isChecked())

    def _get_attribute_value(self) -> str:
        """Return the raw AttributeType value (S/P/C/SP) currently selected.

        T-0032: combo_attribute now shows display-only labels (e.g. "S:石器")
        while storing the raw value as itemData; callers needing the actual
        stored/compared value must use this instead of currentText().

        :return: Currently selected AttributeType value string.
        :rtype: str
        """
        if not hasattr(self, "combo_attribute"):
            return ""
        return self.combo_attribute.currentData() or self.combo_attribute.currentText()

    def _set_attribute_value(self, value: str) -> None:
        """Select the combo_attribute item whose itemData matches ``value``.

        :param value: Raw AttributeType value (S/P/C/SP) to select.
        :type value: str
        """
        idx = self.combo_attribute.findData(value)
        if idx >= 0:
            self.combo_attribute.setCurrentIndex(idx)
        else:
            self.combo_attribute.setCurrentText(value)

    def get_focus_category_filter(self) -> Dict[str, str]:
        """Return dictionary of the 4 category values for focus filtering.

        :return: Dict with keys 'drawing_name', 'excavation_type', 'feature_name', 'attribute_type'.
        :rtype: Dict[str, str]
        """
        d_name = (
            self.combo_drawing_name.currentText().strip()
            if hasattr(self, "combo_drawing_name")
            else ""
        )
        ex_type = (
            self.combo_excavation_type.currentText().strip()
            if hasattr(self, "combo_excavation_type")
            else ""
        )
        feat_name = (
            self.combo_feature_name.currentText().strip()
            if hasattr(self, "combo_feature_name")
            else ""
        )
        if feat_name == UILabels.FEATURE_NEW_OPTION:
            # T-0027: no free-text new-feature field remains inline; the
            # placeholder option means "no concrete feature selected yet".
            feat_name = ""

        attr_type = self._get_attribute_value().strip()

        return {
            "drawing_name": d_name,
            "excavation_type": ex_type,
            "feature_name": feat_name if ex_type == ExcavationType.FEATURE.value else "",
            "attribute_type": attr_type,
        }

    def _push_focus_state_to_tool(self) -> None:
        """Push current Focus Mode state to CanvasDigitizingTool (Step3: one-way push).

        Called whenever Focus Mode is toggled or any of the four category
        selectors change, so the map tool never needs to call back into this
        dock widget to read UI state (see CanvasDigitizingTool.update_focus_state).
        """
        if getattr(self, "map_tool", None) is not None:
            self.map_tool.update_focus_state(
                self.is_focus_mode_active(), self.get_focus_category_filter()
            )

    def _on_focus_mode_toggled(self, checked: bool) -> None:
        """Handle Focus Mode toggle button click.

        :param checked: True if toggled ON, False if OFF.
        :type checked: bool
        """
        if checked:
            self.btn_focus_mode.setText(UILabels.BTN_FOCUS_ON)
            self.btn_focus_mode.setStyleSheet(
                "background-color: #1976D2; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 4px;"
            )
        else:
            self.btn_focus_mode.setText(UILabels.BTN_FOCUS_OFF)
            self.btn_focus_mode.setStyleSheet("")

        self._push_focus_state_to_tool()
        self.update_symbology_opacity()

    def _on_slider_value_changed(self, val: int) -> None:
        """Update opacity label in real-time as slider is dragged.

        :param val: Slider value (0-100).
        :type val: int
        """
        self.lbl_opacity_val.setText(f"{val}%")

    def _on_slider_released(self) -> None:
        """Trigger symbology opacity update only on slider release event."""
        if self.is_focus_mode_active():
            self.update_symbology_opacity()

    def _on_category_changed(self, *args: Any) -> None:
        """Synchronize symbology opacity, drawing visibility, point number, and
        点情報パネル status when category changes.

        Triggered whenever attribute type (S/P/C/SP), excavation type,
        feature name, or target drawing changes (see
        _on_excavation_type_changed / _on_feature_combo_changed below, both
        of which delegate here).

        T-0032: while an existing point is selected (self.selected_edit_point_id
        is not None), auto-numbering (_apply_next_point_number) is skipped so
        that changing 出土形態/遺構名/属性 while editing an existing point does
        not clobber its point_name/branch_no; only the SP<->QSpinBox widget
        visibility is refreshed (per T-0022/T-0023 value retention rules).
        """
        current_drawing = (
            self.combo_drawing_name.currentText().strip()
            if hasattr(self, "combo_drawing_name")
            else ""
        )
        if current_drawing:
            self._ensure_drawing_visible(current_drawing)

        if getattr(self, "selected_edit_point_id", None) is not None:
            self._update_point_name_widget_visibility()
        else:
            self._apply_next_point_number()

        self._push_focus_state_to_tool()
        if self.is_focus_mode_active():
            self.update_symbology_opacity()

        self._refresh_point_info_labels()
        self._update_point_info_status()

    def _update_feature_related_visibility(self) -> None:
        """Sync 遺構名セレクタ/作成ボタン/カラーピッカー visibility with the
        current excavation type + feature selection (T-0027, updated T-0032).

        The 作成 button is enabled only while excavation_type is 遺構 and the
        "新規作成" placeholder is still selected (i.e. no concrete feature is
        chosen yet). T-0032: the color picker button is now always visible
        (no longer hidden) and only its enabled state toggles, per the new
        "常時表示、条件を満たす場合のみ有効化" requirement.
        """
        is_feature = self.combo_excavation_type.currentText() == ExcavationType.FEATURE.value
        self.row_feature_selector.setVisible(is_feature)

        is_placeholder = self.combo_feature_name.currentText() == UILabels.FEATURE_NEW_OPTION
        self.btn_create_feature.setEnabled(is_feature and is_placeholder)
        self.btn_color_picker.setEnabled(is_feature and not is_placeholder)
        self._update_color_picker_button()

    def _on_excavation_type_changed(self, index: int) -> None:
        """Toggle feature name selector/create button/color picker based on excavation type."""
        self._update_feature_related_visibility()
        self._on_category_changed()

    def _on_feature_combo_changed(self, text: str) -> None:
        """Toggle create button/color picker when the feature selection changes."""
        self._update_feature_related_visibility()
        self._on_category_changed()

    def _restore_feature_names(self) -> None:
        """Extract existing unique feature names from points layer and populate combo box."""
        if not self.point_layer or not self.point_layer.isValid():
            return

        UIStyleHelper.populate_combo_from_layer_field(
            self.combo_feature_name,
            self.point_layer,
            "feature_name",
            leading_item=UILabels.FEATURE_NEW_OPTION,
            target_list=self.feature_name_list,
        )

    def register_new_feature_name(self, new_name: str) -> str:
        """Register a newly entered feature name into the combo box and select it."""
        clean_name = new_name.strip()
        idx = self.combo_feature_name.findText(clean_name)
        if idx >= 0:
            self.combo_feature_name.setCurrentIndex(idx)
        else:
            self.combo_feature_name.addItem(clean_name)
            self.feature_name_list.append(clean_name)
            self.combo_feature_name.setCurrentText(clean_name)
        return clean_name

    def _on_create_feature_clicked(self) -> None:
        """Open FeatureCreateDialog (T-0027); on OK, register the new feature name.

        T-0032: no longer auto-opens the color picker afterwards (the former
        immediate _pick_color() call is removed) -- カラーボタンは常時表示の
        ため、ユーザーが任意のタイミングで手動選択する運用に変更された。
        """
        dlg = FeatureCreateDialog(self)
        UIStyleHelper.apply_theme(dlg)
        if dlg.exec_() == QDialog.Accepted:
            self.register_new_feature_name(dlg.result_text)

    def _update_color_picker_button(self) -> None:
        """Reflect current feature color on the picker button.

        T-0033: while the button is disabled (no concrete feature selected,
        or 出土形態 is グリッド), it is shown in flat gray instead of the last
        selected feature color, so switching away from a colored feature
        never leaves a misleading color swatch behind. The real color is
        restored automatically the next time the button becomes enabled
        (see _update_feature_related_visibility, which always calls this
        method right after toggling setEnabled()).
        """
        if self.btn_color_picker.isEnabled():
            color_hex = self.current_feature_color.name()
        else:
            color_hex = "#9E9E9E"
        self.btn_color_picker.setStyleSheet(
            f"background-color: {color_hex}; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 4px;"
        )

    def _pick_color(self) -> None:
        """Open QColorDialog to select a feature group color.

        T-0027: applying the color to all points of the selected feature now
        happens immediately once the dialog is accepted (QColorDialog.getColor()
        only returns a valid color on OK), replacing the former separate
        "グループ一括適用" (btn_apply_color) confirmation step.
        """
        color = QColorDialog.getColor(
            self.current_feature_color, self, UIDialogTitles.COLOR_PICKER
        )
        if color.isValid():
            self.current_feature_color = color
            self._update_color_picker_button()
            self._apply_feature_color_group()

    def _apply_feature_color_group(self) -> None:
        """Apply the selected color to all existing points belonging to the selected feature."""
        if not self.point_layer or not self.point_layer.isValid():
            return

        selected_feat = self.combo_feature_name.currentText()
        if selected_feat == UILabels.FEATURE_NEW_OPTION:
            QMessageBox.information(
                self,
                UIMessages.MSG_TITLE_INFO,
                UIMessages.MSG_SELECT_FEATURE_NAME,
            )
            return

        color_hex = self.current_feature_color.name()
        field_idx = self.point_layer.fields().indexFromName("color_code")

        updated_count = 0
        self.point_layer.startEditing()
        for feat in self.point_layer.getFeatures():
            if safe_get_str(feat, "feature_name") == selected_feat:
                self.point_layer.changeAttributeValue(feat.id(), field_idx, color_hex)
                updated_count += 1
        self.point_layer.commitChanges()
        self.point_layer.triggerRepaint()

        self.iface.messageBar().pushMessage(
            UIMessages.MSG_COLOR_APPLIED_TITLE,
            UIMessages.MSG_COLOR_APPLIED.format(
                feature=selected_feat, count=updated_count, color=color_hex
            ),
            level=Qgis.MessageLevel.Info,
            duration=4,
        )

    def get_digitizing_input_state(self) -> Dict[str, Any]:
        """Collect current input parameters for digitizing validation.

        T-0027: feature creation is now performed explicitly beforehand via
        the 作成 button/FeatureCreateDialog (see _on_create_feature_clicked),
        not implicitly at click-time. If excavation_type is 遺構 and the
        "新規作成" placeholder is still selected (no concrete feature chosen
        yet), digitizing is blocked (see _is_feature_name_missing/
        _update_point_info_status, T-0032).
        """
        d_name = (
            self.combo_drawing_name.currentText().strip()
            if hasattr(self, "combo_drawing_name")
            else ""
        )
        ex_type = self.combo_excavation_type.currentText()
        feat_name = self.combo_feature_name.currentText()
        is_placeholder_feat = feat_name == UILabels.FEATURE_NEW_OPTION

        attr_type = self._get_attribute_value()
        pname, branch = self._get_current_point_name_and_branch()

        if not pname:
            return {
                "can_click": False,
                "error_message": UIMessages.ERR_POINT_NAME_REQUIRED,
            }

        if ex_type == ExcavationType.FEATURE.value and is_placeholder_feat:
            return {
                "can_click": False,
                "error_message": UIMessages.ERR_NEW_FEATURE_REQUIRED,
            }

        return {
            "can_click": True,
            "drawing_name": d_name,
            "excavation_type": ex_type,
            "feature_name": feat_name,
            "color_code": self.current_feature_color.name(),
            "attribute_type": attr_type,
            "point_name": pname,
            "branch_no": branch,
        }

    def _is_sp_attribute(self) -> bool:
        """Return True when the currently selected attribute code is 'SP'.

        :return: True if combo_attribute is currently set to AttributeType.SP.value.
        :rtype: bool
        """
        return hasattr(self, "combo_attribute") and self._get_attribute_value() == AttributeType.SP.value

    def _update_point_name_widget_visibility(self) -> None:
        """Show the widget matching the current attribute type, hide the other.

        S/P/C attributes use the QSpinBox (edit_point_name); SP uses the
        free-text QLineEdit (edit_point_name_sp). See T-0022.
        """
        is_sp = self._is_sp_attribute()
        self.edit_point_name.setVisible(not is_sp)
        self.edit_point_name_sp.setVisible(is_sp)

    def _get_next_point_number(self) -> int:
        """Calculate next point number based on current excavation type and feature name.

        Queries the point layer on-demand for the group matching the current
        excavation_type/feature_name selection (see core_logic.get_next_point_number
        for the "直前打刻追従型" (max point_id) numbering strategy).
        """
        ex_type = self.combo_excavation_type.currentText()
        feat_name = ""
        if ex_type == ExcavationType.FEATURE.value:
            feat_name = self.combo_feature_name.currentText()
            if feat_name == UILabels.FEATURE_NEW_OPTION:
                feat_name = ""

        return get_next_point_number(
            self.point_layer,
            ex_type,
            feat_name,
        )

    def _get_current_point_name_and_branch(self) -> Tuple[str, str]:
        """Read the current point-name (SP text or S/P/C spinbox) and branch number.

        :return: Tuple of (point_name, branch_no) trimmed strings.
        :rtype: Tuple[str, str]
        """
        pname = (
            self.edit_point_name_sp.text().strip()
            if self._is_sp_attribute()
            else str(self.edit_point_name.value())
        )
        branch = self.edit_branch_no.text().strip() if hasattr(self, "edit_branch_no") else ""
        return pname, branch

    def _is_feature_name_missing(self) -> bool:
        """Return True when excavation_type is 遺構 but no concrete feature is selected yet.

        :return: True if 遺構名未指定 (エラー優先順位1位, T-0032).
        :rtype: bool
        """
        if not hasattr(self, "combo_excavation_type"):
            return False
        if self.combo_excavation_type.currentText() != ExcavationType.FEATURE.value:
            return False
        return self.combo_feature_name.currentText() == UILabels.FEATURE_NEW_OPTION

    def _check_realtime_duplicate(self) -> Optional[str]:
        """Real-time duplicate check against the currently entered category/point-name state.

        Excludes the currently selected existing point (if any) from the scan,
        so editing a point in-place is never flagged as a duplicate of itself.

        :return: Formatted identifier (core_logic.build_point_ident) if a
            duplicate exists, otherwise None.
        :rtype: Optional[str]
        """
        if not self.point_layer or not self.point_layer.isValid():
            return None

        pname, branch = self._get_current_point_name_and_branch()
        if not pname:
            return None

        ex_type = self.combo_excavation_type.currentText()
        feat_name = self.combo_feature_name.currentText()
        if feat_name == UILabels.FEATURE_NEW_OPTION:
            feat_name = ""
        drawing_name = (
            self.combo_drawing_name.currentText().strip()
            if hasattr(self, "combo_drawing_name")
            else ""
        )

        is_dup = check_point_duplicate(
            self.point_layer,
            ex_type,
            feat_name,
            pname,
            branch,
            drawing_name,
            exclude_feature_id=getattr(self, "selected_edit_point_id", None),
        )
        if not is_dup:
            return None
        return build_point_ident(ex_type, feat_name, pname, branch, drawing_name)

    def _build_point_info_text(self, status_text: str) -> str:
        """Compose the flat multi-line 点情報パネル summary text (T-0033).

        Combines the status line (新規点作成/既設点編集/エラー, no longer given
        a dedicated banner style) with the 出土形態/点名+枝番/XY座標 summary
        lines computed by _refresh_point_info_labels (stored on
        self._point_info_summary), in the same order used since T-0032.

        :param status_text: Current status line text.
        :type status_text: str
        :return: Newline-joined 4-line summary text.
        :rtype: str
        """
        summary = getattr(self, "_point_info_summary", None) or {}
        return "\n".join(
            [
                status_text,
                f"{UILabels.LBL_INFO_GROUP_OR_FEATURE} {summary.get('group', '-')}",
                f"{UILabels.LBL_INFO_POINT_BRANCH} {summary.get('pointname', '-')}",
                f"{UILabels.LBL_INFO_COORDS} {summary.get('coords', '-')}",
            ]
        )

    def _update_error_borders(self) -> None:
        """Apply/remove red error-highlight borders on the fields directly
        implicated by the current 点情報パネル error state (T-0033):
        combo_feature_name for 遺構名未指定, and whichever point-name input
        is currently active (edit_point_name or edit_point_name_sp) for
        点名重複.
        """
        if hasattr(self, "combo_feature_name"):
            UIStyleHelper.set_error_border(self.combo_feature_name, self._is_feature_name_missing())

        if hasattr(self, "edit_point_name") and hasattr(self, "edit_point_name_sp"):
            is_dup = bool(self._check_realtime_duplicate())
            is_sp = self._is_sp_attribute()
            UIStyleHelper.set_error_border(self.edit_point_name, is_dup and not is_sp)
            UIStyleHelper.set_error_border(self.edit_point_name_sp, is_dup and is_sp)

    def _update_point_info_status(self) -> None:
        """Refresh the 点情報パネル summary text/border color (T-0033: flat
        multi-line QLabel inside a create_status_panel()-style left-border
        QFrame, replacing T-0032's separate banner + whole-panel tint).

        Priority order per the design: 遺構名未指定 > 点名重複エラー > normal
        (新規点作成=info/blue / 既設点編集=warning/orange -- reusing
        QFrame[statusType="warning"] since no dedicated "editing" style is
        defined). Also enables/disables the confirm actions
        (btn_rename_point / btn_update_attribute) so they cannot commit
        while an error is active, and refreshes the per-field red error
        borders (see _update_error_borders, T-0033).
        """
        if not hasattr(self, "lbl_point_info_status"):
            return

        is_editing = getattr(self, "selected_edit_point_id", None) is not None
        tooltip = ""

        if self._is_feature_name_missing():
            status_type = "error"
            text = UILabels.STATUS_ERR_FEATURE_REQUIRED
            self._point_info_has_error = True
        else:
            dup_ident = self._check_realtime_duplicate()
            if dup_ident:
                status_type = "error"
                text = UILabels.STATUS_ERR_DUPLICATE
                tooltip = dup_ident
                self._point_info_has_error = True
            else:
                self._point_info_has_error = False
                if is_editing:
                    status_type, text = "warning", UILabels.STATUS_EDIT_POINT
                else:
                    status_type, text = "info", UILabels.STATUS_NEW_POINT

        full_text = self._build_point_info_text(text)
        UIStyleHelper.update_status_panel(
            self.panel_point_info, self.lbl_point_info_status, full_text, status_type
        )
        self.lbl_point_info_status.setToolTip(tooltip)

        self._update_error_borders()

        if hasattr(self, "btn_rename_point"):
            self.btn_rename_point.setEnabled(not self._point_info_has_error)
        if hasattr(self, "btn_update_attribute"):
            self.btn_update_attribute.setEnabled(not self._point_info_has_error)

    def _on_point_identity_changed(self, *args: Any) -> None:
        """Handle edit_point_name(_sp) value changes: refresh summary + status.

        :param args: Unused signal payload (valueChanged(int)/textChanged(str)).
        :type args: Any
        """
        self._refresh_point_info_labels()
        self._update_point_info_status()

    def _refresh_point_info_labels(self, override: Optional[Dict[str, Any]] = None) -> None:
        """Recompute the 出土形態/点名+枝番/XY座標 summary lines for 点情報パネル
        (T-0027/T-0032; T-0033: stored on self._point_info_summary and
        rendered into the flat multi-line panel text by
        _update_point_info_status/_build_point_info_text rather than being
        set directly on now-removed per-line QLabels).

        :param override: When set (an existing point is selected), the
            loaded feature data dict (as emitted by
            CanvasDigitizingTool.existing_point_selected) is displayed
            instead of the live category-widget selections.
        :type override: Optional[Dict[str, Any]]
        """
        if not hasattr(self, "lbl_point_info_status"):
            return

        if override is not None:
            ex_type = str(override.get("excavation_type") or ExcavationType.GRID.value)
            if ex_type == ExcavationType.FEATURE.value:
                group_label = str(override.get("feature_name") or "") or UILabels.FEATURE_NEW_OPTION
            else:
                group_label = ExcavationType.GRID.value
            pname = str(override.get("point_name") or "")
            branch = str(override.get("branch_no") or "")
            cx = override.get("canvas_x")
            cy = override.get("canvas_y")
            if cx is not None and cy is not None:
                survey_x, survey_y = to_survey_coords(float(cx), float(cy))
                coords_text = f"X: {survey_x:.3f}  Y: {survey_y:.3f}"
            else:
                coords_text = "-"
        else:
            ex_type = (
                self.combo_excavation_type.currentText()
                if hasattr(self, "combo_excavation_type")
                else ExcavationType.GRID.value
            )
            if ex_type == ExcavationType.FEATURE.value:
                group_label = (
                    self.combo_feature_name.currentText()
                    if hasattr(self, "combo_feature_name")
                    else UILabels.FEATURE_NEW_OPTION
                )
            else:
                group_label = ExcavationType.GRID.value
            pname, branch = self._get_current_point_name_and_branch()
            coords_text = "-"

        pn_display = f"{pname} {branch}".strip() if pname else ""
        self._point_info_summary = {
            "group": group_label or "-",
            "pointname": pn_display or "-",
            "coords": coords_text,
        }

    def _apply_next_point_number(self) -> None:
        """Refresh the point-name entry widget(s) for the current attribute/category selection.

        For S/P/C attributes, auto-increments the QSpinBox using the
        "直前打刻追従型" numbering logic. For SP, auto-numbering is skipped
        entirely and the free-text QLineEdit is cleared, awaiting manual entry.
        T-0027: also refreshes the 点情報パネル preview labels.
        """
        self._update_point_name_widget_visibility()
        if self._is_sp_attribute():
            self.edit_point_name_sp.clear()
        else:
            next_num = self._get_next_point_number()
            self.edit_point_name.setValue(next_num)
        self._refresh_point_info_labels()

    @pyqtSlot(str)
    def _on_branch_text_changed(self, text: str) -> None:
        """Handle branch number cleared to increment point number if previously digitized with branch."""
        if not text.strip() and self._has_digitized_with_branch:
            self._apply_next_point_number()
            self._has_digitized_with_branch = False
        self._on_point_identity_changed()

    def _on_canvas_clicked(self, map_point: QgsPointXY) -> None:
        """Handle a plain (non-hit) click on the main canvas from CanvasDigitizingTool.

        Validates the current digitizing input state, resolves duplicate
        checks, builds the feature via core_logic.build_digitized_feature(),
        and writes it to point_layer. This consolidates logic that
        previously lived in CanvasDigitizingTool._handle_digitize_click
        (Step3: event-driven decoupling — map_tool.py now only reports
        "canvas was clicked here").

        T-0027: if an existing point is currently selected, a click on
        blank canvas space (this handler is only reached when
        CanvasDigitizingTool found no point hit) deselects it instead of
        digitizing a new point, mirroring the former "連番再開" behavior.

        T-0032: the former QMessageBox-based duplicate-error prompt is
        removed; digitizing is silently blocked (no dialog) whenever the
        live 点情報パネル status would show an error (遺構名未指定 or 点名重複),
        since that state is already visible to the user via the panel's
        color/status band before they click.

        :param map_point: Click location in standard mathematical/canvas coordinates.
        :type map_point: QgsPointXY
        """
        if not self.point_layer or not self.point_layer.isValid():
            return

        if self.selected_edit_point_id is not None:
            self._reset_point_selection()
            return

        # 1. Retrieve and validate current digitizing input state
        state = self.get_digitizing_input_state()
        if not state.get("can_click", False):
            return

        # 2. Real-time error checks (遺構名未指定 / 点名重複); replaces the
        # former QMessageBox.warning() duplicate-error prompt (T-0032).
        if self._is_feature_name_missing() or self._check_realtime_duplicate():
            self._update_point_info_status()
            return

        drawing_name = state.get("drawing_name", "")
        excavation_type = state["excavation_type"]
        feature_name = state["feature_name"]
        color_code = state["color_code"]
        attribute_type = state["attribute_type"]
        point_name = state["point_name"]
        branch_no = state["branch_no"]

        # 3. Determine next point_id
        next_point_id = get_next_point_id(self.point_layer)

        # 4. Resolve pixel coordinates on the source drawing via the affine adapter
        pixel_coords = (0.0, 0.0)
        if drawing_name and self.layer_manager:
            meta = self.layer_manager.load_image_metadata()
            layer_meta = meta.get(drawing_name)
            affine_params = layer_meta.get("affine_params") if layer_meta else None
            pixel_coords = pixel_from_affine(affine_params, map_point)

        # 5. Build the feature (pre-georeferenced: canvas coords ARE real coords)
        new_feat = build_digitized_feature(
            self.point_layer,
            next_point_id,
            map_point,
            {
                "drawing_name": drawing_name,
                "excavation_type": excavation_type,
                "feature_name": feature_name if excavation_type == ExcavationType.FEATURE.value else "",
                "color_code": color_code if excavation_type == ExcavationType.FEATURE.value else "",
                "attribute_type": attribute_type,
                "point_name": point_name,
                "branch_no": branch_no,
            },
            pixel_coords=pixel_coords,
        )

        # 6. Write the new feature to the layer
        insert_feature_to_layer(self.point_layer, new_feat)

        # 7. Update UI (auto-increment point number / point info panel)
        self._on_point_digitized({
            "point_id": next_point_id,
            "drawing_name": drawing_name,
            "point_name": point_name,
            "branch_no": branch_no,
            "excavation_type": excavation_type,
            "feature_name": feature_name,
        })

    def _on_point_digitized(self, data: dict) -> None:
        """Handle point digitization completion (T-0027: no more status panel;
        the 点情報パネル preview labels are refreshed via _apply_next_point_number
        or, for branch-suffixed digitizing, explicitly below).
        """
        branch_no = data.get("branch_no", "")
        if branch_no:
            self._has_digitized_with_branch = True
        else:
            self._has_digitized_with_branch = False
            self._apply_next_point_number()
        self._refresh_point_info_labels()
        self._update_point_info_status()

    # T-0032: only the target-drawing selector remains locked while an
    # existing point is selected. T-0027/T-0023's former lock list also
    # covered 出土形態/遺構名/属性/点名/枝番 widgets, but those are now
    # directly editable during existing-point editing (see btn_rename_point/
    # btn_update_attribute for the corresponding commit actions).
    _CATEGORY_LOCK_WIDGET_NAMES = (
        "combo_drawing_name",
    )

    def _set_category_widgets_locked(self, locked: bool) -> None:
        """Enable/disable the widgets that must stay locked while an existing
        point is selected (T-0023/T-0027/T-0032; see _CATEGORY_LOCK_WIDGET_NAMES).

        :param locked: True to disable (lock) the widgets, False to re-enable them.
        :type locked: bool
        """
        for name in self._CATEGORY_LOCK_WIDGET_NAMES:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setEnabled(not locked)

    @pyqtSlot(dict)
    def _on_existing_point_selected(self, data: dict) -> None:
        """Load an existing point's attributes into the dock widget for editing."""
        self.selected_edit_point_id = data.get("feature_id")
        # T-0023: retain the full loaded data (drawing_name is immutable
        # while selected; excavation_type/feature_name/attribute_type/
        # point_name/branch_no are now editable in-place, see
        # btn_rename_point/btn_update_attribute) for reuse and for keeping
        # local state in sync after in-place commits.
        self._selected_point_data = dict(data)

        # Select drawing if present
        d_name = str(data.get("drawing_name") or "").strip()
        if d_name and hasattr(self, "combo_drawing_name"):
            idx = self.combo_drawing_name.findText(d_name)
            if idx >= 0:
                self.combo_drawing_name.setCurrentIndex(idx)
            self._ensure_drawing_visible(d_name)

        ex_type = str(data.get("excavation_type") or ExcavationType.GRID.value)
        self.combo_excavation_type.setCurrentText(ex_type)

        if ex_type == ExcavationType.FEATURE.value:
            feat_name = str(data.get("feature_name") or "")
            self.register_new_feature_name(feat_name)
            color_code = str(data.get("color_code") or "#FF5722")
            self.current_feature_color = QColor(color_code)
            self._update_color_picker_button()

        # T-0022: attribute must be applied before the point-name value, since
        # changing combo_attribute triggers _on_category_changed. T-0032:
        # since self.selected_edit_point_id is already set above,
        # _on_category_changed now skips auto-numbering (see its docstring),
        # so this no longer clobbers the point_name value set below.
        attr_type = str(data.get("attribute_type") or AttributeType.S.value)
        self._set_attribute_value(attr_type)

        pname_raw = str(data.get("point_name") or "")
        if attr_type == AttributeType.SP.value:
            self.edit_point_name_sp.setText(pname_raw)
        else:
            try:
                p_val = int(pname_raw or 1)
            except ValueError:
                p_val = 1
            self.edit_point_name.setValue(p_val)
        self._update_point_name_widget_visibility()

        self.edit_branch_no.setText(str(data.get("branch_no") or ""))

        self.row_existing_actions.show()
        self.btn_update_attribute.show()
        self._set_category_widgets_locked(True)
        # T-0027: force the final display to reflect the loaded feature data,
        # overriding any transient normal-mode refresh triggered by the
        # combo/attribute assignments above.
        self._refresh_point_info_labels(override=data)
        self._update_point_info_status()

    def _reset_point_selection(self) -> None:
        """Reset form back to new point creation mode."""
        self.selected_edit_point_id = None
        self._selected_point_data = None
        self.row_existing_actions.hide()
        self.btn_update_attribute.hide()
        self._set_category_widgets_locked(False)

        self._apply_next_point_number()
        self.edit_branch_no.clear()
        self._has_digitized_with_branch = False
        self._refresh_point_info_labels()
        self._update_point_info_status()

        # T-0023: clear the persistent selection marker on the main canvas.
        if getattr(self, "map_tool", None) is not None:
            self.map_tool.clear_selected_marker()

    def _on_delete_selected_point(self) -> None:
        """Delete the currently selected point from point layer.

        T-0027: deletion is now immediate (no confirmation dialog), replacing
        the former QMessageBox.question() confirmation step.
        """
        if self.selected_edit_point_id is None or not self.point_layer:
            return

        self.point_layer.startEditing()
        self.point_layer.deleteFeature(self.selected_edit_point_id)
        self.point_layer.commitChanges()
        self.point_layer.triggerRepaint()

        self.iface.messageBar().pushMessage(
            UIMessages.MSG_DELETE_SUCCESS_TITLE,
            UIMessages.MSG_DELETE_SUCCESS,
            level=Qgis.MessageLevel.Success,
            duration=3,
        )
        self._reset_point_selection()

    def _on_rename_point_clicked(self) -> None:
        """Commit the in-panel edit_point_name(_sp)/edit_branch_no values to the
        selected existing point (T-0032).

        Replaces the former PointRenameDialog-based flow (T-0027, now
        removed): point_name/branch_no are edited directly in 点情報パネル and
        this button commits them immediately. A real-time 遺構名未指定/点名重複
        check (mirroring the 点情報パネル status band) guards the write; on
        error, nothing is committed and the panel's error status is refreshed
        (no dialog is shown, per T-0032).
        """
        if self.selected_edit_point_id is None or not self.point_layer:
            return

        if self._is_feature_name_missing() or self._check_realtime_duplicate():
            self._update_point_info_status()
            return

        point_name, branch_no = self._get_current_point_name_and_branch()
        if not point_name:
            self._update_point_info_status()
            return

        field_names = self.point_layer.fields().names()
        pname_idx = field_names.index("point_name")
        branch_idx = field_names.index("branch_no")

        self.point_layer.startEditing()
        self.point_layer.changeAttributeValue(self.selected_edit_point_id, pname_idx, point_name)
        self.point_layer.changeAttributeValue(self.selected_edit_point_id, branch_idx, branch_no)
        self.point_layer.commitChanges()
        self.point_layer.triggerRepaint()

        if self._selected_point_data is not None:
            self._selected_point_data["point_name"] = point_name
            self._selected_point_data["branch_no"] = branch_no

        self.iface.messageBar().pushMessage(
            UIMessages.MSG_RENAME_POINT_SUCCESS_TITLE,
            UIMessages.MSG_RENAME_POINT_SUCCESS,
            level=Qgis.MessageLevel.Success,
            duration=3,
        )
        self._refresh_point_info_labels(override=self._selected_point_data)
        self._update_point_info_status()

    def _on_update_attribute_clicked(self) -> None:
        """Commit the in-panel 出土形態/遺構名/属性 selections to the selected
        existing point (T-0032; new "属性変更" button in 属性パネル).

        点名/枝番はここでは扱わない(btn_rename_point/_on_rename_point_clicked
        側の責務)。書き込み後は必ず commitChanges() -> triggerRepaint() を呼び、
        シンボロジ(色分け/透明度フィルタ)が反映されるようにする。
        """
        if self.selected_edit_point_id is None or not self.point_layer:
            return

        if self._is_feature_name_missing():
            self._update_point_info_status()
            return

        ex_type = self.combo_excavation_type.currentText()
        feat_name = self.combo_feature_name.currentText()
        if feat_name == UILabels.FEATURE_NEW_OPTION:
            feat_name = ""
        is_feature = ex_type == ExcavationType.FEATURE.value
        attr_value = self._get_attribute_value()

        updates: Dict[str, Any] = {
            "excavation_type": ex_type,
            "feature_name": feat_name if is_feature else "",
            "color_code": self.current_feature_color.name() if is_feature else "",
            "attribute_type": attr_value,
        }

        field_names = self.point_layer.fields().names()
        self.point_layer.startEditing()
        for field_name, value in updates.items():
            if field_name in field_names:
                idx = field_names.index(field_name)
                self.point_layer.changeAttributeValue(self.selected_edit_point_id, idx, value)
        self.point_layer.commitChanges()
        self.point_layer.triggerRepaint()

        if self._selected_point_data is not None:
            self._selected_point_data.update(updates)

        if self.is_focus_mode_active():
            self.update_symbology_opacity()

        self.iface.messageBar().pushMessage(
            UIMessages.MSG_UPDATE_ATTRIBUTE_TITLE,
            UIMessages.MSG_UPDATE_ATTRIBUTE_SUCCESS,
            level=Qgis.MessageLevel.Success,
            duration=3,
        )
        self._refresh_point_info_labels(override=self._selected_point_data)
        self._update_point_info_status()

    def _browse_csv_path(self) -> None:
        """Browse destination path for CSV export."""
        default_dir = self.layers_dict.get("session_dir", os.path.expanduser("~"))
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            UIDialogTitles.BROWSE_CSV,
            default_dir,
            UIDialogTitles.CSV_FILTER,
        )
        if filepath:
            self.edit_csv_path.setText(os.path.normpath(filepath))

    def _on_export_csv_clicked(self) -> None:
        """Export digitized points directly to CSV."""
        filepath = self.edit_csv_path.text().strip()
        if not filepath:
            self._browse_csv_path()
            filepath = self.edit_csv_path.text().strip()
            if not filepath:
                return

        encoding = "utf-8-sig" if self.radio_utf8.isChecked() else "cp932"
        success, msg = export_points_to_csv(
            self.point_layer, filepath, encoding=encoding, parent=self
        )

        if success:
            self.iface.messageBar().pushMessage(
                UIMessages.MSG_EXPORT_CSV_TITLE,
                msg,
                level=Qgis.MessageLevel.Success,
                duration=5,
            )
