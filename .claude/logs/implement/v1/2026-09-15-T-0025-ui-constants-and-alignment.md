## タスクID
T-0025

## 変更ファイル一覧
- src/main_dock_constants.py
- src/main_dock.py
- src/main_dock_dialogs.py
- src/style_helper.py
- src/tab1_georef_mixin.py
- src/tab2_digitizing_mixin.py
- src/plugin.py

## 変更概要

### ① 右ドック幅の固定
- `main_dock_constants.py` の `UIConfig` に `DOCK_WIDTH = 300` を追加。
- `main_dock.py` の `_init_ui()` 内、`self.setWidget(root_widget)` 直前で
  `root_widget.setFixedWidth(UIConfig.DOCK_WIDTH)` を呼び出し、右ドックの
  幅を固定。

### ② モードレスダイアログの幅・高さの先頭定義化
- `main_dock_constants.py` に新規クラス `UIDialogSizes` を追加し、以下を定義。
  - `IMAGE_DIALOG_WIDTH = 1100` / `IMAGE_DIALOG_HEIGHT = 650`
  - `GRID_DIALOG_MIN_WIDTH = 380`
- `main_dock_dialogs.py` の `ImageDialog.__init__` の `self.resize(1100, 650)` を
  `self.resize(UIDialogSizes.IMAGE_DIALOG_WIDTH, UIDialogSizes.IMAGE_DIALOG_HEIGHT)` に、
  `GridInputDialog.__init__` の `self.setMinimumWidth(380)` を
  `self.setMinimumWidth(UIDialogSizes.GRID_DIALOG_MIN_WIDTH)` に置き換え。
- 探索の結果、`ModelessSectionDialog`（設定/出力タブの汎用ラッパー）には
  幅・高さのハードコードは存在しなかった（生成元コンテンツウィジェットの
  サイズに追従する設計のため）。個別ウィジェット（spin_x 等）の
  `setMinimumWidth(70)` 等、ダイアログ全体の幅・高さではないフィールド単位
  の指定は本タスクのスコープ外と判断し変更していない。

### ③ 未定数化メッセージの回収
`main_dock_constants.py` の `UIMessages` に、依頼で列挙された箇所に対応する
定数を追加し、該当箇所を定数参照へ置き換えた。
- `main_dock_dialogs.py`: `MSG_CONFIRM_DELETE_REF`
- `tab1_georef_mixin.py`: `MSG_CONFIRM_DELETE_LAYER_TITLE` /
  `MSG_CONFIRM_DELETE_LAYER` / `MSG_CONFIRM_POINTS_EXIST_TITLE` /
  `MSG_CONFIRM_POINTS_EXIST` / `MSG_DELETE_LAYER_SUCCESS_TITLE` /
  `MSG_DELETE_LAYER_SUCCESS` / `ERR_LAYER_META_NOT_FOUND` /
  `MSG_RENAME_LAYER_SUCCESS_TITLE` / `MSG_TRANSFORM_COMPLETE_TITLE` /
  `ERR_IMAGE_FILE_NOT_FOUND`
- `tab2_digitizing_mixin.py`: `ERR_TITLE_DIGITIZE` / `ERR_DIGITIZE_REQUIRED` /
  `ERR_TITLE_DUPLICATE_DIGITIZE` / `MSG_DUPLICATE_POINT`
  （新規遺構名未入力エラーは既存の `UIMessages.ERR_NEW_FEATURE_REQUIRED` /
  `ERR_TITLE_INPUT` と文言が完全一致していたため新規定数を作らず既存定数を
  再利用。また、1119-1123行目の重複ポイント警告（既存定数
  `ERR_TITLE_DUPLICATE` を使用済みで本文のみ未定数化だった箇所）も同じ
  `MSG_DUPLICATE_POINT` を再利用する形で合わせて定数化した）。
- 追加調査（src/*.py 全体をQMessageBox/pushMessage呼び出しでgrep）で
  `plugin.py` にも未定数化リテラルが複数見つかったため、同じ命名規則で
  `UIMessages` に追加し置き換えた: `MSG_TITLE_PLUGIN` /
  `MSG_UNSAVED_CHANGES_TITLE` / `MSG_UNSAVED_CHANGES` /
  `ERR_TITLE_SESSION` / `ERR_SESSION_INIT_FAILED` / `MSG_STEP1_READY`。
  `plugin.py` はこれまで `main_dock_constants` を import していなかったため、
  新規に `from .main_dock_constants import UIMessages` を追加している
  （`main_dock_constants.py` は `core_logic.py` のみに依存する純粋な定数
  モジュールであり、`main_dock.py` 自体には依存しないため、plugin.py の
  「Step 1環境ではmain_dockが無くてもよい」という既存の遅延import設計との
  循環依存・インポート失敗リスクはない）。
- QAction のラベルやメニュー名（`"点群座標取得"` / `"&点群座標取得"`）は
  QMessageBox/messageBarの対象外であり、本タスクの回収対象に含めていない。

### ④ 確認ダイアログのボタン整列
- `style_helper.py` の `UIStyleHelper` に新規ヘルパー
  `build_centered_button_row(buttons, spacing=12, button_stretch=1)` を追加。
  `start_dialog.py` の `StartDialog`（addStretch(1) → btn_ok → btn_cancel →
  addStretch(1)）と同じパターンを共通化したもの。
- `main_dock_dialogs.py` の `GridInputDialog._init_ui()` 内、確定/キャンセル
  ボタン行（旧: `QHBoxLayout` + `addWidget(btn, 1)` のみで中央寄せなし）を
  `UIStyleHelper.build_centered_button_row([self.btn_confirm, self.btn_cancel])`
  に置き換え、中央寄せ・等幅表示に統一した。
- Tier2の「選択点を削除」ボタン（単独の全幅ボタン）は確認ダイアログの
  確定/キャンセルの対のボタンではなく、既存レイアウト（`layout.addWidget`
  で全幅表示）のままとした。本タスクの対象は「確認ダイアログ・ボタン配置」
  であり、単独ボタンの整列変更は依頼の記述（GridInputDialog含む確認ダイアログ
  のボタン整列）の対象外と判断。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンド未設定のため、`python3 -m py_compile`
による構文確認のみ実施。対象7ファイルすべて成功）。

## スコープ外変更の有無
なし。依頼された4点（main_dock.py/main_dock_constants.py/main_dock_dialogs.py/
tab1_georef_mixin.py/tab2_digitizing_mixin.py/style_helper.py）に加え、依頼文中で
明示的に許可された「探索範囲はsrc/*.py全体」の指示に基づき plugin.py の未定数化
メッセージも合わせて回収した（依頼③の追記指示の範囲内）。それ以外のファイル・
機能には手を入れていない。
