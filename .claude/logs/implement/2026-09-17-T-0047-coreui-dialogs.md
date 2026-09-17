## タスクID
T-0047

## 変更ファイル一覧
- `src/ui/dialogs.py`（808行 → 821行）
- `src/ui/schemas.py`（229行 → 348行、T-0047節を追加）
- `src/ui/core/field_spec.py`（167行 → 186行、`WidgetType.SPINBOX_ROW` と `FieldSpec.spin_min/spin_max/spin_default/centered` を追加）
- `src/ui/core/builder.py`（418行 → 451行、`_build_spinbox_row` 追加、`_build_button_row` に `centered` オプション追加、`get_value`/`set_value`/`_VALUE_WIDGET_TYPES`/`_BUILDERS` へ `SPINBOX_ROW` を組み込み）

## 変更概要

T-0045(tab1_image.py)・T-0046(start_dialog.py)に続き、`src/ui/dialogs.py` の3つのモーダルダイアログ
（`GridInputDialog`/`FeatureCreateDialog`/`PointNameEntryDialog`）にCoreUIパターンを適用した。

### CoreUI側の最小追加（field_spec.py / builder.py）
- `WidgetType.SPINBOX_ROW`: `UIStyleHelper.create_spinbox()`をラップした「ラベル+単一QSpinBox」の行。
  `PointNameEntryDialog`の点名(数値)入力で使用。`FieldSpec.spin_min/spin_max/spin_default`で範囲・初期値を指定。
  `BuiltPanel.get_value()`/`set_value()`はint値をそのまま読み書きする。
- `FieldSpec.centered`（BUTTON_ROW専用、既定False）: `UIStyleHelper.build_centered_button_row()`と同じ
  「stretch-ボタン-ボタン-stretch」レイアウトをBUTTON_ROWでも再現するためのフラグ。3ダイアログの
  OK/キャンセル（確定/キャンセル）行はいずれもこの中央寄せパターンを使っていたため追加した。
  既定Falseのため、Tab1の`rename_delete`/`transform_actions`（左詰めBUTTON_ROW）の挙動は変更していない。

### schemas.py（新規追加分のみ、既存TAB1/START_DIALOG節は変更なし）
- `GRID_INPUT_ACTIONS_SPEC`: GridInputDialog の[確定][キャンセル]行
- `FEATURE_CREATE_INPUT_SPEC` / `FEATURE_CREATE_ACTIONS_SPEC`: FeatureCreateDialog の入力欄+OK/キャンセル行
- `POINT_NAME_ENTRY_SPEC`（`point_name`=SPINBOX_ROW, `point_name_sp`=LINEEDIT_ROW, `branch_no`=LINEEDIT_ROW）/
  `POINT_NAME_ENTRY_ACTIONS_SPEC`: PointNameEntryDialog の入力欄+OK/キャンセル行

### dialogs.py
- `FeatureCreateDialog`: 手書きの`QLabel`+`QLineEdit`+`QPushButton`×2+`build_centered_button_row`を
  `CoreUIBuilder.build(FEATURE_CREATE_INPUT_SPEC)`/`build(FEATURE_CREATE_ACTIONS_SPEC)`+`panel.bind()`に置換。
  従来の赤字インライン`lbl_error`は廃止し、`validators.py`の`RequiredValidator`+`show_validation_error()`
  （`QMessageBox.warning()`+`setFocus()`、tab1_image.pyと同じパターン）に統一した。
- `PointNameEntryDialog`: 数値点名(QSpinBox)/SP点名(QLineEdit、英数字・ハイフン・アンダースコアのみの
  `QRegExpValidator`つき)/枝番(QLineEdit)の3入力とOK/キャンセル行をCoreUI化。`is_sp_attribute`に応じて
  `point_name`/`point_name_sp`いずれかの行を`panel.get_row(...).hide()`で隠す（両フィールドは常に構築される
  が、インスタンスごとに固定の選択なのでschemas.py側は静的宣言のまま）。バリデーションは
  `RequiredValidator`（SP必須チェック）+`DuplicateValidator`（`check_point_duplicate`をラップ）+
  `show_validation_error()`に統一し、従来の`lbl_error`赤字パネルは廃止した。
- `GridInputDialog`: Tier3（[確定][キャンセル]ボタン行）のみを`CoreUIBuilder.build(GRID_INPUT_ACTIONS_SPEC)`
  に置換。Tier1（Xグリッド/Yグリッド/小グリッドの3入力: `TwoDigitSpinBox`・大文字専用`QRegExpValidator`付き
  `QLineEdit`・素の`QSpinBox`を横並びに配置し、リアルタイムでLayerManagerのグリッドキャッシュを検索する
  `_validate_and_lookup`と密結合）とTier4（`UIStyleHelper.create_status_panel`/`update_status_panel`による
  動的な色replace付きステータス表示）は既存のCoreUI WidgetTypeで表現できないため、素のPyQtコードのまま
  残した（`.claude/state/v2-coreui-plan.md`の「画面固有の例外は素のPyQtコードとして残してよい」の逃げ道、
  および同様の判断が下されたstart_dialog.pyの原点/範囲/プレビューパネルの前例に倣う）。
  また、Tier2の「選択点を削除」ボタンは`#D32F2F`/白文字の一点物スタイルシートを使っており、CoreUIの
  `BUTTON`/`ButtonDef.style_variant`が対応する`primary`/`accent`/`success`のいずれにも該当しないため
  bespokeのまま残した（`ui/style.py`へ新しい`danger`系variantを追加することは本タスクのファイルスコープ
  外のため見送り、schemas.py側にもコメントで理由を明記した）。

## 判断理由（設計思想との整合性）
- UI→Logic→Layer→QGIS/Diskの単方向依存は維持（今回の変更はUI層内の構築方法の置換のみで、
  `logic.core.check_point_duplicate`/`build_point_ident`/`to_survey_coords`の呼び出し関係は変更していない）。
- 過度な抽象化を避けるため、SPINBOX_ROW/centeredはいずれも既存3ダイアログで実際に使われる形にのみ限定し、
  投機的な汎用化はしていない。
- GridInputDialogのTier1/Tier4/削除ボタンは、対応困難な画面固有要素として素のPyQtコードのまま残す
  （タスク依頼書の「6. 既存WidgetTypeで表現できないUI要素があれば...対応困難な画面固有要素は素のPyQt
  コードのまま残すことも許容する」に基づく判断）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
`python3 -m py_compile`にて `src/ui/dialogs.py`・`src/ui/schemas.py`・`src/ui/core/field_spec.py`・
`src/ui/core/builder.py` の構文エラーがないことを確認した（実行時のQGIS動作は未確認）。

## スコープ外変更の有無
なし。変更は上記4ファイル（`src/ui/dialogs.py`・`src/ui/schemas.py`・`src/ui/core/field_spec.py`・
`src/ui/core/builder.py`）のみに限定した。`.claude/state/tasks.md`のT-0047行の状態更新は
運用ドキュメントの更新であり、依頼書の「完了時の作業」に基づく想定内の変更である。
