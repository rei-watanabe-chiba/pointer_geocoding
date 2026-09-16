## タスクID
T-0011（バグ修正、T-0010の追加原因対応）

## 変更ファイル一覧
- `src/tab1_georef_mixin.py`

## 変更概要

### 背景
T-0010（コミット9785817）で `_release_raster_layer_for_rename()` / `_reload_raster_layer_after_rename()` を新設し、リネーム前に対象ラスタレイヤを `QgsProject.instance().removeMapLayer()` してから `os.rename()` する方式に変更した。しかしユーザーの実機確認で `[WinError 32]` が依然として再現した。統括の調査により、`LayerManager.raster_layer`（`layer_manager.py:75` で初期化され、`session_io_mixin.py` の `load_georeferenced_raster()`/`load_existing_session()` で設定される、プラグイン生存期間中保持され続ける属性）が、T-0010の `removeMapLayer()` 後も同じレイヤオブジェクトを参照し続けている可能性が指摘され、本タスクで対応した。

### 追加調査で判明した点（依頼文の指示4に基づく再確認）
依頼された `LayerManager.raster_layer` に加え、`grep -rn "\.raster_layer\b" src/` を再確認したところ、依頼文で「通常の使用フローでは問題にならないと想定される」とされていた `PreviewDialog.raster_layer`（`main_dock_dialogs.py`。`LayerManager.load_preview_raster()` で生成され、`QgsProject` には追加されない独立したラスタレイヤ）についても、以下のフローでは問題になりうることを確認した。

- `_on_setup_ref_points_clicked()`（`tab1_georef_mixin.py:614`付近）は、編集削除モードで既存レイヤをセレクタで選び直した状態でも「基準点を設定」を再度クリックすると `_create_preview_canvas()` 経由で `preview_dialog.raster_layer` に対象ファイルのラスタレイヤを再セットする。
- この状態のまま「確定」でリネームを行うと、`preview_dialog.raster_layer` が旧ファイルパスへのGDALファイルハンドルを保持したままとなり、T-0010の `_release_raster_layer_for_rename()`（プロジェクトのレイヤツリーのみを走査）では検知・解放されない。
- なお、正常フロー（画像追加→座標変換確定）の直後は `_destroy_preview_canvas()`（`tab1_georef_mixin.py:1028`）が呼ばれ `preview_dialog.raster_layer` は `None` にクリアされるため、依頼文に記載された「画像1枚のみのシンプルなセッションで、確定直後にすぐ編集削除でリネーム」という主要な再現手順そのものは主に `LayerManager.raster_layer` 側の問題と考えられる。ただし「基準点を設定」を経由するフローでは `preview_dialog.raster_layer` も残留しうるため、依頼文の指示4（念のための確認）に従い、退行防止も兼ねて併せて対処した。

### 修正内容（`_release_raster_layer_for_rename()` / `_reload_raster_layer_after_rename()`）

1. `_release_raster_layer_for_rename(file_path)`:
   - 既存のプロジェクトレイヤツリー走査ロジック（一致するラスタレイヤをスタイル/親グループ/位置/表示状態を保持した上で `removeMapLayer()`）は維持した。
   - 一致したレイヤが `self.layer_manager.raster_layer`（`layer.id()` の一致で判定）と同一の場合、`released_info["was_layer_manager_raster"] = True` を記録した上で `self.layer_manager.raster_layer = None` にクリアするようにした。
   - `self.preview_dialog.raster_layer` が対象ファイルと同一パス（`os.path.normpath()` 比較）の場合、`released_info["was_preview_raster"] = True` を記録した上で `PreviewDialog.clean_up()`（既存メソッド。`georef_tool.clean_up()` → `georef_tool = None`、`canvas.setLayers([])`、`raster_layer = None` を行う）を呼び出して解放するようにした。プロジェクトレイヤツリーとは独立した判定・処理とした（両方に一致する場合は両方とも解放される）。
   - いずれかの参照を解放した場合（`released_info is not None`）、依頼文の指示2に基づき、`QCoreApplication.processEvents()` の後に `import gc` した `gc.collect()` を追加した。
   - `del layer`（プロジェクトレイヤツリー走査でヒットしたローカル変数の明示的な削除）を `removeMapLayer()` 直後に追加した。
2. `_reload_raster_layer_after_rename(file_path, layer_name, released_info)`:
   - `released_info` に `"parent_group"` キーがある場合（＝プロジェクトレイヤツリー側のレイヤが解放されていた場合）のみ、従来通りラスタレイヤを再生成しレイヤツリーへ復元する処理を実行するようガードを追加した（プレビューのみが解放されたケースでレイヤツリー復元処理を誤って実行しないようにするため）。
   - 再生成後、`released_info.get("was_layer_manager_raster")` が真の場合は `self.layer_manager.raster_layer` を新しいレイヤオブジェクトへ更新するようにした。
   - `released_info.get("was_preview_raster")` が真の場合は、`self.layer_manager.load_preview_raster(file_path)` で新パスのプレビュー用ラスタレイヤを生成し直し、`self.preview_dialog.setup_raster(preview_raster, self._on_preview_canvas_point_clicked, self.ref_points_data)` を呼び出して `PreviewDialog` を再セットアップするようにした（プレビューが解放されたまま `georef_tool is None` の状態で放置されないようにするため）。
3. リネーム失敗時のロールバック処理（`_on_confirm_image_clicked()` の `except` 節、`_reload_raster_layer_after_rename()` を呼び出して元パスへ復元する処理）は変更していない。呼び出しの引数・タイミングは既存のまま、`_reload_raster_layer_after_rename()` 内部のロジック拡張のみで両方（`layer_manager.raster_layer`/プレビュー）の復元が行われる形にした。

### 変更していない箇所（確認のみ）
- `session_io_mixin.py`（`load_georeferenced_raster()`/`load_existing_session()` での `self.raster_layer = raster_layer` 代入箇所自体）は変更していない。これらは属性の正規の設定経路であり、依頼文の修正方針（リネーム前にクリア・リネーム後に更新）は呼び出し側の `tab1_georef_mixin.py` から `self.layer_manager.raster_layer` に直接アクセスすることで完結できたため、`layer_manager.py`/`session_io_mixin.py` 自体への変更は不要と判断した。
- `map_tool.py` の `ImageGeorefTool.raster_layer`（`map_tool.py:90`）は、`PreviewDialog.clean_up()` が `self.georef_tool = None` によって `ImageGeorefTool` インスタンス自体への参照を切るため、追加の対処は行っていない。
- `main_dock.py:136`（`self.layer_manager.raster_layer is not None and ... isValid()`）、`main_dock.py:151`（`preview_dialog.raster_layer` を返すプロパティ）は読み取り専用の参照箇所であり、変更していない。今回の修正でリネーム後に両属性が新しいレイヤオブジェクトへ正しく更新される（または解放されなかった場合は元のまま変化しない）ため、これらの参照先が壊れる（削除済みレイヤを指したままになる）ことはない設計とした。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定のため未実行）。

代わりに以下の静的チェックのみ実施した。
- `python3 -m py_compile src/tab1_georef_mixin.py` → コンパイルエラーなし
- `python3 -m py_compile src/*.py` → 全ファイルコンパイルエラーなし
- `python3 -m pyflakes src/tab1_georef_mixin.py` → 293行目（1行前のコミット時点から存在する既存警告 `f-string is missing placeholders`。今回変更していない行）以外の新規警告なし
- `python3 -m pyflakes src/*.py` → 他ファイルの既存警告（未使用importなど、いずれも本タスク以前から存在）のみで、`tab1_georef_mixin.py` に起因する新規警告なし

QGIS環境（`qgis.core`/`qgis.PyQt` 等）がこのサンドボックスに存在しないため、`qgis` モジュールに依存する箇所の実行時動作確認・importテストは行えていない。

**重要な注記**: 本修正は統括の調査に基づく仮説（`LayerManager.raster_layer` および `PreviewDialog.raster_layer` がGDALファイルハンドルを保持し続けていることが `[WinError 32]` の追加原因である、という仮説）に対する対応である。実装エージェントはWindows実機でQGISを操作する手段を持たないため、本修正によって実際に `[WinError 32]` が解消するかどうかは確認できていない。人手確認チェックリスト（`.claude/logs/implement/2026-09-15-T-0011-image-rename-winerror32-additional-fix-checklist.md`）に基づき、Windows環境での確認が必須である。

## スコープ外変更の有無
なし。`src/tab1_georef_mixin.py` のみを変更し、依頼文で候補として挙げられていた `layer_manager.py`/`session_io_mixin.py` は、変更不要と判断し手を加えていない（理由は上記「変更していない箇所」参照）。ファイル分割も行っていない（既存ファイル内でのメソッド改修のみ）。`.claude/state/tasks.md` の更新は統括の役割のため本ログでは行っていない。
