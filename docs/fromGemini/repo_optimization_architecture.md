# リポジトリ全域最適化アーキテクチャ設計書 (UIリファクタリング拡張編)

本ドキュメントは、PyQGISプラグイン（`pointer_geocoding`）における UIリファクタリングアーキテクチャ（CoreUI/Schemas/Thin Controller/core2ファイル統合案）をさらに押し進め、**リポジトリ全域（`src/ui/`, `src/logic/`, `src/layer/`, `src/canvas/`）に適用・拡張した「全域最適化アーキテクチャ」** の設計思想、目的の詳細化、対象ファイルマッピング、抽象化されたアプローチ枠組み、改修対象の探索ヒント、および構成変更後のディレクトリ構造と想定コード行数をまとめたリファクタリング設計書です。

---

## 1. 設計思想 (Architectural Principles)

UIリファクタリングアーキテクチャ（`CoreUI Engine v2`: 構造系 `engine.py` / 振る舞い系 `behavior.py` による集約）で確立した設計原則を、リポジトリ全域へ拡張・適用します。

1. **厳格なレイヤ間境界と単方向依存 (Strict Layer Boundaries & Unidirectional Dependency)**
   依存の方向を **`UI` ➔ `Logic / Domain Services` ➔ `Layer Manager` ➔ `QGIS Objects / Disk Files`** の一方方向に厳格化します。UI層が Layer や QGIS Project、ディスクファイルを直接操作すること（バイパス）や、Canvas マップツールが UI Dock を直接参照（逆参照）することを固く禁止します。
2. **QGIS低層API・I/Oの完全隠蔽 (Complete Encapsulation of Low-level QGIS API & I/O)**
   UIコントローラ（`tab1`, `tab2`, `start_dialog` 等）から、`QgsFeature` の構築、アフィン変換座標計算、ファイル削除（`os.remove`）、ワールドファイル生成、および QGIS プロジェクトレイヤツリーからの削除（`removeMapLayer`）などの低層操作を全廃し、ドメインサービス（`src/logic/`）および `LayerManager` へ完全カプセル化します。
3. **イベント・状態の完全疎結合 (Event & State Decoupling)**
   マップツール（`src/canvas/map_tool.py`）は UI の内部変数（`dock.tab2_current_mode` 等）を直接走査せず、UI側からの **1-way Push 通知（`set_digitizing_mode` 等）** によって状態を受け取り、純粋なキャンバスイベントの発火に専念させます。
4. **ドメインロジックの単体テスト可能性 (Testable Business Logic)**
   打刻データ構築・自動採番・重複検証・ジオリファレンス変換処理を `src/logic/` 配下の純粋な Python サービスとして独立させることで、QGIS GUI インスタンスを起動することなく単体テスト（Unit Test）を実行可能にします。

---

## 2. 目的の詳細化 (Detailed Purpose)

**「Thin Controller（薄いUIコントローラ）の概念を、UI層全体の薄型化と堅牢なドメインコア（Logic/Layer）の構築へ拡張すること」** の具体的な達成基準および各層の責務境界は以下の通りです。

### UI層（`src/ui/`）が手放すこと（剥離対象）
* `QgsFeature` の手動インスタンス化・属性セット・`insert_feature_to_layer` の呼び出し。
* `os.remove` によるワールドファイル/画像の削除や、`QgsProject.instance().removeMapLayer` による直接のレイヤ削除・リネーム処理。
* アフィン変換パラメータ計算、残差評価、ワールドファイル書き出しの各ステップの分散呼び出し。
* `getattr(dock, ...)` や `SymbologyMixin` の多重継承による、直書きのシンボロジ・透過度状態管理。

### 各層が集中的に行うこと（専念対象）
* **`src/ui/` (プレゼンテーション層)**: CoreUI基盤を通じた画面レンダリング、一括データバインディング、および Domain Service へのメッセージ仲介に専念。
* **`src/logic/` (ドメインサービス・計算層)**: 純粋なビジネスロジック、座標変換計算、および打刻・ジオリファレンスのトランザクション型サービス処理を実行。
* **`src/layer/` (データアクセス・セッション管理層)**: `LayerManager` を唯一の窓口とし、GeoPackage/CSV/JSONの永続化、レイヤツリーの安全な操作、およびシンボロジの一元管理を担当。
* **`src/canvas/` (入力イベント検出層)**: QGISマップキャンバス上のユーザー操作（クリック・移動）の検知と、UI側からの状態 Push に基づくクリック挙動の制御に専念。

---

## 3. 対象ファイルマッピング (Target Files)

| レイヤ分類 | 対象ファイル | 役割と全域最適化の方向性 |
| :--- | :--- | :--- |
| **UIプレゼンテーション層** | `src/ui/tab1_image.py`<br>`src/ui/tab2_plot.py`<br>`src/ui/tab3_settings.py`<br>`src/ui/start_dialog.py`<br>`src/ui/dialogs.py`<br>`src/ui/dock.py` | **極薄コントローラ化**。直書きのQGIS操作・ファイルI/O・計算ロジックを全廃し、`CoreUI` / `schemas.py` と Domain Services 呼び出しに専念。`dock.py` から `SymbologyMixin` 継承を剥離。 |
| **コアUIエンジン層 (v2案2)** | `src/ui/core/engine.py`<br>`src/ui/core/behavior.py` | UI構築基盤の2ファイル統合整理。`engine.py` (FieldSpec + Builder + CoreUIDialog) と `behavior.py` (Rules + Validators) による最適化。 |
| **宣言的スキーマ層** | `src/ui/schemas.py` | 全画面・全ダイアログのUI宣言的定義（`PanelSpec`）を一約化。 |
| **ドメインサービス・計算層** | `src/logic/digitizing_service.py` *(新規)*<br>`src/logic/georef_service.py` *(新規)*<br>`src/logic/transform.py`<br>`src/logic/core.py` | **【新規層】** `DigitizingService`（打刻・検証・採番・Feature自動構築）および `GeorefService`（ジオリファレンス・変換一括パイプライン）を創設。 |
| **データアクセス・レイヤ管理層** | `src/layer/manager.py`<br>`src/layer/symbology.py`<br>`src/layer/gpkg.py`, `session_io.py` 等 | `LayerManager` に安全な画像削除・リネーム等の高高度操作APIを集約し、データアクセスの唯一の窓口化。`SymbologyMixin` を LayerManager 専用へ統合。 |
| **マップツール層** | `src/canvas/map_tool.py` | `getattr(dock, ...)` 参照を全廃。UI側からの 1-way Push（`set_digitizing_mode`）受領と純粋イベント発火への独立。 |

---

## 4. アプローチの抽象的枠組みと改修対象探索ヒント

全域リファクタリングを実行する開発者やLLMがソースコードを調査・改修するための探索ヒント（識別子・キーワード）です。

### アプローチ A: 打刻ドメインサービス (`DigitizingService`) によるQGIS低層処理の剥離
* **概要**: `tab2_plot.py` 内で行われている「入力検証 ➔ 重複判定 ➔ アフィン座標変換 ➔ Feature構築 ➔ レイヤ挿入 ➔ 自動採番更新」の連続処理を `DigitizingService.digitize_point(...)` に集約。
* **探索ヒント（コード検索用キーワード）**:
  * `_on_canvas_clicked` (`tab2_plot.py` 内のキャンバスクリックハンドラ)
  * `pixel_from_affine` / `build_digitized_feature` / `insert_feature_to_layer`（`tab2_plot.py` 内の連鎖呼び出し）
  * `get_next_point_name` / `get_next_branch_no`（採番計算処理）

### アプローチ B: ジオリファレンス・変換パイプライン (`GeorefService`) の一括トランザクション化
* **概要**: `tab1_image.py` 内のワールドファイル出力・画像ファイルコピー・残差評価・プロジェクトレイヤ配置を一括実行するパイプライン関数に統合。
* **探索ヒント（コード検索用キーワード）**:
  * `CoordinateTransformer` / `evaluate_residuals` / `write_world_file`（`tab1_image.py` 内のジオリファレンス処理）
  * `WORLD_FILE_EXTENSIONS`（`tab1_image.py` 内の拡張子判定とループファイル処理）

### アプローチ C: `LayerManager` へのファイルI/O・QGIS Project操作の集約
* **概要**: `tab1_image.py` 内の `os.remove` によるファイル削除や `QgsProject.instance().removeMapLayer` などの直書き操作を `LayerManager` の高高度メソッドへ移管。
* **探索ヒント（コード検索用キーワード）**:
  * `_on_delete_layer_clicked` 内の `os.remove` / `removeMapLayer`（`tab1_image.py`）
  * `_on_rename_layer_clicked` 内のレイヤ検索・属性一括リネーム処理（`tab1_image.py`）

### アプローチ D: キャンバスツール (`map_tool.py`) の完全疎結合化と1-way Push化
* **概要**: `map_tool.py` から `dock_widget` への直接参照（`getattr`）を排除し、状態通知メソッド（`set_digitizing_mode`）による単方向バインドに刷新。
* **探索ヒント（コード検索用キーワード）**:
  * `getattr(self.dock_widget, "tab2_current_mode", "new")` (`map_tool.py` L250付近)
  * `class MainDockWidget(..., SymbologyMixin)` (`dock.py` 内の多重継承)

---

## 5. 構成変更後の `src/` 全体ディレクトリ構造案と想定コード行数

全域最適化アーキテクチャ適用後のリポジトリ全体の構造案と、リファクタリング前後の想定コード行数の比較です。

```
src/
├── plugin.py                     # プラグイン初期化・ライフサイクル管理 (軽量化)
├── canvas/
│   └── map_tool.py              # マップツール (getattr排除・純粋イベント発火&1-way Push受領)
├── layer/                        # データアクセス・ファイルI/O・レイヤツリー管理層
│   ├── manager.py               # LayerManager (画像削除/リネームAPIを追加し単一窓口化)
│   ├── symbology.py             # SymbologyMixin (dockからの重複継承を排除しLayerManager専用へ)
│   ├── gpkg.py                  # GeoPackage & SpatialIndex 操作
│   ├── grid_csv.py              # グリッドCSV・参照点レイヤ
│   ├── session_io.py            # セッション入出力
│   ├── settings_io.py           # プラグイン設定入出力
│   └── models.py                # データモデル
├── logic/                        # ドメインサービス・計算エンジン層
│   ├── digitizing_service.py    # 【新規】 打刻・検証・採番・Feature自動構築サービス
│   ├── georef_service.py        # 【新規】 ジオリファレンス一括パイプラインサービス
│   ├── transform.py             # 座標変換数理エンジン (アフィン / ヘルマート)
│   └── core.py                  # 出土形態/属性Enum・共通ルール
└── ui/                           # UIプレゼンテーション層 (UIリファクタリングv2適用)
    ├── core/                    # CoreUI基盤 (案2統合適用)
    │   ├── __init__.py
    │   ├── engine.py            # FieldSpec + Builder + CoreUIDialog (約300行)
    │   └── behavior.py          # Rules + Validators (約220行)
    ├── schemas.py               # 全画面宣言的UI定義 (純粋データ)
    ├── start_dialog.py          # 薄いダイアログコントローラ
    ├── dialogs.py              # 薄いスタンドアロンダイアログ群
    ├── dock.py                 # メディエーター (SymbologyMixin剥離・ツール連携専念)
    ├── tab1_image.py           # 薄い図面管理コントローラ (GeorefService/LayerManager呼び出し)
    ├── tab2_plot.py            # 薄い打刻コントローラ (DigitizingService呼び出し)
    ├── tab3_settings.py        # 薄い設定コントローラ
    ├── style.py                # スタイル定義
    └── constants.py            # UI定数
```

### リポジトリ全域の想定コード行数比較 (Line Count Estimation)

| 層 / ファイルパス | 改修前行数 (Approx.) | 改修後想定行数 | 主な変動理由・削減ポイント |
| :--- | :---: | :---: | :--- |
| **【UI層】** | | | |
| `src/ui/core/` (合計) | ~660 行 | **~520 行** | **【案2適用】** `engine.py` (300行) + `behavior.py` (220行) に2統合 |
| `src/ui/schemas.py` | ~390 行 | **~700 行** | UI定義の集中宣言 |
| `src/ui/start_dialog.py` | ~680 行 | **~200 行** | UI構築・I/Oを Schema / CoreUIDialog へ移管 |
| `src/ui/dialogs.py` | ~350 行 | **~140 行** | スタンドアロンダイアログの極薄化 |
| `src/ui/tab1_image.py` | ~475 行 | **~220 行** | **【約54%削減】** `GeorefService` & `LayerManager` へI/O・ジオリファレンス移管 |
| `src/ui/tab2_plot.py` | ~960 行 | **~180 行** | **【約81%削減】** `DigitizingService` へ Feature構築・採番・挿入を完全剥離 |
| `src/ui/tab3_settings.py` | ~360 行 | **~80 行** | **【約78%削減】** `set_values` / `collect_values` への置き換え |
| `src/ui/dock.py` | ~380 行 | **~220 行** | `SymbologyMixin` 剥離、メディエーター化 |
| `src/ui/style.py` / `constants.py` | ~720 行 | **~720 行** | 現状維持 |
| **【Logic層】** | | | |
| `src/logic/digitizing_service.py` *(新規)* | - | **~220 行** | **【新規ドメイン】** 打刻処理・一括検証・自動採番・Feature構築 |
| `src/logic/georef_service.py` *(新規)* | - | **~150 行** | **【新規ドメイン】** ジオリファレンス・変換一括パイプライン |
| `src/logic/transform.py` | ~290 行 | **~290 行** | 数理エンジンの維持 |
| `src/logic/core.py` | ~230 行 | **~230 行** | Enum・基本計算の維持 |
| **【Layer層】** | | | |
| `src/layer/manager.py` | ~450 行 | **~530 行** | `delete_image_layer` / `rename_image_layer` 等の安全操作API追加 |
| `src/layer/symbology.py` | ~250 行 | **~250 行** | `LayerManager` 専用へ整理 |
| その他 `layer/*.py` | ~900 行 | **~900 行** | 現状維持 |
| **【Canvas & Plugin層】** | | | |
| `src/canvas/map_tool.py` | ~420 行 | **~350 行** | `getattr` 参照削除、純粋イベント化 |
| `src/plugin.py` | ~280 行 | **~260 行** | ライフサイクル管理のクリーンアップ |
| **リポジトリ全体合計** | **~7,800 行** | **~6,160 行** | **全体で約 1,640 行 (約 21%) 削減**。UIコントローラ群は **50〜80%削減** し極めて堅牢化 |

---

### まとめ

「全域最適化アーキテクチャ」を適用することにより、UIリファクタリングで実現した宣言的画面構築と薄型コントローラ構造が、バックエンドのドメインサービス（`DigitizingService`, `GeorefService`）および単一アクセス窓口（`LayerManager`）とシームレスに結合します。結果として、**UI・ロジック・データアクセス・キャンバス操作の4層が疎結合で整理され、単体テスト可能で拡張性の高いPyQGISプラグイン基盤** が完成します。
