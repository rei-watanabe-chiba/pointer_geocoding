## タスクID
T-0039b 新規モードでのホバー赤枠マーカーの無効化

## 変更ファイル一覧
- src/map_tool.py

## 変更概要
`CanvasDigitizingTool.canvasMoveEvent()`の冒頭で、`_handle_digitize_click()`と同じパターン
（`getattr(self.dock_widget, "tab2_current_mode", "new")`を取得し、"new"/"edit"以外の値は
"new"へフォールバック）でモード判定を追加した。

- "new"モードの場合: `find_nearest_feature_id()`の呼び出しを行わず、`hover_marker.hide()`と
  `setCursor(Qt.CrossCursor)`を実行して即座にreturnする（マウス座標の`toMapCoordinates`変換も
  スキップされるモード分岐の外側に移動）。
- "edit"モードの場合: 従来通り`toMapCoordinates`でマップ座標に変換し、`find_nearest_feature_id()`
  でスナップ判定を行い、ヒット時は`hover_marker`表示＋`PointingHandCursor`、ミス時は
  `hover_marker.hide()`＋`CrossCursor`とする処理を維持した。

`_handle_digitize_click()`本体、`ImageGeorefTool`等の他クラスのcanvasMoveEventには手を入れて
いない。

## 自動テスト実行結果
自動テストなし。`python3 -m py_compile src/map_tool.py` を実行し、構文エラーがないことを確認した
（コンパイルはエラーなく完了した）。

## スコープ外変更の有無
なし。`git diff --stat`で変更が`src/map_tool.py`の1ファイル・1箇所（canvasMoveEvent冒頭への
モード分岐追加、17行追加・1行削除）のみであることを確認した。
