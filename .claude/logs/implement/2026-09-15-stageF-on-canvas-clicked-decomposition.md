## タスクID
Stage F: `_on_canvas_clicked()` の責務分解（処理フロー変更を伴わない）

## 変更ファイル一覧
- `src/core_logic.py`
- `src/tab2_digitizing_mixin.py`

## 変更概要

### 1. `src/core_logic.py`
`build_digitized_feature()` の直後（Excel列変換ユーティリティのセクション区切り前）に、以下2関数を新規追加した。

- `get_next_point_id(point_layer: QgsVectorLayer) -> int`
  - `_on_canvas_clicked()` に元々インラインで存在していた「次点ID採番」ロジック（`for f in self.point_layer.getFeatures(): pid = f["point_id"]; if pid is not None and isinstance(pid, int): max_id = max(max_id, pid)` → `return max_id + 1`）を、変数名・処理順序・条件式を一切変更せず、そのまま関数として抽出した。
- `insert_feature_to_layer(point_layer: QgsVectorLayer, feature: QgsFeature) -> bool`
  - 元のインラインコード `self.point_layer.startEditing()` → `addFeatures([new_feat])` → `commitChanges()` → `triggerRepaint()` の4呼び出しを、同一の呼び出し順序のまま関数として抽出した。元コードは戻り値を一切参照/判定していなかったため、成否判定ロジックは新規に追加せず、`return True` を末尾に置くのみとした（API上の体裁のためであり、呼び出し元では戻り値を使用していない）。

### 2. `src/tab2_digitizing_mixin.py`
- import文に `get_next_point_id`, `insert_feature_to_layer` を追加（`.core_logic` からのインポート一覧に統合）。
- `_on_canvas_clicked()` 本体を以下のように整理した。
  - ステップ4（次点ID採番）: インラインのforループを `next_point_id = get_next_point_id(self.point_layer)` の1行に置換。
  - ステップ7（GeoPackage書き込み）: インラインの4行（startEditing/addFeatures/commitChanges/triggerRepaint）を `insert_feature_to_layer(self.point_layer, new_feat)` の1行に置換。
  - ステップ番号コメントを更新: 元の「6. Build and insert the feature」を「6. Build the feature」（組み立てのみ）、新設「7. Write the new feature to the layer」（書き込み）、既存「7. Update UI」→「8. Update UI」に採番し直した。ステップ1〜5（入力検証・新規遺構名登録・重複チェック・ピクセル座標解決）はUI依存（`QMessageBox`, `self.xxx`）のため一切変更していない。

## 変更前後でのロジック一致確認

- ステップ4（次点ID採番）: 変更前後で `max_id` の初期値（0）、ループ対象（`self.point_layer.getFeatures()` 全件）、`point_id` が `None` または非`int`型（例: `NULL`や文字列）の場合にスキップする条件式、`max_id + 1` を返す点は完全に同一。`get_next_point_id()` 内部の変数名・比較演算子も元コードと字面レベルで一致させた（コピー＆貼り付けによる抽出であり、書き換えは行っていない）。
  - エッジケース: レイヤが空（フィーチャ0件）の場合、`max_id = 0` のまま `return 1` となる点も元コードと同一（元コードにも空チェックは存在せず、forループが0回実行されるだけで同じ挙動になる）。
  - エッジケース: `point_id` が `None`（NULLフィールド）のフィーチャが混在する場合、`pid is not None` の判定でスキップされ `max_id` に影響しない点も同一。
  - エッジケース: 既存点を削除して欠番がある状態（例: 1,2,4が存在し3が削除済み）でも、単純に既存フィーチャ中の最大値+1を返すロジックであるため、削除前後で採番アルゴリズム自体は変わらない（欠番を詰める処理は元々存在しない）。
- ステップ7（GeoPackage書き込み）: `startEditing()` → `addFeatures([new_feat])` → `commitChanges()` → `triggerRepaint()` の呼び出し順序・引数・戻り値の扱い（元コードは戻り値を一切参照していない）を完全に維持。`insert_feature_to_layer()` は新たな例外処理・条件分岐を一切追加していない。

上記により、`_on_canvas_clicked()` の入力に対する出力（打刻成功/失敗の分岐、エラーメッセージ文言、GeoPackageへの書き込み内容、UI更新呼び出しに渡すdict）は変更前と完全に同一であることをコードレベルの比較により確認した。

## 自動テスト実行結果
自動テストなし（本プロジェクトに自動テストコマンドは設定されていない）。

`python -m py_compile src/*.py` を実行し、構文エラーがないことを確認した（`src/__pycache__/*.cpython-314.pyc` が19ファイル分すべて生成されたことを確認後、生成物は作業ツリーから削除した）。
実行コマンド: `C:\Python314\python.exe -m py_compile src/*.py` → `COMPILE_OK` を出力（"Could not find platform independent libraries <prefix>" という警告行が出力されたが、これはPython実行環境のプレフィックス検出に関する無害な警告であり、コンパイル結果には影響しない）。
なお、この環境には `qgis` パッケージがインストールされていないため、`py_compile` は構文レベルの検証に留まり、`qgis.core`等のインポート解決やQGIS実行時の動作は検証できていない。

## スコープ外変更の有無
なし。変更は依頼された2箇所の抽出（`get_next_point_id`, `insert_feature_to_layer`）と、それに伴う `_on_canvas_clicked()` 本体のステップ4・7の置換、importの追加、ステップ番号コメントの更新にとどめた。ステップ1（入力検証）・ステップ2（新規遺構名登録）・ステップ3（重複チェックのメッセージ組み立て）はUIバインドされたコードのため `core_logic.py` へ移動していない。他のメソッド・他のファイルは変更していない。

設計書 `docs/integrated_master_design.md` の94行目は `core_logic.py` が提供する関数として `check_point_duplicate`/`get_next_point_number`/`build_digitized_feature`/`pixel_from_affine` 等を列挙しているが、今回追加した `get_next_point_id`/`insert_feature_to_layer` はこの一覧に未反映のままである。設計書の更新は本タスクの依頼範囲外（依頼は `src/core_logic.py` と `src/tab2_digitizing_mixin.py` の変更に限定）のため、ドキュメントには手を入れていない。設計書更新が必要であれば別タスクとして依頼されたい。
