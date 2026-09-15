## タスクID
T-0030（T-0029フォローアップ）

## 変更ファイル一覧
- `src/start_dialog.py`

## 変更概要
`StartDialog._apply_grid_mode_state()` を以下のように修正した。

- 冒頭で `edit_grid_csv` のパスから `_extract_csv_metadata()` を呼び出し、その結果（`metadata`）を
  関数全体で共有するように変更（従来は関数末尾で個別に再抽出していた処理を先頭に移動・一本化）。
- `metadata is None`（パス不正・ファイル読込不可・パース失敗のいずれか）の場合を `csv_valid = False` として判定し、
  - `self.radio_grid_mode_use_csv.setEnabled(csv_valid)` により「CSVファイル利用」ラジオボタン自体を無効化する。
  - このとき「CSVファイル利用」が選択中であれば、`radio_grid_mode_new` / `radio_grid_mode_use_csv` 双方の
    `blockSignals(True/False)` で囲みつつ `radio_grid_mode_new.setChecked(True)` を呼び、
    「新規作成・更新」へ強制的に切り替える（`toggled` シグナルの再帰呼び出しを防止するため）。
  - CSVが有効な状態（`csv_valid = True`）に戻った場合は、`setEnabled(True)` により自動的に再有効化される。
- 原点座標・X範囲・Y範囲のスピンボックスへの値反映処理（`if metadata: ...` ブロック）は、
  上記で先頭に一本化した `metadata` 変数をそのまま使う形に変更しただけで、**反映条件（`metadata` が
  truthy であること＝CSV読込成功時のみ）は変更していない**。CSV読込失敗時にこのブロックへ到達することは
  なく、モード強制切替のロジックとも独立しているため、切替時にスピンボックスの値が変化することはない。
- `_validate_and_accept()` のバリデーションスキップ条件
  (`if not (self.radio_grid_mode_use_csv.isChecked() and grid_csv): ...`) は変更していない。
  無効なCSVの場合は本修正により `radio_grid_mode_use_csv` が非チェック状態に強制されるため、
  この条件は従来通り矛盾なく機能する（スキップされず通常のレンジバリデーションが走る）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。
`python3 -m py_compile src/start_dialog.py` による構文チェックのみ実施し、エラーなし。

## スコープ外変更の有無
なし。`src/start_dialog.py` 内の `_apply_grid_mode_state()` およびその直下の1ブロックのみを変更し、
他のファイル・他の関数には変更を加えていない。
