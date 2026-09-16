## タスクID
T-0036 tab2先頭への[新規][編集]モード切替トグル新設、点情報パネルのボタンエリアのモード連動切替

## 変更ファイル一覧
- `src/tab2_digitizing_mixin.py`
- `src/main_dock_constants.py`
- `src/main_dock.py`

## 変更概要

### ① tab2先頭のモード切替トグル
- `_create_tab2_ui()` の一番先頭（`self.group_point_info` 構築より前）に、`UIStyleHelper.build_segmented_toggle(["新規", "編集"], default_index=0)` を用いた `self.tab2_mode_container` / `self.tab2_mode_buttons` を新設し、`tab1_mode_container`（`tab1_georef_mixin.py`）と同じ `build_flex_row(main_label=None, ...)` パターンでlayout先頭に追加した。
- ラベル文字列は `main_dock_constants.py` の `UILabels.TAB2_MODE_NEW` / `UILabels.TAB2_MODE_EDIT` として定数化した（既存の `TAB1系`/`STATUS系` 命名パターンに合わせた）。
- ボタンの `toggled` シグナルに `_on_tab2_mode_changed(index)` を接続。状態は `self.tab2_current_mode`（`"new"` / `"edit"` の文字列）として新規管理し、既存の `selected_edit_point_id` とは独立させた。
- `_on_tab2_mode_changed` はモード状態の更新と、点情報パネル内の新規/編集用ボタンエリア（`widget_new_mode_actions` / `widget_edit_mode_actions`）の `setVisible()` 切り替えのみを行い、キャンバスクリック処理・既設点選択処理には一切触れていない（T-0037で別途対応予定）。

### ② 点情報パネルのボタンエリアのモード連動切替
- 既存の「既設点選択時のみ表示」行 `self.row_existing_actions`（従来: 点名変更+削除）から `btn_delete_point` を切り離し、`btn_rename_point` のみを残した（表示/非表示の条件・タイミングは従来通り `selected_edit_point_id` に連動、変更なし）。
- 新設した `self.widget_new_mode_actions` に、`UIStyleHelper.build_segmented_toggle(["自動連番", "解除"], default_index=0)` による `self.tab2_autonum_container` / `self.tab2_autonum_buttons` を配置。ラベルは `UILabels.AUTONUM_MODE_AUTO` / `UILabels.AUTONUM_MODE_RELEASE` として定数化。
- 新設した `self.widget_edit_mode_actions` に、既存の `btn_delete_point`（`_on_delete_selected_point` 接続はそのまま）を再配置した。
- `_on_tab2_mode_changed` により、新規モード時は `widget_new_mode_actions` を表示・`widget_edit_mode_actions` を非表示、編集モード時はその逆に切り替える。
- 自動連番/解除の状態は `self.tab2_autonum_mode`（`"auto"` / `"release"`）で新規管理し、`_on_tab2_autonum_mode_changed(index)` で更新。「自動連番」選択時は即座に `_get_next_point_number()`（`core_logic.get_next_point_number`、変更なし）を呼び出し `edit_point_name` に反映する。「解除」選択時は何もせず、現在の `edit_point_name` の値をそのまま残す。
- `_apply_next_point_number()`（S/P/C属性選択時に自動採番を `edit_point_name` へ適用する既存メソッド）を変更し、`self.tab2_autonum_mode == "release"` の場合は `setValue()` による上書きをスキップするようにした。`core_logic.get_next_point_number` 自体のロジックは変更していない。
- SP属性選択時の整合: 新設した `_update_autonum_toggle_for_sp(is_sp)` を `_update_point_name_widget_visibility()`（既存メソッド、SP選択時に `edit_point_name`/`edit_point_name_sp` の表示切替を行う箇所）から呼び出すよう拡張。SP選択時は自動連番/解除トグルの「解除」側（index 1）を自動的にチェックし、トグル自体を disable する。SP以外に戻った際は再度 enable する。既存のSP専用手入力ロジック（`edit_point_name_sp` の表示/非表示、バリデータ等）自体は変更していない。

### その他
- `src/main_dock.py` の `__init__` に `self.tab2_current_mode = "new"` / `self.tab2_autonum_mode = "auto"` の初期化を追加した（`selected_edit_point_id` と同様、UI構築前から `getattr()` で安全に参照できるようにするための保険的初期化。実体は `_create_tab2_ui()` 内のウィジェット構築時に再設定される）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
`python3 -m py_compile src/tab2_digitizing_mixin.py src/main_dock.py src/main_dock_constants.py src/tab1_georef_mixin.py src/style_helper.py` による構文確認のみ実施し、エラーなし。

## スコープ外変更の有無
なし。`src/tab2_digitizing_mixin.py` / `src/main_dock_constants.py` / `src/main_dock.py` のみを変更し、依頼スコープ（T-0036: モード切替トグル新設とボタンエリアのモード連動切替）の範囲内に留めた。T-0037（キャンバスクリック挙動変更）・T-0038（属性リアルタイム反映化）に該当する変更（既存の点名変更/属性変更ボタンの扱い、クリック時の選択/デジタイズ処理の分岐等）には一切手を加えていない。
