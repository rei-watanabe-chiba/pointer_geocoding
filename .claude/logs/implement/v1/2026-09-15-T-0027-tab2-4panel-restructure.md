## タスクID
T-0027

## 変更ファイル一覧
- `src/tab2_digitizing_mixin.py`
- `src/main_dock_dialogs.py`
- `src/main_dock_constants.py`
- `src/main_dock.py`
- `src/core_logic.py`
- `docs/integrated_master_design.md`

## 変更概要

### 1. UIレイアウトの全面再構成（`tab2_digitizing_mixin.py` `_create_tab2_ui`）
旧: `panel_edit_status`（ステータス表示＋連番再開／削除／番号修正を確定ボタン）+ `QgsCollapsibleGroupBox`
3枠（フォーカスモード／入力カテゴリ／個別入力）のアコーディオン構成を全廃し、常時展開の
`QGroupBox`（非collapsible。`style_helper.py`のQSSが`QGroupBox, QgsCollapsibleGroupBox`を
同一スタイルで定義済みのため見た目は維持）4パネルへ再構成した。

- **① 点情報パネル (`group_point_info`)**: グリッド/遺構名・属性・番号枝番
  （既存の`edit_point_name`/`edit_point_name_sp`/`edit_branch_no`を流用、既存点選択時は
  `setEnabled(False)`）・XY座標（既存点選択時のみ、`core_logic.to_survey_coords`で測量座標表示）
  を表示する`_refresh_point_info_labels()`を新設。既存点選択時のみ「削除」（確認ダイアログ
  なしで即削除）「点名変更」ボタン行（`row_existing_actions`）を表示。
- **② 属性パネル (`group_attribute_panel`)**: 対象図面・出土形態・遺構名セレクタ+「作成」
  ボタン（`main_dock_dialogs.FeatureCreateDialog`を開く）・カラーピッカー（遺構名が具体的に
  選択されている時のみ表示）・属性記号+確定ボタン。旧`edit_new_feature`（常時表示の新規遺構名
  入力欄）・`btn_apply_color`（グループ一括適用ボタン）は廃止。
- **③ フォーカスモードパネル (`group_focus`)**: ON/OFFトグルと透明度スライダーのみ。
- **④ 図面選択リスト (`group_drawing_list`)**: 図面表示マルチセレクタ`QListWidget`を
  フォーカスモードパネルから分離。`UIConfig.DRAWING_LIST_HEIGHT`(180px、約6行分)で高さ固定。

### 2. 既設点選択フローの変更
- 「削除」ボタン: `QMessageBox.question`による確認ダイアログを廃止し、`_on_delete_selected_point()`
  で即座に`deleteFeature()`する。
- 「番号修正を確定」ボタン(`btn_correct_number`)を廃止し、「点名変更」ボタン
  (`_on_rename_point_clicked`)がモーダル`PointRenameDialog`（`main_dock_dialogs.py`新設）を開く形に
  変更。自動採番は行わず、OK押下時に`core_logic.check_duplicate_and_build_message()`
  （後述の共通化関数）で重複チェックのみ行い、重複時はダイアログ内に赤字インラインエラーを
  表示して閉じない。問題なければダイアログ自身がフィーチャ属性を更新して閉じる。
- 「連番再開」ボタン(`btn_reset_selection`)を廃止し、`_on_canvas_clicked()`冒頭に
  `self.selected_edit_point_id is not None`の分岐を追加。既設点選択中に空白キャンバスを
  クリックすると新規フィーチャを作成せず`_reset_point_selection()`のみ呼ぶ（map_tool.py側は
  無変更、既存の「フィーチャ非ヒット時のみcanvas_clickedを発火」動作をそのまま利用）。
- `_CATEGORY_LOCK_WIDGET_NAMES`（T-0023）に`edit_point_name`/`edit_point_name_sp`/
  `edit_branch_no`を追加し、既設点選択時は点名/枝番インプットも`setEnabled(False)`にする。

### 3. 重複チェックロジックの共通化（`core_logic.py`）
新規打刻時(`_on_canvas_clicked`)と点名変更ダイアログ(`PointRenameDialog`)の双方で使われていた
「重複判定＋identメッセージ組み立て」の重複コードを、`build_point_ident()`
（ident文字列組み立て）と`check_duplicate_and_build_message()`（`check_point_duplicate()`＋
`build_point_ident()`の合成）としてcore_logic.pyへ切り出し、両方から呼び出す形に統一した。

### 4. 遺構名作成・カラー適用フローの変更
- 旧`edit_new_feature`（常時表示の新規遺構名QLineEdit）を廃止し、「作成」ボタン→
  `FeatureCreateDialog`（`main_dock_dialogs.py`新設、テキスト入力欄のみ＋OK/キャンセル、
  `UIStyleHelper.build_centered_button_row()`使用）に統合。作成後は`register_new_feature_name()`
  でセレクタへ即時反映・選択し、続けて`_pick_color()`（カラーピッカー）を自動的に開く。
- カラー適用: 旧`btn_apply_color`（グループ一括適用ボタン）を廃止し、`_pick_color()`内で
  `QColorDialog.getColor()`がOKで返った瞬間に既存の`_apply_feature_color_group()`（対象フィーチャの
  色を直接更新するロジック、`tab2_digitizing_mixin.py`内。当初の依頼文言は
  「symbology_mixin.py内の色更新関数」としていたが、実際の実装箇所はtab2_digitizing_mixin.py
  であったため、実装はその関数をそのまま流用しトリガーのみ変更した）を呼ぶ形に変更。

### 5. その他
- `get_digitizing_input_state()`: クリック時の新規遺構名自動登録ロジック（Pattern B）を削除。
  遺構名セレクタが「新規作成」プレースホルダのままの場合は打刻不可（`ERR_NEW_FEATURE_REQUIRED`）
  とし、事前に「作成」ダイアログで作成する運用に一本化。
- `get_focus_category_filter()`/`main_dock.py`の`update_symbology_opacity()`から
  `edit_new_feature`参照を除去（プレースホルダ選択時は空文字列扱い）。
- 未使用となった定数（`GROUP_CATEGORY`/`GROUP_INDIVIDUAL`/`EDIT_STATUS_INIT`/
  `STATUS_DIGITIZE_SUCCESS`/`STATUS_EXISTING_POINT`/`BTN_RESET_SELECTION`/`BTN_CORRECT_NUMBER`/
  `MSG_DELETE_CONFIRM`/`MSG_CORRECT_NUMBER_SUCCESS*`/`BTN_APPLY_COLOR`）を`main_dock_constants.py`
  から削除し、新規定数（`GROUP_POINT_INFO`/`GROUP_ATTRIBUTE_PANEL`/`GROUP_DRAWING_LIST`/
  `LBL_INFO_*`/`BTN_CREATE_FEATURE`/`BTN_RENAME_POINT`/`FEATURE_CREATE_DIALOG_TITLE`/
  `RENAME_POINT_DIALOG_TITLE`/`MSG_RENAME_POINT_SUCCESS*`/`UIConfig.DRAWING_LIST_HEIGHT`）を追加。
- `docs/integrated_master_design.md` 2.3節（メインエリア）を新レイアウト・新フローに追随更新。

### スコープ判断メモ（設計書との差異）
- 依頼文の②属性パネル一覧に「対象図面(`combo_drawing_name`)」の明記が無かったが、
  `drawing_name`属性は重複チェック・CSV出力・フォーカスフィルタに必須のため削除せず、
  ②属性パネルの先頭行として維持した（ログに明記の上、implementer判断で継続）。
- カラーピッカーの表示条件は依頼文「遺構名選択時のみ表示」を、「具体的な遺構名が選択されて
  いる時のみ（＝『新規作成』プレースホルダの間は非表示）」と解釈し、`_update_feature_related_visibility()`
  で判定するよう実装した（旧実装は出土形態が「遺構」であれば常に表示していた）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンド未設定のため、`python3 -m py_compile`による
構文チェックのみ実施。全対象ファイルでエラーなし）。

## スコープ外変更の有無
なし。変更は`src/tab2_digitizing_mixin.py`・`src/main_dock_dialogs.py`・
`src/main_dock_constants.py`・`src/main_dock.py`・`src/core_logic.py`と、関連design doc
（`docs/integrated_master_design.md`）の該当節のみに限定した。`map_tool.py`・
`symbology_mixin.py`・`layer_manager.py`等の他モジュールへの変更は行っていない
（`map_tool.py`の`_handle_digitize_click`は無変更のまま利用: 既存点非ヒット時に
`canvas_clicked`を発火する既存動作をそのまま使い、選択解除判定は呼び出し側
`_on_canvas_clicked`のみで完結させた）。
