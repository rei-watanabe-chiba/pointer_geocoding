## タスクID
T-0043

## 変更ファイル一覧
- `git mv` によるファイル移動（19ファイル、履歴保持）
  - src/start_dialog.py → src/ui/start_dialog.py
  - src/main_dock.py → src/ui/dock.py
  - src/main_dock_constants.py → src/ui/constants.py
  - src/main_dock_dialogs.py → src/ui/dialogs.py
  - src/tab1_georef_mixin.py → src/ui/tab1_image.py
  - src/tab2_digitizing_mixin.py → src/ui/tab2_plot.py
  - src/tab3_settings_mixin.py → src/ui/tab3_settings.py
  - src/style_helper.py → src/ui/style.py
  - src/layer_manager.py → src/layer/manager.py
  - src/layer_manager_models.py → src/layer/models.py
  - src/settings_metadata_mixin.py → src/layer/settings_io.py
  - src/gpkg_cache_mixin.py → src/layer/gpkg.py
  - src/grid_csv_mixin.py → src/layer/grid_csv.py
  - src/session_io_mixin.py → src/layer/session_io.py
  - src/symbology_mixin.py → src/layer/symbology.py
  - src/core_logic.py → src/logic/core.py
  - src/transform.py → src/logic/transform.py
  - src/map_tool.py → src/canvas/map_tool.py
- 新規作成（空ファイル、パッケージ化のため）
  - src/ui/__init__.py
  - src/layer/__init__.py
  - src/logic/__init__.py
  - src/canvas/__init__.py
- import文修正（移動19ファイル全て + src/plugin.py）

## 変更概要
- src配下を `ui/`（画面・ダイアログ・タブmixin・スタイル定数）, `layer/`（LayerManagerおよびそのmixin群・データモデル）, `logic/`（座標変換・純粋ロジック）, `canvas/`（QgsMapTool系）の4フォルダへ純粋なファイル移動のみで再構成した。
- クラス名・メソッド名・docstring本文（旧ファイル名を言及するコメント等）は一切変更していない。実行に影響する箇所のみ以下の方針でimport文を追従修正した。
  - 同一フォルダ内参照: `from .モジュール名 import ...` のまま（モジュール名のみ新名称に変更、例: `from .layer_manager_models import` → `from .models import`）
  - 異なるフォルダ参照: `from ..フォルダ名.モジュール名 import ...` に変更（例: `src/ui/dock.py` の `from .map_tool import ...` → `from ..canvas.map_tool import ...`）
  - 関数内ローカルimport（`src/canvas/map_tool.py` の `_create_marker`相当箇所、`src/layer/symbology.py` の `apply_point_symbology`相当箇所）もモジュールレベルimportと同様に `..ui.dock import UIConfig` へ追従修正
  - `src/plugin.py` は `.ui.start_dialog import StartDialog`、`.layer.manager import LayerManager`、`.ui.constants import UIMessages`、関数内の `.ui.dock import MainDockWidget` に修正
  - `src/__init__.py`、`src/plugin.py`冒頭の`from .plugin import`は変更対象外（元々ルート直下を参照するため変更不要）
- `src/ui/dock.py` 内のコメント（`# layer_manager.py and map_tool.py perform \`\`from .main_dock import UIConfig\`\`` の1箇所）は、旧ファイル名を言及する説明文であり実行に影響しないため、タスク指示の通り無理に書き換えなかった（コード自体は新パスに追従済み）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンド未設定）。
静的チェックとして以下を実行した。
- `grep -rn "from \.\(main_dock\|layer_manager\|core_logic\|style_helper\|tab1_georef_mixin\|tab2_digitizing_mixin\|tab3_settings_mixin\|symbology_mixin\|gpkg_cache_mixin\|grid_csv_mixin\|session_io_mixin\|layer_manager_models\|settings_metadata_mixin\)" src/` → コメント行1件（上記）のみヒットし、旧パスを参照するimport文は0件であることを確認した。
- `find src -name "*.py" | xargs -I{} python3 -m py_compile {}` → 全ファイルでコンパイルエラーなし（構文レベルの確認。QGIS/PyQtランタイムでの実際のimport解決は本コマンドでは検証されない）。

## スコープ外変更の有無
なし。`src/__init__.py`、`src/plugin.py`（import文のみ修正）、`src/metadata.txt`、`src/icon/`、`docs/`、`dcs/`はスコープ通り変更していない（`src/plugin.py`は依頼手順3で明示された変更対象）。
