## タスクID
T-0041 UX軽微改修4点

## 変更ファイル一覧
- `src/main_dock_dialogs.py`
- `src/main_dock_constants.py`
- `src/tab2_digitizing_mixin.py`
- `src/style_helper.py`

## 変更概要

### ① 解除モードダイアログの点名初期値プリセット
- `tab2_digitizing_mixin.py` に新規メソッド `Tab2DigitizingMixin._get_last_created_point_name(excavation_type, feature_name, is_sp)` を追加。
  - `core_logic.get_next_point_number()` と同じ「出土形態/遺構名でグループ化し、point_id最大（＝直前打刻）のフィーチャを探す」ロジックを踏襲しつつ、次番号を計算する代わりに、そのフィーチャの `point_name` を生の文字列としてそのまま返す。
  - `attribute_type` が SP か否かで対象フィーチャを絞り込み（`PointNameEntryDialog` が表示する入力ウィジェット＝QSpinBoxかSP用QLineEditかと一致させるため）。
  - 一致するフィーチャがなければ `""` を返す。
- `_handle_release_mode_click()` で、`PointNameEntryDialog` 生成直前にこのメソッドを呼び出し、結果を新設の `initial_point_name` 引数として渡すよう変更。
- `PointNameEntryDialog.__init__` に `initial_point_name: str = ""` パラメータを追加。
  - SP属性時: `edit_point_name_sp`（QLineEdit）に非空なら `setText()` でプリセット。
  - 非SP属性時: `spin_point_name`（QSpinBox）に、`initial_point_name` が数字文字列かつ範囲内(`minimum()`〜`maximum()`)であれば `setValue()` でプリセット。数値でない/範囲外/空の場合はデフォルト値（1）のまま。
- 重複となる値がプリセットされた場合でも、既存の `_on_ok_clicked()` の重複チェックがそのままエラー表示する（挙動変更なし、意図通り）。

### ② 重複エラー文言の統一
- `main_dock_constants.py` の `UIMessages` に新規定数 `ERR_POINT_NAME_DUPLICATE = UILabels.STATUS_ERR_DUPLICATE + ": {ident}"` を追加。
  - `UILabels.STATUS_ERR_DUPLICATE`（既存定数 = `"点名重複エラー"`。tab2点情報パネルのリアルタイム重複表示、`_update_point_info_status()` 内で `text = UILabels.STATUS_ERR_DUPLICATE` として使われている）を流用し、同一文言に揃えた。
  - `UILabels` は `main_dock_constants.py` 内で `UIMessages` より前に定義されているため、クラス属性参照は解決可能（`python3 -m py_compile` で構文・インポートエラーがないことを確認済み。値そのものの実行時検証はしていない）。
- `main_dock_dialogs.py` の `PointNameEntryDialog._on_ok_clicked()` で、重複時のエラー表示を `self.lbl_error.setText(ident)` から `self.lbl_error.setText(UIMessages.ERR_POINT_NAME_DUPLICATE.format(ident=ident))` に変更。表示形式は「点名重複エラー: SK01-5 (a)」のようになる想定（`build_point_ident()` の出力形式は変更していない）。
- なお、tab2点情報パネルのリアルタイム重複表示（`_update_point_info_status()`）自体は「ステータス帯に `点名重複エラー` の文言を表示し、識別子はツールチップ（`lbl_point_info_status.setToolTip(tooltip)`）に格納する」という異なる表示方式であり、これは変更していない（今回はプレフィックス文言 `UILabels.STATUS_ERR_DUPLICATE` を共通化することで表現を揃えた）。

### ③ 点名インプットのスピンボックス矢印のつぶれ修正
- 原因特定: `style_helper.py` の `get_style_sheet()` は `QWidget { font-size: 9pt; }` をはじめ、ドック/ダイアログ全体に `UIStyleHelper.apply_theme()` 経由でスタイルシートを適用している。Qtのスタイルシート機構では、いずれかのウィジェットクラスに1つでもQSSルールが存在すると、そのウィジェットツリー配下の全ウィジェット（QSpinBoxを含む）がネイティブ描画ではなくQtのCSSボックスモデルで描画されるようになる。加えて、`QSpinBox` の内部エディタは実体としては通常の `QLineEdit` インスタンスであるため、既存の `QLineEdit, QgsFilterLineEdit, QComboBox { padding: 0px 8px; min-height: 28px; }` ルールがクラスベースの子孫マッチングにより `QSpinBox` の内部エディタにも適用されてしまう一方、`QSpinBox` 自体（外枠と上下ボタン領域）には明示的なスタイルが一切定義されていなかった。この組み合わせにより、CSSエンジンが上下ステップボタンのサブコントロール幅を狭く計算し、矢印がつぶれて見える状態になっていたと推定される。
- 対処: `get_style_sheet()` に `QSpinBox` 専用のルールブロックを新規追加。
  - `QSpinBox { ... padding: 0px 0px 0px 8px; min-height: 28px; ... }`（内部エディタと同等の外観を明示的に定義）
  - `QSpinBox:focus { border: 1.5px solid palette(highlight); }`
  - `QSpinBox::up-button, QSpinBox::down-button { subcontrol-origin: border; width: 18px; ... }` でボタン列の幅を明示的に確保
  - `QSpinBox::up-arrow, QSpinBox::down-arrow { width: 8px; height: 8px; }` で矢印アイコンのサイズを明示
- この修正は `UIStyleHelper.get_style_sheet()`（共通ヘルパー）側での対応であるため、`UIStyleHelper.create_spinbox()` を使う全箇所（`tab2_digitizing_mixin.py` の `edit_point_name`、`start_dialog.py` の `spin_origin_x`/`spin_origin_y`/`spin_range_x_min`/`spin_range_x_max`/`spin_preview_x`、および `QSpinBox` を直接継承する `ExcelColumnSpinBox`）に共通して適用される。個別ウィジェットへの対症療法は行っていない。

### ④ モードトグルと点情報パネルの間の余白削減
- 調査の結果、`tab2_mode_row`（新規/編集モードトグル）と `group_point_info`（点情報パネル、T-0033でタイトルを削除済みのQGroupBox）の間に、個別の `addSpacing()` 呼び出しや `layout.setContentsMargins()` の特別指定は見つからなかった（両者は同じ `layout`＝`layout.setSpacing(UIConfig.PANEL_MARGIN)` の対象で、他の要素間と同じ間隔のはず）。
- 実際の余分な余白の原因は、共通QSSの `QGroupBox, QgsCollapsibleGroupBox { margin-top: 10px; padding-top: 14px; ... }` ルールが、タイトル文字列を持たない `group_point_info` にもタイトル用の予約スペースとして適用され続けていたこと（T-0033のタイトル削除時にQSS側は調整されていなかった）。他のQGroupBox（属性パネル/フォーカスモード/図面選択リストなど）はタイトルがあるため、このmargin/paddingは正当に必要。
- 対処: `group_point_info` にのみ動的プロパティ `titleless=True` を付与し（`setProperty("titleless", True)` + `style().polish()`）、`style_helper.py` に `QGroupBox[titleless="true"] { margin-top: 0px; padding-top: 6px; }` という上書きルールを追加。他のタイトル付きQGroupBoxのスタイルには影響しない、対象を絞った修正とした。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
`python3 -m py_compile src/main_dock_dialogs.py src/main_dock_constants.py src/tab2_digitizing_mixin.py src/style_helper.py src/start_dialog.py` は成功（構文エラーなし）。

## スコープ外変更の有無
なし。上記4ファイル（`src/main_dock_dialogs.py`, `src/main_dock_constants.py`, `src/tab2_digitizing_mixin.py`, `src/style_helper.py`）のみを変更した。
