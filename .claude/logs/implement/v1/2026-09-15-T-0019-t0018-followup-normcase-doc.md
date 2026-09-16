## タスクID
T-0019（T-0018フォローアップ、verifierの非ブロッキング指摘2件の解消）

## 変更ファイル一覧
- `src/tab1_georef_mixin.py`
- `docs/integrated_master_design.md`

## 変更概要

### ①`os.path.normcase()`の追加（`src/tab1_georef_mixin.py`）
`_on_export_layer_clicked()`内の「未複製判定」ロジック（T-0018で追加、`_on_export_layer_clicked()`冒頭付近、
`self.current_copied_image_path` の妥当性確認直後の箇所）で、`session_image_dir`とカレントディレクトリの
パス比較を行っている部分に`os.path.normcase()`を追加した。

変更前:
```python
session_img_dir = self.layer_manager.session_image_dir
current_dir = os.path.normpath(os.path.dirname(self.current_copied_image_path))
already_in_session = bool(session_img_dir) and current_dir == os.path.normpath(session_img_dir)
```

変更後:
```python
session_img_dir = self.layer_manager.session_image_dir
current_dir = os.path.normcase(os.path.normpath(os.path.dirname(self.current_copied_image_path)))
already_in_session = bool(session_img_dir) and current_dir == os.path.normcase(
    os.path.normpath(session_img_dir)
)
```
併せて、T-0012（`.claude/logs/implement/2026-09-15-T-0012-image-rename-layer-match-fix.md`）で確立された
`normpath()`+`normcase()`併用パターンとの一貫性を示すコメントを追加した。ロジック自体（比較結果の使われ方、
分岐先の挙動）は変更していない。

なお、T-0018のdiff（`git show dc1f4dc -- src/tab1_georef_mixin.py`）を再確認し、同コミットで追加・変更された
他のファイルパス関連処理（`os.path.isfile()`によるワールドファイル存在チェック、`os.path.splitext()`による
拡張子分離等）は、いずれも「別々に取得した2つのパス文字列同士の一致判定」ではなく存在確認・分解処理であり、
`normcase`の適用対象に該当しないことを確認した。よって追加対応は本箇所1件のみとした。

### ②設計書の追随更新（`docs/integrated_master_design.md`）
126行目付近（「2.2 Tab 1: 画像管理と事前ジオリファレンス」の新規追加モードの説明）を、T-0018での実装変更
（画像のセッションへの複製タイミングを「基準点設置」時点から「レイヤ出力」完了時点へ遅延させた変更）に
合わせて更新した。

変更前:
> 2. **新規追加モード**: 画像ファイルを選択・レイヤ名を入力し、「基準点設置」をクリック。画像は元のファイル名のまま
> （レイヤ名とは独立に）セッションにコピーされ、同時にプレビューダイアログが起動する（T-0015: 画像ファイルの
> 物理名はレイヤ名変更に追従しない設計に転換）。

変更後:
> 2. **新規追加モード**: 画像ファイルを選択・レイヤ名を入力し、「基準点設置」をクリック。この時点では画像はまだ
> セッションへコピーされず、選択された元ファイルをそのまま参照してプレビューダイアログが起動する（画像ファイルの
> 物理名はレイヤ名変更に追従しない設計。T-0015）。選択した元画像に既存のワールドファイルが付随している場合は、
> 本プラグインが生成する変換結果との整合性が取れなくなるため、「基準点設置」の時点でエラー表示し処理を拒否する
> （この制約は新規追加モードのみが対象で、次項の編集削除モードにおける既存レイヤの「基準点設置」〈基準点再編集〉
> には適用されない）。画像の `image/` フォルダへの複製は、後述の「座標変換」→「レイヤ出力」完了時点で、
> ワールドファイルの生成と合わせて行われる（T-0018）。

依頼内容に基づき以下を反映した:
- 「基準点設置」時点ではセッションへのコピーを行わず元画像を直接参照する、という実態
- 元画像に既存ワールドファイルが付随する場合の拒否仕様（新規追加モードのみ対象、編集削除モードの
  「基準点設置」〈基準点再編集〉は対象外である旨を明記）
- 画像のセッション複製とワールドファイル生成が「レイヤ出力」完了時点にまとめて行われる旨

129行目（「レイヤ出力」でワールドファイルを生成・上書き）、137行目付近の記述は依頼通り変更していない
（既存記述と矛盾しないため）。見出し構成・箇条書き構造・記述トーンは変更していない（当該1項目の文面のみ更新）。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
代わりに以下の静的確認を実施した:
- `python3 -m py_compile src/tab1_georef_mixin.py` — 構文エラーなし
- `python3 -m pyflakes src/tab1_georef_mixin.py` — 本変更箇所に起因する新規警告なし
  （既存の警告1件 `f-string is missing placeholders`、332行目、本変更とは無関係の既存コード）
- `git show dc1f4dc -- src/tab1_georef_mixin.py` によるT-0018 diffの再確認 — 今回の`normcase`追加対象が
  唯一の該当箇所であることを確認

## スコープ外変更の有無
なし。`src/tab1_georef_mixin.py`の`_on_export_layer_clicked()`内の1箇所（既存の未複製判定ロジックへの
`normcase`追加のみ）と、`docs/integrated_master_design.md`の該当1項目のみを変更しており、それ以外の
ファイル・関数・記述には手を入れていない。
