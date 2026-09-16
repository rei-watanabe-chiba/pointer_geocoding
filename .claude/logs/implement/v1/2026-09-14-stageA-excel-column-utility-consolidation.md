## タスクID
Stage A: 重複ユーティリティ関数の統合（to_excel_column / from_excel_column）

## 変更ファイル一覧
- `src/core_logic.py`
- `src/layer_manager.py`
- `src/start_dialog.py`

## 変更概要
- `src/core_logic.py` にモジュールレベル関数 `to_excel_column(n: int) -> str` と `from_excel_column(col_str: str) -> int` を新設セクション「5. Excel-style Column Letter Conversion Utilities」として追加した。
  - `to_excel_column` は `layer_manager.py` / `start_dialog.py` 双方の実装が完全に同一であったため、そのロジックをそのまま移植した。
  - `from_excel_column` は `start_dialog.py` にのみ存在した実装をそのまま移植した（指示どおり、こちらの実装を採用）。
  - 既存セクション番号がずれるため、旧「5. Affine Inverse Adapter」を「6. Affine Inverse Adapter」に採番し直した（ドキュメンテーションコメントのみの変更で、ロジックには影響なし）。
- `src/layer_manager.py`:
  - `LayerManager.to_excel_column` staticmethod を削除。
  - `from .core_logic import from_survey_coords, to_survey_coords` に `to_excel_column` を追加インポート。
  - `generate_grid_csv` 内の呼び出し `cls.to_excel_column(gy)` を `to_excel_column(gy)` に置き換え。
- `src/start_dialog.py`:
  - `to_excel_column` / `from_excel_column` の両 staticmethod を削除。
  - `from .core_logic import from_excel_column` を追加インポート（`to_excel_column` は当ファイル内で呼び出し箇所が存在しなかったため、未使用importを避けるためインポート対象に含めていない）。
  - `self.from_excel_column(...)` の2箇所（CSVインポート処理、グリッドプレビュー更新処理）を `from_excel_column(...)` に置き換え。
- ロジック（アルゴリズム、エッジケース挙動：`n<=0` で空文字列、不正な列文字列で0を返す等）は一切変更していない。

## 依頼スコープ項目4（他ファイルからの呼び出し確認）
`grep -rn "to_excel_column|from_excel_column" --include=*.py .` を実行し、`src/core_logic.py`, `src/layer_manager.py`, `src/start_dialog.py` の3ファイル以外に呼び出し・定義がないことを確認済み。他のファイル（`plugin.py`, `main_dock.py`, `map_tool.py`, `transform.py`, `style_helper.py`, `__init__.py`）には該当なし。

## 依頼スコープ項目5（設計書追従）
`docs/integrated_master_design.md` を `to_excel_column` / `from_excel_column` で検索したが、言及なし（該当なし）のため、設計書の変更は行っていない。
なお `dcs/integrated_master_design.md` は本リポジトリに存在せず、`docs/integrated_master_design.md` のみが存在することを確認した（探索のみ、変更なし）。

## 自動テスト実行結果（なければ「自動テストなし」）
自動テストコマンドは本プロジェクトに未設定のため、自動テストは実行していない（自動テストなし）。
代わりに以下の静的確認を実施した。

1. 構文チェック: `python -m py_compile src/core_logic.py src/layer_manager.py src/start_dialog.py` を実行し、エラーなく完了（exit code 0）。
   - 使用したPythonは `C:\Python314\python.exe`（QGIS付属のPython環境ではないが、標準ライブラリのみに依存する対象コードの構文検証には支障なし）。
2. ロジック単体確認（QGIS非依存のためコアロジック部分のみを抽出してPythonワンライナーで検証）:
   ```
   assert to_excel_column(1) == 'A'
   assert to_excel_column(26) == 'Z'
   assert to_excel_column(27) == 'AA'
   assert to_excel_column(79) == 'CA'
   assert to_excel_column(0) == ''
   assert to_excel_column(-5) == ''
   assert from_excel_column('A') == 1
   assert from_excel_column('Z') == 26
   assert from_excel_column('AA') == 27
   assert from_excel_column('') == 0
   assert from_excel_column('1') == 0
   ```
   全アサーション成功（`ALL_ASSERTS_PASSED`）。移植前後でエッジケース挙動（`n<=0`時の空文字列、非アルファベット文字列時の0）が一致することを確認した。

## スコープ外変更の有無
なし。指示された `to_excel_column` / `from_excel_column` の重複統合作業（core_logic.pyへの追加、layer_manager.py/start_dialog.pyからの削除と呼び出し置き換え、grepによる網羅確認、設計書追従確認）以外のファイル変更・ロジック変更・リファクタリングは行っていない。
core_logic.py内で既存の「5. Affine Inverse Adapter」セクションを「6. Affine Inverse Adapter」に採番し直した点のみ、新規セクション挿入に伴うコメント番号の整合性維持のための最小限の追従であり、コード（実行ロジック）自体への変更ではない。
