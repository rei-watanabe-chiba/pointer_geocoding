## タスクID
T-0035 余白定数の全面リセット・簡素化

## 変更ファイル一覧
- src/main_dock_constants.py
- src/main_dock.py
- src/tab2_digitizing_mixin.py
- src/tab1_georef_mixin.py
- src/tab3_settings_mixin.py
- src/start_dialog.py
- src/main_dock_dialogs.py

## 変更概要

### src/main_dock_constants.py（UIConfig定数の追加・削除）
T-0034で追加された以下の細分化定数を削除した。
- `SECTION_GAP`, `PANEL_GROUP_SPACING`, `PANEL_INNER_SPACING`,
  `SEPARATOR_MARGIN_TOP`, `SEPARATOR_MARGIN_BOTTOM`,
  `PANEL_CONTAINER_MARGIN_TOP`, `PANEL_CONTAINER_MARGIN_BOTTOM`,
  `DOCK_OUTER_MARGIN`

代わりに以下3つの単一定数を新設した（いずれも値は8）。
- `COMMON_MARGIN_LR = 8`: start_dialog.py・tab1_georef_mixin.py・
  tab3_settings_mixin.py・tab2_digitizing_mixin.py の `_create_tab4_ui()` の
  各最上位コンテナの左右余白に使用。
- `DIALOG_MARGIN = 8`: 各「ダイアログ内コンテンツ」の最上位レイアウトの
  上下margin・setSpacing()（縦方向）に使用（start_dialog.py の
  main_layout、main_dock_dialogs.py の4クラス、tab1/tab3/tab4の各最上位
  コンテナ）。
- `PANEL_MARGIN = 8`: main_dock.py の root_layout（上下左右margin・
  setSpacing()を全てこれに統一。`DOCK_OUTER_MARGIN`を廃止し一本化）、
  および tab2_digitizing_mixin.py の tab2本体最上位コンテナ・info_layout・
  attr_layout・focus_layout・drawing_list_layout の setSpacing() に使用。

維持した既存定数: `PANEL_CONTAINER_MARGIN_LEFT`（4）、
`PANEL_CONTAINER_MARGIN_RIGHT`（16、値は変更なし）、
`TOP_ROW_BUTTON_SPACING`（6、値は変更なし）、`DOCK_WIDTH`、
`DRAWING_LIST_HEIGHT` 等。

### src/main_dock.py
`_init_ui()` の `root_layout.setContentsMargins()` を4方向とも
`UIConfig.PANEL_MARGIN` に統一し、`root_layout.setSpacing()` も
`UIConfig.PANEL_MARGIN` に変更した（従来の `DOCK_OUTER_MARGIN`/
`SECTION_GAP` を置換）。top_row/tab2_container間の区切り線（
`UIStyleHelper.build_separator()`）は元々 `addSpacing()` を使わない単純な
`addWidget()` 実装であることを確認し、変更していない。

### src/tab2_digitizing_mixin.py
- T-0034で追加された `Tab2DigitizingMixin._build_padded_separator()`
  静的メソッドを削除した。
- `_create_tab2_ui()`:
  - tab2本体の最上位コンテナ `layout` の `setContentsMargins()` の
    上下を `UIConfig.PANEL_MARGIN` に変更（左右は
    `PANEL_CONTAINER_MARGIN_LEFT`/`PANEL_CONTAINER_MARGIN_RIGHT` のまま
    維持）、`setSpacing()` を `UIConfig.PANEL_MARGIN` に変更。
  - `info_layout`/`attr_layout`/`focus_layout` の `setSpacing()` を
    いずれも `UIConfig.PANEL_MARGIN` に変更。
  - `drawing_list_layout.setSpacing(4)` を `UIConfig.PANEL_MARGIN` に変更。
  - 属性パネル前・フォーカスモードパネル前の区切り線を、廃止した
    `_build_padded_separator()` 呼び出しから
    `UIStyleHelper.build_separator(container)` の直接 `addWidget()` に
    戻した。
- `_create_tab4_ui()`:
  - `csv_layout` に `setContentsMargins(COMMON_MARGIN_LR, DIALOG_MARGIN,
    COMMON_MARGIN_LR, DIALOG_MARGIN)` を新規に追加（従来
    `setContentsMargins()` 呼び出し自体が存在しなかった）。
  - `csv_layout.setSpacing(6)` を `UIConfig.DIALOG_MARGIN` に変更。

### src/tab1_georef_mixin.py
`_create_tab1_ui()` の最上位コンテナ `layout` の
`setContentsMargins(4, 4, 16, 4)` を
`(COMMON_MARGIN_LR, DIALOG_MARGIN, COMMON_MARGIN_LR, DIALOG_MARGIN)` に、
`setSpacing(12)` を `UIConfig.DIALOG_MARGIN` に変更した（左右非対称の
4/16マージンは左右均一の COMMON_MARGIN_LR=8 に統一される）。

### src/tab3_settings_mixin.py
`_create_tab3_ui()` の最上位コンテナ `layout` の
`setContentsMargins(8, 8, 8, 8)` を
`(COMMON_MARGIN_LR, DIALOG_MARGIN, COMMON_MARGIN_LR, DIALOG_MARGIN)` に、
`setSpacing(12)` を `UIConfig.DIALOG_MARGIN` に変更した。

### src/start_dialog.py
`.main_dock_constants` から `UIConfig` を新規importし、`_init_ui()` の
`main_layout` の `setContentsMargins(12, 12, 12, 12)` を
`(COMMON_MARGIN_LR, DIALOG_MARGIN, COMMON_MARGIN_LR, DIALOG_MARGIN)` に、
`setSpacing(12)` を `UIConfig.DIALOG_MARGIN` に変更した（依頼範囲内の
main_layoutのみ。config_layout/grid_group_layout/panel_settings_layout等の
ネストしたサブセクションは変更していない）。

### src/main_dock_dialogs.py
`.main_dock_constants` のimportに `UIConfig` を追加し、以下4クラスの
最上位レイアウトのmargin/spacingを `COMMON_MARGIN_LR`/`DIALOG_MARGIN` に
変更した。
- `ModelessSectionDialog.__init__()`: `layout.setContentsMargins(6,6,6,6)`
  → `(COMMON_MARGIN_LR, DIALOG_MARGIN, COMMON_MARGIN_LR, DIALOG_MARGIN)`
- `ImageDialog.__init__()`: `layout.setContentsMargins(6,6,6,6)` /
  `setSpacing(6)` → 同上margin + `DIALOG_MARGIN`
- `GridInputDialog._init_ui()`: `layout.setContentsMargins(12,12,12,12)` /
  `setSpacing(10)` → 同上margin + `DIALOG_MARGIN`
- `FeatureCreateDialog.__init__()`: `layout.setContentsMargins(12,12,12,12)`
  / `setSpacing(10)` → 同上margin + `DIALOG_MARGIN`

いずれも各ダイアログの最上位レイアウトのみを対象とし、tier1_vlayout/
header_layout/inputs_layout等のネストしたサブセクションは変更していない。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
代わりに対象ファイル全てに対し `python3 -m py_compile` を実行し、構文エラー
がないことを確認した（実行結果: 全ファイルOK）。

## スコープ外変更の有無
なし。対象ファイルは依頼された7ファイル（
src/main_dock_constants.py, src/main_dock.py,
src/tab2_digitizing_mixin.py, src/tab1_georef_mixin.py,
src/tab3_settings_mixin.py, src/start_dialog.py,
src/main_dock_dialogs.py）のみであり、`git diff --stat` でも同7ファイルの
みが変更されていることを確認した。各ファイル内でも、依頼範囲外とされた
ネストしたサブセクション（start_dialog.pyのconfig_layout等、tab1の
img_layout/trans_layout等、GridInputDialogのtier1_vlayout等）や
style_helper.py内の固定値、addStretch()呼び出しには手を入れていない。
