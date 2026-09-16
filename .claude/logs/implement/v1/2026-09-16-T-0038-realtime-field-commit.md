## タスクID
T-0038 編集モードでの点名/枝番/属性系のリアルタイム反映化（3段階UX改善の3/3、最終段）

## 変更ファイル一覧
- `src/tab2_digitizing_mixin.py`
- `src/main_dock_constants.py`

## 変更概要

### 削除したボタン/ハンドラ
- `btn_rename_point`（「点名変更」ボタン）と `_on_rename_point_clicked()`
- `btn_update_attribute`（「属性変更」ボタン）と `_on_update_attribute_clicked()`
- 上記ボタンのみを保持していた `row_existing_actions`（QWidget/QHBoxLayout）も、空になったため削除
- `main_dock_constants.py` から、上記ボタン専用のラベル定数（`UILabels.BTN_RENAME_POINT`,
  `UILabels.BTN_UPDATE_ATTRIBUTE`）と、対応するメッセージ定数（`UIMessages.MSG_RENAME_POINT_SUCCESS_TITLE`,
  `UIMessages.MSG_RENAME_POINT_SUCCESS`, `UIMessages.MSG_UPDATE_ATTRIBUTE_TITLE`,
  `UIMessages.MSG_UPDATE_ATTRIBUTE_SUCCESS`）を削除（他箇所からの参照なしをgrepで確認済み）
- `_on_existing_point_selected`/`_reset_point_selection` 内にあった
  `row_existing_actions.show()/hide()`・`btn_update_attribute.show()/hide()` 呼び出しも削除
  （`widget_edit_mode_actions`（削除ボタンのみ）の表示/非表示は、既存どおり
  `_on_tab2_mode_changed`（新規/編集モードトグル、T-0036）が一元管理しているため、
  選択の有無で重複制御しないよう整理）

### 新設した共通コミットヘルパー
- `_commit_fields_to_feature(updates: Dict[str, Any]) -> bool`
  - 旧`_on_rename_point_clicked`/`_on_update_attribute_clicked`内にあった
    `startEditing()`→`changeAttributeValue()`ループ→`commitChanges()`→`triggerRepaint()`の
    実コミット処理と、`self._selected_point_data`の更新、フォーカスモード有効時の
    `update_symbology_opacity()`呼び出しを1箇所に集約した共通ヘルパー
  - `self.selected_edit_point_id is None`または`self.point_layer`未設定の場合は何もせず`False`を返す
- `_commit_point_identity_if_editing(*args)`
  - `edit_point_name`（QSpinBox）/`edit_point_name_sp`（SP用自由入力QLineEdit）/`edit_branch_no`
    （QgsFilterLineEdit）の`editingFinished`シグナルに接続
  - `self._suppress_realtime_commit`（下記）、`selected_edit_point_id is None`（新規モード）、
    `self._point_info_has_error`（`_update_point_info_status()`が都度更新する既存のリアルタイム
    バリデーション結果。遺構名未指定/点名重複を含む）のいずれかに該当する場合はコミットしない
  - 上記いずれにも該当しない場合のみ`_commit_fields_to_feature({"point_name": ..., "branch_no": ...})`
    を呼び、その後`_refresh_point_info_labels`/`_update_point_info_status`でパネル表示を更新
- `_commit_attribute_fields_if_editing(*args)`
  - `combo_attribute`の`currentIndexChanged`、および`_on_excavation_type_changed`
    （`combo_excavation_type`用ラッパー）・`_on_feature_combo_changed`（`combo_feature_name`用ラッパー）
    の末尾から呼び出される
  - ガード条件は`_commit_point_identity_if_editing`と同様（`_suppress_realtime_commit`/新規モード/
    `_point_info_has_error`）
  - `excavation_type`/`feature_name`/`color_code`/`attribute_type`をまとめて
    `_commit_fields_to_feature()`に渡す（旧`_on_update_attribute_clicked`と同一のフィールド構成）

### リアルタイムコミット方式への変更点
- `edit_point_name.editingFinished` / `edit_point_name_sp.editingFinished` /
  `edit_branch_no.editingFinished` を新たに`_commit_point_identity_if_editing`へ接続
  （既存の`valueChanged`/`textChanged`→`_on_point_identity_changed`/`_on_branch_text_changed`
  によるリアルタイムパネル更新・赤枠表示ロジックはそのまま維持し、変更していない）
- `combo_attribute.currentIndexChanged`に`_commit_attribute_fields_if_editing`を追加接続
  （既存の`_on_category_changed`接続はそのまま維持）
- `_on_excavation_type_changed`/`_on_feature_combo_changed`の末尾に
  `self._commit_attribute_fields_if_editing()`呼び出しを追加

### ロード中の誤コミット防止
- `self._suppress_realtime_commit`フラグを新設（`_create_tab2_ui`冒頭で`False`初期化）
- `_on_existing_point_selected`の冒頭で`True`にセットし、既設フィーチャの各値を
  `combo_excavation_type.setCurrentText()`等でフォームへプログラム的に反映する間
  （これらの呼び出しは`currentIndexChanged`/`currentTextChanged`を発火させるため）は
  リアルタイムコミットハンドラが起動してもすぐ抜けるようにし、メソッド末尾で`False`に戻す
- 各コミットハンドラの先頭で`getattr(self, "_suppress_realtime_commit", False)`をチェック

### 対象外（変更していない箇所）
- カラーピッカー（OK押下で即時反映、既存のまま）
- フォーカスモード透明度ロジック（`_commit_fields_to_feature`内で既存の
  `is_focus_mode_active()`/`update_symbology_opacity()`呼び出し経路をそのまま踏襲）
- `_CATEGORY_LOCK_WIDGET_NAMES`（`combo_drawing_name`のみロック、変更なし）
- 新規モードの自動採番・SP属性の手入力ロジック本体（T-0036実装分、変更なし）
- キャンバスクリック処理（T-0037実装分、変更なし）
- `core_logic.py`のdocstring内にある`_on_rename_point_clicked`という旧メソッド名への言及
  （コメントのみで機能に影響なし。対象外ファイルのためそのままとした）

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
`python3 -m py_compile src/tab2_digitizing_mixin.py src/main_dock_constants.py src/main_dock.py src/core_logic.py`
による構文確認のみ実施し、エラーなく完了した。

## スコープ外変更の有無
なし。`src/tab2_digitizing_mixin.py`と`src/main_dock_constants.py`のみを変更し、
依頼スコープ（点名/枝番/属性系のリアルタイム反映化、確定ボタン廃止）に沿った変更のみ行った。
