## タスクID
T-0029

## 変更ファイル一覧
- `src/start_dialog.py`

## 変更概要
- 「グリッド設定」パネルのグリッドCSV選択欄（Row 0）の直後に、`QRadioButton`+`QButtonGroup`によるグリッドモード選択行（「新規作成・更新」/「CSVファイル利用」、初期選択は前者）を追加した。
- `UI_CONFIG["LABELS"]`に`GRID_MODE`/`RADIO_GRID_MODE_NEW`/`RADIO_GRID_MODE_USE_CSV`を追加。
- 旧`_on_grid_csv_changed`の本体ロジックを共通処理`_apply_grid_mode_state()`に切り出し、`_on_grid_csv_changed`（`edit_grid_csv.textChanged`）と新設の`_on_grid_mode_changed`（`radio_grid_mode_new.toggled`）の両方から呼び出す形にリファクタリングした。
  - `enable_inputs = not radio_grid_mode_use_csv.isChecked()` により、原点・X/Y範囲の各スピンボックス（ラベル含む）の有効/無効を「新規作成・更新」＝常時有効、「CSVファイル利用」＝常時無効、で切り替える。
  - CSVパスが有効なファイルを指す場合は、モードに関わらず`_extract_csv_metadata()`の結果を都度スピンボックスへ反映する（新規作成モードでは反映後も編集可能なまま維持、CSVファイル利用モードでは反映後に無効化）。
  - モード切替時、直前に反映された値はクリアせずそのまま保持する（`_apply_grid_mode_state`は現在のスピンボックス値を書き換えず、CSVパスが無効/未設定の場合は値に触れない）。
  - プレビュー系ウィジェットは従来通り常時有効のまま。
- `_validate_and_accept()`のX/Y範囲バリデーション条件を`if not grid_csv:`から`if not (radio_grid_mode_use_csv.isChecked() and grid_csv):`に変更。「CSVファイル利用」モードで有効なCSVパスが指定されている場合のみバリデーションをスキップ（CSV由来の値を信頼）し、それ以外（新規作成・更新モード、CSV未指定時など）は従来通りmin>maxチェックを行う。
- `get_session_data()`の`grid_config`に`grid_mode`（`"NEW"`/`"USE_CSV"`、既存の`session_type`キーの命名規則に合わせた）を追加し、`use_existing_csv`を`bool(use_csv_mode and grid_csv)`に変更（従来は`bool(grid_csv)`のみで判定しており、新規作成・更新モードでCSVをテンプレートとして読み込んだ場合でも誤って`use_existing_csv=True`になっていた不整合を解消）。
- ダイアログ初期化時（`__init__`）の呼び出しを`self._update_grid_coordinate_preview()`から`self._apply_grid_mode_state()`に変更し、初期表示から新設ラジオボタンの状態（新規作成・更新＝有効）を反映するようにした。
- プレースホルダ文言（`PLACEHOLDERS.GRID_CSV`）を、CSV選択時に常に無効化されるわけではなくなったことに合わせて更新。

## 自動テスト実行結果
自動テストなし（`python3 -m py_compile src/start_dialog.py`による構文チェックのみ実施し、エラーなし）。

## スコープ外変更の有無
なし。`src/grid_csv_mixin.py`・`src/plugin.py`・`src/session_io_mixin.py`側は`grid_config`の既存キー（`use_existing_csv`/`csv_path`/`origin_x`等）をそのまま参照する実装のままで変更不要であることを確認済み（変更はしていない）。
