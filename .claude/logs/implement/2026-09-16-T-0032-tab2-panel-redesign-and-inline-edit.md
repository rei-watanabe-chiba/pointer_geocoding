## タスクID
T-0032（T-0027フォローアップ、大規模改修）

## 変更ファイル一覧
- `src/tab2_digitizing_mixin.py`（主対象。UI構築・イベントハンドラを大幅改修）
- `src/core_logic.py`（`check_point_duplicate`から対象図面フィルタを除去、`build_point_ident`のメッセージ形式変更）
- `src/main_dock_dialogs.py`（`PointRenameDialog`クラスおよび関連未使用import削除）
- `src/main_dock_constants.py`（ラベル文言変更、属性表示マップ・ステータス文言・ボタン文言の新設/削除）
- `src/style_helper.py`（`set_panel_status()`新設、`QLabel[banner="editing"/"error"]`・`QGroupBox[panelStatus=...]`のQSS追加、`set_banner_status()`にunpolish追加）
- `src/main_dock.py`（`update_symbology_opacity()`内の`combo_attribute.currentText()`を`currentData()`に修正。属性コンボが表示専用ラベルを持つようになった副作用の是正）

## 変更概要

### 1. 点情報パネルの再設計
- パネル最上部に状態帯（`lbl_point_info_status`）を新設し、`UIStyleHelper.set_banner_status()`/`set_panel_status()`（新設、`QGroupBox[panelStatus=...]`のQSSでパネル全体の背景色をタグ付け）で新規点作成=青(`info`)／既設点編集=黄(`editing`)／エラー=赤(`error`)を表示。
- 表示項目を「出土形態表示」「点名+枝番表示」「XY座標表示」の3行に整理（旧・属性表示行(`lbl_info_attribute_*`)は削除）。既存の点名/枝番の編集用ウィジェット(`edit_point_name`/`edit_point_name_sp`/`edit_branch_no`)はこの表示のすぐ下に維持。

### 2. リアルタイム判定ロジック
- `_update_point_info_status()`を新設。優先順位「遺構名未指定 > 点名重複」でエラー判定し、状態帯・パネル背景・`btn_rename_point`/`btn_update_attribute`の有効/無効を更新。
- `_is_feature_name_missing()`/`_check_realtime_duplicate()`を新設。出土形態・遺構名・点名・枝番のいずれかの変更時（`valueChanged`/`textChanged`/`currentIndexChanged`）に`_update_point_info_status()`が呼ばれるよう配線（`_on_category_changed`/`_on_point_identity_changed`/`_on_branch_text_changed`経由）。
- エラー時は`_on_canvas_clicked`・`_on_rename_point_clicked`・`_on_update_attribute_clicked`の確定処理を早期returnでブロック。

### 3. 重複判定ロジックの変更
- `core_logic.check_point_duplicate()`から`drawing_name`による絞り込みを削除（出土形態＋遺構名＋点名＋枝番のみで判定。`drawing_name`引数はシグネチャ互換のため残置）。
- `core_logic.build_point_ident()`のメッセージ形式を変更: `識別子`の後に改行し`図面:[drawing_name]`（15文字超は末尾省略+`...`）を付加。新規打刻フロー・既設点編集フローとも`_check_realtime_duplicate()`経由で共通利用。

### 4. QMessageBox/PointRenameDialogの廃止
- 新規打刻の重複エラーQMessageBox・`PointRenameDialog`（クラスごと削除）を廃止。
- `btn_rename_point`（「点名変更」ボタン）を、入力中の点名・枝番をそのままフィーチャへコミットするボタンとして再実装（ダイアログなし）。
- `_CATEGORY_LOCK_WIDGET_NAMES`を`("combo_drawing_name",)`のみに縮小し、既設点編集中も出土形態/遺構名/属性/点名/枝番を直接編集可能化。

### 5. 既設点編集での属性系編集許可
- 属性パネルに既設点編集時のみ表示される「属性変更」ボタン(`btn_update_attribute`)を新設。出土形態・遺構名・属性記号のみをコミットし、`commitChanges()`→`triggerRepaint()`後に`update_symbology_opacity()`を呼び出し。
- `_on_category_changed()`は既設点編集中(`selected_edit_point_id is not None`)のとき自動採番をスキップし、`_update_point_name_widget_visibility()`のみ呼び出すよう分岐。

### 6. 属性パネルのラベル・レイアウト変更
- 「遺構名セレクタ:」→「遺構名:」、「属性記号:」→「属性:」。
- `combo_attribute`の表示文言を「S:石器」「P:土器」「C:炭化物」「SP」に変更（`itemData`に内部値を保持、`_get_attribute_value()`/`_set_attribute_value()`で読み書き）。
- 「作成」ボタンとカラーボタンを別行(`row_feature_actions`)に分離し1:1幅比率で配置。カラーボタンは常時表示、`btn_color_picker.setEnabled(is_feature and not is_placeholder)`のみ切替。
- `FeatureCreateDialog`成功後の自動`_pick_color()`呼び出しを削除。
- ウィジェット順序を「属性→出土形態→遺構名→(作成・カラー行)→対象図面→(既設点編集時)属性変更ボタン」に変更。

### 7. 属性確定ボタンの廃止と「更新」ボタンの新設
- `btn_confirm_attribute`を削除。フォーカスモードパネルの透明度スライダー横に`btn_update_attribute`ならぬ`btn_update_opacity`（「更新」）を新設し、スライダー:ラベル:ボタン = 2:0:1 相当の幅配分（`build_flex_row`の`stretch`指定）で配置。押下時の処理(`_on_update_opacity_clicked`)は旧`_confirm_attribute_transparency`のロジックを移植。

### 副次対応
- `combo_attribute`が表示専用ラベルを持つようになったため、`main_dock.py`の`update_symbology_opacity()`内フィルタ構築部を`currentText()`→`currentData()`に修正（属性フィルタが正しい内部値で機能するようにするための必須の連鎖修正）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンド未設定のため未実施）。
`python3 -m pyflakes` による静的構文チェックを実施し、変更対象ファイル群および`src/`全体で
未定義名・構文エラーなし（既存の無関係な未使用import警告3件のみ、いずれも本タスクの変更箇所外）。

## スコープ外変更の有無
なし。変更は依頼スコープに明記された`src/tab2_digitizing_mixin.py`・`src/main_dock_dialogs.py`・
`src/core_logic.py`・`src/main_dock_constants.py`・`src/style_helper.py`のみ。ただし`src/main_dock.py`
（依頼スコープの明示リストになし）を1箇所のみ修正した。これは`combo_attribute`の表示文言変更
（依頼項目6）に伴い、同コンボの`.currentText()`を直接参照していた`update_symbology_opacity()`の
属性フィルタが機能しなくなる（フォーカスモードの属性別絞り込みが常に不一致になる）ため、本タスクの
変更が引き起こす直接的な副作用の是正として必須と判断し実施した。念のためここに明記する。
