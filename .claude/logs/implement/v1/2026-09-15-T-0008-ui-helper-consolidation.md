## タスクID
T-0008

## 変更ファイル一覧
- `src/style_helper.py`
- `src/tab1_georef_mixin.py`
- `src/tab2_digitizing_mixin.py`
- `src/tab3_settings_mixin.py`

## 変更概要

### アプローチB: UIコンボ/リスト更新パターンの共通ヘルパー化
`style_helper.py` の `UIStyleHelper` に以下の静的メソッドを新設し、重複していた5箇所の処理を置き換えた。ファイル分割は行わず、既存の `style_helper.py` 内に追記する形とした。

1. **`repopulate_combo_box(combo, items, preserve_current=True)`**
   - QComboBoxを `blockSignals` で保護しつつ、渡された文字列リストで再構築する。`preserve_current=True` の場合は現在の選択テキストが新リストにも存在すれば復元し、なければ先頭を選択する。
   - `tab2_digitizing_mixin.py` の `_update_drawing_combo()` （`preserve_current=True`）と、`tab1_georef_mixin.py` の `_refresh_edit_layer_combo()` （`preserve_current=False`、元コードは選択復元を行っていなかったためこの引数で挙動を維持）の双方から呼び出す形に置換。

2. **`repopulate_checkable_list(list_widget, entries)`**
   - `(text, user_data, is_checked)` のタプルリストからQListWidgetのチェック可能アイテム群を`blockSignals`保護下で再構築する。
   - `_update_drawing_combo()` 内の `list_drawing_visibility` 再構築部分を置換。

3. **`get_checkable_item_state(item)`**
   - QListWidgetItemから `(Qt.UserRole のuser_data, is_checked)` を取り出す小さな共通処理。
   - `tab2_digitizing_mixin.py` の `_on_drawing_visibility_item_changed()` の冒頭2行を置換。
   - なお、QGIS固有のレイヤツリー操作（`QgsProject.instance().layerTreeRoot()` 以降）は `style_helper.py` の責務範囲外として`tab2_digitizing_mixin.py`側に残置（設計書上 `style_helper.py` はQtベースのUIコンポーネント管理に限定される旨の記述と整合させるため）。

4. **`rebuild_table_rows(table, row_count, row_builder)`**
   - `blockSignals`保護下でQTableWidgetの行を全クリアし、`row_builder(i)` が返す各列のQTableWidgetItemタプルで1行ずつ再構築する汎用ヘルパー。
   - `tab1_georef_mixin.py` の `_refresh_ref_points_table_and_markers()` を、行データ構築ロジック（`_build_row`ローカル関数、`preview_dialog.add_marker`呼び出しを含む）とテーブル再構築処理（ヘルパー呼び出し）に分離する形で置換。プレビューダイアログへのマーカー追加呼び出し順序は変更していない。

5. **`populate_combo_from_layer_field(combo, layer, field_name, leading_item=None, target_list=None)`**
   - ベクタレイヤの指定フィールドから重複なしソート済み値を抽出し、任意の先頭固定アイテム（「新規作成」等）と共にQComboBoxへ反映、かつ任意の外部リストへも同じ値を追記する。
   - `tab2_digitizing_mixin.py` の `_restore_feature_names()` を置換（`leading_item=UILabels.FEATURE_NEW_OPTION`, `target_list=self.feature_name_list`）。

いずれも「`blockSignals(True)` → 再構築 → `blockSignals(False)`」という既存の対称構造をヘルパー内に閉じ込めており、呼び出し元での対称性崩れのリスクを低減している。QGIS依存（`qgis.core`）は導入せず、`qgis.PyQt` の標準ウィジェットのみに依存する形とし、`style_helper.py` の既存の役割分担（設計書 1.4節記載の「Qtコードベースのフレックスレイアウトおよびコンポーネント管理」）を維持した。

### アプローチG: UIコンポーネント生成ヘルパーの拡張（Tab3のみ実施）
`style_helper.py` に以下2つの高レベルヘルパーを新設した。

- **`build_form_row(label_text, widget, spacing=4)`**: 既存の `build_child_container()` を土台に、ラベル文字列からQLabelを内部生成する形へ拡張した「ラベル+単一ウィジェット」の行構築ヘルパー。
- **`build_section_header(title)`**: 太字のセクション見出しQLabelを生成するヘルパー。

`tab3_settings_mixin.py` の `_create_tab3_ui()` 内でローカル関数として定義されていた `_make_section_header()` / `_make_sub_container()` を削除し、呼び出し箇所（計12箇所）をすべて `UIStyleHelper.build_section_header(...)` / `UIStyleHelper.build_form_row(...)` の直接呼び出しに置換した。スタイル文字列・スペーシング（4px）は元のローカル関数と完全に一致させており、見た目・レイアウト挙動に変更はない。

**Tab1/Tab2への展開について**: 依頼文の「範囲が広い場合はTab3のみ実施し、Tab1/Tab2は未着手と明記して報告してよい」という許可に基づき、今回はTab3のみ実施した。
- 理由: `tab1_georef_mixin.py`・`tab2_digitizing_mixin.py` は既にほぼ全てのラベル+ウィジェット行を `UIStyleHelper.build_flex_row(main_label, child_configs, main_ratio=MAIN_RATIO, row_height=UIConfig.ROW_HEIGHT)` という既存の共通ヘルパー経由で構築しており（Tab3の `_make_section_header`/`_make_sub_container` のようなヘルパー未経由のロジック重複ではない）、Tab3のような「ローカル関数によるヘルパー未利用の重複」とは性質が異なる。
- `build_form_row` をTab1/Tab2にも適用する場合、`build_flex_row` の `main_ratio`/`row_height` 引数を内包する形でシグネチャを再設計する必要があり、呼び出し箇所が約25箇所（Tab1: 約8箇所、Tab2: 約9箇所、うち条件付き表示制御用の `row_feature_selector` 等の特殊行を含む）に及ぶため、今回のスコープでは着手せず未実施とした。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。

代わりに以下の静的チェックを実施した。
- `python3 -m py_compile src/style_helper.py src/tab1_georef_mixin.py src/tab2_digitizing_mixin.py src/tab3_settings_mixin.py` → 構文エラーなし。
- `python3 -m pyflakes` による未使用importの確認 → 今回の変更差分に起因する新規の未使用import・未定義名は検出されなかった（`src/style_helper.py` の `QLineEdit` 未使用インポート、`src/tab1_georef_mixin.py:289` のf-stringプレースホルダなし警告は、いずれも本タスクの変更前から存在していた既存の指摘であり、`git stash` による差分比較で本タスク由来でないことを確認した）。

## スコープ外変更の有無
なし。`src/` 配下のうち、依頼スコープで明示された `style_helper.py` / `tab1_georef_mixin.py` / `tab2_digitizing_mixin.py` / `tab3_settings_mixin.py` の4ファイルのみを変更した。ファイル分割は行っていない。`.claude/state/tasks.md` の更新は統括の役割と判断し、本タスクでは変更していない。
