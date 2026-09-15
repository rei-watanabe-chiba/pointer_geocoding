# QGIS 連続打点＆座標出力プラグイン 統合マスター設計書 (v3.0 詳細版)

本ドキュメントは、点群座標取得プラグイン（pointer_geocoding）のシステムアーキテクチャ、設計思想、およびユーザー体験（UX）フローに沿った内部処理（UI、ロジック、State変化）の詳細を追跡・統合した正本設計書です。リファクタリング後に本ドキュメントを更新する場合は、直前の改修内容に影響された記述いは禁止する。何を削除した・何を変えたなどの物語的なを記述するのではなく **「どのような理由でこの機能を採用している」** という説明的な記述をして現状のコードを正とする設計書として記述すること。また**リファクタリングにより矛盾・衝突あるいは追加となった箇所のみ**を変更し、影響のない項目については**情報粒度の軽減や削除を禁止します**。ただし、**レガシー化した記述があれば、ユーザーの許可に改修を提案**してください。また開発環境の整合性を保つために**本冒頭文の削除・改修も禁止**します。

---

## 1. プラグインの要件と根幹アーキテクチャ

### 1.1 基本情報とメタデータ
* **対応GISプラットフォーム**: QGIS 3.x (PyQGIS API 3系)
* **推奨互換バージョン**: qgisMinimumVersion=3.22, qgisMaximumVersion=3.99 (LTR動作保証)
* **プラグイン名**: 点群座標取得 (pointer_geocoding)
* **システム目的**:
  1. アナログ図面に対する事前ジオリファレンス（実空間化）から連続打刻・CSV出力までを専用キャンバスでシームレスに実施する。
  2. セッション単位でのフォルダ管理機構を提供し、ファイル保存先ミスやレイヤ消失を完全に防ぐ。

### 1.2 根幹アーキテクチャ・設計思想
* **GUI完全コード構築とコンテナ主導サイジング (DRY徹底)**:
  * `.ui` ファイルを排除し、`style_helper.py` を用いたPythonベースの宣言的UIを採用。
  * UI表示テキストは `UILabels`, `UIMessages` などの定数クラス群で一元管理し、ロジックと文字列定義を完全に分離（DRY化）する。
  * 【レイアウト規則の厳格化（親コンテナ依存の原則）】
    * ウィジェットの縦横比や整列は子コンテナとStretch比率などで統制し、`setFixedHeight` や `padding` の固定値指定による泥臭い微調整を禁止する。ウィジェット自身ではなく、**親コンテナのFlexレイアウト（QHBoxLayout 等の stretch 比率）**に伸縮を依存させる。
* **OSネイティブUIの保護とスタイルの例外**:
  * 一般的なボタン（QPushButton）やトグルは親コンテナに追従させるが、**QSpinBox 等の数値入力ウィジェット**は例外とする。これらにQSSで過度な枠線や強制的な高さを指定するとOS標準の上下矢印UIが破壊されるため、OSネイティブの保護を最優先し、他ウィジェットとは設定アプローチ（QSS適用範囲）を分けること。
* **Z軸非対応とローカル平面・測量座標系の完全適用**:
  * QGISのポイントレイヤは 2D (PointXY) ベース。
  * 距離計測や座標変換の歪みを防ぐため、未定義CRSではなく完全なローカル平面直交座標系 (カスタムPROJ: +proj=tmerc ...) をプロジェクトに強制適用。
  * 【変更不可侵の絶対的ルール】数学座標系と反転した「測量座標系（X軸=南北, Y軸=東西）」を採用。QGISキャンバス上のX座標(東西)はSurvey Y、Y座標(南北)はSurvey Xに完全に対応するように変換ロジックを設計。

### 1.3 ディレクトリ・セッション構成
本プラグインのソースコードディレクトリ（開発用）および、実行時に生成されるセッションのディレクトリ構造は以下の通りです。

**【ソースコード構成 (プラグインディレクトリ)】**
```text
[QGIS_Dev]/
├── src/                                   ← プラグインのコアロジックを格納
│   ├── plugin.py                          ← エントリポイント
│   ├── start_dialog.py                    ← セッション開始ダイアログ
│   ├── main_dock.py                       ← メインUI共通基盤 (QDockWidget本体・Tab1/2/3 Mixinの合成)
│   ├── main_dock_constants.py             ← main_dock系UI文字列・設定定数クラス群 (UIConfig/UILabels等)
│   ├── main_dock_dialogs.py               ← main_dock系独立ダイアログ (PreviewDialog/GridInputDialog等)
│   ├── tab1_georef_mixin.py               ← Tab1 (画像管理・事前ジオリファレンス) のUI構築・イベント処理Mixin
│   ├── tab2_digitizing_mixin.py           ← Tab2 (フォーカスモード・遺物点打刻・CSV出力) のUI構築・イベント処理Mixin
│   ├── tab3_settings_mixin.py             ← Tab3 (設定) のUI構築・イベント処理Mixin
│   ├── layer_manager.py                   ← LayerManager本体 (QObjectシグナル・__init__・session_*_dirプロパティのみ。GeoPackage・設定等のファイルIO実体は下記Mixin群に分割)
│   ├── layer_manager_models.py            ← LayerManager系データモデル (PluginSettings/RefPointMeta/ImageLayerMeta) とCRSヘルパー (get_local_crs/suppress_crs_prompt)
│   ├── settings_metadata_mixin.py         ← LayerManager用Mixin: settings.json・image_metadata.jsonの読み書き
│   ├── symbology_mixin.py                 ← LayerManager用Mixin: 打刻点・基準点のシンボロジ/ラベリング適用
│   ├── gpkg_cache_mixin.py                ← LayerManager用Mixin: GeoPackage生成・スキーママイグレーション・空間インデックス/属性キャッシュのObserver同期
│   ├── grid_csv_mixin.py                  ← LayerManager用Mixin: PointGeo_grid.csvの生成・配置・メモリロード(ref_points CSVレイヤ構築含む)
│   ├── session_io_mixin.py                ← LayerManager用Mixin: セッション新規作成/既存読込、画像コピー、ワールドファイル生成、ラスタ/基準点/プロジェクトの読み書き
│   ├── map_tool.py                        ← QGISキャンバスマウスツール
│   ├── core_logic.py                      ← UIから分離された純粋ロジック・座標系アダプター
│   ├── transform.py                       ← 座標変換モジュール
│   └── style_helper.py                    ← 宣言的UIコンポーネント・レイアウトヘルパー
└── docs/                                  ← 設計書等のドキュメント格納
```

**【実行時のセッション・データ構成】**
```text
[ユーザー指定親ディレクトリ]/
└── [セッション名]/
    ├── [セッション名].qgz                     ← QGISプロジェクトファイル (相対パス保存)
    ├── PointGeo_grid.csv                      ← 測量系グリッド座標データ
    ├── json/
    │   └── settings.json                      ← シンボル・ラベル・縮尺等のユーザー設定
    ├── image/
    │   ├── image_metadata.json                ← 画像ごとの基準点・アフィンパラメータメタデータ
    │   ├── analog_drawing.png                 ← コピーされた画像
    │   └── analog_drawing.pgw                 ← 生成されたワールドファイル
    └── point/
        └── session_layers.gpkg                ← 打刻点・基準点を保持するGeoPackage
```

### 1.4 モジュール構成と役割
* **plugin.py**: エントリポイント。QGISメニューへの登録と StartDialog の起動。独立ツールバーボタンも構築。
* **start_dialog.py**: 新規・既存セッションの選択と、入力値のバリデーション、グリッド座標の動的プレビュー。
* **main_dock.py**: メイン操作UI (QDockWidget) の共通基盤。画像管理(旧Tab1)・遺物点作成(旧Tab2)・設定(旧Tab3)のUI構築・イベント制御自体は下記のMixinクラス群に分割されており、`MainDockWidget`はそれらを多重継承して束ねる（Stage B: 機械的分割、ロジック変更なし）。T-0020より、これら3画面は`QTabWidget`によるタブ切替ではなく、**左端アイコンレール＋開閉可能な固定幅サイドパネル**（VSCodeアクティビティバー方式）＋常時表示のメインエリアという構成に再編されている。左端の`nav_btn_drawing`（図面管理）／`nav_btn_settings`（設定）の2つの`QToolButton`（`QButtonGroup`で排他制御）をクリックすると`self.side_panel`内の`QStackedWidget`（`self.side_stack`）が対応するコンテナ（`tab1_container`／`tab3_container`）に切り替わり表示される。既に開いているパネルのボタンを再クリックすると`side_panel`ごと非表示になり閉じる（同時に2つのパネルは開かない）。遺物点作成の`tab2_container`はタブ化されておらず、常にメインエリアとして表示される。本体には`__init__`（各種状態初期化・シグナル接続）、`preview_canvas`/`preview_raster_layer`/`georef_tool`の後方互換プロパティ、`_init_ui`（アイコンレール・サイドパネル・メインエリアの組み立て）、パネル開閉クリック処理(`_on_nav_button_clicked`)、開いているパネルに応じたマップツール有効/無効・UI更新処理(`_on_panel_changed`。旧`_on_tab_changed`をパネル開閉状態ベースに再設計したもので、`self._active_panel`（`"drawing"`/`"settings"`/`None`）の変化のたびに呼ばれ、`_init_ui`完了直後にも一度呼ばれて既定状態（両パネル閉・メインエリアのみ表示）を適用する）、サイドパネルを閉じてメインエリアへ戻す(`_close_side_panel`。旧・座標変換完了後のTab2自動遷移に相当)、プロジェクト保存(`_save_project`)、終了処理(`closeEvent`)、および Tab2 のフォーカスモードと Tab3 の設定適用の両方から呼ばれる共有メソッド`update_symbology_opacity`のみが残る。`update_symbology_opacity`自体は現在のUI状態（フォーカスモードの有無・4カテゴリの選択値・スライダー値）を収集するだけの薄い委譲メソッドであり、透過度条件式の組み立てと`QgsCategorizedSymbolRenderer`への適用は`symbology_mixin.py`の`SymbologyMixin.build_opacity_expression`/`apply_opacity_expression`（`self.layer_manager`経由で呼び出し）に委譲している（Stage E: シンボロジ/透明度操作の一元化。呼び出し名・シグネチャ、およびTab2/Tab3から見た挙動は変更なし）。打刻データの入力検証・重複チェック・フィーチャ組み立て・GeoPackageへの書き込みは`tab2_digitizing_mixin.py`側の`_on_canvas_clicked()`等が行う（`map_tool.py`からは`canvas_clicked`シグナルでキャンバス座標のみ通知を受ける。Step3: イベント駆動化）。
* **main_dock_constants.py**: `main_dock.py`および各Tab Mixin・ダイアログが共有するUI文字列/設定定数クラス群 (`UIConfig`, `UILabels`, `UIPlaceholders`, `UIDialogTitles`, `UIMessages`, `MAIN_RATIO`)。QGIS/PyQt標準ライブラリ以外への依存を持たない（循環import回避）。なお`symbology_mixin.py`(旧`layer_manager.py`)・`map_tool.py`は既存の`from .main_dock import UIConfig`呼び出しを維持しており、`main_dock.py`が`main_dock_constants.py`から`UIConfig`を再exportすることで後方互換を保っている。
* **main_dock_dialogs.py**: `main_dock.py`系の独立ダイアログ/ウィジェットクラス群。`PreviewDialog`（Tab1のモードレス基準点設定プレビュー）、`TwoDigitSpinBox`（00-99表示スピンボックス）、`GridInputDialog`（基準点グリッド入力モーダル）を提供。`main_dock_constants.py`と`style_helper.py`・`core_logic.py`・`map_tool.py`にのみ依存する。
* **tab1_georef_mixin.py**: `Tab1GeorefMixin`。Tab1 (画像管理・事前ジオリファレンス) のUI構築(`_create_tab1_ui`)と、画像確定・基準点設定・プレビュー操作・座標変換・レイヤ出力までの一連のイベントハンドラを提供する`MainDockWidget`用Mixin。
* **tab2_digitizing_mixin.py**: `Tab2DigitizingMixin`。Tab2 (マスターフォーカスモード・連続打刻・CSV出力) のUI構築(`_create_tab2_ui`)と、フォーカスモード制御・カテゴリ選択・打刻(`_on_canvas_clicked`)・既存点編集/削除・CSV出力までの一連のイベントハンドラを提供する`MainDockWidget`用Mixin。
* **tab3_settings_mixin.py**: `Tab3SettingsMixin`。Tab3 (設定) のUI構築(`_create_tab3_ui`)と、色選択・設定値のUI反映・「適用」ボタン処理・`LayerManager.settings_changed`購読ハンドラを提供する`MainDockWidget`用Mixin。
* **layer_manager.py**: セッションフォルダ作成、GeoPackage (points, ref_points) の初期化、メタデータ管理(image_metadata.json)、設定ファイル管理(`settings.json`)、CSVロード機能、CRS管理、ファイルIO全般を担う`LayerManager`本体。`QObject`を継承し、`metadata_updated` / `layer_deleted` / `settings_changed` シグナルで状態変化を通知する（Step3: イベント駆動化。現状、`main_dock.py`側で実際に購読・反応しているのは`settings_changed`のみ）。Stage C: 上記の実処理自体は下記のMixinクラス群に分割されており、`LayerManager`はそれらを多重継承して束ねる（機械的分割、ロジック変更なし）。本体には`QObject`シグナル宣言、`__init__`（各種状態初期化）、`session_image_dir`/`session_json_dir`プロパティのみが残る。
* **layer_manager_models.py**: `LayerManager`および各Mixinが共有するデータモデルとCRSヘルパー。設定値dataclass `PluginSettings`、基準点メタデータdataclass `RefPointMeta`、画像レイヤメタデータdataclass `ImageLayerMeta`、ローカル直交CRS取得関数`get_local_crs()`、CRS未定義プロンプト抑制用コンテキストマネージャ`suppress_crs_prompt()`を提供する。`LayerManager`本体や他のMixinには依存しない（循環import回避）。
* **settings_metadata_mixin.py**: `SettingsMetadataMixin`。`settings.json`の読み書き(`load_settings`/`load_settings_dataclass`/`save_settings`/`ensure_json_dir`、クラス属性`DEFAULT_SETTINGS`)と、`image_metadata.json`の読み書き(`load_image_metadata`/`save_image_metadata`/`update_image_metadata`/`delete_image_metadata`)を提供する`LayerManager`用Mixin。
* **symbology_mixin.py**: `SymbologyMixin`。打刻点レイヤへの動的ラベリング(`apply_point_labeling`)、基準点レイヤへのクロスシンボル・ルールベースレンダリング・ラベリング適用(`apply_ref_point_symbology`)、ラベルのAboveRightクアドラント整列を両者で共有する`apply_above_right_label_quadrant`、および打刻点のフォーカスモード透過度制御を担う`build_opacity_expression`（条件式文字列の組み立てのみを行う純粋関数）と`apply_opacity_expression`（組み立てた式を`QgsCategorizedSymbolRenderer`の各カテゴリシンボルへ実際に適用しレイヤを再描画）を提供する`LayerManager`用Mixin（Stage E: 旧`main_dock.py`の`update_symbology_opacity`から式の組み立て・適用ロジックを移管。`MainDockWidget`側からは`self.layer_manager`経由で呼び出される）。
* **gpkg_cache_mixin.py**: `GpkgCacheMixin`。GeoPackageへのレイヤ書き出し(`create_gpkg_layer`)、`points`スキーマ初期化(`create_initial_gpkg`)、既存レイヤの自動スキーママイグレーション(`check_and_migrate_point_layer`)、および`QgsSpatialIndex`・属性キャッシュ・ジオメトリキャッシュをObserverパターンで同期する一式(`init_spatial_index_and_cache`、`_on_feature_added`等のシグナルハンドラ)を提供する`LayerManager`用Mixin。
* **grid_csv_mixin.py**: `GridCsvMixin`。`PointGeo_grid.csv`の生成(`generate_grid_csv`)、セッションディレクトリへの配置(`setup_or_copy_grid_csv`)、メモリキャッシュへのロードとDelimited Text Providerによる`ref_points`レイヤ構築(`load_grid_csv_to_memory`)を提供する`LayerManager`用Mixin。
* **session_io_mixin.py**: `SessionIOMixin`。新規セッション構築(`setup_new_session`)、既存セッション読み込み(`load_existing_session`)、画像のセッションフォルダへのコピー(`copy_image_to_session`)、ワールドファイル生成(`write_world_file`)、プレビュー用/ジオリファレンス済みラスタのロード(`load_preview_raster`/`load_georeferenced_raster`)、基準点の永続化(`save_ref_points`)、プロジェクト保存(`save_project`)を提供する`LayerManager`用Mixin。
* **map_tool.py**: QGISキャンバス上でのマウスクリック・ホバー処理。
  * ImageGeorefTool: プレビューキャンバスでの画像ピクセル座標取得。
  * CanvasDigitizingTool: メインキャンバスでの既存点検索（ホバー、`existing_point_selected`シグナル発火）、および未ヒット時のクリック座標通知（`canvas_clicked`シグナル発火）、ポイント・ラベルへのシンボロジ設定・動的オーバーライド(`setup_point_layer_symbology`/`setup_ref_point_layer_symbology`/`update_attribute_transparency`)。ラベルのAboveRightクアドラント整列部分は`symbology_mixin.py`の`SymbologyMixin.apply_above_right_label_quadrant`を呼び出して基準点側と共通化している（Stage E: 明確に重複していたロジック片のみを対象とした共通化で、`QgsMapTool`としての構造自体は変更していない）。フォーカスモードのフィルタ条件は`main_dock.py`から`update_focus_state()`で一方向にプッシュされキャッシュする。フィーチャの組み立て・GeoPackageへの書き込みは行わない（Step3以前はこのツールが直接行っていたが、`main_dock.py`側に移管した）。
* **core_logic.py**: UIから分離された純粋ロジック。座標系アダプター(`to_survey_coords`/`from_survey_coords`)、重複点チェック(`check_point_duplicate`)、点番号採番(`get_next_point_number`)、フィーチャ組み立て(`build_digitized_feature`)、ジオリファレンス画像上のピクセル座標へのアフィン逆変換(`pixel_from_affine`)、点群ジオメトリ一括更新・残差評価ロジックを提供。
* **transform.py**: 座標変換モジュール (ヘルマート変換 / 最小二乗法アフィン変換)、点群の追従再配置ロジック、およびスリム化されたCSV(7項目)出力ロジック。
* **style_helper.py**: QtコードベースのフレックスレイアウトUI構築およびステータスパネル、汎用トグルボタン等のコンポーネント管理。

---

## 2. UXフローと内部処理詳細

本節では、実際のユーザー操作に沿って、UIの遷移、ロジックの働き、および状態変数（State）の変化を解説します。

### 2.1 セッション起動とプロジェクト構築
**起点**: plugin.py -> start_dialog.py -> layer_manager.py

* **UX/UI フロー**:
  1. プラグイン起動時、現在開いているQGISプロジェクトに未保存の変更（Dirty状態）があれば保護ダイアログを表示。
  2. StartDialog が開き、「新規セッション」または「既存セッション」を選択。
  3. 新規の場合、親フォルダとセッション名、測量グリッドの原点・数を入力。
  4. 確定後、セッションフォルダが自動生成され、メイン操作パネル（QDockWidget）が起動する。
* **主要ロジック & State**:
  * **UIインタロック**: ラジオボタンの切り替えにより各入力項目の Enable/Disable が動的に切り替わる。
  * **グリッド座標プレビュー**: 
    * 入力されたプレビュー名（例: 152C）からリアルタイムに座標を計算（1大グリッド=40m間隔）。範囲外の場合は赤色のエラー表示。
  * **GeoPackage とレイヤ・CRS初期化 (LayerManager)**:
    * `session_layers.gpkg` に `points` (打刻点) と `ref_points` (基準点) テーブルを作成（points には `drawing_name`, `pixel_x`, `pixel_y` カラムを追加）。
    * QGIS特有の「未定義CRS警告ダイアログ」を抑制しつつ、ローカルCRSをプロジェクトに適用。
    * **CSVデータのメモリキャッシュ**: 対象グリッドCSVを読み込み、座標変換用辞書をメモリにキャッシュ。

### 2.2 図面管理サイドパネル（旧Tab 1）: 画像管理と事前ジオリファレンス
**起点**: main_dock.py (図面管理サイドパネル; `tab1_georef_mixin.py`) -> map_tool.py:ImageGeorefTool -> transform.py

* **UX/UI フロー**:
  0. 左端アイコンレールの「図面」ボタン（`nav_btn_drawing`）をクリックすると、固定幅のサイドパネルが開き本画面が表示される（T-0020）。同ボタンを再クリックするとパネルが閉じ、常時表示のメインエリア（遺物点作成）のみに戻る。パネル最下部には情報パネル（画像名・基準点登録数・座標変換状態・残差）が配置されている。
  1. 「新規追加 / 編集削除」の汎用トグルボタンでモードを切り替える。
  2. **新規追加モード**: 画像ファイルを選択・レイヤ名を入力し、「基準点設置」をクリック。この時点では画像はまだセッションへコピーされず、選択された元ファイルをそのまま参照してプレビューダイアログが起動する（画像ファイルの物理名はレイヤ名変更に追従しない設計。T-0015）。選択した元画像に既存のワールドファイルが付随している場合は、本プラグインが生成する変換結果との整合性が取れなくなるため、「基準点設置」の時点でエラー表示し処理を拒否する（この制約は新規追加モードのみが対象で、次項の編集削除モードにおける既存レイヤの「基準点設置」〈基準点再編集〉には適用されない）。画像の `image/` フォルダへの複製は、後述の「座標変換」→「レイヤ出力」完了時点で、ワールドファイルの生成と合わせて行われる（T-0018）。
  3. **編集削除モード**: 既存のレイヤ（図面）をセレクタで選び、「基準点設置」で保存されたメタデータから基準点を復元してプレビューダイアログを起動する。レイヤ名を変更したい場合は「レイヤ名変更」ボタンで `image_metadata.json` のキー付け替えと QGIS レイヤの表示名 (`setName()`) のみを更新する（画像ファイル自体のコピー・削除・リネームは発生しない）。「削除」で対象を安全に削除（紐づく点群はグローバル化）する。
  4. プレビューキャンバス上で既存基準点へスナップさせるか、新規の空白部分をクリックして **グリッド入力ダイアログ (モーダル, GridInputDialog)** で実座標を割り当てる。
  5. 「座標変換」を実行して残差を確認し、「レイヤ出力」で画像（ワールドファイル更新）をメインキャンバスへ再配置。同時に、その画像に紐づく過去の打刻点群も自動で新しい位置へ追従移動し、図面管理サイドパネルが自動的に閉じてメインエリア（遺物点作成）の表示に戻る（`MainDockWidget._close_side_panel()`）。
* **主要ロジック & State**:
  * **State 変数 & メタデータ管理**: 
    * `self.current_copied_image_path`: セッションの `session_image_dir` 内に配置された画像のパス。
    * `self.ref_points_data`: 基準点リスト。
    * `image_metadata.json`: 画像パス、基準点リスト、座標変換パラメータを永続化し、編集削除モードでの再ロードと再変換を可能にする。
  * **座標変換とグループ化保存 (CoordinateTransformer)**:
    * 「座標変換」で 2点(ヘルマート) または 3点以上(アフィン) の変換行列を計算し、残差を表示。
    * 「レイヤ出力」でワールドファイルを生成・上書き。
    * メインキャンバスへ変換済み画像をロード/更新し、「画像ファイル」グループへ格納。さらに `pixel_x`, `pixel_y` を基に既存の打刻点群の実座標とキャンバス座標を再計算・追従再配置する。

### 2.3 メインエリア（旧Tab 2）: 遺物点作成・連続打刻とCSV出力
**起点**: main_dock.py (常時表示のメインエリア; `tab2_digitizing_mixin.py`) -> map_tool.py:CanvasDigitizingTool

本画面はT-0020以降タブ化されておらず、図面管理・設定いずれのサイドパネルも閉じている（＝既定の）状態で常時表示されるメインエリアである。図面管理・設定パネルのどちらかが開いている間はメインキャンバス上でのマップツール（`CanvasDigitizingTool`）が無効化され打刻できない。

* **UX/UI フロー**:
  1. 出土形態（遺構 / グリッド）、遺構名（新規作成対応）、属性（S/P/C/SP）、カラーを選択。
  2. 「対象図面」マルチセレクタで作業対象の画像をアクティブにする。メインキャンバス上で打刻時、対象画像上のローカル座標(`pixel_x`, `pixel_y`)が取得され保存される。枝番なしの場合は点名が自動インクリメントされる。
  3. 既存の点にマウスを近づけると赤い枠で強調され、クリックすると属性がUIフォームにロードされて編集・削除が可能になる。
  4. 「フォーカスモード」と「スライダー」を利用し、対象図面以外に属する点群を透過させて視認性を向上させる。
* **主要ロジック & State**:
  * **QGIS特有の描画制御・シンボロジ操作**:
    * 属性ごとに `QgsCategorizedSymbolRenderer` で形状を定義（例：基準点は十字、SPは二重円など。グリッド時は赤色固定）。
    * **フォーカスモード**: QGISの式エンジン (`QgsProperty`) を用いて、非対象の点群の透過度をリアルタイムに上書き制御。
  * **ホバー判定と既存点選択 (CanvasDigitizingTool)**:
    * `QgsSpatialIndex` を活用した高速な近傍探索（許容誤差 15px）。フォーカスモードのフィルタ条件（対象図面・出土形態・遺構名・属性）は`main_dock.py`側から`update_focus_state()`で一方向にプッシュされ、CanvasDigitizingTool内にキャッシュされる（Step3: イベント駆動化。以前はツール側がドックへ都度問い合わせていた）。
    * クリック時に `existing_point_selected` シグナルを発火し、ドック側でフォームに値をバインド。
  * **新規打刻とデータ永続化 (Step3以降: main_dock.py側の責務)**:
    * 既存点にヒットしなかったクリックは、CanvasDigitizingToolが`canvas_clicked`シグナルでキャンバス座標のみを通知する。入力値の検証、新規遺構名の登録、重複チェック（`core_logic.check_point_duplicate`）、フィーチャ組み立て（`core_logic.build_digitized_feature`）、GeoPackageへの書き込みは、すべて`tab2_digitizing_mixin.py`の`Tab2DigitizingMixin._on_canvas_clicked()`が行う。
    * 打刻時はキャンバス座標を実空間座標 (`real_x`, `real_y`) としてGeoPackageに追加するだけでなく、対象図面のローカル座標 (`pixel_x`, `pixel_y`) も、アフィン逆変換（`core_logic.pixel_from_affine`）により算出して併せて保存する。これにより画像再変換時の点群自動追従を実現する。
    * **CSV出力**: 打刻データは「出土形態, 遺構名, 属性, 点名, 枝番, Ｘ座標(南北), Ｙ座標(東西)」の7項目のみにスリム化されてエクスポートされる。

### 2.4 設定サイドパネル（旧Tab 3）: 設定と動的シンボロジ更新
**起点**: main_dock.py (設定サイドパネル; `tab3_settings_mixin.py`) -> layer_manager.py -> map_tool.py

* **UX/UI フロー**:
  1. 左端アイコンレールの「設定」ボタン（`nav_btn_settings`）をクリックしてサイドパネルを開くと、保存された `settings.json` の内容が各コンポーネント（基準点・遺物点のサイズ/線幅/線色/塗り有無、ラベルのサイズ/配置間隔/白線有無、大・小グリッドの表示縮尺）に反映される（`update_settings_ui_from_dict`。パネルを開くたびに`_on_panel_changed`から呼ばれる）。
  2. 各項目を調整し「適用」ボタンを押すと、即座にキャンバス上のすべてのレイヤの見た目が更新される。
  3. 遺物点のラベル文字色や塗り色は、UI上で明示的に指定しなくても、ポイント枠線の色（出土形態が「グリッド」なら設定色、「遺構」等なら各遺構の設定色）に自動追従して描画される。
* **主要ロジック & State**:
  * **フレキシブルレイアウトとUIステート**:
    * 行頭ラベルを廃止し、`QHBoxLayout` による比率（`stretch`）指定を用いた完全なフレキシブルUIとして実装。これにより画面幅の変動にも美しく対応。
  * **データ定義上書き (Data Defined Override)**:
    * シンボルやラベルの描画に際し、QGISの式エンジンを用いた動的プロパティ（`QgsProperty.fromExpression`）を多用。
    * 特にラベル文字色（`QgsPalLayerSettings.Color`）やシンボルの塗り（`PropertyFillColor`）に対し、UIと属性値から動的生成したカラー判定式を上書き適用し、自動追従を実現している。
  * **設定の永続化**:
    * `settings.json` をセッションごとに保持し、次回起動時にも前回の設定状態を復元する。
    * `LayerManager.save_settings()`は保存成功時に`settings_changed`シグナルを発行し、`tab3_settings_mixin.py`の`Tab3SettingsMixin._on_layer_manager_settings_changed()`がこれを購読して基準点・打刻点シンボロジの再適用とキャンバス再描画を行う（Step3: イベント駆動化。「適用」ボタンのハンドラ自体はUI値の収集と保存のみを行う）。
