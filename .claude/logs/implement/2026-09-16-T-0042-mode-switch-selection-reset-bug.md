## タスクID
T-0042

## 変更ファイル一覧
- src/tab2_digitizing_mixin.py

## 変更概要
`_on_tab2_mode_changed()`（1046行目付近）は、これまで`self.tab2_current_mode`の更新とボタンエリア（`widget_new_mode_actions`/`widget_edit_mode_actions`）の表示切替のみを行い、`self.selected_edit_point_id`をリセットしていなかった。

このため、編集モードで点を選択した状態から新規モードへトグルを切り替えても`selected_edit_point_id`が残存し、
- `_check_realtime_duplicate()`（1112行目付近）が`check_point_duplicate()`呼び出し時に渡す`exclude_feature_id`が直前に選択していたフィーチャIDのままになる
- `edit_point_name`（点名スピンボックス）の値も編集時の値のまま再計算されない

という2点により、新規モードへ戻った後の打点で「直前に編集していた点自身」が重複判定から除外され、同名の点が重複作成されるバグが発生していた。

修正として、`_on_tab2_mode_changed()`の末尾に、新規モード（`index == 0` / `self.tab2_current_mode == "new"`）へ切り替わり、かつ`self.selected_edit_point_id`が`None`でない場合に既存の`_reset_point_selection()`を呼ぶ処理を追加した。`_reset_point_selection()`は既に`_on_blank_click_in_edit_mode()`から呼ばれている既存メソッドであり、以下を行う（新規実装なし、既存メソッドの呼び出し箇所を追加しただけ）。
- `self.selected_edit_point_id = None`、`self._selected_point_data = None`
- カテゴリウィジェットのロック解除（`_set_category_widgets_locked(False)`）
- `_apply_next_point_number()`による点名の再計算
- 枝番（`edit_branch_no`）のクリア、`_has_digitized_with_branch = False`
- `_refresh_point_info_labels()` / `_update_point_info_status()`によるUI状態更新
- `map_tool.clear_selected_marker()`による選択マーカーのクリア

編集モード（`index == 1`）への切り替え時の挙動は変更していない（既存の通り、選択されるまで新規点作成状態のまま）。

## 自動テスト実行結果
自動テストコマンドは設定されていないため未実行。`python3 -m py_compile src/tab2_digitizing_mixin.py`による構文確認のみ実施し、エラーなしであった。

## スコープ外変更の有無
なし。src/tab2_digitizing_mixin.py の `_on_tab2_mode_changed()` 内への数行追加のみ。
