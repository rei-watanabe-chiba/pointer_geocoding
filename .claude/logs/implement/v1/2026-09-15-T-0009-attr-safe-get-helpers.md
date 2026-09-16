## タスクID
T-0009

## 変更ファイル一覧
- `src/core_logic.py`
- `src/tab1_georef_mixin.py`
- `src/tab2_digitizing_mixin.py`

（`src/main_dock_dialogs.py` は精査の結果、対象パターンの呼び出し箇所が存在しなかったため変更なし。詳細は「スコープ外変更の有無」欄を参照）

## 変更概要

### 1. `core_logic.py` にNULLセーフな属性取得ヘルパーを新設
既存のセクション構成（`# N. ...` 見出し）の末尾に新セクション「7. QgsFeature Attribute Access Helpers」を追加し、以下3関数を実装した。

- `safe_get_str(feat, field_name, default="") -> str`
  - `feat[field_name]` を試み、フィールドが存在しない場合（`KeyError`）は `default` を返す。
  - 値が `None` または QGISの `NULL` センチネルの場合も `default` を返す。
  - それ以外は `str(value).strip()` を返す。
  - 既存の重複パターン `str(feat["xxx"] or "").strip()` を置き換える。
- `safe_get_float(feat, field_name, default=0.0) -> float`
  - 同様のNULL/欠損フィールドガードに加え、`float(value)` 変換時の `ValueError`/`TypeError` を `default` にフォールバックする。
- `safe_get_int(feat, field_name, default=0) -> int`
  - 同様に `int(value)` 変換時の例外を `default` にフォールバックする。

NULL判定は本プロジェクト内の既存慣例（`gpkg_cache_mixin.py` の `_extract_field_str`/`_safe_str` が採用している `val is None or val == NULL` パターン）に合わせた。

### 2. `core_logic.py` 内の重複箇所を置換
以下、いずれも `QgsFeature` 属性の `NULLガード→str変換→strip` の重複パターンだった箇所を `safe_get_str()` 呼び出しへ置換した（デフォルト値はいずれも `""` で、置換前後の挙動は同一）。

- `update_point_layer_geometry()`: `feat_drawing = str(feat["drawing_name"] or "").strip()` → `safe_get_str(feat, "drawing_name")`
- `check_point_duplicate()`: `f_drawing`/`f_type`/`f_feat`/`f_pname`/`f_branch` の5箇所
- `get_next_point_number()`: `ex_type`/`f_name` の2箇所

### 3. `tab1_georef_mixin.py` の置換
`from .core_logic import (..., safe_get_str)` を追加し、`point_layer.getFeatures()` から取得した `QgsFeature` の `drawing_name` 属性を読む3箇所（`_on_delete_layer_clicked()` 内2箇所、レイヤ名変更処理内1箇所）を `str(f["drawing_name"] or "").strip()` から `safe_get_str(f, "drawing_name")` に置換した。

### 4. `tab2_digitizing_mixin.py` の置換
`from .core_logic import (..., safe_get_str)` を追加し、`_apply_feature_color_group()` 内の `str(feat["feature_name"] or "") == selected_feat` を `safe_get_str(feat, "feature_name") == selected_feat` に置換した。

**留意点（挙動の差異なしを確認済みの前提での置換）**: このオリジナルコードは唯一 `.strip()` を伴わない書き方（`str(feat["feature_name"] or "")`）だったため、`safe_get_str()`（常に `.strip()` する）へ置換したことで、理論上は前後空白付きの `feature_name` が保存されているケースでのみ比較結果が変わり得る。ただし `feature_name` は本プラグイン内で常に `get_digitizing_input_state()` の `new_feat_name = self.edit_new_feature.text().strip()`、または `register_new_feature_name()` を経由してのみ書き込まれており、書き込み時点で既にトリム済みの文字列しか保存され得ない設計になっている（`core_logic.build_digitized_feature()` も受け取った `feature_name` をそのまま設定するのみで独自に空白を付加しない）。そのため実運用上の挙動差は生じない前提で置換したが、念のためここに明記する。

### 5. 対象外とした箇所（意図的に置換しなかった箇所）
以下は「NULLガード→str/float/int型変換」という表層は似ているが、性質が異なるため今回のヘルパーへは統合しなかった。

- `core_logic.py` `get_next_point_number()` 内の `point_name` 最大値探索（`pname = feat["point_name"]; if pname is not None and str(pname).isdigit(): max_num = max(...)`）
  - `isdigit()` による「非負の数字のみの文字列」判定であり、`int()` の try/except（負号・空白を許容してしまう）とは厳密には挙動が異なるため、`safe_get_int` へ置換すると許容範囲が変わってしまう懸念があり対象外とした。
- `core_logic.py` `get_next_point_id()` 内の `point_id` 最大値探索（`isinstance(pid, int)` による型チェック）
  - 文字列や浮動小数点からの変換を許容しない厳密な型チェックであり、`safe_get_int` の「変換を試みる」性質とは異なるため対象外とした。
- `core_logic.py` `update_point_layer_geometry()` 内の `pixel_x`/`pixel_y`（存在すれば優先、なければ `canvas_x`/`canvas_y` にフォールバックしてから `float()` 変換、失敗時は `continue` で当該フィーチャをスキップ）
  - 単一フィールドのNULLガード＋デフォルト値付与という単純な形ではなく、「別フィールドへのフォールバック」および「失敗時はスキップ（デフォルト値で処理を継続しない）」という異なる制御構造のため、`safe_get_float` へ機械的に置換すると意味が変わるため対象外とした。
- `tab1_georef_mixin.py` の `self.ref_points_data`（基準点リスト）や `QTableWidget` セル（`table_ref_points.item(row, col).text()`）からの座標取得・型変換（`_on_preview_canvas_point_clicked()`、`_on_ref_table_cell_changed()` など）
  - これらは `QgsFeature` ではなく、素の `dict` または `QTableWidgetItem`（実質 `QLineEdit` 相当の入力値検証）が対象であり、依頼文中で明示的に「QgsFeature以外の入力値検証パターン…は無理に同じヘルパーに統合せず」とされている対象に該当するため、今回のヘルパーでは対象外とした。
- `tab2_digitizing_mixin.py` の `get_digitizing_input_state()`（`QComboBox`/`QLineEdit`/`QSpinBox` 等のUIウィジェットから値を取得・検証）
  - 同上の理由（`QgsFeature` 属性アクセスではなくUIウィジェット入力値の検証）により対象外とした。
- `tab2_digitizing_mixin.py` の `_on_existing_point_selected(self, data: dict)`
  - 引数 `data` は `map_tool.py`（本タスクのスコープ外ファイル）側で `QgsFeature` から組み立てられた `dict` であり、本メソッド自体は `dict.get()` に対する `str(... or "").strip()` / `int(... or 1)` 処理を行っている。`QgsFeature` への直接アクセスではないため、依頼文の「QgsFeature以外の入力値検証パターン」に該当すると判断し対象外とした。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定のため未実行）。

代わりに以下の静的チェックのみ実施した:
- `python3 -m py_compile src/core_logic.py src/tab1_georef_mixin.py src/tab2_digitizing_mixin.py src/main_dock_dialogs.py` → コンパイルエラーなし
- `python3 -m pyflakes ...`（利用可能だった範囲で実行）→ 今回の変更箇所に起因する新規の警告なし（`core_logic.py` の `QgsProject`/`QVariant` 未使用インポート警告は本タスク着手前から存在していた既存の警告であり、本タスクでは変更していない）

## スコープ外変更の有無
なし。ただし、依頼文で「対象箇所」として例示されていた `main_dock_dialogs.py`（`GridInputDialog` 等）については、実装時にコードを精査した結果、`QgsFeature` 属性への直接アクセス（NULLガード→型変換）パターンが存在しなかった（同ファイルは `dict` と `QLineEdit`/`QSpinBox` 等のUIウィジェット入力のみを扱っており、依頼文が明示的に対象外としている「QgsFeature以外の入力値検証パターン」に該当する）ため、変更を行わなかった。これはファイル変更漏れではなく、精査結果に基づく意図的な対象外判断である。
