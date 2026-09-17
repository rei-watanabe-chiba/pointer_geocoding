## タスクID
T-0047（デバッグ用一時変更、通常のタスク状態遷移の対象外）

## 変更ファイル一覧
- `src/ui/dialogs.py`

## 変更概要
`FeatureCreateDialog._on_realtime_validate` / `PointNameEntryDialog._on_realtime_validate` が
実機QGIS上で機能しない不具合（textChanged/textEdited併用フォールバック済みでも未解決）の原因を
実機で切り分けるため、以下の**一時的なデバッグログ**を追加した。

1. import追加（1箇所）:
   `from qgis.core import QgsRasterLayer` を
   `from qgis.core import QgsRasterLayer, Qgis, QgsMessageLog  # DEBUG T-0047 temp import (remove with debug lines below)`
   に変更（`dialogs.py` 33行目付近）。

2. `FeatureCreateDialog._on_realtime_validate`（648行目付近）の冒頭1行目に以下を追加:
   ```python
   QgsMessageLog.logMessage(f"DEBUG T-0047 FeatureCreateDialog._on_realtime_validate called args={args!r} text={self.edit_name.text()!r}", "pointer_geocoding", level=Qgis.MessageLevel.Info)  # DEBUG T-0047 temp line (remove after root cause confirmed)
   ```

3. `PointNameEntryDialog._on_realtime_validate`（846行目付近）の冒頭1行目に以下を追加:
   ```python
   QgsMessageLog.logMessage(f"DEBUG T-0047 PointNameEntryDialog._on_realtime_validate called args={args!r} is_sp={self._is_sp_attribute!r} text={(self.edit_point_name_sp.text() if self._is_sp_attribute else None)!r}", "pointer_geocoding", level=Qgis.MessageLevel.Info)  # DEBUG T-0047 temp line (remove after root cause confirmed)
   ```

タグ名は、プロジェクト内に `QgsMessageLog` 使用の既存慣例が見当たらなかった
（`tab1_image.py`/`plugin.py`/`dock.py`/`symbology.py` は `iface.messageBar().pushMessage(..., level=Qgis.MessageLevel.*)`
のメッセージバー方式のみを使用しており、`QgsMessageLog.logMessage` の使用例はプロジェクト内になし）ため、
plugin_id `pointer_geocoding` をタグ名として新規に採用した。

**これは一時的な原因切り分け用の変更であり、恒久化しない。** 実機での挙動確認後、必ず除去すること。

### 除去手順（原因確定後に必ず実施）
1. `src/ui/dialogs.py` の import行を
   `from qgis.core import QgsRasterLayer, Qgis, QgsMessageLog  # DEBUG T-0047 temp import (remove with debug lines below)`
   から `from qgis.core import QgsRasterLayer` に戻す（`Qgis`/`QgsMessageLog` が他で使われていないことを確認の上）。
2. `FeatureCreateDialog._on_realtime_validate` 冒頭の `QgsMessageLog.logMessage(...)` の1行（`# DEBUG T-0047 temp line` コメント付き）を削除する。
3. `PointNameEntryDialog._on_realtime_validate` 冒頭の `QgsMessageLog.logMessage(...)` の1行（同上コメント付き）を削除する。
4. `python3 -m py_compile src/ui/dialogs.py` で構文確認する。

いずれも `# DEBUG T-0047` を含むコメント/行として検索すれば容易に特定できる。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
`python3 -m py_compile src/ui/dialogs.py` による構文確認のみ実施し、エラーなし。

## スコープ外変更の有無
なし。`src/ui/dialogs.py` の対象2メソッドの冒頭1行追加と、それに伴うimport1行の変更のみ。
ロジック変更は一切行っていない。
