## タスクID
T-0023

## 変更ファイル一覧
- `src/core_logic.py`
- `src/tab2_digitizing_mixin.py`
- `src/map_tool.py`
- `src/main_dock_constants.py`
- `docs/integrated_master_design.md`
- `.claude/state/tasks.md`（状態更新）

## 変更概要

### 1. バグ修正: SP属性から他(S/P/C)へ戻した際の自動採番が機能しない
- `core_logic.get_next_point_number()`のフィーチャ絞り込みループに、`attribute_type == AttributeType.SP.value`のフィーチャを除外する条件を追加。
- SP属性の点は自由入力(手入力)専用であり、S/P/C側の「直前打刻追従型」採番探索(max point_id)の対象から常に除外されるようにした。
- 関数シグネチャは変更せず(引数追加不要)、`safe_get_str(feat, "attribute_type")`による絞り込みのみで対応。呼び出し元`_get_next_point_number()`(tab2_digitizing_mixin.py)の変更は不要だった。

### 2. 機能追加①: 既存点の番号修正機能
- `tab2_digitizing_mixin.py`にボタン`btn_correct_number`(「番号修正を確定」)を`btn_reset_selection`/`btn_delete_point`と並べて追加。既存点未選択時は無効。
- `_on_existing_point_selected()`にて、既存点選択時に出土形態・遺構名・対象図面・属性・カラー関連ウィジェット(`combo_drawing_name`/`combo_excavation_type`/`combo_feature_name`/`edit_new_feature`/`btn_color_picker`/`btn_apply_color`/`combo_attribute`)を`_set_category_widgets_locked(True)`で無効化し、点番号(本体番号・枝番)のみ編集可能にした。選択時のデータは`self._selected_point_data`として保持。
- 新規ハンドラ`_on_correct_point_number()`を追加。新規打刻時と同じバリデーション(点名必須)・重複チェックを行い(`core_logic.check_point_duplicate`に新設した`exclude_feature_id`引数で自分自身を除外)、対象フィーチャの`point_name`/`branch_no`のみを`startEditing()`→`changeAttributeValue()`→`commitChanges()`→`triggerRepaint()`で更新する。
- `_reset_point_selection()`で`_set_category_widgets_locked(False)`により再有効化、`btn_correct_number`を無効化、`_selected_point_data`をクリアする処理を追加。
- `core_logic.check_point_duplicate()`に`exclude_feature_id: Optional[int] = None`引数を追加(デフォルトNoneで既存呼び出しは非破壊)。
- `main_dock_constants.py`に`UILabels.BTN_CORRECT_NUMBER`、`UIMessages.MSG_CORRECT_NUMBER_SUCCESS_TITLE`/`MSG_CORRECT_NUMBER_SUCCESS`を追加。

### 3. 機能追加②: 既存点選択時の赤枠常時表示
- `map_tool.py`の`CanvasDigitizingTool`に、`hover_marker`と同スタイル(赤色ボックス)の`self.selected_marker`(QgsVertexMarker)を新設。
- `_handle_digitize_click()`で既存点にヒットした際、フィーチャの`canvas_x`/`canvas_y`座標に`show_selected_marker()`でマーカーを表示。別の点を選択すると自動的に位置が更新される。地図上の空白をクリック(=`canvas_clicked`発火)した際は`clear_selected_marker()`で非表示化。
- `deactivate()`/`clean_up()`にも`selected_marker`の非表示・破棄処理を追加(`hover_marker`との対称性を維持)。
- ホバー用の赤枠と選択用の赤枠は同一スタイルで実装(ユーザー要件により区別必須ではないため)。`tab2_digitizing_mixin.py`の`_reset_point_selection()`(「連番再開」ボタン押下含む)から`map_tool.clear_selected_marker()`を呼び、削除ボタンも内部で`_reset_point_selection()`を呼ぶため同様に解除される。

## 自動テスト実行結果
自動テストなし(プロジェクトに自動テストコマンド未設定)。`python -m py_compile`によるシンタックスチェックのみ実施し、対象ファイル(`core_logic.py`/`tab2_digitizing_mixin.py`/`map_tool.py`/`main_dock_constants.py`)はエラーなくコンパイル可能であることを確認した。

## スコープ外変更の有無
なし。依頼スコープ(`src/core_logic.py`, `src/tab2_digitizing_mixin.py`, `src/map_tool.py`, `src/main_dock_constants.py`, `docs/integrated_master_design.md`)の範囲内で実装した。`main_dock.py`の`selected_edit_point_id`初期化箇所への追記は行わず、`getattr(self, "_selected_point_data", None)`によるフォールバックで対応しスコープ外ファイルへの変更を回避した。
