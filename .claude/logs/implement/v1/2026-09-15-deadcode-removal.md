## タスクID
デッドコード削除(A+B+C全区分)

## 変更ファイル一覧
- `src/tab1_georef_mixin.py`
- `src/main_dock.py`
- `src/tab2_digitizing_mixin.py`
- `src/main_dock_constants.py`
- `src/layer_manager.py`

## 変更概要

### 区分A(安全確度高)
1. `src/tab1_georef_mixin.py`: `_on_show_preview_clicked()`メソッド（`_on_setup_ref_points_clicked()`への後方互換別名）を削除。
   - 削除前確認: `Grep pattern="_on_show_preview_clicked|_on_execute_georef_clicked" path=src` を実行し、定義箇所（`tab1_georef_mixin.py:536`）以外に呼び出し箇所が0件であることを確認した。
2. `src/tab1_georef_mixin.py`: `_on_execute_georef_clicked()`メソッド（`_on_export_layer_clicked()`への後方互換別名）を削除。
   - 削除前確認: 上記と同一のgrep結果により、定義箇所（`tab1_georef_mixin.py:968`）以外に呼び出し箇所が0件であることを確認した。
3. `src/main_dock.py`の`self.current_image_ext: str = ""`属性初期化(96行目)、および`src/tab1_georef_mixin.py`内で当該属性に値をsetしている2箇所（`_browse_image_file()`内、`_on_confirm_image_clicked()`内）を削除。
   - 削除前確認: `Grep pattern="current_image_ext" path=src` を実行し、`main_dock.py`の初期化1箇所と`tab1_georef_mixin.py`のset箇所2箇所（読み取り箇所は0件）であることを確認した。

### 区分B(要確認だったが削除許可済み)
4. `src/tab2_digitizing_mixin.py`の`self.group_excavation = self.group_category` / `self.group_feature = self.row_feature_selector`という属性エイリアス代入（コメント「Backward compatibility alias」付き、2行）を削除。
   - 削除前確認: `Grep pattern="group_excavation|group_feature" path=src` を実行し、代入箇所（`tab2_digitizing_mixin.py:228-229`）以外に読み取り参照が0件であることを確認した。

### 区分C(判断保留だったが削除許可済み)
5. `src/main_dock_constants.py`の未使用UI定数5個を削除: `UILabels.BTN_SHOW_PREVIEW`, `UILabels.BTN_EXECUTE_TRANSFORM`, `UILabels.GROUP_IMAGE`, `UILabels.GROUP_EXCAVATION`, `UILabels.GROUP_FEATURE`。
   - 削除前確認: `Grep pattern="BTN_SHOW_PREVIEW|BTN_EXECUTE_TRANSFORM|GROUP_IMAGE|GROUP_EXCAVATION|GROUP_FEATURE" path=src` を実行し、定義箇所（`main_dock_constants.py`内5行）以外に参照が0件であることを確認した。
6. `src/layer_manager.py`のdefensive re-export（`layer_manager_models`から`PluginSettings`/`RefPointMeta`/`ImageLayerMeta`/`get_local_crs`/`suppress_crs_prompt`を再exportしていたimport文とそれに付随するコメントブロック）を削除。
   - 削除前確認: `layer_manager.py`全文（113行）を読み、これらの名前が同モジュール内で実際に使用されていない（コメントにも「not used directly in this module's own body」と明記されていた）ことを確認。
   - `Grep pattern="from \.layer_manager import|from src\.layer_manager import" path=src` を実行し、`layer_manager.py`を外部からimportしているのは`plugin.py`の`from .layer_manager import LayerManager`のみで、`PluginSettings`等の名前をこの経路でimportしている箇所は0件であることを確認した。
   - `Grep pattern="layer_manager\.(PluginSettings|RefPointMeta|ImageLayerMeta|get_local_crs|suppress_crs_prompt)" path=src` も0件であることを確認した。
   - `layer_manager.py`が内部（mixin群経由ではなく自身の関数本体）で`PluginSettings`等を直接使用している箇所はなかったため、import自体を削除した（mixin側は各自`layer_manager_models`から直接importしており、今回の変更の影響を受けない）。

## docs追従修正
`docs/integrated_master_design.md`に対し、上記削除対象の識別子（`_on_show_preview_clicked`, `_on_execute_georef_clicked`, `current_image_ext`, `group_excavation`, `group_feature`, `BTN_SHOW_PREVIEW`, `BTN_EXECUTE_TRANSFORM`, `GROUP_IMAGE`, `GROUP_EXCAVATION`, `GROUP_FEATURE`）でgrepしたが、言及箇所は0件だったため、設計書への追従修正は行っていない。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定）。

代わりに静的構文チェックとして `py -m py_compile src/*.py` を実行し、`src/`配下の全Pythonファイルが構文エラーなくコンパイルできることを確認した（出力: `COMPILE_OK`。なお `Could not find platform independent libraries <prefix>` は本環境のPythonインストール構成に起因する無関係な警告であり、コンパイル結果には影響しない）。

## スコープ外変更の有無
なし。依頼された6項目の削除以外のコード変更は行っていない。
