## タスクID
T-0018（バグ修正）: 画像追加/削除まわりのガード不足（人手確認で発見）

## 変更ファイル一覧
- `src/tab1_georef_mixin.py`
- `src/main_dock_constants.py`

## 変更概要

### ①-1 画像複製タイミングの遅延化（新規追加モード）
- `_on_confirm_image_clicked()`（新規追加モード分岐）内で、これまで押下直後に呼んでいた
  `self.layer_manager.copy_image_to_session(src_path)` の呼び出しを削除し、代わりに
  `self.current_copied_image_path = src_path`（選択されたオリジナルファイルのパスそのまま）を
  設定するように変更した。プレビューダイアログは既存の `_create_preview_canvas(self.current_copied_image_path)`
  呼び出しをそのまま使い、オリジナルパスを直接参照して開く。
- `_on_export_layer_clicked()` の冒頭（ワールドファイル書き込み `write_world_file()` 呼び出しより前）に、
  `self.current_copied_image_path` が `self.layer_manager.session_image_dir` 配下にまだ存在しない
  （＝オリジナルパスのまま）かどうかを `os.path.dirname()` の比較で判定するロジックを追加し、
  未複製と判定した場合にその場で `copy_image_to_session()` を実行し、`self.current_copied_image_path` を
  複製先の新しいパスへ更新してから、以降のワールドファイル書き込み・メタデータ更新処理へ進むようにした。
  複製に失敗した場合はエラーダイアログ（`QMessageBox.critical`）を表示して処理を中断する
  （この時点ではまだセッションに何も書き込んでいないためロールバック処理は追加していない）。
- 編集削除モード側（`_on_edit_layer_changed()` がメタデータから設定する `current_copied_image_path`）は
  常にセッション内の複製済みパスを指すため、上記の判定により `already_in_session=True` となり、
  複製処理はスキップされる（新規追加モードのみが対象であることをコードコメントで明記した）。
- `_on_export_layer_clicked()` 冒頭にあった、`current_copied_image_path` が無効な場合に
  `os.path.splitext(f)[0] == layer_name` でセッション`image/`フォルダ内を検索するフォールバックロジック
  （935〜944行目付近、T-0015以前のファイル名=レイヤ名前提の名残）を削除した。判断根拠:
  T-0015でファイル名とレイヤ名が分離されて以降、このマッチングは本質的に不正確であったこと、
  かつ「レイヤ出力」ボタンは「座標変換」成功後にのみ有効化されるため、この関数に到達する時点では
  `current_copied_image_path` は必ず `_on_confirm_image_clicked()`（新規追加、オリジナルパス）または
  `_on_edit_layer_changed()`（編集削除、メタデータ由来の複製済みパス）のいずれかによって正しく
  設定されているはずであり、このフォールバックは事実上到達不能であったこと、さらに今回の変更で
  複製前はファイルがそもそもセッションフォルダに存在しないため新規追加モードでは無意味になることから、
  削除して「パスが無効なら明確なエラーを出す」という単純な形に統一した。

### ①-2 既存ワールドファイルの拒否
- `_on_confirm_image_clicked()`（新規追加モード）の入力検証（`src_path` の存在確認の直後、複製処理より前）に、
  選択元画像と同じベース名を持つワールドファイル（`.tfw`, `.jgw`, `.pgw`, `.bpw`, `.wld`）が
  元画像と同じディレクトリに存在するかをチェックするロジックを追加した。存在する場合は
  `UIMessages.ERR_SOURCE_HAS_WORLDFILE`（新規追加した文言定数、`src/main_dock_constants.py`）を
  表示して処理を中断し、画像の複製・登録は一切行わない。
- ワールドファイル拡張子リストは、`_on_delete_layer_clicked()` 内の既存リストと重複させないよう
  モジュールレベル定数 `WORLD_FILE_EXTENSIONS = (".tfw", ".jgw", ".pgw", ".bpw", ".wld")` として
  `tab1_georef_mixin.py` 先頭付近に新設し、新規チェックと `_on_delete_layer_clicked()` の既存の
  ワールドファイル削除ループの両方から参照するようリファクタリングした（値は変更していない）。

### ② 編集削除: キャンバス再描画・ゴースト画像ガード・ボタン無効化
- `_on_delete_layer_clicked()` 内、`project.removeMapLayer(l.id())` の直後に `self.canvas.refresh()` を
  追加し、レイヤ削除がキャンバスへ即座に反映されるようにした。
- 同関数内、メタデータ・ファイル削除完了後に `self._destroy_preview_canvas()`
  （内部で `PreviewDialog.clean_up()` を呼び `raster_layer` を `None` にリセットする既存メソッド）を
  無条件に呼び出し、プレビューダイアログを都度後片付けするようにした。
- `_on_edit_layer_changed()` の早期return（コンボボックスが空 = 画像0件の場合）ブロック内に
  `self.current_copied_image_path = None` を追加した（`main_dock.py` での宣言 `Optional[str] = None` と
  型・デフォルト値を合わせた）。これにより、画像0件になった後に古いパスが有効と誤判定されて
  ゴースト画像プレビューが開いてしまう経路を塞いだ。
- 新規ヘルパー `_update_edit_mode_button_states()` を追加した。編集削除モードでは
  `self.layer_manager.load_image_metadata()` が空の場合に `btn_rename_layer` / `btn_delete_layer` /
  `btn_confirm_image` の3ボタンを `setEnabled(False)` にし、画像が1件以上あれば有効化する。
  新規追加モードでは `btn_confirm_image` を常に有効化する
  （`btn_rename_layer`/`btn_delete_layer` は新規追加モードでは非表示行 `row_rename_delete` に含まれるため
  このヘルパーでは触れていない）。
  呼び出しタイミングは (a) `_on_tab1_mode_changed()` の末尾（新規追加/編集削除いずれのモード切替時にも
  共通で呼ばれるようにした）、(b) `_on_delete_layer_clicked()` の削除完了・コンボ再描画後。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
`python3 -m py_compile src/*.py` による構文チェックのみ実施し、エラーなし。

## スコープ外変更の有無
コードの変更としてはスコープ外の変更は行っていない（`src/tab1_georef_mixin.py` と、そこから参照する
文言定数1件を追加した `src/main_dock_constants.py` のみ）。

ただし、ドキュメントとの整合性について1点、統括側での判断・対応が必要な差分を発見したため、
実装は行わずここに記載する:
`docs/integrated_master_design.md` の126行目付近に「画像は元のファイル名のまま（レイヤ名とは独立に）
セッションにコピーされ、同時にプレビューダイアログが起動する（T-0015: ...）」という記述があるが、
これは今回の①-1の変更（複製タイミングを「基準点設置」時から「レイヤ出力」完了直前へ遅延）により、
新規追加モードでは事実と異なる記述になった（現在は「基準点設置」時点ではまだコピーされない）。
設計書本文の更新はスコープ外（対象は `src/tab1_georef_mixin.py` 中心、かつ本タスクの依頼文に
`docs/` 編集の指示はない）と判断し、コードのみを変更した。設計書側の追随更新要否は統括の判断を仰ぎたい。
