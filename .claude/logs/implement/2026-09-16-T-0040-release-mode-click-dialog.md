## タスクID
T-0040: 新規モード「解除」時のクリック位置への点名・枝番入力ダイアログ

## 変更ファイル一覧
- `src/main_dock_dialogs.py`
- `src/tab2_digitizing_mixin.py`
- `src/main_dock_constants.py`

## 変更概要

### 新設ダイアログクラス: `PointNameEntryDialog` (`src/main_dock_dialogs.py`)
- 既存の `FeatureCreateDialog`（OK/キャンセル、`self.lbl_error` を用いたボタン上の赤字エラー表示パターン）を踏襲して新設。
- コンストラクタ引数: `point_layer`, `excavation_type`, `feature_name`, `drawing_name`, `parent`（いずれも呼び出し元＝`Tab2DigitizingMixin`のパネル現在値をそのまま渡す想定）。
- 入力項目:
  - 点名: `UIStyleHelper.create_spinbox(1, 999999, 1, self)`（既存の `edit_point_name` と同一レンジ）。
  - 枝番: `QLineEdit`（`UIPlaceholders.BRANCH_NO` を流用したプレースホルダ）。
  - **設計上の注記**: 依頼スコープの記述（「点名(整数)」「`edit_point_name`/`edit_branch_no`と同様のウィジェット種別」）に従い、点名は常に `QSpinBox`（整数）としている。SP属性選択時（`edit_point_name_sp`、英数字・ハイフン等の自由入力）も本ダイアログの対象に含まれるが、本ダイアログでは統一して整数スピンボックスを用いる実装とした（`edit_point_name_sp` 用の別バリデータ・別ウィジェットへの分岐は行っていない）。人手確認チェックリストにこの点を明記した。
- OKボタン押下時: `core_logic.check_point_duplicate()` で重複判定。重複時は `core_logic.build_point_ident()` の文字列を `self.lbl_error` に赤字表示しダイアログを閉じない。重複なしなら `result_point_name`/`result_branch_no` にセットして `self.accept()`。
- キャンセルボタン押下時: `self.reject()`（何も作らない）。
- `get_values()` で `(point_name, branch_no)` のタプルを返す。

### `main_dock_constants.py`
- `UILabels.POINT_NAME_ENTRY_DIALOG_TITLE = "点名・枝番入力"` を追加（ダイアログタイトル用）。点名/枝番のラベル文言・プレースホルダは既存の `UILabels.POINT_NAME` / `UILabels.BRANCH_NO` / `UIPlaceholders.BRANCH_NO` を流用し、新規追加していない。

### `tab2_digitizing_mixin.py`
- `_on_canvas_clicked()`: 冒頭で `self.tab2_autonum_mode == "release"` の場合は `_handle_release_mode_click(map_point)` に処理を委譲して早期returnするよう分岐を追加。`"auto"` の場合は従来通りのフロー（`get_digitizing_input_state()` → 遺構名未指定/重複チェック → フィーチャ作成）を維持。
- フィーチャ作成本体（旧 `_on_canvas_clicked` の後半、point_id採番〜`build_digitized_feature`〜`insert_feature_to_layer`〜`_on_point_digitized`）を `_create_digitized_point_from_state(state, map_point)` として抽出。ロジック自体は変更せず、入力を `state` dict化して自動連番フロー・解除フローの両方から共通利用できる形にした。
- `_handle_release_mode_click(map_point)` を新設:
  1. `_is_feature_name_missing()` チェック（従来通り）。
  2. パネルの現在値（`combo_drawing_name`/`combo_excavation_type`/`combo_feature_name`）を読み取り。
  3. `PointNameEntryDialog` をモーダル表示（`_position_dialog_near_map_point()` でクリック地点付近へ移動）。
  4. `QDialog.Accepted` でなければ何もせずreturn（フィーチャ未作成）。
  5. ダイアログの `get_values()` の点名・枝番と、パネルの出土形態・遺構名・色・属性・対象図面から `state` dictを構築し `_create_digitized_point_from_state()` を呼び出す。
- `_position_dialog_near_map_point(dlg, map_point)` を新設: `self.map_tool.canvas.getCoordinateTransform().transform(map_point)` でキャンバス上のピクセル座標を取得し、`canvas.mapToGlobal(QPoint(...))` でグローバル座標へ変換して `dlg.move()` を呼ぶ。`map_tool`/`canvas` が未初期化の場合や変換に失敗した場合は例外を握りつぶし、Qtのデフォルト表示位置にフォールバックする（ベストエフォート、依頼文の「正確にその位置に表示されない場合がある点は許容」に対応）。
- `_on_canvas_clicked()` の docstring にT-0040の分岐説明を追記。

### 対象外（手を加えていない）
- 編集モードのロジック（T-0037/T-0038）
- 自動連番("auto")時の即時作成フロー本体（`_create_digitized_point_from_state`に処理を切り出したのみで、`state`の内容・組み立てロジック自体は変更していない）
- SP属性の判定ロジック自体（`_is_sp_attribute()`, `_update_autonum_toggle_for_sp()`）

## 自動テスト実行結果
自動テストなし。`python3 -m py_compile src/main_dock_dialogs.py src/tab2_digitizing_mixin.py src/main_dock_constants.py` を実行し、構文エラーがないことを確認した（実行結果: 終了コード0、出力なし）。

## スコープ外変更の有無
なし。変更は依頼範囲内の `src/main_dock_dialogs.py` / `src/tab2_digitizing_mixin.py` と、それらが参照する定数追加のための `src/main_dock_constants.py`（ラベル文字列1件の追加のみ）に限定した。

---

## 追記: verifier指摘（SP属性の点名入力欠落）修正 (2026-09-16)

### 背景
verifierによる静的検証で、`PointNameEntryDialog` の点名入力欄が整数 `QSpinBox`（`spin_point_name`, 1〜999999）のみのため、SP属性選択時（`_update_autonum_toggle_for_sp()` により自動連番/解除トグルが強制的に「解除」へ固定され、キャンバスクリックが必ず `_handle_release_mode_click()` 経由になる）に、既存の `edit_point_name_sp`（英数字・ハイフン・アンダースコア可のQLineEdit＋正規表現バリデータ）が持っていた自由記述の点名入力手段が失われる、という不整合がCONFIRMEDされた。今回はこの一点のみをピンポイントで修正した。

### 変更ファイル
- `src/main_dock_dialogs.py`
- `src/tab2_digitizing_mixin.py`

### 変更概要

#### `PointNameEntryDialog.__init__` (`src/main_dock_dialogs.py`)
- コンストラクタに `is_sp_attribute: bool = False` 引数を追加（`point_layer, excavation_type, feature_name, drawing_name, is_sp_attribute, parent` の順。呼び出し元は `Tab2DigitizingMixin._is_sp_attribute()` の戻り値を渡す想定）。`self._is_sp_attribute` として保持。
- 点名入力欄の構築を `is_sp_attribute` で分岐:
  - `True`（SP属性）の場合: `self.spin_point_name = None` のまま、代わりに `self.edit_point_name_sp` という `QLineEdit` を生成し、`tab2_digitizing_mixin.py` の既存 `edit_point_name_sp` と同一のバリデータ（`QRegExpValidator(QRegExp(r"^[A-Za-z0-9_-]+$"), ...)`。`main_dock_dialogs.py` は元々Qt5系の `QRegExp`/`QRegExpValidator` を無条件importしており、`tab2_digitizing_mixin.py` のようなQt5/Qt6両対応の try/except パターンは採用していなかったため、今回もそのファイル既存の import 方針に合わせた）と `UIPlaceholders.POINT_NAME_SP` プレースホルダを設定。
  - `False`（非SP属性）の場合: `self.edit_point_name_sp = None` のまま、従来通り `self.spin_point_name`（`UIStyleHelper.create_spinbox(1, 999999, 1, self)`）を表示。
- `_get_point_name_text()` を新設し、`self._is_sp_attribute` に応じて `edit_point_name_sp.text().strip()` または `str(spin_point_name.value())` のいずれかを返す共通処理とした。
- `_on_ok_clicked()` は `point_name = str(self.spin_point_name.value())` の直接呼び出しから `point_name = self._get_point_name_text()` に変更。以降の `check_point_duplicate()`/`build_point_ident()`/エラー表示ロジックは変更していない（文字列を渡す既存の呼び出し形は元々変わらない）。
- SP属性時のみ、空文字での確定を防ぐガード（`if self._is_sp_attribute and not point_name:` で `UIMessages.ERR_POINT_NAME_REQUIRED` を `self.lbl_error` に表示して return）を追加。非SP側は `QSpinBox` の最小値が1のため元々空値になり得ず、このガードの対象外。

#### `_handle_release_mode_click()` (`src/tab2_digitizing_mixin.py`)
- `PointNameEntryDialog(...)` のコンストラクタ呼び出しに `self._is_sp_attribute()` を追加（`drawing_name` と `self`(parent) の間に挿入）。
- `dlg.get_values()` で得た `point_name`（SP属性なら英数字文字列、非SP属性なら整数の文字列表現）はいずれもそのまま `state["point_name"]` に文字列として格納し `_create_digitized_point_from_state()` に渡す。同メソッド・`build_digitized_feature()` は元々 `point_name` を文字列として扱っており（`_get_current_point_name_and_branch()` が返す値も常に文字列）、SP/非SPで後続処理を分岐させる追加変更は不要だったため行っていない。

### 対象外（手を加えていない）
- `_apply_next_point_number` / `_is_sp_attribute` / `_update_autonum_toggle_for_sp` 等、SP属性判定・トグル制御ロジック自体
- 自動連番("auto")時にダイアログを経由しないフロー
- キャンセル時に何も作成されない挙動
- `check_point_duplicate()` へのパラメータ受け渡し順序・内容
- `UILabels.POINT_NAME`（"点名 (半角数字):"）のラベル文言自体（SP時も同一ラベルを流用。文言の分岐は依頼スコープに含まれないため変更していない）

## 自動テスト実行結果（追記分）
自動テストなし。`python3 -m py_compile src/main_dock_dialogs.py src/tab2_digitizing_mixin.py` を実行し、構文エラーがないことを確認した（終了コード0、出力なし）。

## スコープ外変更の有無（追記分）
なし。変更は依頼範囲内の `src/main_dock_dialogs.py` / `src/tab2_digitizing_mixin.py` の、SP属性の点名入力欠落に関わる箇所のみに限定した。
