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

#### ③のフォローアップ修正（本追記時点）
- 実機確認の結果、上記の初回対処後は「矢印つぶれ」ではなく「ボタン領域は確保されているが矢印グリフ自体が非表示（空白）」という別の症状であることが判明した。
- 原因の再分析: `QSpinBox::up-button, QSpinBox::down-button` に `background-color`/`border-left` 等のカスタムQSSを指定すると、Qtのスタイルエンジンはそのサブコントロールに対してネイティブの矢印プリミティブ（`PE_IndicatorSpinUp`/`PE_IndicatorSpinDown`）の自動描画を行わなくなる場合がある。既存の `QSpinBox::up-arrow, QSpinBox::down-arrow { width: 8px; height: 8px; }` はサイズを指定しているのみで、実際に描画する `image` プロパティやボーダーを指定していなかったため、矢印の占有領域だけが確保され中身が描画されない状態になっていたと考えられる。
- 対処: `QSpinBox::up-arrow, QSpinBox::down-arrow { width: 8px; height: 8px; }` の1ブロックを削除し、代わりに `QSpinBox::up-arrow` と `QSpinBox::down-arrow` をそれぞれ個別ルールとして新設。border-triangleトリック（`width: 0px; height: 0px;` の箱に、進行方向と垂直な2辺を `transparent` の `border-left`/`border-right`（4px）、矢の向いた1辺を `palette(text)` の `border-bottom`（up-arrow）/`border-top`（down-arrow）（5px）として指定）により、スタイルエンジンやOSテーマに依存せず三角形を明示的に描画するようにした。`image: none;` を明示し、既存の空画像由来の表示崩れの可能性を排除。また `subcontrol-origin: border; subcontrol-position: top right;`（up-arrow）/`bottom right;`（down-arrow）を対応する `::up-button`/`::down-button` と同じ位置指定で明示し、矢印サブコントロールの配置がデフォルトの中央寄せ等で見えなくなることを防いだ。
- サイズ確認: `::up-button`/`::down-button` の `width: 18px` に対し、三角形の横幅は `border-left 4px + border-right 4px = 8px` であり、既存の18px枠内に収まるため `width: 18px` 自体の変更は行っていない。
- 変更範囲は `src/style_helper.py` の該当QSSブロック（旧 `QSpinBox::up-arrow, QSpinBox::down-arrow { width: 8px; height: 8px; }` の置き換え）のみ。①②④のスコープには触れていない。

### ④ モードトグルと点情報パネルの間の余白削減
- 調査の結果、`tab2_mode_row`（新規/編集モードトグル）と `group_point_info`（点情報パネル、T-0033でタイトルを削除済みのQGroupBox）の間に、個別の `addSpacing()` 呼び出しや `layout.setContentsMargins()` の特別指定は見つからなかった（両者は同じ `layout`＝`layout.setSpacing(UIConfig.PANEL_MARGIN)` の対象で、他の要素間と同じ間隔のはず）。
- 実際の余分な余白の原因は、共通QSSの `QGroupBox, QgsCollapsibleGroupBox { margin-top: 10px; padding-top: 14px; ... }` ルールが、タイトル文字列を持たない `group_point_info` にもタイトル用の予約スペースとして適用され続けていたこと（T-0033のタイトル削除時にQSS側は調整されていなかった）。他のQGroupBox（属性パネル/フォーカスモード/図面選択リストなど）はタイトルがあるため、このmargin/paddingは正当に必要。
- 対処: `group_point_info` にのみ動的プロパティ `titleless=True` を付与し（`setProperty("titleless", True)` + `style().polish()`）、`style_helper.py` に `QGroupBox[titleless="true"] { margin-top: 0px; padding-top: 6px; }` という上書きルールを追加。他のタイトル付きQGroupBoxのスタイルには影響しない、対象を絞った修正とした。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
`python3 -m py_compile src/main_dock_dialogs.py src/main_dock_constants.py src/tab2_digitizing_mixin.py src/style_helper.py src/start_dialog.py` は成功（構文エラーなし）。
（③フォローアップ追記時点）`python3 -m py_compile src/style_helper.py` を再実行し成功。

## スコープ外変更の有無
なし。上記4ファイル（`src/main_dock_dialogs.py`, `src/main_dock_constants.py`, `src/tab2_digitizing_mixin.py`, `src/style_helper.py`）のみを変更した。
