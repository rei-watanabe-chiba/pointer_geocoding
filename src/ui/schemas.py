"""
/***************************************************************************
 PointerGeocoding Plugin - CoreUI Screen Schemas
 ***************************************************************************/

T-0045 (追加スコープ): single consolidated file for all CoreUI declarative
panel/field schemas, one section per screen (``# --- TAB1 ---`` etc.), so
that adding TAB2/TAB3/START_DIALOG schemas in T-0046/T-0047 does not
re-fragment the schema layer back into one file per screen (see
.claude/state/v2-coreui-plan.md's "スキーマファイル統合" note). Originally
``tab1_image_schema.py``; moved here unchanged aside from this consolidation.

This file only declares widget kinds/labels/hook names; all business logic
(event handler bodies) stays in each screen's own module (e.g.
tab1_image.py's Tab1GeorefMixin), bound via BuiltPanel.bind(hook_name,
callback) after building.
"""
from .constants import UILabels, UIPlaceholders

from .core import ButtonDef, FieldSpec, InfoLine, PanelSpec, WidgetType

# --- TAB1 --------------------------------------------------------------
# Tab 1 (Georeferencing): consumed by CoreUIBuilder.build() in
# tab1_image.py's Tab1GeorefMixin._create_tab1_ui().

# --- Information panel (bottom of the 図面管理 side panel) -----------------
TAB1_INFO_PANEL_SPEC = PanelSpec(
    panel_id="tab1_info_panel",
    fields=[
        FieldSpec(
            field_id="tab1_info",
            widget_type=WidgetType.INFO_PANEL,
            info_lines=[
                InfoLine(
                    kind="bold",
                    field_id="line1",
                    text=UILabels.TAB1_INFO_IMAGE_REF.format(name=UILabels.UNLOADED, count=0),
                ),
                InfoLine(kind="separator"),
                InfoLine(kind="plain", field_id="line2", text=UILabels.TRANSFORM_INIT_STATUS),
                InfoLine(
                    kind="wrap",
                    field_id="line3_6",
                    text=UILabels.TAB1_INFO_RESIDUAL_INIT,
                    min_height=14 * 4,
                ),
            ],
        ),
    ],
)

# --- 新規追加/編集削除 segmented mode toggle ---------------------------------
TAB1_MODE_TOGGLE_SPEC = PanelSpec(
    panel_id="tab1_mode_toggle",
    fields=[
        FieldSpec(
            field_id="tab1_mode",
            widget_type=WidgetType.SEGMENTED_TOGGLE,
            options=["新規追加", "編集削除"],
            default_index=0,
            main_ratio=(0, 10),
            on_change="mode_changed",
        ),
    ],
)

# --- Image add/edit form + reference-points table ---------------------------
TAB1_IMAGE_SECTION_SPEC = PanelSpec(
    panel_id="tab1_image_section",
    spacing=6,
    fields=[
        # 3a. Image File (New Mode)
        FieldSpec(
            field_id="image_path",
            widget_type=WidgetType.LINEEDIT_ROW,
            label=UILabels.IMAGE_FILE,
            placeholder=UIPlaceholders.IMAGE_PATH,
            trailing_button=ButtonDef(
                field_id="browse_image", text=UILabels.BTN_BROWSE, on_click="browse_image"
            ),
        ),
        # 3b. Edit Layer Selector (Edit Mode; hidden until 編集削除 mode is chosen)
        FieldSpec(
            field_id="edit_layer",
            widget_type=WidgetType.COMBOBOX_ROW,
            label="編集レイヤ:",
            on_change="edit_layer_changed",
            visible=False,
        ),
        # 3c. Layer Name (Both Modes)
        FieldSpec(
            field_id="image_name",
            widget_type=WidgetType.LINEEDIT_ROW,
            label=UILabels.LAYER_NAME,
            placeholder=UIPlaceholders.IMAGE_NAME,
        ),
        # 3d. Actions: Rename & Delete (Edit/Delete mode only)
        FieldSpec(
            field_id="rename_delete",
            widget_type=WidgetType.BUTTON_ROW,
            visible=False,
            buttons=[
                ButtonDef(field_id="rename_layer", text="レイヤ名変更", on_click="rename_layer"),
                ButtonDef(field_id="delete_layer", text="削除", on_click="delete_layer"),
            ],
        ),
        # Setup Reference Points (both modes)
        FieldSpec(
            field_id="confirm_image",
            widget_type=WidgetType.BUTTON,
            label="基準点設置",
            style_variant="primary",
            on_click="confirm_image",
        ),
        # 4. Reference Points Table
        FieldSpec(
            field_id="ref_points_table",
            widget_type=WidgetType.TABLE,
            table_headers=UILabels.REF_TABLE_HEADERS,
            table_col_resize_modes=["contents", "contents", "stretch", "stretch"],
            table_min_height=130,
            on_change="ref_table_cell_changed",
        ),
    ],
)

# --- 5. Coordinate Transformation & Placement -------------------------------
TAB1_TRANSFORM_SECTION_SPEC = PanelSpec(
    panel_id="tab1_transform_section",
    spacing=6,
    fields=[
        FieldSpec(
            field_id="transform_actions",
            widget_type=WidgetType.BUTTON_ROW,
            buttons=[
                ButtonDef(
                    field_id="transform",
                    text=UILabels.BTN_TRANSFORM,
                    style_variant="primary",
                    on_click="transform_clicked",
                    enabled=False,
                ),
                ButtonDef(
                    field_id="export_layer",
                    text=UILabels.BTN_EXPORT_LAYER,
                    style_variant="accent",
                    on_click="export_layer_clicked",
                    enabled=False,
                ),
            ],
        ),
    ],
)

# --- START DIALOG --------------------------------------------------------
# Session start dialog (start_dialog.py's StartDialog._init_ui()). T-0046:
# covers the "セッション設定" group (session type radio, folder path with a
# trailing browse button, session name) and the leading part of the
# "グリッド設定" group (grid CSV path with a trailing browse button, grid
# mode radio). The origin/range/preview coordinate panel and its dynamic
# warning status panel (ExcelColumnSpinBox, nested sub-labeled spinbox
# pairs, and a confirm button embedded in a dynamically-restyled status
# panel) remain bespoke code in start_dialog.py: none of those map onto an
# existing CoreUI WidgetType, and inventing new kinds solely for this one
# screen's stateful widgets would be speculative abstraction, per the CoreUI
# plan's "画面固有の例外は素のPyQtコードとして残してよい" escape hatch
# (see .claude/state/v2-coreui-plan.md).

START_DIALOG_SESSION_SPEC = PanelSpec(
    panel_id="start_dialog_session",
    spacing=10,
    fields=[
        FieldSpec(
            field_id="session_type",
            widget_type=WidgetType.RADIO_ROW,
            label="セッション種別:",
            options=["新規セッション", "既存セッション"],
            default_index=0,
            on_change="session_type_changed",
        ),
        # Label/placeholder are re-set at runtime by
        # StartDialog._on_session_type_changed() (親ディレクトリ/セッション
        # フォルダ swap); the values below are only the initial "new session"
        # state.
        FieldSpec(
            field_id="folder",
            widget_type=WidgetType.LINEEDIT_ROW,
            label="親ディレクトリ:",
            placeholder="セッションフォルダを新規作成する親ディレクトリを選択してください",
            trailing_button=ButtonDef(
                field_id="browse_folder", text=UILabels.BTN_BROWSE, on_click="browse_folder"
            ),
        ),
        FieldSpec(
            field_id="session_name",
            widget_type=WidgetType.LINEEDIT_ROW,
            label="セッション名:",
            placeholder="例: session_01 (半角英数推奨)",
        ),
    ],
)

START_DIALOG_GRID_CSV_SPEC = PanelSpec(
    panel_id="start_dialog_grid_csv",
    spacing=10,
    fields=[
        FieldSpec(
            field_id="grid_csv",
            widget_type=WidgetType.LINEEDIT_ROW,
            label="グリッドCSV選択:",
            placeholder=(
                "既存のPointGeo_grid.csvを選択"
                "（下のモードにより新規作成の初期値、または利用CSVとして扱われます）"
            ),
            trailing_button=ButtonDef(
                field_id="browse_grid_csv", text=UILabels.BTN_BROWSE, on_click="browse_grid_csv"
            ),
            on_change="grid_csv_changed",
        ),
        FieldSpec(
            field_id="grid_mode",
            widget_type=WidgetType.RADIO_ROW,
            label="グリッドモード:",
            options=["新規作成・更新", "CSVファイル利用"],
            default_index=0,
            on_change="grid_mode_changed",
        ),
    ],
)
