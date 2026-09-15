## 人手確認チェックリスト

### 確認手順
1. QGIS（対応バージョン3.22〜3.99）でプラグイン「点群座標取得」(pointer_geocoding)を読み込み、プラグインメニュー/ツールバーからエラーなく起動できることを確認する。
2. StartDialogで「新規セッション」を選択し、親フォルダ・セッション名・測量グリッドの原点/範囲を入力して確定し、新規セッションが作成されること（セッションフォルダ、`session_layers.gpkg`、`PointGeo_grid.csv`、`json/settings.json`、メイン操作パネル(QDockWidget)の起動）を確認する。
3. 一旦QGISプロジェクトを閉じるか再読込し、手順2で作成したセッションを「既存セッション」として開き直し、レイヤ・設定・基準点データが正しく復元されることを確認する。
4. Tab1（画像管理）で画像ファイルを新規追加し、レイヤ名を入力して確定する。プレビューダイアログで基準点（2点以上）をグリッド入力ダイアログ経由で設定し、「座標変換」を実行して残差表示を確認後、「レイヤ出力」を行い、画像がメインキャンバスへ配置されること、`image/image_metadata.json`とワールドファイル（.pgw/.tfw等）が生成されることを確認する。
5. Tab2（遺物点作成・打刻）に遷移し、出土形態・遺構名・属性・カラーを設定した上で、メインキャンバス上で複数回打刻する。GeoPackageの`points`テーブルに書き込まれること、打刻直後に重複チェックが機能すること、既存点にマウスを近づけたときのホバー強調・クリックによる編集フォームへの値ロードが正常に動作することを確認する。
6. Tab2で「フォーカスモード」を有効化し、対象図面以外の点群の透過度が正しく変化することを確認する。
7. Tab2で「CSV出力」を実行し、7項目（出土形態, 遺構名, 属性, 点名, 枝番, Ｘ座標, Ｙ座標）のCSVが正しく出力されることを確認する。
8. Tab3（設定）に切り替え、既存の`settings.json`の内容がUIに反映されていることを確認した上で、シンボルサイズ・線幅・線色・ラベルサイズ・グリッド表示縮尺等を変更し、「適用」ボタンを押して、`json/settings.json`への保存と、基準点・打刻点シンボロジ/ラベルの即時再適用（キャンバス再描画）が行われることを確認する。
9. メイン操作パネルを閉じる、またはQGISプロジェクトを保存する操作を行い、プロジェクトファイル(.qgz)への保存（`save_project`相当の処理）が正しく行われることを確認する。

### 各手順で期待される挙動（設計書ベース）
- 手順1: `docs/integrated_master_design.md` §1.4「plugin.py: エントリポイント。QGISメニューへの登録とStartDialogの起動」の記述に基づき、プラグインがエラーなくロードされ、メニュー/ツールバーからStartDialogが起動すること。今回のStage C分割によりimport経路が`layer_manager.py -> layer_manager_models.py / settings_metadata_mixin.py / symbology_mixin.py / gpkg_cache_mixin.py / grid_csv_mixin.py / session_io_mixin.py`に変化しているため、循環import・import順エラーが発生しないことが特に重要な確認ポイントとなる。
- 手順2: §2.1「セッション起動とプロジェクト構築」の記述（`session_layers.gpkg`への`points`テーブル作成、ローカルCRSの適用、CSVデータのメモリキャッシュ）に基づき、新規セッション作成が正常に完了すること。この処理は`session_io_mixin.py`の`setup_new_session`（内部で`gpkg_cache_mixin.py`の`create_initial_gpkg`、`grid_csv_mixin.py`の`setup_or_copy_grid_csv`/`load_grid_csv_to_memory`、`gpkg_cache_mixin.py`の`init_spatial_index_and_cache`を呼び出す）に対応する。
- 手順3: §2.1および§1.4の`layer_manager.py`の記述に基づき、既存セッション読み込み（`session_io_mixin.py`の`load_existing_session`）でGeoPackage・設定・基準点データが復元されること。
- 手順4: §2.2「Tab 1: 画像管理と事前ジオリファレンス」の記述（画像コピー、基準点設定、座標変換、レイヤ出力、`image_metadata.json`永続化、ワールドファイル生成）に基づく。この処理は`session_io_mixin.py`の`copy_image_to_session`/`write_world_file`/`load_georeferenced_raster`と、`settings_metadata_mixin.py`の`update_image_metadata`に対応する。
- 手順5: §2.3「Tab 2: 遺物点作成・連続打刻とCSV出力」の記述（`QgsSpatialIndex`を活用した近傍探索、既存点ヒット時の`existing_point_selected`シグナル、GeoPackageへの書き込み）に基づく。空間インデックス・属性キャッシュのObserver同期は`gpkg_cache_mixin.py`の`init_spatial_index_and_cache`/`_on_feature_added`/`_on_features_deleted`/`_on_attribute_changed`/`_on_geometry_changed`に対応しており、本Stage Cで最もロジック構造が複雑な分割対象であるため重点確認が必要。
- 手順6: §2.3の「フォーカスモード」の記述に基づく（`main_dock.py`/`map_tool.py`側の処理であり、本Stage Cでの直接変更対象ではないが、LayerManagerの分割影響がないことの確認として含める）。
- 手順7: §2.3の「CSV出力」の記述に基づく。
- 手順8: §2.4「Tab 3: 設定と動的シンボロジ更新」の記述（`settings.json`の永続化、`LayerManager.save_settings()`による`settings_changed`シグナル発行、`Tab3SettingsMixin._on_layer_manager_settings_changed()`での再適用）に基づく。`save_settings`は`settings_metadata_mixin.py`に、シンボロジ再適用のロジック本体（`apply_ref_point_symbology`）は`symbology_mixin.py`に、それぞれ分割されているため、この一連の連携が正しく機能することの確認が重要。
- 手順9: §1.4の`layer_manager.py`の記述（ファイルIO全般）に基づく。プロジェクト保存処理は`session_io_mixin.py`の`save_project`に対応する。

### 注意喚起
- 今回のStage C分割は`src/layer_manager.py`（約1,360行、`LayerManager(QObject)`単一クラス）を6ファイルに機械的に分割したものであり、影響範囲はLayerManagerを利用する全機能（セッション作成・読込、画像管理、打刻、設定適用）に及ぶ。ロジック自体は変更していないが、多重継承によるMRO（メソッド解決順序）が正しく機能しない場合、実行時に`AttributeError`等が発生する可能性があるため、特に手順1（プラグインロード）と手順5（打刻時のObserverパターン同期）を重点的に確認すること。
- `symbology_mixin.py`の`apply_ref_point_symbology`内にある`from .main_dock import UIConfig`という遅延import（分割前の`layer_manager.py`から変更なく移動したもの）が、実行時に正しく解決されることを確認すること。特に基準点CSVレイヤ構築時（`grid_csv_mixin.py`の`load_grid_csv_to_memory`から呼び出される）に問題が起きないか、手順2・3で注視すること。
- `settings_metadata_mixin.py`のクラス属性`DEFAULT_SETTINGS`（`PluginSettings().to_dict()`をモジュールロード時に評価）が、分割後も正しく初期化されることを確認すること。特に新規セッション作成直後（手順2）に`json/settings.json`へデフォルト値が正しく書き込まれるかを確認すること。
- `gpkg_cache_mixin.py`のObserver信号接続・切断処理（`_disconnect_point_layer_signals`等）はセッション切り替え時に再初期化されるため、既存セッションを複数回開き直す操作（手順2→3の繰り返しなど）を行った場合に、シグナルの二重接続や未接続が発生しないか確認すること。
