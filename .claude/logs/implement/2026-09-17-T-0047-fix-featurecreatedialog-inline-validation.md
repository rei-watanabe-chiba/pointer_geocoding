## タスクID
T-0047 追加修正（FeatureCreateDialogのバリデーションエラー表示をインライン方式へ戻す）

## 変更ファイル一覧
- `src/ui/dialogs.py`

## 変更概要
- T-0047適用前の`FeatureCreateDialog`は、確定ボタン押下時に`self.lbl_error`（`color: #C62828`のインライン赤字ラベル）へ`UIMessages.ERR_NEW_FEATURE_REQUIRED`を表示していたが、T-0047で`RequiredValidator` + `show_validation_error()`（`QMessageBox.warning`）方式に変更されてしまっていた。
- 本修正で、直前に同種の問題を修正した`PointNameEntryDialog`（コミット`40205e6`）と統一感のある実装に戻した。
- **実装方式の判断理由**: `FeatureCreateDialog`は「遺構名」1項目のみの必須チェックであり、`PointNameEntryDialog`のように複数項目（点名/枝番、SP/非SP切替）を扱う複雑さはない。しかし、単純な`lbl_error`（素のQLabel + 手動`show()/hide()`）に戻すのではなく、`PointNameEntryDialog`と同じ`UIStyleHelper.create_status_panel()`/`update_status_panel()`パターンに揃えた。理由は以下の通り。
  - `GridInputDialog`（Tier4）と`PointNameEntryDialog`が既に同一パターンを採用しており、`dialogs.py`内の3ダイアログでインラインエラー表示方式を統一できる（素の`lbl_error`だけこのダイアログに残すと、かえって表示パターンが分散する）。
  - `create_status_panel`/`update_status_panel`はQFrame+QLabelの生成とスタイル更新をカプセル化した既存のヘルパーであり、独自に`setStyleSheet`/`setWordWrap`/`hide()`/`show()`を書き直すより行数・保守コストが小さい。
  - 項目数が1つであっても、"info"（非表示相当の空文字）/"error"の2状態を`status_type`引数で表現でき、過度な抽象化とは言えない（`create_status_panel`自体は既存のプロジェクト標準部品であり、新規抽象を導入するわけではない）。
- 具体的な変更内容:
  - `FeatureCreateDialog.__init__`で、`self.panel_status`/`self.lbl_status`を`UIStyleHelper.create_status_panel("", status_type="info", parent=self)`で生成し、`input_panel`とアクション行の間に配置。
  - `self.edit_name.textChanged`に`self._on_realtime_validate`を接続し、リアルタイムに`RequiredValidator(UIMessages.ERR_NEW_FEATURE_REQUIRED)`を実行、失敗時は`panel_status`を`error`状態にして`btn_ok`を無効化、成功時は空文字＆`info`状態に戻し`btn_ok`を有効化する（`PointNameEntryDialog._on_realtime_validate`と同型）。
  - `_on_ok_clicked`は、確定時の`QMessageBox`呼び出し（`show_validation_error`）を廃止し、防御的に同じバリデーションを再実行して`panel_status`へ反映する形に変更（`PointNameEntryDialog._on_ok_clicked`のSP必須チェック部分と同型）。通常はリアルタイム検証で`btn_ok`が無効化されているため、この分岐に到達することは想定していない。
  - `from .core.validators import RequiredValidator, DuplicateValidator, show_validation_error` から `show_validation_error` を削除（`dialogs.py`内での使用箇所がコメントのみとなり、未使用importとなるため）。`RequiredValidator`/`DuplicateValidator`は`PointNameEntryDialog`側で引き続き使用しており変更なし。
- `show_validation_error`は`src/ui/tab1_image.py`・`src/ui/start_dialog.py`で個別にimportして使用しており、本修正による影響はない。

## 自動テスト実行結果
自動テストなし（`python3 -m py_compile src/ui/dialogs.py` による構文チェックのみ実施し、エラーなし）。

## スコープ外変更の有無
なし。`src/ui/dialogs.py`のみを変更した（依頼時の想定通り）。`src/ui/schemas.py`（`FEATURE_CREATE_INPUT_SPEC`等）は変更不要だったため未変更。`.claude/state/tasks.md`のT-0047行に本追加修正のログパスを追記したが、これは依頼内の「完了時の作業」に含まれる状態管理更新であり、スコープ外変更ではない。
