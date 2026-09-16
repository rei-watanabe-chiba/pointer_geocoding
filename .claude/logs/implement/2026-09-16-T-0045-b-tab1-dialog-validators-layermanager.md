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

---

## 追記: T-0045-b 延長（Validatorのエラー表示ヘルパー化）

### タスクID
T-0045-b（延長）: `.claude/state/v2-coreui-plan.md`「T-0045-b 延長: Validatorのエラー表示ヘルパー化」節

### 変更ファイル一覧
- `src/ui/core/validators.py`（変更、116行→144行、`show_validation_error()`関数を追加）
- `src/ui/tab1_image.py`（変更、1047行→1046行）

### 変更概要
`src/ui/core/validators.py`に`show_validation_error(parent, title, result: ValidationResult,
focus_widget=None) -> None`関数を追加した。`result.is_valid`がFalseの場合に
`QMessageBox.warning(parent, title, result.message)`を表示し、`focus_widget`が指定されていれば
`.setFocus()`を呼ぶ。`is_valid`がTrueの場合は何もしない（呼び出し側は`if not result.is_valid: return`と
組み合わせて使う）。`QMessageBox`/`QWidget`のimportは`tab1_image.py`と同じ`qgis.PyQt.QtWidgets`から
行った。

`tab1_image.py`の`_on_confirm_image_clicked`内、新規追加モード分岐の3箇所
（`RequiredValidator`/`RegexValidator`/`DuplicateValidator`）を、各Validatorのコンストラクタに既存の
エラーメッセージ文言（`UIMessages.ERR_REQUIRED_IMAGE_NAME`/`UIMessages.ERR_INVALID_IMAGE_NAME`/
`UIMessages.ERR_DUPLICATE_LAYER_NAME.format(name=layer_name)`）を`message`引数として渡す形に変更し、
判定→`QMessageBox.warning`直書き→`setFocus`→`return`（4〜6行）を、
`result = Validator(...).validate(value)` / `if not result.is_valid: show_validation_error(...); return`
の2〜3行に圧縮した。エラータイトル（`UIMessages.ERR_TITLE_INPUT`/`ERR_TITLE_DUPLICATE`）・メッセージ
文言・フォーカス先ウィジェット（`self.edit_image_name`）はすべて変更前と同一のものを使用しており、
表示挙動は変更していない。importを`from .core.validators import (RequiredValidator, RegexValidator,
DuplicateValidator, show_validation_error)`に更新した。

`_on_rename_layer_clicked`内の同種チェックは、今回のスコープ（`_on_confirm_image_clicked`内の3箇所）に
含まれないため変更していない。

`src/ui/core/__init__.py`は、タスク指示で「対象は`validators.py`、`tab1_image.py`のみ」と明示されて
いたため、`show_validation_error`のexport追加は行っていない（`tab1_image.py`は`.core.validators`から
直接importしており、`.core`パッケージ経由のexportに依存していないため動作上の支障はない）。

### 行数の変化
- `src/ui/tab1_image.py`: 1047行 → 1046行（純減1行。3箇所とも「判定4〜6行→2〜3行」に圧縮された分、
  コメント2行を追記した影響で差引はわずかとなった）
- `src/ui/core/validators.py`: 116行 → 144行（`show_validation_error`関数本体・docstring・import追加分、
  +28行）

### 自動テスト実行結果
自動テストなし（`python3 -m py_compile src/ui/core/validators.py src/ui/tab1_image.py`によるバイト
コンパイル確認のみ実施し、両ファイルとも構文エラーがないことを確認した。実行時動作の保証はしない）。

### スコープ外変更の有無
なし。指示された2ファイル（`src/ui/core/validators.py`, `src/ui/tab1_image.py`）のみを変更した。
`src/ui/core/__init__.py`・`src/ui/constants.py`・`_on_rename_layer_clicked`等、スコープに含まれない
箇所には触れていない。
