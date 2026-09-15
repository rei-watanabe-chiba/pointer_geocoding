## タスクID
T-0012（バグ修正、T-0010/T-0011の追加原因対応）

## 変更ファイル一覧
- `src/tab1_georef_mixin.py`

## 変更概要
`_release_raster_layer_for_rename()` のプロジェクトツリー内ラスタレイヤの一致判定方式を、
`os.path.normpath(layer.source()) == os.path.normpath(file_path)` というファイルパス比較方式から、
安定動作が報告されている削除処理 `_on_delete_layer_clicked()` と同じ `layer.name() == old_name`
（レイヤ表示名での一致判定）方式に変更した。

具体的な変更点:
1. `_release_raster_layer_for_rename(self, file_path: str)` のシグネチャに `old_name: str` 引数を追加し、
   `_release_raster_layer_for_rename(self, file_path: str, old_name: str)` とした。
2. 呼び出し元（`_on_confirm_image_clicked()` のリネーム分岐、既に `old_name = self.combo_edit_layer.currentText()`
   として取得済み）から `self._release_raster_layer_for_rename(old_path, old_name)` の形で `old_name` を渡すよう変更した。
3. 関数内のプロジェクトツリー走査ループの一致判定を `if os.path.normpath(layer.source()) != norm_target: continue`
   から `if layer.name() != old_name: continue` へ置き換えた。依頼内容の通り、ファイルパス比較との AND 条件には
   せず、表示名一致のみの判定に完全に置き換えた。
4. 依頼の方針3に基づき、`PreviewDialog.raster_layer` 側の一致判定（プレビューダイアログのレイヤは
   `プレビュー_<name>` という異なる命名のため、引き続きファイルパス比較を使用する箇所）に、
   `os.path.normpath()` に加えて `os.path.normcase()` を併用する比較へ変更し、堅牢性を高めた
   （Windows でのドライブレター大文字小文字差異等を吸収する意図）。この部分の一致判定ロジック自体
   （ファイルパスベース）は変更していない。
5. 依頼の方針4に基づき、プロジェクトツリー内で `old_name` に一致するレイヤが見つからず
   `released_info` が `None` のまま処理が進むケースに備え、該当箇所（`for` ループ直後）に
   「レイヤが見つからず解放処理がスキップされた」ことを示すコメントを追加した。今後同様の問題を
   再調査する際の手掛かりとして、`layer.name()`/`old_name` をログ出力して確認する等の対応候補を
   コメント内に記載した。
6. 関数のdocstringに、今回の変更理由（統括による原因特定の要旨、および本変更が「仮説への対応」であり
   実機での解消は未検証である旨）を `NOTE (T-0012):` として追記した。

T-0010・T-0011で実装済みの以下のロジックは変更していない（一致判定方法のみを変更し、それ以外は維持）:
- リネーム後のレイヤ再生成時のスタイル/グループ/位置/表示状態の保持・復元
  （`_reload_raster_layer_after_rename()`、`released_info` の内容は変更なし）
- リネーム失敗時のロールバック処理（`_on_confirm_image_clicked()` の `except Exception as e:` ブロック）
- `self.layer_manager.raster_layer` のクリア・復元ロジック（`was_layer_manager_raster` フラグ）
- `QCoreApplication.processEvents()` + `gc.collect()` による防御的対応
- `PreviewDialog.raster_layer` の解放（`clean_up()`）・再セットアップ（`setup_raster()`）対応

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
代わりに `python3 -m py_compile src/tab1_georef_mixin.py`（構文エラーなし）、
`python3 -m ast`（`ast.parse`）によるパース確認、および `python3 -m pyflakes src/tab1_georef_mixin.py`
（本変更箇所に起因する新規の警告なし。既存の警告1件 `f-string is missing placeholders`（294行目、本変更とは
無関係の既存コード）のみ）を実施した。

## スコープ外変更の有無
なし。`src/tab1_georef_mixin.py` の `_release_raster_layer_for_rename()` およびその呼び出し元
（`_on_confirm_image_clicked()` 内のリネーム分岐1箇所）のみを変更しており、それ以外のファイル・関数には
手を入れていない。

## 付記（重要）
本タスクは統括による原因調査（「レイヤ表示名一致判定であれば削除処理と同様に安定動作するはず」という仮説）
への対応であり、Windows実機で実際に `[WinError 32]` が解消するかどうかは、実装エージェント（本セッション）
には確認する手段がない。本変更によって「レイヤ一致判定が一度もマッチしていなかった」という仮説上の問題は
コード上解消されている（削除処理と同じロジックになっている）が、これが実機での事象解消を保証するものではない。
