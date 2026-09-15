"""
/***************************************************************************
 PointerGeocoding Plugin - Start / Session Selection Dialog
 ***************************************************************************/
"""
# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

import csv
import os
import re
from typing import Dict, Any, Optional, Tuple, List

from qgis.core import Qgis
from qgis.gui import QgsFilterLineEdit, QgsCollapsibleGroupBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QRadioButton,
    QLabel,
    QPushButton,
    QFileDialog,
    QWidget,
    QFrame,
    QLineEdit,
    QSpinBox,
)

try:
    from qgis.PyQt.QtGui import QRegularExpressionValidator
    from qgis.PyQt.QtCore import QRegularExpression
    HAS_QT_REGEX = True
except ImportError:
    from qgis.PyQt.QtGui import QRegExpValidator
    from qgis.PyQt.QtCore import QRegExp
    HAS_QT_REGEX = False

from .core_logic import from_excel_column, to_excel_column
from .style_helper import UIStyleHelper

# UI Configuration dictionary and layout ratios
UI_CONFIG = {
    "MAIN_RATIO": (2, 8),
    "ROW_HEIGHT": 32,
    "LABELS": {
        "WINDOW_TITLE": "点群座標取得 - セッション選択",
        "GROUP_SESSION": "セッション設定",
        "GROUP_GRID": "グリッド設定",
        "SESSION_TYPE": "セッション種別:",
        "RADIO_NEW": "新規セッション",
        "RADIO_EXISTING": "既存セッション",
        "FOLDER_PARENT": "親ディレクトリ:",
        "FOLDER_EXISTING": "セッションフォルダ:",
        "BTN_BROWSE": "参照...",
        "SESSION_NAME": "セッション名:",
        "GRID_CSV": "グリッドCSV選択:",
        "ORIGIN_GROUP": "原点 (1A-00):",
        "RANGE_X_GROUP": "X範囲:",
        "RANGE_Y_GROUP": "Y範囲:",
        "RANGE_MIN": "最小:",
        "RANGE_MAX": "最大:",
        "PREVIEW_TITLE": "グリッドプレビュー:",
        "COORD_X": "X:",
        "COORD_Y": "Y:",
        "BTN_OK": "セッションを開始",
        "BTN_CANCEL": "キャンセル",
    },
    "PLACEHOLDERS": {
        "FOLDER_NEW": "セッションフォルダを新規作成する親ディレクトリを選択してください",
        "FOLDER_EXISTING": "既存のセッションフォルダ（.qgzが存在するフォルダ）を選択してください",
        "SESSION_NAME": "例: session_01 (半角英数推奨)",
        "GRID_CSV": "既存のPointGeo_grid.csvを選択（指定時は原点・範囲を無効化）",
        "PREVIEW_Y": "A",
    },
    "DIALOG_TITLES": {
        "BROWSE_FOLDER_NEW": "親保存先フォルダを選択",
        "BROWSE_FOLDER_EXISTING": "既存セッションフォルダを選択",
        "BROWSE_GRID_CSV": "グリッドCSVファイルを選択",
        "CSV_FILTER": "CSVファイル (*.csv);;すべてのファイル (*.*)",
    },
    "MESSAGES": {
        "OUT_OF_BOUNDS": "範囲外",
        "ERR_TITLE_INPUT": "入力エラー",
        "ERR_TITLE_PATH": "パスエラー",
        "ERR_TITLE_DUPLICATE": "重複エラー",
        "ERR_TITLE_GENERIC": "エラー",
        "ERR_FOLDER_REQUIRED_NEW": "親ディレクトリを指定してください。",
        "ERR_FOLDER_REQUIRED_EXISTING": "既存セッションフォルダを指定してください。",
        "ERR_FOLDER_NOT_FOUND": "指定されたフォルダが存在しません:\n{path}",
        "ERR_SESSION_NAME_REQUIRED": "セッション名を入力してください。",
        "ERR_SESSION_NAME_INVALID": "セッション名に使用できない文字 (\\ / : * ? \" < > |) が含まれています。\n適切な名称を入力してください。",
        "ERR_SESSION_EXISTS": "指定された親ディレクトリ内に同名のフォルダが既に存在します:\n{name}\n別のセッション名を指定してください。",
        "ERR_NO_QGZ": "選択されたフォルダ内にQGISプロジェクトファイル (.qgz) が見つかりません:\n{path}\n有効なセッションフォルダを選択してください。",
        "ERR_CSV_NOT_FOUND": "指定されたグリッドCSVファイルが存在しません:\n{path}",
        "ERR_RANGE_INVALID": "X範囲・Y範囲は、それぞれ最小値が最大値以下になるように指定してください。",
    },
    "LIMITS": {
        "RANGE_X_MIN_VALUE": 1,
        "RANGE_X_MAX_VALUE": 300,
        "RANGE_X_DEFAULT_MIN": 1,
        "RANGE_X_DEFAULT_MAX": 10,
        "RANGE_Y_DEFAULT_MIN": 1,
        "RANGE_Y_DEFAULT_MAX": 10,
    },
}

MAIN_RATIO = UI_CONFIG["MAIN_RATIO"]


class ExcelColumnSpinBox(QSpinBox):
    """QSpinBox variant that displays/accepts an Excel-style column letter
    (A, B, ..., Z, AA, AB, ..., ZZ) while internally storing the equivalent
    1-based integer index (1..702). Used for the Y-axis grid range inputs,
    where the large-grid axis is identified by a 1-2 character uppercase
    alphabetic label (see grid_csv_mixin.generate_grid_csv / core_logic.
    to_excel_column / from_excel_column)."""

    MIN_VALUE = 1
    MAX_VALUE = 702  # 'ZZ'

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the spinbox with a fixed 'A'..'ZZ' range.

        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)
        if HAS_QT_REGEX:
            self._validator = QRegularExpressionValidator(
                QRegularExpression(r"^[A-Za-z]{1,2}$"), self
            )
        else:
            self._validator = QRegExpValidator(QRegExp(r"^[A-Za-z]{1,2}$"), self)
        self.setRange(self.MIN_VALUE, self.MAX_VALUE)

    def textFromValue(self, value: int) -> str:
        """Render the internal integer as an Excel-style column letter.

        :param value: 1-based integer value.
        :type value: int
        :return: Excel-style column letter representation.
        :rtype: str
        """
        return to_excel_column(value)

    def valueFromText(self, text: str) -> int:
        """Parse an Excel-style column letter back into a 1-based integer.

        :param text: Excel-style column letter string.
        :type text: str
        :return: 1-based integer value (clamped to the valid range).
        :rtype: int
        """
        value = from_excel_column(text)
        if value <= 0:
            return self.MIN_VALUE
        return min(value, self.MAX_VALUE)

    def validate(self, text: str, pos: int):
        """Restrict input to 1-2 half-width uppercase (or lowercase) letters.

        :param text: Current editor text.
        :type text: str
        :param pos: Cursor position within the text.
        :type pos: int
        :return: Validation result tuple (state, text, pos).
        """
        return self._validator.validate(text, pos)


class StartDialog(QDialog):
    """Dialog for creating a new digitizing session or loading an existing one."""

    # Pattern to detect invalid characters in directory or file names on Windows and UNIX
    INVALID_CHARS_PATTERN = r'[\\/:*?"<>|]'

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the session startup dialog.

        :param parent: Optional parent QWidget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)
        self.setWindowTitle(UI_CONFIG["LABELS"]["WINDOW_TITLE"])
        self.setModal(True)
        self.setMinimumWidth(600)

        self._init_ui()
        UIStyleHelper.apply_theme(self)
        self._on_session_type_changed()
        self._update_grid_coordinate_preview()

    def _init_ui(self) -> None:
        """Construct the user interface programmatically using native QGIS widgets and flexbox builders."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 1. Configuration Parameters Group (QgsCollapsibleGroupBox)
        config_group = QgsCollapsibleGroupBox(UI_CONFIG["LABELS"]["GROUP_SESSION"], self)
        config_group.setCollapsed(False)
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)

        # Row 0: Session Type Selection
        self.lbl_type = QLabel(UI_CONFIG["LABELS"]["SESSION_TYPE"], config_group)
        self.radio_new = QRadioButton(UI_CONFIG["LABELS"]["RADIO_NEW"], config_group)
        self.radio_new.setChecked(True)
        self.radio_existing = QRadioButton(UI_CONFIG["LABELS"]["RADIO_EXISTING"], config_group)
        self.radio_new.toggled.connect(self._on_session_type_changed)

        row_session_type = UIStyleHelper.build_flex_row(
            self.lbl_type,
            [(self.radio_new, 1), (self.radio_existing, 1), (None, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UI_CONFIG["ROW_HEIGHT"],
        )
        config_layout.addWidget(row_session_type)

        # Row 1: Directory Path (Parent Directory for NEW, Session Folder for EXISTING)
        self.lbl_folder = QLabel(UI_CONFIG["LABELS"]["FOLDER_PARENT"], config_group)
        self.edit_folder = QgsFilterLineEdit(config_group)
        self.edit_folder.setShowClearButton(True)
        self.btn_browse_folder = QPushButton(UI_CONFIG["LABELS"]["BTN_BROWSE"], config_group)
        self.btn_browse_folder.clicked.connect(self._browse_folder)

        row_folder = UIStyleHelper.build_flex_row(
            self.lbl_folder,
            [(self.edit_folder, 1), (self.btn_browse_folder, 0)],
            main_ratio=MAIN_RATIO,
            row_height=UI_CONFIG["ROW_HEIGHT"],
        )
        config_layout.addWidget(row_folder)

        # Row 2: Session Name (Enabled only for NEW session)
        self.lbl_session_name = QLabel(UI_CONFIG["LABELS"]["SESSION_NAME"], config_group)
        self.edit_session_name = QgsFilterLineEdit(config_group)
        self.edit_session_name.setShowClearButton(True)
        self.edit_session_name.setPlaceholderText(UI_CONFIG["PLACEHOLDERS"]["SESSION_NAME"])

        row_session_name = UIStyleHelper.build_flex_row(
            self.lbl_session_name,
            [(self.edit_session_name, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UI_CONFIG["ROW_HEIGHT"],
        )
        config_layout.addWidget(row_session_name)
        config_layout.addStretch()

        main_layout.addWidget(config_group)

        # 2. Grid Configuration Group (QgsCollapsibleGroupBox)
        self.grid_group = QgsCollapsibleGroupBox(UI_CONFIG["LABELS"]["GROUP_GRID"], self)
        self.grid_group.setCollapsed(False)
        grid_group_layout = QVBoxLayout(self.grid_group)
        grid_group_layout.setSpacing(10)

        # Row 0: Grid CSV Selection
        self.lbl_grid_csv = QLabel(UI_CONFIG["LABELS"]["GRID_CSV"], self.grid_group)
        self.edit_grid_csv = QgsFilterLineEdit(self.grid_group)
        self.edit_grid_csv.setShowClearButton(True)
        self.edit_grid_csv.setPlaceholderText(UI_CONFIG["PLACEHOLDERS"]["GRID_CSV"])
        self.btn_browse_grid_csv = QPushButton(UI_CONFIG["LABELS"]["BTN_BROWSE"], self.grid_group)
        self.btn_browse_grid_csv.clicked.connect(self._browse_grid_csv)
        self.edit_grid_csv.textChanged.connect(self._on_grid_csv_changed)

        row_grid_csv = UIStyleHelper.build_flex_row(
            self.lbl_grid_csv,
            [(self.edit_grid_csv, 1), (self.btn_browse_grid_csv, 0)],
            main_ratio=MAIN_RATIO,
            row_height=UI_CONFIG["ROW_HEIGHT"],
        )
        grid_group_layout.addWidget(row_grid_csv)

        # Row 1: Flat Status Panel containing Origin and Grid Count Settings in 2 rows
        self.panel_grid_settings = QFrame(self.grid_group)
        UIStyleHelper.set_status_panel(self.panel_grid_settings)
        panel_settings_layout = QVBoxLayout(self.panel_grid_settings)
        panel_settings_layout.setContentsMargins(8, 6, 8, 6)
        panel_settings_layout.setSpacing(8)

        # 1st Row: Origin Coordinates (1A-00)
        self.lbl_origin_group = QLabel(UI_CONFIG["LABELS"]["ORIGIN_GROUP"], self.panel_grid_settings)
        self.lbl_origin_group.setStyleSheet("font-weight: bold;")
        self.lbl_origin_x = QLabel(UI_CONFIG["LABELS"]["COORD_X"], self.panel_grid_settings)
        self.spin_origin_x = UIStyleHelper.create_spinbox(-9999999, 9999999, 0, self.panel_grid_settings)
        child_origin_x = UIStyleHelper.build_child_container(self.lbl_origin_x, self.spin_origin_x)

        self.lbl_origin_y = QLabel(UI_CONFIG["LABELS"]["COORD_Y"], self.panel_grid_settings)
        self.spin_origin_y = UIStyleHelper.create_spinbox(-9999999, 9999999, 0, self.panel_grid_settings)
        child_origin_y = UIStyleHelper.build_child_container(self.lbl_origin_y, self.spin_origin_y)

        row_origin = UIStyleHelper.build_flex_row(
            self.lbl_origin_group,
            [(child_origin_x, 1), (child_origin_y, 1), (None, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UI_CONFIG["ROW_HEIGHT"],
        )
        panel_settings_layout.addWidget(row_origin)

        # 2nd Row: X-axis Grid Range (numeric, min/max, both ends inclusive)
        limits = UI_CONFIG["LIMITS"]
        self.lbl_range_x_group = QLabel(UI_CONFIG["LABELS"]["RANGE_X_GROUP"], self.panel_grid_settings)
        self.lbl_range_x_group.setStyleSheet("font-weight: bold;")
        self.lbl_range_x_min = QLabel(UI_CONFIG["LABELS"]["RANGE_MIN"], self.panel_grid_settings)
        self.spin_range_x_min = UIStyleHelper.create_spinbox(
            limits["RANGE_X_MIN_VALUE"], limits["RANGE_X_MAX_VALUE"], limits["RANGE_X_DEFAULT_MIN"],
            self.panel_grid_settings,
        )
        child_range_x_min = UIStyleHelper.build_child_container(self.lbl_range_x_min, self.spin_range_x_min)

        self.lbl_range_x_max = QLabel(UI_CONFIG["LABELS"]["RANGE_MAX"], self.panel_grid_settings)
        self.spin_range_x_max = UIStyleHelper.create_spinbox(
            limits["RANGE_X_MIN_VALUE"], limits["RANGE_X_MAX_VALUE"], limits["RANGE_X_DEFAULT_MAX"],
            self.panel_grid_settings,
        )
        child_range_x_max = UIStyleHelper.build_child_container(self.lbl_range_x_max, self.spin_range_x_max)

        row_range_x = UIStyleHelper.build_flex_row(
            self.lbl_range_x_group,
            [(child_range_x_min, 1), (child_range_x_max, 1), (None, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UI_CONFIG["ROW_HEIGHT"],
        )
        panel_settings_layout.addWidget(row_range_x)

        # 3rd Row: Y-axis Grid Range (alphabetic 'A'..'ZZ', min/max, both ends inclusive)
        self.lbl_range_y_group = QLabel(UI_CONFIG["LABELS"]["RANGE_Y_GROUP"], self.panel_grid_settings)
        self.lbl_range_y_group.setStyleSheet("font-weight: bold;")
        self.lbl_range_y_min = QLabel(UI_CONFIG["LABELS"]["RANGE_MIN"], self.panel_grid_settings)
        self.spin_range_y_min = ExcelColumnSpinBox(self.panel_grid_settings)
        self.spin_range_y_min.setValue(limits["RANGE_Y_DEFAULT_MIN"])
        child_range_y_min = UIStyleHelper.build_child_container(self.lbl_range_y_min, self.spin_range_y_min)

        self.lbl_range_y_max = QLabel(UI_CONFIG["LABELS"]["RANGE_MAX"], self.panel_grid_settings)
        self.spin_range_y_max = ExcelColumnSpinBox(self.panel_grid_settings)
        self.spin_range_y_max.setValue(limits["RANGE_Y_DEFAULT_MAX"])
        child_range_y_max = UIStyleHelper.build_child_container(self.lbl_range_y_max, self.spin_range_y_max)

        row_range_y = UIStyleHelper.build_flex_row(
            self.lbl_range_y_group,
            [(child_range_y_min, 1), (child_range_y_max, 1), (None, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UI_CONFIG["ROW_HEIGHT"],
        )
        panel_settings_layout.addWidget(row_range_y)

        # 4th Row: Grid Preview Section
        self.lbl_preview_title = QLabel(UI_CONFIG["LABELS"]["PREVIEW_TITLE"], self.panel_grid_settings)
        self.lbl_preview_title.setStyleSheet("font-weight: bold;")

        self.lbl_preview_x = QLabel(UI_CONFIG["LABELS"]["COORD_X"], self.panel_grid_settings)
        self.spin_preview_x = UIStyleHelper.create_spinbox(1, 9999, 1, self.panel_grid_settings)
        child_preview_x = UIStyleHelper.build_child_container(self.lbl_preview_x, self.spin_preview_x)

        self.lbl_preview_y = QLabel(UI_CONFIG["LABELS"]["COORD_Y"], self.panel_grid_settings)
        self.edit_preview_y = QLineEdit(self.panel_grid_settings)
        self.edit_preview_y.setMaxLength(5)
        self.edit_preview_y.setPlaceholderText(UI_CONFIG["PLACEHOLDERS"]["PREVIEW_Y"])
        self.edit_preview_y.setText(UI_CONFIG["PLACEHOLDERS"]["PREVIEW_Y"])
        if HAS_QT_REGEX:
            self.edit_preview_y.setValidator(
                QRegularExpressionValidator(QRegularExpression(r"^[A-Za-z]+$"), self.edit_preview_y)
            )
        else:
            self.edit_preview_y.setValidator(
                QRegExpValidator(QRegExp(r"^[A-Za-z]+$"), self.edit_preview_y)
            )
        child_preview_y = UIStyleHelper.build_child_container(self.lbl_preview_y, self.edit_preview_y)

        row_preview_input = UIStyleHelper.build_flex_row(
            self.lbl_preview_title,
            [(child_preview_x, 1), (child_preview_y, 1), (None, 1)],
            main_ratio=MAIN_RATIO,
            row_height=UI_CONFIG["ROW_HEIGHT"],
        )
        panel_settings_layout.addWidget(row_preview_input)
        panel_settings_layout.addStretch()

        grid_group_layout.addWidget(self.panel_grid_settings)

        # Dynamic Coordinate Result Panel (green success / red error status panel)
        self.panel_preview_status, self.lbl_preview_status = UIStyleHelper.create_status_panel(
            "", status_type="success", parent=self.grid_group
        )
        grid_group_layout.addWidget(self.panel_preview_status)
        grid_group_layout.addStretch()

        # Connect signals for dynamic preview calculation
        self.spin_origin_x.valueChanged.connect(self._update_grid_coordinate_preview)
        self.spin_origin_y.valueChanged.connect(self._update_grid_coordinate_preview)
        self.spin_range_x_min.valueChanged.connect(self._update_grid_coordinate_preview)
        self.spin_range_x_max.valueChanged.connect(self._update_grid_coordinate_preview)
        self.spin_range_y_min.valueChanged.connect(self._update_grid_coordinate_preview)
        self.spin_range_y_max.valueChanged.connect(self._update_grid_coordinate_preview)
        self.spin_preview_x.valueChanged.connect(self._update_grid_coordinate_preview)
        self.edit_preview_y.textChanged.connect(self._update_grid_coordinate_preview)

        main_layout.addWidget(self.grid_group)
        main_layout.addStretch()

        # 3. Action Buttons (Equal width & centered: stretch 1 : btn_ok 1 : btn_cancel 1 : stretch 1)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_ok = QPushButton(UI_CONFIG["LABELS"]["BTN_OK"], self)
        self.btn_ok.setDefault(True)
        self.btn_ok.setFixedHeight(UI_CONFIG["ROW_HEIGHT"])
        UIStyleHelper.set_primary_button(self.btn_ok)
        self.btn_ok.clicked.connect(self._validate_and_accept)

        self.btn_cancel = QPushButton(UI_CONFIG["LABELS"]["BTN_CANCEL"], self)
        self.btn_cancel.setFixedHeight(UI_CONFIG["ROW_HEIGHT"])
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_ok, 1)
        btn_layout.addWidget(self.btn_cancel, 1)
        btn_layout.addStretch(1)

        main_layout.addLayout(btn_layout)

    def _on_session_type_changed(self) -> None:
        """Handle interlock toggling between New and Existing session modes."""
        match self.radio_new.isChecked():
            case True:
                self.lbl_folder.setText(UI_CONFIG["LABELS"]["FOLDER_PARENT"])
                self.edit_folder.setPlaceholderText(UI_CONFIG["PLACEHOLDERS"]["FOLDER_NEW"])
                self.lbl_session_name.setEnabled(True)
                self.edit_session_name.setEnabled(True)
            case False:
                self.lbl_folder.setText(UI_CONFIG["LABELS"]["FOLDER_EXISTING"])
                self.edit_folder.setPlaceholderText(UI_CONFIG["PLACEHOLDERS"]["FOLDER_EXISTING"])
                self.lbl_session_name.setEnabled(False)
                self.edit_session_name.setEnabled(False)

                # Auto-detect existing PointGeo_grid.csv if folder is already selected
                if (folder_path := self.edit_folder.text().strip()) and os.path.isdir(folder_path):
                    potential_csv = os.path.join(folder_path, "PointGeo_grid.csv")
                    if os.path.isfile(potential_csv) and not self.edit_grid_csv.text().strip():
                        self.edit_grid_csv.setText(os.path.normpath(potential_csv))

    def _browse_folder(self) -> None:
        """Open a directory browser dialog based on the selected session mode."""
        is_new = self.radio_new.isChecked()
        match is_new:
            case True:
                dialog_title = UI_CONFIG["DIALOG_TITLES"]["BROWSE_FOLDER_NEW"]
            case False:
                dialog_title = UI_CONFIG["DIALOG_TITLES"]["BROWSE_FOLDER_EXISTING"]

        start_dir = self.edit_folder.text().strip() or os.path.expanduser("~")

        selected_dir = QFileDialog.getExistingDirectory(
            self, dialog_title, start_dir, QFileDialog.ShowDirsOnly
        )
        if selected_dir:
            norm_path = os.path.normpath(selected_dir)
            self.edit_folder.setText(norm_path)
            if not is_new:
                potential_csv = os.path.join(norm_path, "PointGeo_grid.csv")
                if os.path.isfile(potential_csv):
                    self.edit_grid_csv.setText(potential_csv)

    def _browse_grid_csv(self) -> None:
        """Open a file dialog to select an existing PointGeo_grid.csv file."""
        current_csv = self.edit_grid_csv.text().strip()
        start_dir = ""
        if current_csv and os.path.isfile(current_csv):
            start_dir = os.path.dirname(current_csv)
        elif self.edit_folder.text().strip() and os.path.isdir(self.edit_folder.text().strip()):
            start_dir = self.edit_folder.text().strip()
        else:
            start_dir = os.path.expanduser("~")

        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            UI_CONFIG["DIALOG_TITLES"]["BROWSE_GRID_CSV"],
            start_dir,
            UI_CONFIG["DIALOG_TITLES"]["CSV_FILTER"],
        )
        if selected_file:
            self.edit_grid_csv.setText(os.path.normpath(selected_file))

    def _extract_csv_metadata(self, csv_path: str) -> Optional[Dict[str, int]]:
        """Extract origin coordinates and grid range from an existing PointGeo_grid.csv.

        Supports UTF-8 (with or without BOM) and CP932 / Shift-JIS with automatic fallback.
        The origin (1A-00) is back-calculated from any encountered small-grid "00" row
        (upper-left corner of a large grid) using the same offset formula as
        grid_csv_mixin.generate_grid_csv, since the grid range may not start at 1/A.
        Min/max grid range is calculated across all data rows.

        :param csv_path: Absolute path to the grid CSV file.
        :type csv_path: str
        :return: Dictionary with keys 'origin_x', 'origin_y', 'range_x_min', 'range_x_max',
            'range_y_min', 'range_y_max', or None on failure.
        :rtype: Optional[Dict[str, int]]
        """
        if not os.path.isfile(csv_path):
            return None

        for encoding in ("utf-8-sig", "cp932"):
            try:
                with open(csv_path, mode="r", encoding=encoding, newline="") as f:
                    reader = csv.reader(f)
                    derived_origin: Optional[Tuple[int, int]] = None
                    min_gx: Optional[int] = None
                    max_gx: int = 0
                    min_gy: Optional[int] = None
                    max_gy: int = 0

                    col_gx, col_gy, col_sub, col_x, col_y = 0, 1, 2, 3, 4
                    header_parsed: bool = False

                    for row in reader:
                        if not row or not any(field.strip() for field in row):
                            continue

                        # Detect header row
                        if not header_parsed:
                            try:
                                int(row[0].strip())
                            except ValueError:
                                # First element is not integer -> header row
                                for idx, col_name in enumerate(row):
                                    clean_name = col_name.strip()
                                    match clean_name:
                                        case name if "大グリッド" in name and ("Ｘ" in name or "X" in name):
                                            col_gx = idx
                                        case name if "大グリッド" in name and ("Ｙ" in name or "Y" in name):
                                            col_gy = idx
                                        case name if "小グリッド" in name:
                                            col_sub = idx
                                        case name if "Ｘ座標" in name or "X座標" in name or name.upper() == "X":
                                            col_x = idx
                                        case name if "Ｙ座標" in name or "Y座標" in name or name.upper() == "Y":
                                            col_y = idx
                                header_parsed = True
                                continue
                            header_parsed = True

                        # Parse data row
                        try:
                            gx = int(row[col_gx].strip())
                            gy = from_excel_column(row[col_gy].strip())
                            if min_gx is None or gx < min_gx:
                                min_gx = gx
                            if gx > max_gx:
                                max_gx = gx
                            if min_gy is None or gy < min_gy:
                                min_gy = gy
                            if gy > max_gy:
                                max_gy = gy

                            if derived_origin is None:
                                # Back-calculate the theoretical 1A-00 origin from this row's
                                # own small-grid offset (sx, sy), so it works even when the
                                # CSV's grid range does not start at gx=1 / gy=A.
                                sub_grid = row[col_sub].strip() if len(row) > col_sub else ""
                                if len(sub_grid) == 2 and sub_grid.isdigit():
                                    sx = int(sub_grid[0])
                                    sy = int(sub_grid[1])
                                    coord_x = float(row[col_x].strip())
                                    coord_y = float(row[col_y].strip())
                                    ox = int(round(coord_x + (gx - 1) * 40 + sx * 4))
                                    oy = int(round(coord_y - (gy - 1) * 40 - sy * 4))
                                    derived_origin = (ox, oy)
                        except (ValueError, IndexError):
                            continue

                    if derived_origin is not None and min_gx is not None and min_gy is not None:
                        return {
                            "origin_x": derived_origin[0],
                            "origin_y": derived_origin[1],
                            "range_x_min": min_gx,
                            "range_x_max": max_gx,
                            "range_y_min": min_gy,
                            "range_y_max": max_gy,
                        }
            except (UnicodeDecodeError, OSError):
                continue

        return None

    def _on_grid_csv_changed(self, text: str) -> None:
        """Handle grid CSV file selection: extract metadata and update UI state.

        Disables origin and range inputs when a CSV is selected, but keeps
        preview UI elements always enabled. Populates origin and range fields
        with values calculated from the CSV.

        :param text: Current text in the grid CSV line edit.
        :type text: str
        """
        csv_path = text.strip()
        has_csv = bool(csv_path)
        enable_inputs = not has_csv

        # Origin inputs disabled when CSV is specified
        self.lbl_origin_group.setEnabled(enable_inputs)
        self.lbl_origin_x.setEnabled(enable_inputs)
        self.spin_origin_x.setEnabled(enable_inputs)
        self.lbl_origin_y.setEnabled(enable_inputs)
        self.spin_origin_y.setEnabled(enable_inputs)

        # Range inputs disabled when CSV is specified
        self.lbl_range_x_group.setEnabled(enable_inputs)
        self.lbl_range_x_min.setEnabled(enable_inputs)
        self.spin_range_x_min.setEnabled(enable_inputs)
        self.lbl_range_x_max.setEnabled(enable_inputs)
        self.spin_range_x_max.setEnabled(enable_inputs)
        self.lbl_range_y_group.setEnabled(enable_inputs)
        self.lbl_range_y_min.setEnabled(enable_inputs)
        self.spin_range_y_min.setEnabled(enable_inputs)
        self.lbl_range_y_max.setEnabled(enable_inputs)
        self.spin_range_y_max.setEnabled(enable_inputs)

        # Preview inputs are ALWAYS enabled regardless of CSV selection
        self.lbl_preview_title.setEnabled(True)
        self.lbl_preview_x.setEnabled(True)
        self.spin_preview_x.setEnabled(True)
        self.lbl_preview_y.setEnabled(True)
        self.edit_preview_y.setEnabled(True)
        self.panel_preview_status.setEnabled(True)

        # Extract metadata from CSV if valid file exists
        if has_csv and os.path.isfile(csv_path):
            metadata = self._extract_csv_metadata(csv_path)
            if metadata:
                # Extend the X-axis numeric spinbox maxima if the CSV exceeds current limits.
                # (Y-axis ExcelColumnSpinBox already covers the full 'A'..'ZZ' range.)
                if metadata["range_x_max"] > self.spin_range_x_max.maximum():
                    self.spin_range_x_max.setMaximum(metadata["range_x_max"])
                if metadata["range_x_min"] > self.spin_range_x_min.maximum():
                    self.spin_range_x_min.setMaximum(metadata["range_x_min"])

                self.spin_origin_x.setValue(metadata["origin_x"])
                self.spin_origin_y.setValue(metadata["origin_y"])
                self.spin_range_x_min.setValue(metadata["range_x_min"])
                self.spin_range_x_max.setValue(metadata["range_x_max"])
                self.spin_range_y_min.setValue(metadata["range_y_min"])
                self.spin_range_y_max.setValue(metadata["range_y_max"])

        self._update_grid_coordinate_preview()

    def _update_grid_coordinate_preview(self) -> None:
        """Dynamically compute and display coordinates for the preview grid input.
        # 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。

        If within bounds, marks panel as success and shows '{gx}{display_y}-00座標: X: {px}, Y: {py}'.
        If out of bounds, marks panel as error and shows '{gx}{display_y}-00座標: 範囲外'.
        """
        gx = self.spin_preview_x.value()
        y_text = self.edit_preview_y.text().strip().upper()
        gy = from_excel_column(y_text)

        display_y = y_text if y_text else "?"
        grid_prefix = f"{gx}{display_y}-00座標"

        rx_min = self.spin_range_x_min.value()
        rx_max = self.spin_range_x_max.value()
        ry_min = self.spin_range_y_min.value()
        ry_max = self.spin_range_y_max.value()
        ox = self.spin_origin_x.value()
        oy = self.spin_origin_y.value()

        # Check if coordinates are strictly within configured grid range
        # px is Survey X (南北), py is Survey Y (東西)
        if rx_min <= gx <= rx_max and ry_min <= gy <= ry_max:
            px = ox - (gx - 1) * 40
            py = oy + (gy - 1) * 40
            UIStyleHelper.update_status_panel(
                self.panel_preview_status,
                self.lbl_preview_status,
                f"{grid_prefix}: X: {px}, Y: {py}",
                status_type="success",
            )
        else:
            UIStyleHelper.update_status_panel(
                self.panel_preview_status,
                self.lbl_preview_status,
                f"{grid_prefix}: {UI_CONFIG['MESSAGES']['OUT_OF_BOUNDS']}",
                status_type="error",
            )

    def _validate_and_accept(self) -> None:
        """Validate all required inputs according to business constraints before accepting."""
        folder_path = self.edit_folder.text().strip()

        # Check directory input
        if not folder_path:
            msg = (
                UI_CONFIG["MESSAGES"]["ERR_FOLDER_REQUIRED_NEW"]
                if self.radio_new.isChecked()
                else UI_CONFIG["MESSAGES"]["ERR_FOLDER_REQUIRED_EXISTING"]
            )
            UIStyleHelper.show_warning_dialog(self, UI_CONFIG["MESSAGES"]["ERR_TITLE_INPUT"], msg)
            self.edit_folder.setFocus()
            return

        if not os.path.isdir(folder_path):
            UIStyleHelper.show_warning_dialog(
                self,
                UI_CONFIG["MESSAGES"]["ERR_TITLE_PATH"],
                UI_CONFIG["MESSAGES"]["ERR_FOLDER_NOT_FOUND"].format(path=folder_path),
            )
            self.edit_folder.setFocus()
            return

        match self.radio_new.isChecked():
            case True:
                session_name = self.edit_session_name.text().strip()

                # 1. Validate session name
                if not session_name:
                    UIStyleHelper.show_warning_dialog(
                        self,
                        UI_CONFIG["MESSAGES"]["ERR_TITLE_INPUT"],
                        UI_CONFIG["MESSAGES"]["ERR_SESSION_NAME_REQUIRED"],
                    )
                    self.edit_session_name.setFocus()
                    return

                if re.search(self.INVALID_CHARS_PATTERN, session_name):
                    UIStyleHelper.show_warning_dialog(
                        self,
                        UI_CONFIG["MESSAGES"]["ERR_TITLE_INPUT"],
                        UI_CONFIG["MESSAGES"]["ERR_SESSION_NAME_INVALID"],
                    )
                    self.edit_session_name.setFocus()
                    return

                # Check if session folder already exists in the parent directory
                target_session_dir = os.path.join(folder_path, session_name)
                if os.path.exists(target_session_dir):
                    UIStyleHelper.show_warning_dialog(
                        self,
                        UI_CONFIG["MESSAGES"]["ERR_TITLE_DUPLICATE"],
                        UI_CONFIG["MESSAGES"]["ERR_SESSION_EXISTS"].format(name=session_name),
                    )
                    self.edit_session_name.setFocus()
                    return

            case False:
                # Existing session validation: verify that a .qgz file exists
                qgz_files = [f for f in os.listdir(folder_path) if f.endswith(".qgz")]
                if not qgz_files:
                    UIStyleHelper.show_warning_dialog(
                        self,
                        UI_CONFIG["MESSAGES"]["ERR_TITLE_GENERIC"],
                        UI_CONFIG["MESSAGES"]["ERR_NO_QGZ"].format(path=folder_path),
                    )
                    self.edit_folder.setFocus()
                    return

        # Validate grid CSV path if specified
        if (grid_csv := self.edit_grid_csv.text().strip()) and not os.path.isfile(grid_csv):
            UIStyleHelper.show_warning_dialog(
                self,
                UI_CONFIG["MESSAGES"]["ERR_TITLE_INPUT"],
                UI_CONFIG["MESSAGES"]["ERR_CSV_NOT_FOUND"].format(path=grid_csv),
            )
            self.edit_grid_csv.setFocus()
            return

        # Validate X/Y grid range (min must not exceed max) when generating a new grid CSV
        if not grid_csv:
            if self.spin_range_x_min.value() > self.spin_range_x_max.value():
                UIStyleHelper.show_warning_dialog(
                    self,
                    UI_CONFIG["MESSAGES"]["ERR_TITLE_INPUT"],
                    UI_CONFIG["MESSAGES"]["ERR_RANGE_INVALID"],
                )
                self.spin_range_x_min.setFocus()
                return
            if self.spin_range_y_min.value() > self.spin_range_y_max.value():
                UIStyleHelper.show_warning_dialog(
                    self,
                    UI_CONFIG["MESSAGES"]["ERR_TITLE_INPUT"],
                    UI_CONFIG["MESSAGES"]["ERR_RANGE_INVALID"],
                )
                self.spin_range_y_min.setFocus()
                return

        self.accept()

    def get_session_data(self) -> Dict[str, Any]:
        """Retrieve the validated session configuration parameters.

        :return: Dictionary containing session parameters.
        :rtype: Dict[str, Any]
        """
        is_new = self.radio_new.isChecked()
        folder_path = self.edit_folder.text().strip()
        grid_csv = self.edit_grid_csv.text().strip()

        grid_config: Dict[str, Any] = {
            "use_existing_csv": bool(grid_csv),
            "csv_path": grid_csv,
            "origin_x": self.spin_origin_x.value(),
            "origin_y": self.spin_origin_y.value(),
            "range_x_min": self.spin_range_x_min.value(),
            "range_x_max": self.spin_range_x_max.value(),
            "range_y_min": self.spin_range_y_min.value(),
            "range_y_max": self.spin_range_y_max.value(),
        }

        match is_new:
            case True:
                session_name = self.edit_session_name.text().strip()
                return {
                    "session_type": "NEW",
                    "parent_dir_path": folder_path,
                    "session_name": session_name,
                    "image_file_path": "",
                    "session_dir_path": os.path.join(folder_path, session_name),
                    "grid_config": grid_config,
                    "grid_csv_path": grid_csv,
                    "grid_origin_x": grid_config["origin_x"],
                    "grid_origin_y": grid_config["origin_y"],
                    "grid_range_x_min": grid_config["range_x_min"],
                    "grid_range_x_max": grid_config["range_x_max"],
                    "grid_range_y_min": grid_config["range_y_min"],
                    "grid_range_y_max": grid_config["range_y_max"],
                }
            case False:
                return {
                    "session_type": "EXISTING",
                    "parent_dir_path": "",
                    "session_name": os.path.basename(folder_path),
                    "image_file_path": "",
                    "session_dir_path": folder_path,
                    "grid_config": grid_config,
                    "grid_csv_path": grid_csv,
                    "grid_origin_x": grid_config["origin_x"],
                    "grid_origin_y": grid_config["origin_y"],
                    "grid_range_x_min": grid_config["range_x_min"],
                    "grid_range_x_max": grid_config["range_x_max"],
                    "grid_range_y_min": grid_config["range_y_min"],
                    "grid_range_y_max": grid_config["range_y_max"],
                }
