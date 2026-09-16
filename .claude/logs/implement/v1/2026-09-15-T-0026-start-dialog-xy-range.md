## タスクID
T-0026

## 変更ファイル一覧
- `src/start_dialog.py`
- `src/grid_csv_mixin.py`

## 変更概要

### 1. 起動時ダイアログ「グリッド数:」→「X範囲」「Y範囲」への置換
- `src/start_dialog.py` の `StartDialog._init_ui()` にあった単一行「グリッド数:」
  （`self.spin_range_x`/`self.spin_range_y`、いずれも通常の `QSpinBox` min=1,max=300,デフォルト10）を削除し、
  以下2行に置換した。
  - 「X範囲:」行: `self.spin_range_x_min`/`self.spin_range_x_max`（通常の `QSpinBox`、範囲 1〜300、
    デフォルト 最小=1・最大=10）
  - 「Y範囲:」行: `self.spin_range_y_min`/`self.spin_range_y_max`（新設の `ExcelColumnSpinBox`、
    内部整数1〜702を保持しつつ表示・入力は半角英大文字1〜2桁 `A`〜`ZZ`。デフォルト 最小=A(1)・最大=J(10)）
  いずれも既存の `UIStyleHelper.build_flex_row`/`build_child_container` パターンを踏襲し、
  サブラベルとして「最小:」「最大:」を追加した。
- `ExcelColumnSpinBox`（`QSpinBox` サブクラス、`start_dialog.py` 内、`UI_CONFIG`/`MAIN_RATIO` の直後、
  `StartDialog` クラス定義の直前に配置）を新設。
  - `textFromValue()`/`valueFromText()` を `core_logic.to_excel_column`/`from_excel_column` を用いてオーバーライドし、
    内部整数値⇔Excel列名方式の英大文字表記（A, B, …, Z, AA, …, ZZ）の相互変換を行う。
  - `MIN_VALUE=1`, `MAX_VALUE=702`（'ZZ'）で範囲を固定。
  - `validate()` をオーバーライドし、正規表現 `^[A-Za-z]{1,2}$`（既存コードの `HAS_QT_REGEX` 分岐パターンを踏襲し
    `QRegularExpressionValidator`/`QRegExpValidator` を使い分け）でそれ以外の文字列入力を無効化。
- UI定数: `UI_CONFIG["LABELS"]` に `RANGE_X_GROUP`/`RANGE_Y_GROUP`/`RANGE_MIN`/`RANGE_MAX` を追加し
  `RANGE_GROUP` を削除。`UI_CONFIG["MESSAGES"]` に `ERR_RANGE_INVALID` を追加。
  新規に `UI_CONFIG["LIMITS"]` 辞書（`RANGE_X_MIN_VALUE=1`, `RANGE_X_MAX_VALUE=300`,
  `RANGE_X_DEFAULT_MIN=1`, `RANGE_X_DEFAULT_MAX=10`, `RANGE_Y_DEFAULT_MIN=1`, `RANGE_Y_DEFAULT_MAX=10`）を追加し、
  マジックナンバーを定数化した。
- シグナル接続: `spin_range_x.valueChanged`/`spin_range_y.valueChanged` の2本を、新設4スピンボックス
  （`spin_range_x_min`/`spin_range_x_max`/`spin_range_y_min`/`spin_range_y_max`）の `valueChanged` 接続4本に置換
  （いずれも `_update_grid_coordinate_preview` に接続。ダイアログのライフサイクル上、解除処理は既存の他シグナルと同様に
  明示的なdisconnectは行っていない＝既存コードの慣習を踏襲）。
- `_on_grid_csv_changed()`: 既存CSV選択時の有効/無効切り替え対象ウィジェットを新設4つのスピンボックス・4つの
  ラベル（`lbl_range_x_group`/`lbl_range_x_min`/`lbl_range_x_max`/`lbl_range_y_group`/`lbl_range_y_min`/`lbl_range_y_max`）
  に置換。既存CSVからのメタデータ反映も `range_x_min`/`range_x_max`/`range_y_min`/`range_y_max` ベースに変更。

### 2. UIラベルと内部軸の対応関係（XY反転の有無について）
既存の原点座標入力（`spin_origin_x`＝ラベル「X:」、`spin_origin_y`＝ラベル「Y:」）は、
`_update_grid_coordinate_preview()` / `grid_csv_mixin.generate_grid_csv()` において以下のように対応している。
- ラベル「X」（`spin_origin_x`, 数値）→ 内部変数 `gx`（数値の大グリッド番号）→ Survey X（南北）
- ラベル「Y」（`spin_origin_y`, 数値だが `to_excel_column`/`from_excel_column` で英字表記される軸）→
  内部変数 `gy`（英字の大グリッド番号）→ Survey Y（東西）

この対応関係はコード内コメント
`# 【変更不可侵の絶対的ルール】 測量座標系（X軸=南北, Y軸=東西）を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに対応する。`
にある通り、QGISキャンバス座標とSurvey座標の間で軸が入れ替わる設計だが、これは「起動時ダイアログのUIラベル」対「内部ロジックのgx/gy」の対応関係とは別レイヤーの話であり、
UIラベル「X」/「Y」と内部ロジックの `gx`/`gy`（およびそれぞれの座標軸 Survey X/Survey Y）の対応そのものにねじれ・スワップは確認できなかった。
新設の X範囲（`spin_range_x_min`/`max`）は `gx` に、Y範囲（`spin_range_y_min`/`max`）は `gy` に対応させ、
既存の原点座標入力と同じ対応関係を維持した。

### 3. CSV出力ロジックの範囲ベース化
- `src/grid_csv_mixin.py` の `generate_grid_csv()` のシグネチャを
  `(output_path, origin_x, origin_y, range_x, range_y)` から
  `(output_path, origin_x, origin_y, range_x_min, range_x_max, range_y_min, range_y_max)` に変更。
  ループを `range(1, range_x + 1)` / `range(1, range_y + 1)` から
  `range(range_x_min, range_x_max + 1)` / `range(range_y_min, range_y_max + 1)` に変更（両端含む）。
  オフセット計算式 `gx_offset = origin_x - (gx - 1) * 40` / `gy_offset = origin_y + (gy - 1) * 40` は変更せず、
  origin は常に理論上の「1A-00」を表す点として据え置いた（範囲の最小値が1でなくても、原点からのオフセットで計算する）。
- `setup_or_copy_grid_csv()` のフォールバック `grid_config` デフォルト値、および
  `grid_config.get(...)` の読み出しキーを `range_x`/`range_y` から
  `range_x_min`/`range_x_max`/`range_y_min`/`range_y_max`（デフォルト 1/10/1/10）に変更し、
  `generate_grid_csv()` への呼び出し引数を追随させた。
- `StartDialog.get_session_data()` の返却値: `grid_config` 内の `range_x`/`range_y` を
  `range_x_min`/`range_x_max`/`range_y_min`/`range_y_max` に変更。トップレベルの
  `grid_range_x`/`grid_range_y` キーも `grid_range_x_min`/`grid_range_x_max`/`grid_range_y_min`/`grid_range_y_max`
  に変更（NEW/EXISTING両方の分岐）。
- 呼び出し元の洗い出し: `grid_config` を経由する `src/plugin.py`（`session_io_mixin.handle_session_selection`
  経由で `layer_manager.setup_new_session`/`load_existing_session` へ渡す）、`src/session_io_mixin.py`
  （`setup_new_session`/`load_existing_session` から `setup_or_copy_grid_csv` へ渡す）を確認したが、
  いずれも `grid_config` 辞書をそのまま透過的に受け渡すのみで、`range_x`/`range_y` キーへの直接参照は無かったため、
  これらのファイルへの変更は不要だった。トップレベルの `grid_range_x`/`grid_range_y` キーは
  `start_dialog.py` 以外での参照が repo 全体で見つからなかった（未使用の付随情報）ため、
  キー名のみ新命名規則に追随させた。

### 4. プレビュー機能の調整
- `_update_grid_coordinate_preview()` の範囲判定を `1 <= gx <= rx and 1 <= gy <= ry` から
  `rx_min <= gx <= rx_max and ry_min <= gy <= ry_max` に変更し、新設4スピンボックスの値を参照するように変更。
  表示ロジック（`{gx}{display_y}-00座標: X: {px}, Y: {py}` / 範囲外メッセージ）自体は変更していない。

### 5. 既存グリッドCSV読み込み時のメタデータ抽出（`_extract_csv_metadata`）の変更
- 既存セッションのグリッドCSVを選択した際に原点・範囲入力欄へ反映するロジックを、
  「個数（max_gx/max_gy）＋先頭行=原点」という従来の前提から、「範囲の最小値が1/Aとは限らない」前提に対応させた。
  - 全データ行を走査して `min_gx`/`max_gx`/`min_gy`/`max_gy` を計算するように変更。
  - 原点(1A-00)は、CSV中の各行が持つ小グリッド番号（列「小グリッド」、`sx`,`sy`の2桁）を用いて
    `origin_x = coord_x + (gx-1)*40 + sx*4` / `origin_y = coord_y - (gy-1)*40 - sy*4`
    の逆算式で、範囲の先頭が1/Aでなくても正しく理論上の1A-00座標を復元するように変更した
    （従来は「ファイル先頭行の座標＝原点」という誤った前提だったため、範囲最小値が1/A以外の場合は
    このタスクの変更がなければ誤動作していた箇所）。
  - 返却辞書のキーを `range_x`/`range_y` から `range_x_min`/`range_x_max`/`range_y_min`/`range_y_max` に変更。
- `_on_grid_csv_changed()` 側もこの新しいキーに追随。

### 6. 入力バリデーションの追加
- `_validate_and_accept()` に、新規グリッドCSV生成時（既存CSV未指定時）のみ、
  X範囲・Y範囲それぞれについて最小値が最大値を超えていないかのチェックを追加し、
  超えている場合は `UI_CONFIG["MESSAGES"]["ERR_RANGE_INVALID"]` を表示してフォーカスを戻す処理を追加した
  （タスク本文に明示の指示はなかったが、範囲入力を新設したことに伴う自明な入力保護として追加）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
`python3 -m py_compile src/start_dialog.py src/grid_csv_mixin.py` による構文チェックのみ実施し、エラーなし。

## スコープ外変更の有無
なし。変更は `src/start_dialog.py` と `src/grid_csv_mixin.py` の2ファイルのみで、
依頼スコープ（起動時ダイアログのグリッド数→X/Y範囲UI、`generate_grid_csv`の範囲ベース化、
`get_session_data`の返却値変更、プレビュー機能の維持）の範囲内に収まっている。
`src/plugin.py`・`src/session_io_mixin.py` は呼び出し経路の確認のみ行い、変更は不要だった
（`grid_config`辞書を透過的に受け渡すのみのため）。
