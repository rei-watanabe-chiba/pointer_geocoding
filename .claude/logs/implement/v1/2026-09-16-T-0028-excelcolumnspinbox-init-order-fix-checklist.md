## 人手確認チェックリスト

### 確認手順
1. QGISを起動し、`pointer_geocoding`プラグインを有効化する（起動ダイアログ = StartDialogが表示される、またはプラグイン起動操作を行う）。
2. 起動ダイアログのY軸範囲入力欄（ExcelColumnSpinBox、"A".."ZZ"のExcel列風表記）に、半角英大文字1〜2文字（例: "A", "ZZ", "M"）を入力する。
3. Y軸範囲入力欄に不正な文字（数字・記号・3文字以上の英字等）を入力しようとする。

### 各手順で期待される挙動（設計書ベース）
- 手順1: `.claude/logs/implement/2026-09-15-T-0026-start-dialog-xy-range.md`（T-0026実装ログ）の記述に基づき、起動ダイアログが`AttributeError: 'ExcelColumnSpinBox' object has no attribute '_validator'`を発生させずに正常表示されること。
- 手順2: `src/start_dialog.py`の`ExcelColumnSpinBox`クラス（T-0026で追加、MIN_VALUE=1〜MAX_VALUE=702='ZZ'）の仕様通り、半角英大文字1〜2文字がそのまま受理され、スピンボックスの表示・値変換（`to_excel_column`/`from_excel_column`）が引き続き正しく機能すること。
- 手順3: `ExcelColumnSpinBox.validate()`が引き続き正規表現`^[A-Za-z]{1,2}$`で入力を制限し、不正な文字の入力が拒否またはブロックされること（今回の修正は初期化順序の入れ替えのみで、バリデーションのロジック自体は変更していないため、T-0026時点の挙動が維持されるはず）。

### 注意喚起
- 本修正は`ExcelColumnSpinBox.__init__()`内の2つの処理ブロックの順序入れ替えのみであり、ロジック変更は行っていない。ただし、Qtの内部実装（`QSpinBox.setRange()`が`validate()`を呼び出すタイミング）に起因する不具合であったため、実際にQGIS上でエラーが再発しないことの確認が最重要。
- 影響範囲は起動ダイアログのY軸範囲スピンボックスのみ（X軸範囲は通常のQSpinBoxのため影響なし）。
