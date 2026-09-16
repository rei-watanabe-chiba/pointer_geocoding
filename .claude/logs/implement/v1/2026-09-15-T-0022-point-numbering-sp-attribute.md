## タスクID
T-0022

## 変更ファイル一覧
- `src/core_logic.py`
- `src/tab2_digitizing_mixin.py`
- `src/main_dock_constants.py`
- `docs/integrated_master_design.md`

## 変更概要

### 1. `src/core_logic.py`
- `get_next_point_number(point_layer, excavation_type, feature_name)` のロジックを、「選択条件に一致する全フィーチャ中でpoint_nameが純数字のものの最大値+1」から、「選択条件に一致するフィーチャのうち`point_id`（自増主キー、int）が最大のフィーチャの`point_name`から先頭の数字部分（本体番号。`5-a`なら`5`）を`re.match(r"^(\d+)", pname)`で抽出し、その+1」を返す方式（直前打刻追従型）へ変更。
  - 該当フィーチャが0件、または最大point_idフィーチャの`point_name`に先頭数字が無い場合は`1`を返す既存の初期値契約を維持。
  - 関数シグネチャ（引数・戻り値型）は変更なし。
  - `import re` を追加。

### 2. `src/tab2_digitizing_mixin.py`
- インポートに `QLineEdit` を追加。`start_dialog.py`(L31-38付近)と同一のPyQt5/PyQt6両対応バリデータimportパターン（`QRegularExpressionValidator`優先、フォールバックで`QRegExpValidator`）を`HAS_QT_REGEX`フラグとともに追加。
- 点名入力行（Section 3: Individual Input Panel）に、既存の`edit_point_name`(QSpinBox、変更なし)と並置する新規`QLineEdit`の`edit_point_name_sp`を追加。
  - プレースホルダーは`UIPlaceholders.POINT_NAME_SP`。
  - バリデータは`^[A-Za-z0-9_-]+$`（半角英数字・ハイフン・アンダースコアのみ）。
  - 初期状態は非表示（`hide()`）。`UIStyleHelper.build_flex_row`のchild_configsに両ウィジェットを追加し、表示/非表示で切替（QHBoxLayout内の非表示ウィジェットは領域を占有しないため単純なshow/hideで対応、QStackedWidgetは不要と判断）。
- 新規ヘルパーメソッドを追加:
  - `_is_sp_attribute()`: `combo_attribute`の現在値が`AttributeType.SP.value`かどうかを返す。
  - `_update_point_name_widget_visibility()`: 属性に応じて`edit_point_name`/`edit_point_name_sp`の表示を排他的に切替。
  - `_apply_next_point_number()`: 属性がSP以外ならオンデマンドで`core_logic.get_next_point_number`（=`_get_next_point_number()`経由）を呼び自動採番してQSpinBoxへセット、SPならQLineEditを空欄化。表示切替も同時に行う。
- 以下の呼び出し元を、旧来の`next_num = self._get_next_point_number(); self.edit_point_name.setValue(next_num)`パターンから`self._apply_next_point_number()`呼び出しへ置き換え（`_on_category_changed()`・`_on_branch_text_changed()`・`_on_point_digitized()`・`_reset_point_selection()`）。
  - `_on_category_changed()`は`combo_attribute.currentIndexChanged`（属性変更）・`_on_excavation_type_changed()`（出土形態変更）・`_on_feature_combo_changed()`（遺構名変更）のいずれからも呼ばれる既存の共通ハンドラであり、これを拡張することで仕様の「属性(S/P/C⇔SP)・出土形態・遺構名のいずれかが切り替わった際にオンデマンド照会」要件を満たす（新規シグナル接続は追加していないため、対称的な解除処理の追加は不要）。
- `get_digitizing_input_state()`: `pname`取得元を属性がSPなら`edit_point_name_sp.text().strip()`、それ以外は従来通り`edit_point_name.value()`に分岐。必須チェック（空文字判定）は共通のまま機能する。
- `_on_existing_point_selected()`: 既存点編集時のロード順序を修正。従来は`edit_point_name.setValue(p_val)`の後で`combo_attribute.setCurrentText(...)`を呼んでいたため、属性が変化する既存点を選択すると`_on_category_changed()`が発火して直後にセットした点名が自動採番値で上書きされてしまう潜在的な不整合があった（本タスクのSP対応で当該メソッドに手を入れる必要があったため合わせて是正）。修正後は`combo_attribute`を先に確定させ、その後で属性に応じて`edit_point_name`（数値）または`edit_point_name_sp`（自由入力文字列）へ実際のロード値をセットし、最後に`_update_point_name_widget_visibility()`で表示を確定する。

### 3. `src/main_dock_constants.py`
- `UIPlaceholders`に`POINT_NAME_SP = "半角英数字・ハイフン・アンダースコアのみ (例: SP-01)"`を追加。

### 4. `docs/integrated_master_design.md`
- L23-24付近のQSpinBox保護原則に、「SP属性選択時は例外的に専用QLineEditを並置する」旨の追記段落を追加。
- 遺物点作成セクション（旧L148付近）の「枝番なしの場合は点名が自動インクリメントされる」という記述を、直前打刻追従型（選択中の条件内でmax point_idの次番号を抽出し、枝番は本体番号の採番対象外である旨）の説明に更新。SP属性時は自動採番せず空欄で手入力を待つ旨も追記。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
`py -c "import ast; ast.parse(...)"` によるPython構文チェックのみ実施し、変更した3つの`.py`ファイルに構文エラーがないことを確認した。

## スコープ外変更の有無
なし。指定4ファイル（`src/core_logic.py`, `src/tab2_digitizing_mixin.py`, `src/main_dock_constants.py`, `docs/integrated_master_design.md`）以外への変更は行っていない。
