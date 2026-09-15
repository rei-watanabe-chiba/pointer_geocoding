## タスクID
Stage C: layer_manager.py のMixinベース分割

## 変更ファイル一覧
- `src/layer_manager_models.py`（新規）
- `src/settings_metadata_mixin.py`（新規）
- `src/symbology_mixin.py`（新規）
- `src/gpkg_cache_mixin.py`（新規）
- `src/grid_csv_mixin.py`（新規）
- `src/session_io_mixin.py`（新規）
- `src/layer_manager.py`（大幅縮小・更新）
- `docs/integrated_master_design.md`（§1.3ツリー図、§1.4モジュール構成の更新）

## 変更概要
`src/layer_manager.py`（分割前、約1,360行、`LayerManager(QObject)`単一クラス）を、指示された構成に従い機械的に分割した。ロジックの変更は行わず、コードの移動とimport文の追加・整理のみを行った。

- `layer_manager_models.py`: `PluginSettings`/`RefPointMeta`/`ImageLayerMeta`の各dataclass、`get_local_crs()`、`suppress_crs_prompt()`をそのまま移動。他のmixin・`layer_manager.py`本体には依存しない（qgis.core標準ライブラリのみに依存）。
- `settings_metadata_mixin.py`: `SettingsMetadataMixin`クラスとして、`get_settings_path`/`DEFAULT_SETTINGS`（クラス属性として定義）/`load_settings`/`load_settings_dataclass`/`save_settings`/`ensure_json_dir`/`get_image_metadata_path`/`load_image_metadata`/`save_image_metadata`/`update_image_metadata`/`delete_image_metadata`を移動。
- `symbology_mixin.py`: `SymbologyMixin`クラスとして、`apply_point_labeling`（staticmethod）/`apply_ref_point_symbology`（staticmethod、内部で`from .main_dock import UIConfig`の遅延importをそのまま維持）を移動。
- `gpkg_cache_mixin.py`: `GpkgCacheMixin`クラスとして、`create_gpkg_layer`/`create_initial_gpkg`/`check_and_migrate_point_layer`/`_extract_field_str`/`_safe_str`/`init_spatial_index_and_cache`/`_disconnect_point_layer_signals`/`_on_feature_added`/`_on_features_deleted`/`_on_attribute_changed`/`_on_geometry_changed`を移動。
- `grid_csv_mixin.py`: `GridCsvMixin`クラスとして、`generate_grid_csv`/`setup_or_copy_grid_csv`/`load_grid_csv_to_memory`を移動。
- `session_io_mixin.py`: `SessionIOMixin`クラスとして、`setup_new_session`/`copy_image_to_session`/`write_world_file`/`load_preview_raster`/`load_georeferenced_raster`/`save_ref_points`/`load_existing_session`/`save_project`を移動。
- `layer_manager.py`: `class LayerManager(QObject, SettingsMetadataMixin, SymbologyMixin, GpkgCacheMixin, GridCsvMixin, SessionIOMixin):`に変更。クラスdocstring、`pyqtSignal`宣言3つ（`metadata_updated`/`layer_deleted`/`settings_changed`、いずれもQObjectを継承する本体クラスに残置）、`__init__`、`session_image_dir`/`session_json_dir`プロパティのみを残した。`layer_manager_models`の5シンボル（`PluginSettings`/`RefPointMeta`/`ImageLayerMeta`/`get_local_crs`/`suppress_crs_prompt`）は、本体では未使用だが、念のため後方互換の再exportとしてコメント付きでimportを維持した（`src/`全体grepの結果、外部からの直接import箇所はなかったため必須ではないが、安全策として残した）。

### 事前確認（再grep結果）
- `PluginSettings`/`RefPointMeta`/`ImageLayerMeta`/`get_local_crs`/`suppress_crs_prompt`/`DEFAULT_SETTINGS`を`layer_manager`モジュールから直接importしている他ファイルは存在しないことを再確認した（`grep -rn "PluginSettings\|RefPointMeta\|ImageLayerMeta\|get_local_crs\|suppress_crs_prompt\|DEFAULT_SETTINGS\|layer_manager import\|layer_manager\." src`）。
- `LayerManager.xxx(...)`のようなクラス経由の静的呼び出しも見つからず、すべてインスタンス経由（`self.layer_manager.xxx(...)`等）であることを確認した。
- `src/plugin.py:16`の`from .layer_manager import LayerManager`が分割後も解決可能な構成であることをコードレベルで確認した（`LayerManager`クラスは`layer_manager.py`にそのまま存在）。

### メソッド名集合の突き合わせ結果
分割前後で`grep -n "^    def \|^def \|^class "`によりメソッド名集合を突き合わせ、以下を確認した。
- dataclass（`PluginSettings`/`RefPointMeta`/`ImageLayerMeta`）のメソッド群: `layer_manager_models.py`に過不足なく移動（欠落・重複なし）。
- `get_local_crs`/`suppress_crs_prompt`: `layer_manager_models.py`に移動（欠落・重複なし）。
- `LayerManager`旧本体のメソッド・プロパティ34件（`__init__`/`session_image_dir`/`session_json_dir`を含む）: 各mixinファイルおよび新`layer_manager.py`本体に合計37件（プロパティ2件・`__init__`含む）として過不足なく分配されていることを確認した。mixin間・本体との間で同名メソッドの重複は存在しない。
  - 分割前後の内訳（件数一致を確認）:
    - `settings_metadata_mixin.py`: 10件
    - `symbology_mixin.py`: 2件
    - `gpkg_cache_mixin.py`: 11件
    - `grid_csv_mixin.py`: 3件
    - `session_io_mixin.py`: 8件
    - `layer_manager.py`本体: `__init__`+プロパティ2件 = 3件
    - 合計: 37件（分割前の`LayerManager`本体の全メンバー数と一致）

### 循環import対策
- `layer_manager_models.py`は他のmixin・`layer_manager.py`本体に一切依存しない（qgis.core標準ライブラリのみに依存）ことを確認。
- 各mixinファイルは`layer_manager_models`・qgis/PyQt標準ライブラリ・`core_logic`にのみ依存し、`layer_manager.py`本体や他のmixinへの直接importは行っていない（`symbology_mixin.py`の`apply_ref_point_symbology`内の`from .main_dock import UIConfig`は分割前から存在した遅延import・呼び出し時importであり、モジュールロード時の循環importは発生しない。元の`layer_manager.py`にあったものをそのまま移動）。

### ドキュメント更新
`docs/integrated_master_design.md`を以下の通り更新した（冒頭文の規約に従い、情報粒度を削除せず、矛盾箇所のみ改訂）。
- §1.3ツリー図: `layer_manager.py`の説明を更新し、新規6ファイル（`layer_manager_models.py`/`settings_metadata_mixin.py`/`symbology_mixin.py`/`gpkg_cache_mixin.py`/`grid_csv_mixin.py`/`session_io_mixin.py`）を追加。
- §1.4モジュール構成と役割: `layer_manager.py`の説明をMixin構成に合わせて更新し、新規6ファイルそれぞれの説明を追加。`main_dock_constants.py`の項で`layer_manager.py`が行っていた`from .main_dock import UIConfig`呼び出しの実体が`symbology_mixin.py`に移ったことを明記。
- `grep -n "layer_manager" docs/integrated_master_design.md`で本文中の全言及箇所（更新前6件・更新後7件）を洗い出し、確認した。§2.1/§2.4の「起点」表記（`plugin.py -> start_dialog.py -> layer_manager.py`、`main_dock.py (Tab 3) -> layer_manager.py -> map_tool.py`）および`LayerManager.save_settings()`の言及は、`LayerManager`クラス（モジュール）レベルの抽象度で書かれており、Stage B時の`main_dock.py (Tab N)`表記の踏襲と同様に、分割後も引き続き有効な記述であるため変更不要と判断した（具体的な所属Mixinファイルへの言及ではないため）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは設定されていない）。

`python -m py_compile` による構文チェックは実施した（`py -3 -m py_compile`、`src/*.py`全20ファイルに対して個別実行）。全ファイルで構文エラーなし（`__pycache__`に20件の`.pyc`が生成されたことを確認）。ただし、これはPython構文レベルの検証であり、QGIS環境での実際のimport解決・実行動作を保証するものではない。

## スコープ外変更の有無
なし。`src/layer_manager.py`から分割した新規6ファイルの作成、`layer_manager.py`本体の更新、および`docs/integrated_master_design.md`の該当箇所更新のみを行った。他のファイル（`main_dock.py`、`tab1_georef_mixin.py`、`tab2_digitizing_mixin.py`、`tab3_settings_mixin.py`、`map_tool.py`、`plugin.py`、`transform.py`等）には一切手を加えていない。
