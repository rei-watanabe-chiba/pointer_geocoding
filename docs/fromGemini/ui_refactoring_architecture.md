# UI全域スリム化アーキテクチャ設計書 (v2: core2ファイル再編案)

本ドキュメントは、PyQGISプラグイン（`pointer_geocoding`）における `src/ui/` 配下の全ファイルを対象とした **「UI全域スリム化アーキテクチャ」** の設計思想、目的の詳細化、対象ファイルマッピング、抽象化されたアプローチ枠組み、改修対象の探索ヒント、および構成変更後のディレクトリ構造と想定コード行数をまとめたリファクタリング設計書です。

---

## 1. 設計思想 (Architectural Principles)

1. **完全宣言型UI (Declarative UI as Pure Data)**
   ウィジェットのインスタンス化やレイアウト構造（`QVBoxLayout` / `QHBoxLayout`）の手動構築手順をUIコントローラから排除し、**「画面がどのようなUI要素で構成されているか」を宣言的なデータ構造（`PanelSpec` / `FieldSpec`）として定義**します。
2. **薄いコントローラ (Thin Controller)**
   UIコントローラクラス（各TabクラスやDialogクラス）は、**「UIスキーマのロード」「`BuiltPanel.bind` によるイベント遅延結合」「QGIS固有処理（レイヤ・キャンバス操作）への委譲」** のみに専念させます。
3. **単一責任と高凝集 (Single Responsibility & High Cohesion)**
   * **UI構成定義**: `src/ui/schemas.py` に全画面分を一約化
   * **UI自動構築・ダイアログ・状態走査**: `src/ui/core/engine.py` に集約
   * **画面間連動 (Interlock)・入力検証 (Validation)**: `src/ui/core/behavior.py` に集約
4. **遅延結合と疎結合 (Loose Coupling via Pending Hooks)**
   スキーマ定義側（`schemas.py`）はビジネスロジックやハンドラ関数の実体に直接依存せず、文字列識別子（`hook_name`）のみを保持し、ビルド後にコントローラ側からバインドします。

---

## 2. 目的の詳細化 (Detailed Purpose)

**「UIレイアウトの宣言的定義（スキーマ）とタブ特有のQGISイベント制御のみを行う薄いコントローラ化」** の具体的な達成基準および責務境界は以下の通りです。

### コントローラクラス（Tab / Dialog）が手放すこと（剥離対象）
* `QSpinBox`, `QLineEdit`, `QComboBox` 等のPyQtウィジェットの手動 `new` 生成および `layout.addWidget()` 呼び出し。
* ウィジェットから手動で1項目ずつ `.text()`, `.value()`, `.currentText()` を読み出して辞書化する状態抽出処理。
* UIイベントに対する個別シグナル接続（`.connect()`）の直接記述。
* 「特定の選択項目に応じて他ウィジェットを表示/非表示化する」といった条件分岐UI制御コード。
* 手動での入力必須チェック、エラーダイアログ呼び出し、赤枠強調の適用処理。

### コントローラクラス（Tab / Dialog）が集中的に行うこと（専念対象）
* **UI生成の委譲**: `CoreUIBuilder.build(SPEC)` の呼び出し。
* **イベントの紐付け**: `panel.bind("hook_name", self._handler)` によるビジネスロジック接続。
* **QGISドメイン制御**: QGISキャンバスや `LayerManager` への命令発火（ジオメトリ更新、属性書き込み、マップツール切替、プロジェクト保存等）。

---

## 3. 対象ファイルマッピング (Target Files)

コア基盤である `src/ui/core/` は過度なファイル細分化を避け、**「構造構築（`engine.py`）」** と **「動的振る舞い（`behavior.py`）」** の 2 ファイルへ集約・再編します。

| レイヤ分類 | 対象ファイル | 役割とスリム化の方向性 |
| :--- | :--- | :--- |
| **コアUIエンジン層** | `src/ui/core/engine.py` *(再編)* | **【統合ファイル】** `field_spec` (データ構造定義), `builder` (ウィジェット生成・一括状態走査エンジン), `dialog` (`CoreUIDialog` 共通ダイアログ基盤) を1つに統合。 |
| **コア振る舞い・検証層** | `src/ui/core/behavior.py` *(再編)* | **【統合ファイル】** `rules` (画面連動・自動コミット・モード可視性Ruleエンジン) と `validators` (入力検証・赤枠強調・エラー通知パイプライン) を1つに統合。 |
| **宣言的スキーマ層** | `src/ui/schemas.py` | 全画面のUI構造定義を一約化。`START_DIALOG_SPEC`, `TAB2_SPEC`, `TAB3_SPEC` などを集約宣言。 |
| **ダイアログ実装層** | `src/ui/start_dialog.py`<br>`src/ui/dialogs.py` | `CoreUIDialog` と `schemas.py` を呼び出す薄いダイアログへ置換。個別のレイアウト構築コードを撤廃。 |
| **タブ・コントローラ層** | `src/ui/tab1_image.py`<br>`src/ui/tab2_plot.py`<br>`src/ui/tab3_settings.py` | `CoreUIBuilder` を採用し、UI構築・状態同期・バリデーションを剥ぎ取り、QGISイベントハンドラのみに特化。 |
| **メディエーター層** | `src/ui/dock.py` | メインパネル。各モデレスダイアログとのライフサイクル調停・マップツール（`map_tool`）の休止/再開同期に専念。 |
| **スタイル・定数層** | `src/ui/style.py`<br>`src/ui/constants.py` | テーマ適用・ウィジェットファクトリ・UI文字列定数の一元管理。 |

---

## 4. アプローチの抽象的枠組みと改修対象探索ヒント

実装設計・コード改修を行う開発者やLLMがソースコードを検索・調査するための探索ヒント（識別子・キーワード）です。

### アプローチ A: フォーム状態（State）の一括自動バインディング
* **概要**: ウィジェットからの個別の値取得/注入コードを全廃し、`BuiltPanel`（`src/ui/core/engine.py` 内）の `collect_values()` / `set_values()` による一括処理へ置き換えます。
* **探索ヒント（コード検索用キーワード）**:
  * `get_digitizing_input_state`（`tab2_plot.py` 内の手動辞書化関数）
  * `update_settings_ui_from_dict` / `_on_settings_apply_clicked`（`tab3_settings.py` 内の手動 `.setValue()` / `.value()` 連続呼び出し）
  * `get_session_data`（`start_dialog.py` 内の手動フォーム読取り）

### アプローチ B: ダイアログ構造の共通化 (`CoreUIDialog`)
* **概要**: ダイアログ構築のボイラープレート（`QVBoxLayout`, OK/Cancelボタン配置, `UIStyleHelper.apply_theme`）を `CoreUIDialog`（`src/ui/core/engine.py` 内）へ追い出します。
* **探索ヒント（コード検索用キーワード）**:
  * `class StartDialog(QDialog)` （`start_dialog.py`）
  * `class GridInputDialog` / `class FeatureCreateDialog` / `class PointNameEntryDialog` （`dialogs.py`）
  * 上記ダイアログ内の `_init_ui()` メソッドおよび `btn_ok` / `btn_cancel` のレイアウト構築コード

### アプローチ C: 宣言的ルールエンジンによるUI連動・シグナル結合の自動化
* **概要**: UI間の連動（特定の選択項目で他の表示/非表示や有効/無効を切り替える処理）や、編集時のリアルタイムコミットを `Rule` クラス（`src/ui/core/behavior.py` 内）としてカプセル化します。
* **探索ヒント（コード検索用キーワード）**:
  * `_update_feature_related_visibility`（`tab2_plot.py` 内の遺構関連ウィジェット表示切替）
  * `_on_session_type_changed`（`start_dialog.py` 内の新規/既存モード切替連動）
  * `_commit_attribute_fields_if_editing` / `_commit_point_identity_if_editing`（`tab2_plot.py` 内のリアルタイムコミット発火）

### アプローチ D: バリデーション・パイプラインの標準化
* **概要**: 直書きの条件チェック・警告ダイアログ表示・赤枠適用処理を、`Validator` パイプライン（`src/ui/core/behavior.py` 内）に統一します。
* **探索ヒント（コード検索用キーワード）**:
  * `_validate_and_accept`（`start_dialog.py` や各種ダイアログ内の入力チェック）
  * `_update_error_borders` / `show_warning_dialog` / `show_validation_error` （手動エラー強調・通知）
  * `QMessageBox.warning` がハンドラ内で直接呼び出されている箇所

---

## 5. 構成変更後の `src/ui/` ディレクトリ構造案と想定コード行数

`src/ui/core/` を `engine.py` と `behavior.py` の 2 ファイルへ整理・再編した後の構成と、ファイル別想定コード行数の比較です。

```
src/ui/
├── core/                        # UIコア基盤 (役割別に2ファイルへ再編)
│   ├── __init__.py              # engine / behavior からのシンボル再エクスポート
│   ├── engine.py                # 【構造系】 WidgetSpec, CoreUIBuilder, BuiltPanel, CoreUIDialog
│   └── behavior.py              # 【動的制御】 Ruleエンジン (可視性/連動), Validatorパイプライン
├── schemas.py                   # 全画面・全ダイアログのUI宣言的スキーマ定義 (純粋データ)
├── start_dialog.py              # セッション開始ダイアログ (CoreUIDialog継承の薄いコントローラ)
├── dialogs.py                  # スタンドアロンダイアログ群 (GridInput, FeatureCreate, PointNameEntry)
├── dock.py                     # メイン操作ドックパネル (ダイアログ調停・マップツール連動メディエーター)
├── tab1_image.py               # 図面管理・ジオリファレンス・基準点設定 (薄いコントローラ)
├── tab2_plot.py                # 遺物点打刻・フォーカスモード・属性管理 (薄いコントローラ)
├── tab3_settings.py            # プラグイン表示・シンボル設定 (薄いコントローラ)
├── style.py                    # Materialデザイン調QSS・共通ウィジェットファクトリ
└── constants.py                # UI文字列・デフォルトサイズ・設定定数
```

### ファイル別 想定コード行数比較 (Line Count Estimation)

| ファイルパス | 改修前行数 (Approx.) | 改修後想定行数 | 主な変動理由・削減ポイント |
| :--- | :---: | :---: | :--- |
| `src/ui/core/engine.py` *(再編)* | - | **~850 行** | `field_spec` (~350行) + `builder` (~420行) + `dialog` (~80行) を1ファイルに統合 |
| `src/ui/core/behavior.py` *(再編)* | - | **~440 行** | `rules` (~120行) + `validators` (~320行) を1ファイルに統合 |
| `src/ui/schemas.py` | ~390 行 | **~700 行** | Tab 2, Tab 3, StartDialog, 各小ダイアログのUI定義（`PanelSpec`）を集約 |
| `src/ui/start_dialog.py` | ~680 行 | **~220 行** | **【約68%削減】** UI手動構築・連動・値取得を `schemas.py` と `CoreUIDialog` へ移管 |
| `src/ui/dialogs.py` | ~350 行 | **~150 行** | **【約57%削減】** `GridInput`, `FeatureCreate`, `PointNameEntry` の手動UI生成を排除 |
| `src/ui/tab1_image.py` | ~475 行 | **~400 行** | `behavior.py` の検証パイプライン活用と手動チェックコードの整理 |
| `src/ui/tab2_plot.py` | ~960 行 | **~380 行** | **【約60%削減】** 手動ウィジェット生成・状態走査・連動可視性制御を Rule/Schema へ抽出 |
| `src/ui/tab3_settings.py` | ~360 行 | **~80 行** | **【約78%削減】** 手動設定値読書きコードを `set_values` / `collect_values` に一括置換 |
| `src/ui/dock.py` | ~380 行 | **~250 行** | **【約34%削減】** 各ダイアログ・キャンバスツール間の調停（メディエーター）処理に専念 |
| `src/ui/style.py` | ~440 行 | **~440 行** | テーマ適用・ファクトリは現状維持 |
| `src/ui/constants.py` | ~280 行 | **~280 行** | UI文字列・定数は一元管理を維持 |
| **UIディレクトリ全体合計** | **~5,675 行** | **~4,190 行** | **全体で約 1,485 行 (約 26%) 削減**。特にコントローラコードは50%以上削減 |

---

### まとめ
`src/ui/core/` を構造系の `engine.py` と振る舞い系の `behavior.py` の 2 ファイルへ整理したことで、`core` 内のモジュール過多が抑えられ、開発者が機能を探す際の迷いが大きく軽減されます。インポートも `from .core import CoreUIBuilder, Rule, Validator` のように `core/__init__.py` からシンプルに行えるため、可読性と保守性の両立が達成されます。
