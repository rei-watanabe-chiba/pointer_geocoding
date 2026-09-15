## タスクID
T-0010

## 変更ファイル一覧
- `src/tab1_georef_mixin.py`

## 変更概要

### 背景・根本原因
Tab1「編集削除」モードで既存の画像レイヤ（QGISプロジェクトに既に読み込まれ表示されている状態）の名前を変更して「確定」した際、`_on_confirm_image_clicked()` のリネーム処理は以下の順序になっていた。

1. `os.rename(old_path, new_path)` でファイルをリネーム（この時点でラスタレイヤはまだプロジェクトに読み込まれたまま＝GDALがファイルハンドルを保持）
2. その後にレイヤツリーを走査し `l.setName(layer_name)` で表示名だけを変更（ファイルの再読込はしない）

Windowsは使用中のファイルの改名を許可しないため、手順1の `os.rename()` が `[WinError 32]` で失敗する（Linux/Macでは再現しない）。

### 修正内容
`_on_confirm_image_clicked()` のEditモード分岐（リネーム処理）を以下の流れに変更した。

1. リネーム対象ファイル（`old_path`）を `os.rename()` する**前**に、新設ヘルパー `_release_raster_layer_for_rename(file_path)` を呼び出す。
   - `QgsProject.instance().layerTreeRoot().findLayers()` を走査し、`isinstance(layer, QgsRasterLayer)` かつ `os.path.normpath(layer.source()) == os.path.normpath(old_path)` で一致するレイヤを1件特定する。
   - 一致した場合、リネーム後に復元できるよう以下を事前に保持する。
     - スタイル: `layer.exportNamedStyle(QDomDocument)` でXML文字列として取得
     - レイヤツリー上の親グループ: `tree_layer.parent()`
     - 親グループ内での元の位置（インデックス）: `parent_group.children().index(tree_layer)`
     - チェック状態（表示/非表示）: `tree_layer.itemVisibilityChecked()`
   - `QgsProject.instance().removeMapLayer(layer.id())` でプロジェクトから削除してGDALのファイルハンドルを解放したのち、`QCoreApplication.processEvents()` を呼び出し、`removeMapLayer()` がQtのイベントループに遅延させる可能性のあるC++オブジェクトの実削除処理をこの時点で確実に完了させる。
   - 一致するレイヤが見つからなければ `None` を返す（プロジェクトに読み込まれていないケース。この場合は従来通りファイルリネームのみ行い、レイヤツリー同期処理はスキップされる）。
2. 画像本体・ワールドファイル（`.tfw`/`.jgw`/`.pgw`/`.bpw`/`.wld`）の `os.rename()` 処理自体は変更していない（既存の例外ハンドリング・エラーメッセージ表示も維持）。
3. リネームが例外で失敗した場合は、新設ヘルパー `_reload_raster_layer_after_rename()` を使って、手順1で解放したレイヤを（本体ファイルのリネームだけ先に成功していた場合は新パス、それ以外は元パスを判定して）復元してから、従来通りのエラーダイアログを表示して処理を中断する（＝失敗時にキャンバスから画像が消えたままにならないようにする）。
4. リネームが成功した場合は、`_reload_raster_layer_after_rename(new_path, layer_name, released_info)` を呼び出し、新パスで `QgsRasterLayer` を再生成する。
   - `layer.setCrs(get_local_crs())` でCRSを設定（既存の `load_georeferenced_raster()` と同じ手順・同じ `layer_manager_models.get_local_crs()`/`suppress_crs_prompt()` を利用）。
   - 保持しておいたスタイルXMLを `raster_layer.importNamedStyle(QDomDocument)` で復元。
   - `project.addMapLayer(raster_layer, addToLegend=False)` の後、保持しておいた親グループの `insertLayer(position, raster_layer)`（失敗時は `addLayer()` にフォールバック）で元の位置に再配置。
   - 復元後のレイヤツリーノードに対し `setItemVisibilityChecked(checked)` でチェック状態を復元。
5. 従来「レイヤツリー上のレイヤ名を `setName()` で更新する」ループ（`project.layerTreeRoot().findLayers()` を走査して `l.name() == old_name` のレイヤを `setName(layer_name)`）は、上記の削除→再生成方式に置き換わったため削除した。
6. 「点群属性のdrawing_name更新」「メタデータ更新（`save_image_metadata`）」「コンボボックス再描画（`_refresh_edit_layer_combo`）」等、既存ロジックの実行順序は変更していない（レイヤ解放・リネーム・再生成は、従来レイヤ名同期処理が行われていた箇所より前＝メタデータ更新より前の位置に配置し、それ以降のロジックは元の並び順のまま維持した）。

### 参考にした既存パターン
`src/session_io_mixin.py` の `load_georeferenced_raster()`（画像追加時のラスタレイヤ配置処理）を参照し、CRS設定（`get_local_crs()`）・CRSプロンプト抑制（`suppress_crs_prompt()`）・`project.addMapLayer(raster_layer, addToLegend=False)` の呼び出し方を踏襲した。「画像ファイル」グループそのものは今回新設していない（リネーム前に実際に所属していた親グループをそのまま復元する設計のため）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定のため未実行）。

代わりに以下の静的チェックのみ実施した。
- `python3 -m py_compile src/tab1_georef_mixin.py` → コンパイルエラーなし
- `python3 -m pyflakes src/tab1_georef_mixin.py` → 今回の変更箇所に起因する新規の警告なし（293行目の `f-string is missing placeholders` は本タスク着手前から存在していた既存の警告であり、変更前のHEADコミット時点の同ファイルでも同一行に同一警告が出ることを確認済み。本タスクでは当該箇所を変更していない）
- `python3 -m pyflakes src/*.py` → `tab1_georef_mixin.py` に起因する未使用インポート等の新規警告なし（他ファイルの既存警告は本タスク範囲外のため対応せず）

QGIS環境（`qgis.core`/`qgis.PyQt` 等）がこのサンドボックスに存在しないため、`qgis` モジュールに依存する箇所の実行時動作確認・importテストは行えていない。

## スコープ外変更の有無
なし。`src/tab1_georef_mixin.py` のみを変更し、新規セッション作成時（`is_edit_mode=False`）の分岐には手を加えていない。ファイル分割も行っていない（既存ファイル内でのメソッド追加・改修のみ）。
