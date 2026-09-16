## タスクID
T-0046: `src/ui/start_dialog.py`（実装前1101行）へCoreUIパターン（T-0045/T-0045-bでtab1_image.pyに確立）を適用する。

## 変更ファイル一覧
- `src/ui/start_dialog.py`（1101行 → 1057行、-44行）
- `src/ui/schemas.py`（`START_DIALOG_SESSION_SPEC`/`START_DIALOG_GRID_CSV_SPEC`を追記）
- `src/ui/core/field_spec.py`（`WidgetType.RADIO_ROW`を新設。docstring更新）
- `src/ui/core/builder.py`（`RADIO_ROW`用ビルダー`_build_radio_row`追加、`_VALUE_WIDGET_TYPES`・`get_value`/`set_value`にRADIO_ROWを追加、`_build_lineedit_row`にラベル参照`f"{field_id}.label"`の登録を追加）

## 変更概要

### 1. CoreUIエンジンの拡張（`src/ui/core/`）
T-0045完了時点でRADIO_ROW相当のwidget_typeが存在せず（SEGMENTED_TOGGLEはiOS風トグル、start_dialogの「セッション種別」「グリッドモード」は素のQRadioButtonペア）、start_dialogを宣言化するために以下を追加した。

- `WidgetType.RADIO_ROW`: ラベル付きの排他QRadioButton行。`FieldSpec.options`/`default_index`/`on_change`をSEGMENTED_TOGGLEと同じ契約（インデックスベースのget_value/set_value、toggled→index通知のon_change）で流用する。
- `CoreUIBuilder._build_radio_row`: `UIStyleHelper.build_flex_row`でラベル+ラジオボタン群+末尾ストレッチの行を構築し、`QButtonGroup`で排他制御する（`_build_segmented_toggle`と対称の実装）。
- `BuiltPanel.get_value`/`set_value`/`_VALUE_WIDGET_TYPES`にRADIO_ROWを追加。
- `_build_lineedit_row`: ラベルウィジェットを`field_widgets[f"{field_id}.label"]`として追加登録（start_dialogが実行時にラベル文言を「親ディレクトリ:」⇔「セッションフォルダ:」で切替える必要があるため）。既存のtab1側の挙動には影響しない追加のみ。

### 2. スキーマ追加（`src/ui/schemas.py`）
`START_DIALOG_SESSION_SPEC`（セッション種別RADIO_ROW＋フォルダパスLINEEDIT_ROW＋セッション名LINEEDIT_ROW）と`START_DIALOG_GRID_CSV_SPEC`（グリッドCSV選択LINEEDIT_ROW＋グリッドモードRADIO_ROW）を追記した。

### 3. `start_dialog.py`側の置き換え
`_init_ui()`内の該当ブロックを`CoreUIBuilder.build()`呼び出し＋`panel.get()`/`get_buttons()`によるウィジェット参照取得＋`panel.bind()`によるイベント接続に置き換えた。既存のインスタンス属性名（`self.radio_new`/`self.edit_folder`/`self.edit_session_name`/`self.edit_grid_csv`/`self.radio_grid_mode_new`等）はそのまま維持し、後続のバリデーション・`get_session_data()`・グリッド設定パネル連携ロジックへの影響をゼロにした（属性の生成元が手動`QWidget`構築からCoreUIBuilder経由に変わっただけ）。

`_on_session_type_changed`/`_on_grid_mode_changed`は、RADIO_ROWのon_changeフックがチェックされたインデックスを引数で渡す仕様のため、`(self, _index: int = 0)`のシグネチャに変更した（本体ロジックは`self.radio_new.isChecked()`等で最終状態を都度読み直す既存方式のまま、インデックス自体は未使用）。

未使用となった`QRadioButton`/`QButtonGroup`インポート、および`UI_CONFIG["LABELS"]`/`UI_CONFIG["PLACEHOLDERS"]`内の構築時のみ参照されていたキー（`SESSION_TYPE`/`RADIO_NEW`/`RADIO_EXISTING`/`BTN_BROWSE`/`SESSION_NAME`/`GRID_CSV`/`GRID_MODE`/`RADIO_GRID_MODE_NEW`/`RADIO_GRID_MODE_USE_CSV`、`PLACEHOLDERS.SESSION_NAME`/`GRID_CSV`）を削除した。実行時に動的参照される`FOLDER_PARENT`/`FOLDER_EXISTING`（ラベル・プレースホルダとも）は維持している。

### 4. 意図的にCoreUI化を見送った範囲（スコープ内の判断・過度な抽象化回避）
「グリッド設定」グループの原点(1A-00)/X範囲/Y範囲/プレビュー入力パネルと、動的に警告表示・確認ボタンを切り替える`panel_preview_status`ステータスパネルは、既存のPyQtコードのまま維持した。理由:
- `ExcelColumnSpinBox`（カスタムQSpinBoxサブクラス）、`build_child_container`によるサブラベル付きスピンボックスの入れ子構成、ステータスパネル内への確認ボタンの動的埋め込みなど、現行のCoreUI WidgetType（LINEEDIT_ROW/COMBOBOX_ROW/BUTTON/BUTTON_ROW/TABLE/SEGMENTED_TOGGLE/INFO_PANEL/RADIO_ROW）のいずれにも自然に対応しない、この画面固有のステートフルな構造である。
- これらのためだけに新規WidgetTypeを増やすことは、CoreUI計画（`.claude/state/v2-coreui-plan.md`）が明記する「画面固有の例外は素のPyQtコードとして残してよい」という逃げ道方針、および依頼文の「過度な抽象化は避ける」という指示に沿った判断である。
- `_on_grid_mode_changed`等のモード連動可視性制御も、依頼文の指示通り`rules.py`の汎用Rule化はせず、既存のシンプルな条件分岐（`match`文）のまま維持した。

### 5. logic層への移管について
`_extract_csv_metadata`（CSVファイルI/O）や`_browse_folder`/`_browse_grid_csv`（`os.path`操作、`QFileDialog`呼び出し）など、UI層がファイルI/Oを直接行っている箇所が複数存在するが、これらは今回のスコープ（CoreUI適用）とは別の関心事であり、大規模なlogic層移管が必要と判明したため、依頼文の指示通りスコープを広げずT-0049（`src/logic/`分離状況の棚卸し）の対象として記録するに留めた。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。

## スコープ外変更の有無
なし。変更は`src/ui/start_dialog.py`・`src/ui/schemas.py`・`src/ui/core/field_spec.py`・`src/ui/core/builder.py`の4ファイルに限定した。後三者はCoreUIエンジン自体（T-0045で新設された共通基盤）への機能追加であり、依頼文中「T-0046以降の方針確定」節に記載の「T-0045の実装で得られた知見を反映してCoreUI自体も調整してよい」という許容範囲内である。tab1_image.py等、他画面のファイルは一切変更していない。
