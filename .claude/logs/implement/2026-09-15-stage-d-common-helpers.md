## タスクID
Stage D: 低リスク・機械的な共通化 (D-1〜D-3)

## 変更ファイル一覧
- `src/core_logic.py`
- `src/transform.py`
- `src/settings_metadata_mixin.py`
- `src/layer_manager_models.py`
- `src/style_helper.py`
- `src/start_dialog.py`

## 変更概要

### D-1: レイヤ編集ボイラープレートの共通ヘルパー化
- `src/core_logic.py` に `batch_update_attributes(layer, updates, geometries=None) -> int` を新規追加。
  - `startEditing()` → フィールド名ごとの `indexFromName` 解決（名前ごとにキャッシュ）→ `changeAttributeValue`（インデックスが `-1` の場合はスキップ）→（`geometries` 指定時のみ）`changeGeometry` → `commitChanges()` という一連の処理をカプセル化し、処理した `(feature_id, 更新内容)` の件数を返す。
  - 元の2箇所はいずれも「`changeAttributeValue` 前にフィールドインデックスを解決し、`-1` なら書き込みをスキップする」「全フィーチャ処理後に一括 `commitChanges()`」という同一の構造だったため、素直に置き換え可能だった。
- `src/core_logic.py` の `update_point_layer_geometry()`:
  - 元は `rx_idx`/`ry_idx`/`cx_idx`/`cy_idx` を事前解決し、ループ内で `changeAttributeValue` を個別に4回呼び、同時に `changeGeometry` を呼んでいた。
  - 変更後は、ループ内で `updates`（`(feature_id, {"canvas_x":…, "canvas_y":…, "real_x":…, "real_y":…})` のリスト）と `geometries`（`feature_id -> QgsGeometry` の辞書）を組み立てるだけとし、ループ後に `batch_update_attributes()` を1回呼び出す形に変更。フィルタ条件（`drawing_name` 一致判定）、`pixel_x`/`pixel_y` 優先・`canvas_x`/`canvas_y` フォールバックのロジック、`float` 変換失敗時の `continue`、戻り値（処理件数）、`triggerRepaint()` の呼び出しタイミングはすべて従来通り。
- `src/transform.py` の `CoordinateTransformer.execute_transformation()`:
  - 基準点レイヤ（`ref_point_layer`）の `target_x`/`target_y` 更新ループを、`fid is not None` のものだけ `(fid, {"target_x":…, "target_y":…})` のリストに詰め、`batch_update_attributes(self.ref_point_layer, ref_updates)` を1回呼ぶ形に置き換え。`fid is None` の場合はリストに追加しない点（元の `if fid is not None:` ガードと同義）、フィールド未存在時は個別に書き込みスキップされる点（`tx_idx != -1`/`ty_idx != -1` の個別ガードと同義）は変更なし。この箇所は元々 `triggerRepaint()` を呼んでいなかったため、置き換え後も呼んでいない。
- `src/gpkg_cache_mixin.py` の `_on_attribute_changed`/`_on_geometry_changed` は「レイヤ変更をキャッシュへ反映する読み取り専用の同期処理」であり対象外のため、**一切変更していない**（grepで確認済み）。

### D-2: JSON読み書き・エラーハンドリングパターンの統一
- `src/layer_manager_models.py`（QGIS非依存のユーティリティが既に置かれているモジュールのため、指示に従いこちらを優先）に以下を追加:
  - `safe_json_load(path, default=None) -> Any`: `path` が falsy または存在しない場合、または読み込み/パースで例外が発生した場合に `default` を返す。それ以外は `json.load()` の結果をそのまま返す。
  - `safe_json_save(path, data, ensure_dir=False) -> bool`: `path` が falsy なら `False`。`ensure_dir=True` の場合のみ書き込み前に `os.makedirs(os.path.dirname(path), exist_ok=True)` を実行（呼び出し元ごとに元々の `os.makedirs` 有無が異なっていたため、フラグで区別し挙動を維持）。書き込み成功で `True`、例外発生で `False`。
- `src/settings_metadata_mixin.py`:
  - `load_settings()`: `safe_json_load(self.get_settings_path())` の結果が `None` でなければ `result.update(stored)` を試みる（`update` 自体が例外を投げるケースまで元の `try/except` で握り潰していたため、`update` 呼び出しはそのままローカルの `try/except Exception: pass` で包んで維持）。
  - `save_settings()`: ファイル書き込み部分を `safe_json_save(path, data, ensure_dir=True)` に置き換え。`settings_changed.emit(data)` を含む全体は元通り `try/except Exception: return False` で包み、失敗時の戻り値・例外の扱いを変更していない。
  - `load_image_metadata()`: `return safe_json_load(self.get_image_metadata_path(), default={})` の1行に置き換え（元は「パス未指定/未存在なら `{}`、読み込み/パース例外でも `{}`」というロジックで、`safe_json_load` の挙動と完全一致）。
  - `save_image_metadata()`: ファイル書き込み部分を `safe_json_save(path, metadata)`（`ensure_dir` 未指定＝`False`。元コードもここでは `os.makedirs` を呼んでいなかったため一致）に置き換え。`metadata_updated.emit("")` を含む全体は元通り `try/except` で包んだまま。
  - 未使用となった `import json` を削除（`os` は `os.path.join`/`os.makedirs`/`os.path.exists` で引き続き使用するため残置）。

### D-3: QMessageBoxエラー表示パターンの集約
- `src/style_helper.py` の `UIStyleHelper` に薄いラッパーを追加:
  - `show_error_dialog(parent, title, message) -> None`: `QMessageBox.critical(parent, title, message)` を呼ぶだけ。
  - `show_warning_dialog(parent, title, message) -> None`: `QMessageBox.warning(parent, title, message)` を呼ぶだけ。
  - `QMessageBox` を `qgis.PyQt.QtWidgets` からインポート追加。
- `src/transform.py`: `QMessageBox.critical(...)`/`QMessageBox.warning(...)` の呼び出し箇所（`compute_helmert_2p` 2箇所、`compute_affine_3p` 2箇所、`compute_affine_points` 2箇所、`execute_transformation` 1箇所、`export_points_to_csv` 3箇所、計10箇所）をすべて `UIStyleHelper.show_error_dialog(...)`/`UIStyleHelper.show_warning_dialog(...)` に置き換え。引数（`parent`, タイトル文言, メッセージ文言・f-string/`.format()` 含む）は一切変更していない。呼び出しを囲む `if parent:` ガードもそのまま維持。置き換え後、直接の `QMessageBox` 利用箇所がなくなったため `from qgis.PyQt.QtWidgets import QMessageBox, QWidget` から `QMessageBox` を削除（`QWidget` は型ヒントで引き続き使用するため残置）。`UIStyleHelper` を `.style_helper` からインポート追加。
- `src/start_dialog.py`: `_validate_and_accept()` 内の `QMessageBox.warning(...)` 呼び出し6箇所をすべて `UIStyleHelper.show_warning_dialog(...)` に置き換え（`UIStyleHelper` は既にインポート済みのため追加インポート不要）。文言・引数・呼び出し後の `setFocus()`/`return` の順序は一切変更していない。置き換え後、直接の `QMessageBox` 利用箇所がなくなったため import から `QMessageBox` を削除。

## ロジック一致確認の方法
コードを書き換えるツールではなく、以下の方法で目視突き合わせを行った（実行によるアサーションは環境上不可のため未実施）。

1. 各置き換え箇所について、変更前コード（本セッション冒頭で `Read` した内容）と変更後コードを1文ずつ突き合わせ、以下を確認:
   - 条件分岐（`if fid is not None`, `if idx != -1`, `if parent:` など）が同じ順序・同じ条件式で残っているか。
   - 例外処理のスコープ（どのステートメントが `try` の中にあるか）が変わっていないか。
   - 呼び出し元に返る値（`updated_count`, `bool`, `Dict[str, Any]` の中身等）が同じ式・同じソースから来ているか。
   - `commitChanges()`/`triggerRepaint()`/`emit()` の呼び出し回数・タイミングが変わっていないか。
2. `batch_update_attributes` については、置き換え前の2箇所それぞれの「フィールド存在チェック→`changeAttributeValue`」の反復を、ヘルパー内の「フィールド名キャッシュ→`changeAttributeValue`」の反復と1対1で対応付けて確認した。
3. `safe_json_load`/`safe_json_save` については、`try/except` の内側に元々含まれていた処理（特に `save_settings()` の `result.update(stored)` や `settings_changed.emit(data)` のように、ヘルパーの外側でも例外を握り潰す必要がある処理）を洗い出し、呼び出し元側で元通り `try/except` を維持することで、ヘルパー抽出後も例外発生時の戻り値・副作用が変わらないようにした。
4. D-3 の置き換えは、`QMessageBox.critical/warning(parent, title, message)` → `UIStyleHelper.show_error/warning_dialog(parent, title, message)` という関数名以外は完全に同一の引数列であることを1箇所ずつ確認した（文言・引数の追加/削除/並び替えは行っていない）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定）。
代わりに `python -m py_compile` を対象ファイル全体（変更した6ファイルおよび `src/*.py` 全体）に対して実行し、構文エラーがないことを確認した。

```
"C:\Python314\python.exe" -m py_compile src/*.py
→ 出力: "Could not find platform independent libraries <prefix>"（Windows Python の既知の無害な警告）のみ、exit code 0
```

## スコープ外変更の有無
なし。D-1〜D-3で指定された6ファイル（`core_logic.py`, `transform.py`, `settings_metadata_mixin.py`, `layer_manager_models.py`, `style_helper.py`, `start_dialog.py`）以外は変更していない。`gpkg_cache_mixin.py` は指示通り対象外として変更していない（grepで確認）。
各ファイルで未使用となった import（`transform.py`/`start_dialog.py` の `QMessageBox`、`settings_metadata_mixin.py` の `json`）は、今回の置き換えの直接的な副産物として削除したが、ロジック・処理フローには影響しない。

## 行数の概算
- `src/core_logic.py`: 416行 → 457行（+41行。新規ヘルパー `batch_update_attributes` 本体・docstringの追加分。`update_point_layer_geometry` 内部の重複記述自体は圧縮されている）。
- `src/transform.py`: 495行 → 490行（-5行。基準点レイヤ更新ループは16行→9行に圧縮（-7行）。QMessageBox関連の置き換えは1:1の文言置換のため行数はほぼ変化なし、importの整理で若干減）。
- `src/settings_metadata_mixin.py`: 150行 → 140行（-10行。4メソッドの重複していたopen/json.load/json.dump/except構造がヘルパー呼び出しに圧縮された）。
- `src/layer_manager_models.py`: 165行 → 220行（+55行。新規ヘルパー `safe_json_load`/`safe_json_save` 本体・docstringの追加分）。
- `src/style_helper.py`: 458行 → 484行（+26行。新規ラッパー `show_error_dialog`/`show_warning_dialog` 本体・docstringの追加分）。
- `src/start_dialog.py`: 684行 → 683行（-1行。呼び出し自体は1:1置換のため行数変化はほぼなく、未使用import削除分のみ減）。

合計では新規ヘルパー本体（docstring込み）の追加により全体の行数はわずかに増加している（概算 2368行 → 2474行、+106行）が、これはD-1/D-2/D-3いずれも「呼び出し側の重複コードを1箇所の共有ヘルパーに集約する」ことが目的であり、各呼び出し箇所単体で見ると重複していたボイラープレートは確実に削減されている（特に D-1 の `transform.py` 側、D-2 の `settings_metadata_mixin.py` 側で顕著）。
