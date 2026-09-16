## タスクID
T-0016, T-0017

## 変更ファイル一覧
- `src/main_dock_constants.py`
- `src/core_logic.py`
- `src/symbology_mixin.py`
- `src/map_tool.py`
- `src/tab2_digitizing_mixin.py`
- `src/tab3_settings_mixin.py`

## 変更概要

### T-0016: 軽微な文言修正
前回セッションの時点で `src/main_dock_constants.py` の `UIMessages.MSG_CONFIRM_IMAGE_FIRST` は
`"編集対象のレイヤを選択してから「基準点設置」を実行してください。"` に修正済み（未コミット状態）だった。
本セッションでは、唯一の呼び出し元である `src/tab1_georef_mixin.py` の `_on_setup_ref_points_clicked()`
（`current_copied_image_path` が未設定/実ファイルなしの場合にこのメッセージを表示する）と、
`current_copied_image_path` を設定する `_on_edit_layer_changed()`（編集削除モードでコンボボックスに
レイヤ未選択の場合は `current_copied_image_path` が空のまま）を実コードで再確認し、修正後の文言が
新規登録モード・編集削除モードいずれの未選択ケースにも妥当な説明になっていることを確認した。
コード変更は行わず、既存の修正内容をそのまま採用した。

### T-0017: 第3フェーズ アプローチC+A

#### アプローチC: シンボロジ操作の統合
`src/map_tool.py` の `CanvasDigitizingTool` が保持していた以下3つの静的メソッドを
`src/symbology_mixin.py` の `SymbologyMixin` へ移設した（本文のロジックは変更なし、そのまま移動）。

- `setup_point_layer_symbology()` → `SymbologyMixin.apply_point_symbology()`
  （打刻点のS/P/C/SPカテゴリシンボル + ラベリングを一括構築。`apply_point_labeling`/
  `apply_ref_point_symbology` と同じ命名規則 `apply_*` に統一するため改名）
- `setup_ref_point_layer_symbology()` → `SymbologyMixin.apply_ref_point_cross_symbology()`
  （メインキャンバス向け基準点クロスシンボル。既存の `apply_ref_point_symbology`（CSV由来の
  基準点レイヤ・ルールベースレンダラ）とは別物であるため、両者の役割の違いをdocstringに明記した。
  移設時点で呼び出し元ゼロの未使用メソッドだったが、デッドコード削除は本タスクの依頼範囲外のため
  挙動を変えずにそのまま移設した）
- `update_attribute_transparency()` → `SymbologyMixin.apply_attribute_transparency()`
  （こちらも移設時点で呼び出し元ゼロの未使用メソッド。同様にそのまま移設）

`map_tool.py` 側は上記3メソッドの定義を削除し、代わりに `self.layer_manager` 経由で
`apply_point_symbology()` を呼び出す形に変更した（`CanvasDigitizingTool.__init__` および
`src/tab3_settings_mixin.py` の `_on_layer_manager_settings_changed()` の2箇所）。
`tab3_settings_mixin.py` はもともと同メソッド内で `self.layer_manager.apply_ref_point_symbology(...)`
を呼んでいたため、点シンボロジの呼び出しも同じ「`layer_manager` 経由」のスタイルに揃え、
不要になった `from .map_tool import CanvasDigitizingTool` のローカルインポートを削除した。

`map_tool.py` からメソッド本体を削除したことで不要になった以下のimportも合わせて削除した
（削除前は本体で使用されていたが、移設後は同ファイル内で一切参照されなくなったため）:
`QgsCategorizedSymbolRenderer` / `QgsRendererCategory` / `QgsMarkerSymbol` /
`QgsSimpleMarkerSymbolLayer` / `QgsSymbolLayer` / `QgsProperty` / `QgsPalLayerSettings` /
`QgsVectorLayerSimpleLabeling` / `QgsTextFormat` / `QgsTextBufferSettings` / `Qgis` /
`from .symbology_mixin import SymbologyMixin`。
なお `QgsProject` / `QgsFeatureRequest` / `QgsCoordinateReferenceSystem` / `QgsSymbol` は
今回の変更前から既に本文未使用だったことをgit差分の照合で確認済みであり、これらは
本タスクの変更に起因しない既存の状態のため、スコープ外として一切手を加えていない。

`symbology_mixin.py` 側は移設に伴い必要な import（`QgsRendererCategory` /
`QgsSimpleMarkerSymbolLayer` / `QgsSymbolLayer` / `QgsSingleSymbolRenderer` / `List`）を追加し、
`.core_logic` から `ExcavationType` / `AttributeType`（後述）をトップレベルでimportした
（`core_logic.py` はプラグイン内モジュールを一切importしていないため循環importのリスクはない）。

#### アプローチA: 出土形態・属性のEnum化
`src/core_logic.py` に `str` を継承したEnum（`class ExcavationType(str, Enum)` /
`class AttributeType(str, Enum)`）を新設した。

```python
class ExcavationType(str, Enum):
    GRID = "グリッド"
    FEATURE = "遺構"

class AttributeType(str, Enum):
    S = "S"
    P = "P"
    C = "C"
    SP = "SP"
```

`str` 継承のため `ExcavationType.GRID == "グリッド"` は True となり、既存の文字列ベースの
比較・GeoPackage属性・CSV出力との互換性を壊さない設計とした。ただし `feat.setAttribute(...)` や
辞書のデフォルト値など「実際にQGIS APIへ値を渡す/保存する」箇所は、曖昧さを避けるため明示的に
`.value`（例: `ExcavationType.GRID.value`）を用いるよう統一した。QGISのフィールド式（CASE WHEN等）
文字列テンプレートに埋め込む場合も同様に `.value` をf-stringで展開する形にし、生成される式文字列
自体は変更前と完全に同一であることを確認した。

置換対象（すべて実際のPython分岐・比較箇所のみ。`"小グリッド"`/`"大グリッドＸ"`等のCSV列名や、
コメント・UIラベル文字列は対象外とし変更していない）:

- `src/core_logic.py`: `check_point_duplicate()` / `get_next_point_number()` /
  `build_digitized_feature()`（デフォルト値含む）
- `src/tab2_digitizing_mixin.py`: `get_focus_category_filter()` / `_on_excavation_type_changed()` /
  `get_digitizing_input_state()` / `_get_next_point_number()` / `_on_canvas_clicked()`
  （重複時のエラーメッセージ組み立て含む）/ `_on_existing_point_selected()`（デフォルト値含む）
- `src/symbology_mixin.py`: `apply_point_labeling()` / `apply_point_symbology()`（移設分、
  CASE WHEN式とカテゴリ値タプルの双方）/ `build_opacity_expression()`

さらに、UIコンボボックス文字列とEnumの単一情報源化のため `src/main_dock_constants.py` の
`UILabels.EXCAVATION_OPTIONS` / `UILabels.ATTRIBUTE_OPTIONS` を `ExcavationType`/`AttributeType`
の `.value` から構築する形に変更した（リストの中身・順序は変更前と完全に同一:
`["グリッド", "遺構"]` / `["S", "P", "C", "SP"]`）。`main_dock_constants.py` はこれまでプラグイン内
importを持たない定数専用モジュールだったため、`from .core_logic import ExcavationType, AttributeType`
を新規追加した（`core_logic.py` はプラグイン内モジュールを一切importしていないため循環import
のリスクはない）。

`src/gpkg_cache_mixin.py` / `src/transform.py` / `src/main_dock.py` も `excavation_type` /
`attribute_type` というフィールド名文字列を参照しているが、いずれも値そのものの分岐・比較は
行っておらず（フィールド名のパススルーのみ）、置換対象は存在しないことをgrepで確認した。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定）。
`python3 -m py_compile` による構文チェックのみ実施し、変更した全ファイルでエラーが無いことを確認した
（QGISバインディング自体はこの実行環境に存在しないため、実行時のimport解決・GUI描画等の検証はできない）。

## スコープ外変更の有無
`src/` 配下は、依頼された範囲（`main_dock_constants.py` の文言確認/T-0016、および
`map_tool.py`/`symbology_mixin.py`/`core_logic.py`/`tab2_digitizing_mixin.py`/`tab3_settings_mixin.py`
のシンボロジ統合・Enum化/T-0017）に限定して変更した。ファイル分割は行っていない。
`map_tool.py` から移設メソッド削除に伴い不要になったimportの削除のみ、上記の範囲に付随する
最小限のクリーンアップとして実施した（それ以外の既存の未使用import・未使用コードには一切触れていない）。

なお、`docs/integrated_master_design.md` の93行目付近（CanvasDigitizingToolの説明）は、
`setup_point_layer_symbology`/`setup_ref_point_layer_symbology`/`update_attribute_transparency`
が `map_tool.py` 側にある前提で記述されており、本タスクによる移設後は実態と乖離する（過去の
T-0015時のverifier指摘・T-0016化と同様のパターン）。本タスクの依頼範囲は `src/` 配下のコード実装
であり、設計書の追随修正は明示的に依頼されていないため、今回は変更せず、次回以降のフォローアップ
候補として本ログに記載するに留めた。
