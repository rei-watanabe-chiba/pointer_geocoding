## タスクID
T-0039 編集モードでの空白クリック時の選択解除（編集モードは維持）

## 変更ファイル一覧
- `src/map_tool.py`
- `src/tab2_digitizing_mixin.py`
- `src/main_dock.py`

## 変更概要
- `src/map_tool.py`
  - `CanvasDigitizingTool` に新規シグナル `blank_click_in_edit_mode = pyqtSignal()` を追加（`canvas_clicked`/`existing_point_selected` と同じパターンでクラス変数として定義）。
  - `_handle_digitize_click()` の編集モード分岐で、`find_nearest_feature_id()` がヒットしなかった場合（空白クリック）に `self.blank_click_in_edit_mode.emit()` を呼ぶよう変更。従来の「何もしない」から変更。ヒット時の挙動（`existing_point_selected.emit(data)` 等）は変更なし。新規モード側の分岐（`mode == "new"`）には一切触れていない。
  - 関連するdocstring（メソッド冒頭のコメント、編集モード分岐直前のコメント）をT-0039の挙動に合わせて更新。

- `src/main_dock.py`
  - `MainDockWidget.__init__()` 内、既存の `self.map_tool.canvas_clicked.connect(...)` / `self.map_tool.existing_point_selected.connect(...)` の直後に `self.map_tool.blank_click_in_edit_mode.connect(self._on_blank_click_in_edit_mode)` を追加。既存の2シグナルと同様、対応するdisconnect処理はコード内に存在しない（`MainDockWidget`のライフサイクル終了まで維持される既存の設計パターンに合わせた）。

- `src/tab2_digitizing_mixin.py`
  - `Tab2DigitizingMixin` に新規スロット `_on_blank_click_in_edit_mode()`（`@pyqtSlot()`）を追加。`self.selected_edit_point_id is None` の場合は何もせず早期returnし、選択中の点がある場合のみ既存の `self._reset_point_selection()` を呼び出す。
  - `_reset_point_selection()` 自体は変更していない（既存実装を再利用する方針のため）。このメソッドは `self.tab2_current_mode` を変更しないため、編集モードは維持される。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定）。
`python3 -m py_compile src/map_tool.py src/tab2_digitizing_mixin.py src/main_dock.py` は成功（構文エラーなし）。

## スコープ外変更の有無
なし。依頼された3ファイル（`src/map_tool.py`, `src/tab2_digitizing_mixin.py`）に加え、シグナル接続のために `src/main_dock.py`（`CanvasDigitizingTool` のシグナルを `connect()` している唯一の箇所）を変更したが、これは依頼内の「新しいシグナルをemitし、dock widget側で購読する」という実装内容に必要な最小限の接続追加であり、依頼の意図する範囲内と判断した。それ以外のファイル・機能には手を入れていない。
