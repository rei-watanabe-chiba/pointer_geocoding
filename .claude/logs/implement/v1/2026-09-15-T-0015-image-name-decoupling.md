## タスクID
T-0015（設計転換、ユーザー提案採用）: 画像ファイルの物理名を変更しない設計への転換

## 変更ファイル一覧
- `src/tab1_georef_mixin.py`
- `src/session_io_mixin.py`
- `src/main_dock_constants.py`
- `docs/integrated_master_design.md`

## 変更概要

### 1. レイヤ名と画像ファイルの物理名の分離（`src/tab1_georef_mixin.py`）
- 新規追加時、`copy_image_to_session()` を `custom_name` 引数なしで呼ぶように変更。これにより
  `SessionIOMixin.copy_image_to_session()`（`src/session_io_mixin.py`、本タスクでは無変更）の
  「`custom_name` 省略時は `os.path.basename(src_image_path)`（元のファイル名）を使う」という
  既存実装がそのまま活きるようになり、image/ フォルダには常に元のファイル名のまま複製される。
- 新規追加時、コピー先に同名ファイルが既に存在する場合の分岐（従来は `dest_path` が存在すれば
  エラーを握りつぶして処理続行していた特別扱い）を廃止し、`copy_image_to_session()` が返す
  失敗メッセージをそのまま `QMessageBox.warning()` で表示して処理を中断するよう単純化。
- 新規追加時、レイヤ名の重複チェックを「ファイル存在チェックへの依存」から
  「`self.layer_manager.load_image_metadata()` のキー一覧との直接比較」へ変更（新設定数
  `UIMessages.ERR_DUPLICATE_LAYER_NAME` を使用）。元ファイル名が異なっていても、同じレイヤ名を
  持つ2件目の登録はここでブロックされる設計とした。

### 2. 「レイヤ名変更」処理の新設（メタデータキー付け替え + `setName()` のみ、ファイルI/Oなし）
- 新設ハンドラ `_on_rename_layer_clicked()` を追加。処理内容:
  1. 入力検証（空文字チェック、`INVALID_CHARS_PATTERN` チェック、旧名と同名なら何もしない）。
  2. `load_image_metadata()` のキー一覧に対して新名称の重複チェック（重複時はエラーダイアログで中断）。
  3. `QgsProject.instance().layerTreeRoot().findLayers()` から表示名が旧レイヤ名と一致するラスタ
     レイヤを検索し、見つかった場合は `layer.setName(new_name)` のみを呼ぶ（T-0012で確立した
     「表示名一致」ロジックを踏襲。`removeMapLayer()`/レイヤ再生成は一切行わない）。
  4. `meta[new_name] = meta.pop(old_name)` によるメタデータキーの付け替えと `save_image_metadata()`。
  5. `point_layer` の `drawing_name` 属性のうち旧レイヤ名と一致するものを新レイヤ名に更新
     （`startEditing()` → ループで `changeAttributeValue()` → `commitChanges()`、既存パターンを踏襲）。
  6. `_refresh_edit_layer_combo()` で再描画し、新しい名前を選択状態にした上で `_on_edit_layer_changed()`
     を明示的に呼び出して UI（テーブル・情報ラベル等）を同期。
  7. 画像ファイル自体へは一切アクセスしない（コピー・削除・リネームのいずれも発生しない）。
- このハンドラは、旧 `_on_confirm_image_clicked()` の編集モード分岐にあった「リネーム処理」
  （コピー+レイヤ解放+削除等、T-0010〜T-0014で追加されたロジック）を完全に置き換えるものであり、
  設計上ファイルI/Oを一切含まないため、原理的に Windows の `[WinError 32]` は発生し得ない構造と
  なっている（ただし実機での最終確認は別途必須。「人手確認チェックリスト」参照）。

### 3. UI変更（`_create_tab1_ui()`）
- 旧ボタン構成（「確定」＋「レイヤ削除」の横並び1行）を、以下の2行構成に変更:
  - 1行目 `self.row_rename_delete`（`QWidget`+`QHBoxLayout`）: 「レイヤ名変更」ボタン
    （新設 `self.btn_rename_layer`、`_on_rename_layer_clicked()` に接続）＋「削除」ボタン
    （旧 `self.btn_delete_layer` を改称・再利用、`_on_delete_layer_clicked()` のロジックは無変更）。
    新規追加モードでは非表示、編集削除モードでは表示。
  - 2行目: 「基準点設置」ボタン（旧 `self.btn_confirm_image` を改称・再利用、`_on_confirm_image_clicked()`
    に接続）。両モードで常に表示。
- `_on_tab1_mode_changed()` を更新し、モード切替時に `self.row_rename_delete` の `show()`/`hide()` を
  切り替えるようにした（従来の `btn_delete_layer.setEnabled()` による有効/無効化は、行全体の表示/
  非表示に一本化して置き換えた）。

### 4. 「基準点設置」ボタン（旧「確定」）のハンドラ再設計
- `_on_confirm_image_clicked()` の冒頭でモード分岐:
  - **編集削除モード**: 既存の（従来どのボタンにも接続されていなかった）`_on_setup_ref_points_clicked()`
    をそのまま呼び出して即 return するだけに単純化。「現在選択中のレイヤの基準点プレビューを開くだけ」の
    仕様どおり、ファイルI/O・メタデータ更新・レイヤ名変更は一切行わない。
  - **新規追加モード**: 上記1.のとおり、`copy_image_to_session()` の呼び出しから `custom_name` を除去、
    レイヤ名重複チェックをメタデータキー依存に変更した以外は、既存ロジック（基準点データのクリア、
    プレビューキャンバスの自動表示等）を踏襲。

### 5. デッドコードの削除（`src/tab1_georef_mixin.py`）
以下を削除し、伴って不要となった import（`shutil`, `gc`, `time`, `QDomDocument`,
`QgsRasterLayer`, `get_local_crs`, `suppress_crs_prompt`）も削除した:
- `_release_raster_layer_for_rename()`
- `_reload_raster_layer_after_rename()`
- `_remove_with_retry()`
- `UIMessages.MSG_RENAME_OLD_FILE_LEFT`（`src/main_dock_constants.py`）
削除前に、これらのヘルパーが `_on_delete_layer_clicked()` 等の他箇所から参照されていないことを
`grep` で確認済み（削除対象の関数群以外からの参照はゼロだった）。

### 6. セッション開始時点での「画像ファイル」レイヤグループの保証（`src/session_io_mixin.py`）
- `setup_new_session()`: 打刻点レイヤ追加後・`project.write(qgz_path)` 実行前に、
  `project.layerTreeRoot().findGroup("画像ファイル")` が `None` の場合は `addGroup("画像ファイル")`
  を呼ぶ処理を追加。これにより新規セッション作成直後（画像未追加）でもレイヤパネルにグループが
  表示される設計とした。
- `load_existing_session()`: `project.read(qgz_path)` 後・`CRS` 適用直後に同様のチェックを追加。
  画像を一度も追加していない状態で保存された旧セッションを再読込した場合でも、この時点でグループを
  補完し、`project.write(qgz_path)` で永続化するようにした（既存の `load_georeferenced_raster()` 内の
  遅延生成ロジックはそのまま維持しており、変更していない）。

### 7. 定数の追加・削除（`src/main_dock_constants.py`）
- 追加: `UIMessages.ERR_DUPLICATE_LAYER_NAME`（新規追加時・レイヤ名変更時の重複エラー共用）、
  `UIMessages.MSG_RENAME_LAYER_SUCCESS`（レイヤ名変更完了ダイアログ用）。
- 削除: `UIMessages.MSG_RENAME_OLD_FILE_LEFT`（T-0014由来、コピー+best-effort削除方式の
  「旧ファイル削除失敗」通知用だったが、本タスクでファイルI/Oを伴うリネーム処理自体を撤廃したため不要）。
- ボタンラベル文言（「基準点設置」「レイヤ名変更」「削除」）は、既存コードの大半のボタンラベルが
  インライン文字列（例: 旧「確定」「レイヤ削除」も定数化されていなかった）だったパターンに合わせ、
  今回もインライン文字列のまま実装した（定数化は行っていない）。

### 8. 設計書の更新（`docs/integrated_master_design.md`）
- 2.2節「Tab 1: 画像管理と事前ジオリファレンス」のUXフロー記述（旧: 両モードとも「確定」ボタンで
  操作し、編集削除モードでは「確定」がファイル・QGISレイヤ・点群属性連動のリネームを行うという記述）
  を、今回のUI変更・設計転換に合わせて更新した。乖離が実態と大きく異なっていた（ボタン名・処理内容とも
  完全に変わっている）ため、本タスクのスコープに含めて更新することとした。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
代わりに以下の静的チェックを実施した:
- `python3 -c "import ast; ast.parse(...)"` による構文チェック（`src/tab1_georef_mixin.py`）: 成功。
- `python3 -m py_compile src/*.py` による全ファイルのコンパイルチェック: 成功。
- `grep` による削除対象シンボル（`_release_raster_layer_for_rename` 等）の残存参照ゼロを確認。

## スコープ外変更の有無
なし。依頼されたスコープ（`src/tab1_georef_mixin.py` を主対象とし、`src/session_io_mixin.py`
（⑥対応）、`src/main_dock_constants.py`（定数の追加・削除）、`docs/integrated_master_design.md`
（2.2節の記述更新、乖離が大きいと判断したため実施）の範囲内で変更を行った。ファイル分割は行っていない。
「画像ファイル」レイヤグループの手動削除ガードは、依頼どおり対象外として実装していない。

## 実行時挙動に関する注記（重要）
本ログは静的なコード変更内容の記録であり、QGIS上での実際の動作を確認したものではない。
「レイヤ名変更」処理からファイルI/O（コピー・削除・`os.rename()`）を完全に排除したことにより、
設計上は Windows の `[WinError 32]` が発生し得ない構造になっているはずであるが、これは設計上の
理由に基づく期待であり、実機（QGIS上）での最終確認は別途 `.claude/logs/implement/2026-09-15-T-0015-image-name-decoupling-checklist.md`
に基づいて人手で行う必要がある。
