## タスクID
T-0045-b（T-0045の追加試行: tab1におけるCoreUI化・機能分離の追加試行、②③④）

## 変更ファイル一覧
- `src/ui/tab1_image.py`（変更、1059行→1047行）
- `src/ui/core/validators.py`（新設、115行）
- `src/ui/core/__init__.py`（変更、Validator系クラスのexport追加）
- `src/layer/manager.py`（変更、99行→150行、`safe_get_str`のimport追加）

## 変更概要

### ②座標変換後ダイアログの廃止
`_on_transform_clicked()`末尾にあった`QMessageBox.information()`呼び出し（回転角度・アスペクト比を
表示するモーダルダイアログ、約11行）を削除。同内容は既に`self.lbl_tab1_info_3_6`（情報パネルの
line3_6、`res_summary`変数）に表示済みであり、削除箇所の直前でセットされていることを確認済み。
`self.iface.messageBar().pushMessage(...)`（4秒成功通知）とステータスパネル更新
（`UIStyleHelper.update_status_panel(..., UILabels.TAB1_INFO_TRANSFORM_DONE, status_type="success")`）は
そのまま残した。
削除箇所に理由を説明するコメントを追加した。
なお、`UIMessages.MSG_TRANSFORM_COMPLETE_TITLE`（`src/ui/constants.py`）は本変更後に参照箇所がなくなる
（未使用定数として残る）が、`constants.py`は今回のスコープ外ファイルのため変更していない。

### ③バリデーションヘルパーの汎用化
`src/ui/core/validators.py`を新設し、以下3クラス＋共通結果型`ValidationResult`
（`is_valid: bool, message: str`のdataclass）を実装した。
- `Validator`（ABC、`validate(value) -> ValidationResult`）
- `RequiredValidator`: 文字列が空/空白のみでないことをチェック
- `RegexValidator(pattern, reject_if_match=True)`: 正規表現マッチの有無で合否判定
  （デフォルトは「マッチしたら不合格」=禁止文字パターン向け。`reject_if_match=False`で
  「マッチしなければ不合格」も表現可能）
- `DuplicateValidator(exists_check: Callable)`: 呼び出し側が渡す判定callableの戻り値で重複判定。
  `logic.core.check_point_duplicate`等の業務ロジックには一切依存しない汎用設計。

`tab1_image.py`の`_on_confirm_image_clicked`（新規追加モード分岐）内、既存の3チェック
（image_name必須／禁止文字正規表現／layer_name重複）を、上記Validatorクラス経由の判定に置き換えた。
判定結果（`.is_valid`）のみを条件分岐に使い、エラーメッセージ・`QMessageBox.warning`呼び出し・
`setFocus()`等の表示処理は既存コードのまま変更していない（Validator側の`message`引数は今回未使用。
将来他画面で流用する際の共通インターフェースとして用意）。
`_on_rename_layer_clicked`内の同種チェックは、タスク指示（`_on_confirm_image_clicked`内のみが対象）に
従い変更していない。

`src/ui/core/__init__.py`に`Validator`/`ValidationResult`/`RequiredValidator`/`RegexValidator`/
`DuplicateValidator`のexportを追加した（既存の`ButtonDef`等と同様のパッケージ公開パターンに合わせた）。

### ④レイヤー管理の共通部品化
`src/layer/manager.py`の`LayerManager`クラスに以下2メソッドを追加した。
- `clear_drawing_name_for_layer(layer_name: str) -> None`: `point_layer`上でdrawing_name==layer_nameの
  featureのdrawing_nameを空文字にクリアする。`_on_delete_layer_clicked`が直接行っていた
  `startEditing`/`indexFromName`/`getFeatures`ループ/`changeAttributeValue`/`commitChanges`を移植。
- `rename_drawing_name(old_name: str, new_name: str) -> None`: 同様にdrawing_name==old_nameの
  featureをnew_nameへ更新する。`_on_rename_layer_clicked`が直接行っていた同パターンを移植。
両メソッドとも、`point_layer`が未設定/invalid、または`drawing_name`フィールドが存在しない場合は
no-op（移植元の既存ガード条件と同一）。

`safe_get_str`（`src/logic/core.py`）を`manager.py`にimportし、両メソッド内のfeature属性読み取りに使用
（`tab1_image.py`側で既に使われていたものと同じ関数・同じ呼び出し方）。循環importの懸念を確認済み
（`logic/core.py`は`layer`パッケージに依存していない）。

`tab1_image.py`側:
- `_on_delete_layer_clicked`: `self.point_layer.startEditing()`〜`commitChanges()`の5行を
  `self.layer_manager.clear_drawing_name_for_layer(layer_name)`の1行に置き換えた。
- `_on_rename_layer_clicked`: 同様に`self.layer_manager.rename_drawing_name(old_name, new_name)`の
  1行に置き換えた。

## 自動テスト実行結果
自動テストなし（`python3 -m py_compile`によるバイトコンパイル確認のみ実施し、構文エラーがないことを
確認した。実行時動作の保証はしない）。

対象ファイル: `src/ui/tab1_image.py`, `src/ui/core/validators.py`, `src/ui/core/__init__.py`,
`src/layer/manager.py` — いずれも`py_compile`が正常終了した。

## スコープ外変更の有無
なし。指示された3ファイル（`src/ui/tab1_image.py`, `src/ui/core/validators.py`新設,
`src/layer/manager.py`）のみを変更した（`src/ui/core/__init__.py`は、新設した`validators.py`を
既存の`ButtonDef`等と同様にパッケージから公開するための付随的な変更であり、`src/ui/core/`パッケージ内の
一部として扱った）。`tab2_plot.py`/`start_dialog.py`/`src/ui/constants.py`等には触れていない。
`src/ui/constants.py`の`MSG_TRANSFORM_COMPLETE_TITLE`が未使用定数として残る点は上記「変更概要」に
記載の通り、スコープ外ファイルのため意図的に手を入れていない。
