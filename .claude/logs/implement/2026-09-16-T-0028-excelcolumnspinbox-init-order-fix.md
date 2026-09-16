## タスクID
T-0028

## 変更ファイル一覧
- `src/start_dialog.py`

## 変更概要
`ExcelColumnSpinBox.__init__()`（T-0026で追加されたクラス）において、`self.setRange(self.MIN_VALUE, self.MAX_VALUE)`の呼び出しが`self._validator`の生成より先に行われていたため、`setRange()`内部から呼ばれる可能性のあるオーバーライド済み`validate()`が`self._validator`未設定の状態で実行され、`AttributeError: 'ExcelColumnSpinBox' object has no attribute '_validator'`が発生していた（ユーザー報告: QGIS起動時のエラー）。

修正として、`__init__()`内の処理順序を入れ替え、`HAS_QT_REGEX`分岐による`self._validator`生成（`QRegularExpressionValidator`または`QRegExpValidator`）を`self.setRange(...)`より前に移動した。ロジック自体（バリデータの生成内容・範囲の値）は変更していない。

## 自動テスト実行結果
自動テストなし

## スコープ外変更の有無
なし。`src/start_dialog.py`の`ExcelColumnSpinBox.__init__()`メソッド内の処理順序入れ替えのみ。他メソッド・他ファイルへの変更は行っていない。

なお、本タスクに付随して以下のドキュメント更新のみ実施（スコープ内の運用作業）:
- `.claude/state/tasks.md`: T-0026を「再オープン(T-0028へ)」に更新、T-0028行を追加
