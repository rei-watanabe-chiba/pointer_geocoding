## タスクID
Stage E: シンボロジ/透明度操作の一元化（処理フロー変更を伴う、ユーザー許可済み）

## 変更ファイル一覧
- `src/symbology_mixin.py`
- `src/main_dock.py`
- `src/map_tool.py`
- `docs/integrated_master_design.md`

（`src/tab2_digitizing_mixin.py`, `src/tab3_settings_mixin.py` は依頼どおり読み取り・呼び出し箇所の確認のみを行い、コード変更は行っていない。）

## 変更概要

### 1. `MainDockWidget.update_symbology_opacity()` の責務分解（main_dock.py → symbology_mixin.py）
従来 `main_dock.py` の `update_symbology_opacity()`（約70行）が担っていた

- (a) フォーカスモード条件式（QgsProperty用のCASE WHEN式文字列）の組み立て
- (b) 組み立てた式を `QgsCategorizedSymbolRenderer` の各カテゴリシンボルへ実際に適用する処理

の2つを分離し、`src/symbology_mixin.py` の `SymbologyMixin` に以下の2メソッドとして移管した。

- `SymbologyMixin.build_opacity_expression(is_focus_on, filters, slider_val) -> str`
  - 純粋関数。QGISオブジェクトの読み書きは行わず、文字列を返すのみ。
  - ロジックは移管前の `main_dock.py` 内の条件式組み立てコード（`_escape_sql`、`drawing_name`/`excavation_type`/`feature_name`/`attribute_type` に対するCASE WHEN組み立て）をそのまま移植（変数の受け渡し方法のみ変更、条件分岐・文字列フォーマットは一字一句同一）。
- `SymbologyMixin.apply_opacity_expression(layer, expr) -> None`
  - `QgsProperty.fromExpression(expr)` を生成し、`QgsCategorizedSymbolRenderer` の各カテゴリシンボルへ `setDataDefinedProperty(PropertyOpacity, prop)` を適用し、レンダラーを再設定して `triggerRepaint()` する処理をそのまま移植。

`main_dock.py` の `update_symbology_opacity()` は、UI状態（フォーカスモードON/OFF、4カテゴリの現在値、スライダー値）を収集し、`self.layer_manager.build_opacity_expression(...)` → `self.layer_manager.apply_opacity_expression(...)` を呼び出したのち `canvas.refresh()` する薄い委譲メソッドとして残した（`LayerManager` は既存どおり `SymbologyMixin` を多重継承しているため、`self.layer_manager.build_opacity_expression` / `apply_opacity_expression` で到達可能。既存の `apply_ref_point_symbology` 呼び出し（tab3_settings_mixin.py）と同じ「`self.layer_manager.<SymbologyMixinのメソッド>`」という呼び出し形態に揃えた）。

メソッド名・シグネチャ（`update_symbology_opacity(self) -> None`）は変更していないため、`tab2_digitizing_mixin.py`（`_on_focus_mode_toggled`, `_on_slider_released`, `_on_category_changed`, `_confirm_attribute_transparency`）および `main_dock.py` 自身の `_on_tab_changed`（Tab3経由でTab2に戻った際のフォーカスモード再適用）からの呼び出し箇所は無変更。

`main_dock.py` からは、この処理で使わなくなった `QgsProperty` / `QgsSymbol` / `QgsCategorizedSymbolRenderer` のimportを削除した（他箇所で未使用であることを確認済み）。

### 2. `map_tool.py` と `symbology_mixin.py` の重複ロジック共通化
`map_tool.py` の `CanvasDigitizingTool.setup_point_layer_symbology()` と `symbology_mixin.py` の `SymbologyMixin.apply_ref_point_symbology()` の双方に、ラベルの表示位置をAboveRight（クアドラント値2）に固定するための、完全に同一のtry/exceptブロック（`Qgis.LabelQuadrantPosition.QuadrantAboveRight` の存在確認・フォールバック・`pal.quadrantPosition`/`pal.quadOffset`への代入）が存在していた。これを明確な重複ロジックと判断し、`SymbologyMixin.apply_above_right_label_quadrant(pal: QgsPalLayerSettings) -> None` として `symbology_mixin.py` に切り出し、両箇所から呼び出す形に統一した。

`map_tool.py` には `from .symbology_mixin import SymbologyMixin` を追加（`symbology_mixin.py` はモジュールトップレベルで `map_tool.py`/`main_dock.py` をimportしていない＝遅延import限定のため、循環importは発生しない。`layer_manager.py`も同様にモジュールトップレベルで`symbology_mixin`をimportしており既存パターンと整合）。

`setup_point_layer_symbology`/`setup_ref_point_layer_symbology`/`update_attribute_transparency` のそれ以外の部分（シンボル生成条件、色分け条件式の組み立て、カテゴリ別マーカー形状の定義等）は、`QgsMapTool` 由来のキャンバス依存処理と密結合しており、依頼文の「無理に統合せず、明確に重複しているロジック片のみを対象にすること」に従い、変更していない。`update_attribute_transparency`（属性別の静的50%/100%不透明度設定、現状コードベース内から未呼び出し）も同様に無変更。

### 3. ドキュメント更新（docs/integrated_master_design.md）
`grep` で `update_symbology_opacity` / シンボロジ関連の言及箇所を洗い出し（該当: 78行目 main_dock.py の説明、87行目 symbology_mixin.py の説明、93行目 map_tool.py の説明）、以下を実態に合わせて更新した。

- 78行目: `update_symbology_opacity` が薄い委譲メソッドになったこと、式の組み立て・適用は `SymbologyMixin.build_opacity_expression`/`apply_opacity_expression`（`self.layer_manager`経由）に委譲していることを追記。
- 87行目: `symbology_mixin.py`の説明に `apply_above_right_label_quadrant`、`build_opacity_expression`、`apply_opacity_expression` を追記。
- 93行目: `map_tool.py`の`CanvasDigitizingTool`の説明に、AboveRightクアドラント整列処理を`SymbologyMixin.apply_above_right_label_quadrant`に共通化した旨を追記（`QgsMapTool`としての構造自体は変更していない旨も明記）。

それ以外の記述（1.4節冒頭のディレクトリ構成表、2.3節「フォーカスモード」のUX説明等）は、外部から見た挙動・ファイル配置に変更がないため変更していない。

## 変更前後でのメソッド構成・責務分担の変化

**変更前**
```
main_dock.py
  MainDockWidget.update_symbology_opacity()
    - フォーカスモード状態・カテゴリ値・スライダー値の収集
    - CASE WHEN式文字列の組み立て（インライン）
    - QgsCategorizedSymbolRenderer への適用（インライン）
    - canvas.refresh()

symbology_mixin.py
  SymbologyMixin.apply_point_labeling()
  SymbologyMixin.apply_ref_point_symbology()
    - AboveRightクアドラント設定コード（インライン、map_tool.pyと重複）

map_tool.py
  CanvasDigitizingTool.setup_point_layer_symbology()
    - AboveRightクアドラント設定コード（インライン、symbology_mixin.pyと重複）
  CanvasDigitizingTool.setup_ref_point_layer_symbology()
  CanvasDigitizingTool.update_attribute_transparency()
```

**変更後**
```
main_dock.py
  MainDockWidget.update_symbology_opacity()  ← 薄い委譲メソッドとして存続
    - フォーカスモード状態・カテゴリ値・スライダー値の収集
    - self.layer_manager.build_opacity_expression(...) 呼び出し
    - self.layer_manager.apply_opacity_expression(...) 呼び出し
    - canvas.refresh()

symbology_mixin.py
  SymbologyMixin.apply_point_labeling()
  SymbologyMixin.apply_above_right_label_quadrant()   ← 新規（共通化）
  SymbologyMixin.apply_ref_point_symbology()          ← 内部でapply_above_right_label_quadrant呼び出し
  SymbologyMixin.build_opacity_expression()           ← 新規（main_dock.pyから移管、式組み立てのみ）
  SymbologyMixin.apply_opacity_expression()           ← 新規（main_dock.pyから移管、レンダラー適用のみ）

map_tool.py
  CanvasDigitizingTool.setup_point_layer_symbology()  ← 内部でSymbologyMixin.apply_above_right_label_quadrant呼び出し
  CanvasDigitizingTool.setup_ref_point_layer_symbology()  ← 無変更
  CanvasDigitizingTool.update_attribute_transparency()    ← 無変更
```

## 「見た目の最終結果を変えていないこと」の確認方法（コードレベル）
実行による確認は行っていない（QGIS上での動作確認は不可）。以下はコードレベルでの前後比較による確認内容。

1. **`build_opacity_expression`**: 移管元コード（`main_dock.py` 旧 `update_symbology_opacity` 内の `if is_focus_on:` ブロック以下、`_escape_sql` 定義、`conditions` リストの組み立て順序、`condition_str`・`expr` の文字列フォーマット）を、変数の受け渡し（インスタンス属性 → 関数引数 `is_focus_on`/`filters`/`slider_val`）以外は一切変更せず、行単位でそのまま新メソッドへ移植したことを目視で確認した。`is_focus_on=False` の場合は移管前同様 `"100"` を即座に返す分岐を維持。
2. **`apply_opacity_expression`**: 移管元コードの `QgsProperty.fromExpression`・`PropertyOpacity` キー解決（`getattr`によるフォールバック）・`for idx, category in enumerate(...)` によるシンボルクローン＋`setDataDefinedProperty`＋`renderer.updateCategorySymbol`・`layer.setRenderer(renderer.clone())`・`layer.triggerRepaint()` を、レイヤ引数を`self.point_layer`から`layer`引数に置き換えた以外は変更せずそのまま移植したことを確認した。呼び出し元の `main_dock.py` 側で従来どおり `canvas.refresh()` を呼び出す順序も維持し、キャンバス再描画のタイミングを変えていない。
3. **`main_dock.py` の新 `update_symbology_opacity`**: フォーカスモードOFF時にUI値（`combo_drawing_name`等）を読まずに `filters={}` のまま `build_opacity_expression` を呼ぶ（内部で即 `"100"` を返す）構成とし、移管前の「`if is_focus_on:` の中でのみUI値を読む」という制御フローの意味的な等価性を確認した（UI値を読まないことによる副作用は元々なく、結果として渡される式文字列は同一）。
4. **`apply_above_right_label_quadrant`**: 抽出元の2箇所（`symbology_mixin.py`旧`apply_ref_point_symbology`内、`map_tool.py`の`setup_point_layer_symbology`内）のコードが、コメント文言も含めて完全に同一のtry/exceptブロックであったことをdiff相当の目視比較で確認した上で、引数名`pal`を含めそのまま関数化し、両呼び出し元を1行の呼び出しに置換した。ロジック自体（quad_val解決の優先順位、`hasattr`によるフォールバック、例外握り潰し）は変更していない。
5. `setup_ref_point_layer_symbology` / `update_attribute_transparency` / `setup_point_layer_symbology`の残りの部分（シンボル生成・カテゴリ定義・色分け式・ラベルフォーマット）は一切変更していないため、これらが出力する `QgsRenderer`/`QgsPalLayerSettings`/`QgsTextFormat` の内容は変更前と同一。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。

`python -m py_compile` を `src/*.py` 全体に対して実行し、構文エラーがないことを確認した（`py -3 -m py_compile src/*.py` → 終了コード0、"Could not find platform independent libraries <prefix>" は環境依存の警告であり構文エラーではない）。加えて変更対象ファイル（`symbology_mixin.py`, `main_dock.py`, `map_tool.py`, `tab2_digitizing_mixin.py`, `tab3_settings_mixin.py`, `layer_manager.py`）個別でも同様にコンパイル成功を確認した。

## スコープ外変更の有無
なし。変更は `src/symbology_mixin.py`, `src/main_dock.py`, `src/map_tool.py`, `docs/integrated_master_design.md` に限定した。`src/tab2_digitizing_mixin.py`, `src/tab3_settings_mixin.py` はコード変更不要と判断し、無変更（呼び出し箇所の確認のみ実施）。
