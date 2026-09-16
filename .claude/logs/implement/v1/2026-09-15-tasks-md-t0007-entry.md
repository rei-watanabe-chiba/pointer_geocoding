## タスクID
T-0007（タスク状態ファイルへの完了行追加のみ）

## 変更ファイル一覧
- `.claude/state/tasks.md`

## 変更概要
`.claude/state/tasks.md` のタスク表に、T-0007（Stage F: `_on_canvas_clicked()` の責務分解。
次点ID採番ロジックを `get_next_point_id()`、GeoPackage書き込みを `insert_feature_to_layer()`
として `core_logic.py` へ抽出）の行を追加した。

追加した行の内容:
- タスクID: T-0007
- 内容: Stage F: `_on_canvas_clicked()`の責務分解（次点ID採番ロジックを`get_next_point_id()`、GeoPackage書き込みを`insert_feature_to_layer()`として`core_logic.py`へ抽出）
- 状態: 完了
- 実装ログ: `.claude/logs/implement/2026-09-15-stageF-on-canvas-clicked-decomposition.md`
- 検証結果: 静的検証問題なし
- 人手確認: ユーザーがQGIS上で動作確認済み（「動作確認した。問題ない」）

本作業は依頼内容の通り `.claude/state/tasks.md` の表への1行追加のみであり、`src/` 配下のコードは
一切変更していない。

## 自動テスト実行結果
自動テストなし（本タスクは状態ファイルの追記のみであり、コード変更を伴わないため実行対象コードもなし）

## スコープ外変更の有無
なし。`.claude/state/tasks.md` 以外のファイルは変更していない。
