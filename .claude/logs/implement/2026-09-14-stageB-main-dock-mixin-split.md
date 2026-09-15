## タスクID
Stage B: main_dock.py のMixinベース分割

## 変更ファイル一覧
- `src/main_dock.py`（更新・大幅縮小: 3,088行 → 308行）
- `src/main_dock_constants.py`（新規: 193行）
- `src/main_dock_dialogs.py`（新規: 428行）
- `src/tab1_georef_mixin.py`（新規: 971行）
- `src/tab2_digitizing_mixin.py`（新規: 993行）
- `src/tab3_settings_mixin.py`（新規: 381行）
- `docs/integrated_master_design.md`（更新: §1.3 ディレクトリ構成ツリー、§1.4 モジュール構成と役割 に新規ファイルの説明を追加・既存main_dock.py説明をMixin構成に合わせて改訂）

## 変更概要
指示書（実装依頼メッセージ）に記載された分割方針に厳密に従い、`main_dock.py`（旧3,088行、`MainDockWidget`クラス1つに全タブのUI構築・イベント処理が同居）を以下の方針で機械的に分割した。ロジック（条件分岐・計算式・文字列・シグナル接続等）は一切変更せず、コードの物理的な移動とimport文の追加・整理のみを行った。

1. **`main_dock_constants.py`**: `UIConfig` / `UILabels` / `UIPlaceholders` / `UIDialogTitles` / `UIMessages` の5クラスと、それらから派生するモジュール変数 `MAIN_RATIO`（元のファイルで `UIConfig` の直後・`PreviewDialog` の直前に定義されていたもの）をそのまま移動。QGIS/PyQt標準ライブラリにも一切依存しない純粋な定数モジュールとした（循環import回避）。

2. **`main_dock_dialogs.py`**: `PreviewDialog` / `TwoDigitSpinBox` / `GridInputDialog` の3クラスをそのまま移動。`main_dock_constants`・`style_helper`・`core_logic`・`map_tool`（`ImageGeorefTool`）にのみ依存させ、`main_dock.py`や各Tab Mixinには依存させていない。

3. **`tab1_georef_mixin.py`**: `Tab1GeorefMixin` として、依頼書に列挙された20メソッド（`_create_tab1_ui` 〜 `_on_execute_georef_clicked`）をそのまま移動。`__init__`は定義していない。

4. **`tab2_digitizing_mixin.py`**: `Tab2DigitizingMixin` として、依頼書に列挙された32メソッド（`_create_tab2_ui` 〜 `_on_export_csv_clicked`）をそのまま移動。

5. **`tab3_settings_mixin.py`**: `Tab3SettingsMixin` として、依頼書に列挙された5メソッド（`_create_tab3_ui` 〜 `_on_layer_manager_settings_changed`）をそのまま移動。

6. **`main_dock.py`**: `class MainDockWidget(QDockWidget, Tab1GeorefMixin, Tab2DigitizingMixin, Tab3SettingsMixin):` に変更し、依頼書指定の「共通基盤」9メンバのみを残した: `__init__`、`preview_canvas`/`preview_raster_layer`/`georef_tool`（後方互換プロパティ）、`_init_ui`、`_on_tab_changed`、`_save_project`、`closeEvent`、および Tab2/Tab3 双方から呼ばれる共有メソッド `update_symbology_opacity`（指示通りどちらのMixinにも入れず本体に残置）。

### 抽出手順（機械的移動の方法）
- 元ファイルの行番号ベースで各メソッド（デコレータ・直前のセクションコメント行を含む）の開始/終了位置を特定し、Pythonスクリプトで該当行範囲をテキストのまま切り出して移動先ファイルへ配置した（手動での再入力によるロジック改変リスクを排除するため）。
- `@property`（3件）、`@pyqtSlot(...)`（4件: `_on_preview_canvas_point_clicked`, `_on_new_feature_text_changed`, `_on_branch_text_changed`, `_on_existing_point_selected`）の各デコレータ行、およびタブの切れ目を示すセクションコメントブロック（例: `# === Tab 1: ... Handlers ===`）は、直後のメソッドと同じファイルへ一緒に移動した。

### 各ファイルのimport整理
- 各ファイル本文で実際に使用されている識別子（モジュール、`qgis.core`/`qgis.gui`/`qgis.PyQt.*`クラス、`.map_tool`/`.transform`/`.style_helper`/`.core_logic`/`.main_dock_constants`/`.main_dock_dialogs`のシンボル）を洗い出し、過不足なく`import`文を用意した。
- `main_dock_dialogs.py` と `main_dock_constants.py` は、指示書の「循環import注意」に従い、`main_dock.py`や各Tab Mixinへは依存させていない（`main_dock_dialogs.py`は`map_tool.py`・`style_helper.py`・`core_logic.py`・`main_dock_constants.py`にのみ依存）。

### 追加で判明した後方互換上の必須対応（スコープ内での最小限の対応）
`src/layer_manager.py` と `src/map_tool.py` は、それぞれの関数内でローカルに `from .main_dock import UIConfig` を実行している（本分割対象外のファイル）。分割前は `main_dock.py` が `UIConfig` をトップレベルで定義していたためこのimportは成立していたが、分割後は `UIConfig` が `main_dock_constants.py` に移動するため、`main_dock.py` が単に他Mixinをまとめるだけの構成のままだと `main_dock.UIConfig` という名前バインディングが消滅し、上記2ファイルの `from .main_dock import UIConfig` が `ImportError` になる。
これは `layer_manager.py`/`map_tool.py` を一切変更せずに済む、`main_dock.py`（本タスクの対象ファイル）側だけで解決可能な問題であるため、`main_dock.py` の冒頭import部に `from .main_dock_constants import UIConfig, UILabels, UIMessages` として `UIConfig` を再exportする形で対応した（コメントで意図を明記）。`main_dock.py`自身の本体コードは`UIConfig`を直接使用しないため、静的解析上は「未使用import」として検出されるが、既存の外部依存契約（`layer_manager.py`・`map_tool.py`からの参照）を壊さないための意図的な再exportである。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。

代わりに以下の静的検証を実施した:
1. `python -m py_compile` を新規/変更した6ファイル（`main_dock.py`, `main_dock_constants.py`, `main_dock_dialogs.py`, `tab1_georef_mixin.py`, `tab2_digitizing_mixin.py`, `tab3_settings_mixin.py`）に対して実行し、構文エラーがないことを確認した（全て成功）。さらに `src/*.py` 全体（他の既存ファイルを含む）でも `py_compile` を実行し、既存ファイルに構文的な副作用がないことを確認した（全て成功）。
2. 独自に作成したASTベースの自由変数検査スクリプトで、各ファイル内で参照されている識別子（`Name`ノード、`Load`コンテキスト）のうち、import文・関数/ラムダ引数・代入・クラス定義・組み込み関数（`builtins`）のいずれにも該当しないものが存在しないことを確認した（6ファイターすべて `missing candidates: []`）。ただしこれはモジュールレベルの粗い静的チェックであり、QGIS/PyQtの実行時の属性・シグナル解決までは検証できない。
3. 同じくASTベースで未使用import（importしたが`Name`ノードとして参照されていない識別子）を検査した。`tab2_digitizing_mixin.py` で未使用だった `typing.Optional` を削除した。`main_dock.py` の `UIConfig` は上記の後方互換上の理由により意図的に未使用のまま残している。
4. 移動前後でのメソッド名集合の突き合わせ:
   - 元の `main_dock.py`（分割前、3,088行）を `grep -n "^class |^    def "` で走査し、`MainDockWidget`クラス内の66メンバ（`__init__` 1、`@property` 3、通常メソッド62）を確認。内訳は 依頼書の「共通基盤」9 + Tab1向け20 + Tab2向け32 + Tab3向け5 = 66 で一致。
   - `PreviewDialog`（7メソッド）、`TwoDigitSpinBox`（2メソッド）、`GridInputDialog`（8メソッド、`__init__`含む）は移動前後で変化なし（`main_dock_dialogs.py`へそのまま移動）。
   - 分割後の各ファイルを同様に `grep -n "^class |^    def "` で走査し、`main_dock.py`=9、`tab1_georef_mixin.py`=20、`tab2_digitizing_mixin.py`=32、`tab3_settings_mixin.py`=5、`main_dock_dialogs.py`=17（3クラス分の全メソッド）となり、欠落・重複がないことを確認した。

## スコープ外変更の有無
あり（軽微・最小限）。`src/layer_manager.py` と `src/map_tool.py` は編集していないが、上記「追加で判明した後方互換上の必須対応」に記載の通り、これら2ファイルが `from .main_dock import UIConfig` に依存している事実を把握した。この依存を壊さないよう、対象ファイルである `main_dock.py` 内で `UIConfig` を再exportする形にとどめ、`layer_manager.py`・`map_tool.py` 自体への変更は一切行っていない。これにより本来のスコープ（`main_dock.py`分割関連ファイルのみ）を逸脱していない。
それ以外に、依頼書に明記されていない追加のファイル変更・機能変更は行っていない。
