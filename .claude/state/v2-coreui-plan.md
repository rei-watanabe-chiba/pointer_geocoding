# v2: 巨大3ファイル対応 詳細計画（T-0045〜T-0047）

T-0043（責務別フォルダ再構成）・T-0044（QSpinBox安全QSSパターン確立）に続く、v2の中心テーマ。
対象は1000行を超える3ファイル（`src/ui/tab2_plot.py` 1905行、`src/ui/tab1_image.py` 1151行、
`src/ui/start_dialog.py` 1101行）。単純なUIパーツのコンポーネント化だけでは1000行を切れないと
判明したため（後述）、「CoreUI」という宣言的UI構築エンジン+汎用業務ロジックルール層を新設する
抜本的アプローチを採用する。

## 背景・経緯（この計画に至った理由）

### 調査で判明した事実
- 各ファイルの内訳（explorer調査、2026-09-16実施）:

| ファイル | 総行数 | UI構築部分 | イベントハンドラ/業務ロジック |
|---|---|---|---|
| tab2_plot.py | 1905 | 372(19.5%) | 1533(80.5%) |
| tab1_image.py | 1151 | 171(14.9%) | 980(85.1%) |
| start_dialog.py | 1101 | 302(27.4%) | 799(72.6%) |

- UI構築コードは各ファイルの15〜27%程度に過ぎず、大半は業務ロジック。単純な「UIパーツのコンポーネント化」
  （QWidgetサブクラスへの切り出し）だけでは、特にtab2_plot.pyは1000行を切れない試算だった。
- tab2_plot.pyはUI構築とイベントハンドラが密結合しており（`self.combo_attribute`等のウィジェット参照を
  18個以上のイベントハンドラが直接操作）、単純な「ウィジェットを返す関数」への切り出しでは不十分で、
  状態と値の取得/設定インターフェースをコンポーネント自身にカプセル化する設計が必要と判明した。

### 採用した方針転換
ユーザーからの指示で、「コンポーネント化」よりさらに抜本的な「CoreUI」（宣言的UI構築エンジン+汎用業務
ロジックルールの汎用化）というアプローチへ転換した。呼び出し側は「構築元を判別するマーカー・接続要素・
付随させる業務ロジックを指定するのみ」とする設計。あわせて、**アコーディオン方式は廃止し、常時展開の
パネル方式へUIレイアウトを統一することが許可されている**（tab2_plot.pyがT-0027で先行して採用した
「常時展開4パネル」方式を、CoreUI移行後も画面構成の標準とする。アコーディオンへの回帰は行わない）。

### Qt Designer(.uiファイル)を採用しない理由
Qt Designerはレガシー化しつつあるとの判断でユーザーが明示的に不採用とした。PyQt6のネイティブなコード
構築方式（現行の`docs/integrated_master_design.md` 1.2節の「GUI完全コード構築」原則）を維持する。

## アーキテクチャ全体像

```
src/ui/core/                  ← 新設「CoreUI」: 宣言的UI構築エンジン
├── __init__.py
├── field_spec.py                 FieldSpec/PanelSpec データクラス群（宣言のみ）
├── builder.py                    PanelSpec→実ウィジェット生成（内部で既存ui/style.pyのbuild_flex_row等を利用）
└── rules.py                      汎用業務ロジックの型（後述）

src/ui/tab1_image_schema.py   ← 各画面の宣言（薄いデータファイル、T-0045で新設）
src/ui/tab2_plot_schema.py    ← T-0047で新設
src/ui/start_dialog_schema.py ← T-0046で新設

src/ui/tab1_image.py          ← 呼び出し側（大幅減量）: schemaを渡して構築、bind()で業務ロジック接続
src/ui/tab2_plot.py
src/ui/start_dialog.py
```

### CoreUI（宣言的UI構築、`src/ui/core/field_spec.py` + `builder.py`）
`FieldSpec`（1フィールド＝1行の宣言: 種別/ラベル/選択肢/表示条件/バリデータ/イベントフック名）と
`PanelSpec`（フィールドの集合＝1パネル）というデータだけで画面を記述し、
`CoreUIBuilder.build(spec, parent)`が実ウィジェットを組み立てる。内部実装は既存の
`UIStyleHelper.build_flex_row`等をそのまま部品として使う（`ui/style.py`を置き換えるのではなく1段上に被せる）。

呼び出し側イメージ:
```python
# ui/tab2_plot_schema.py（宣言のみ、業務ロジックの実体は書かない）
POINT_INFO_PANEL = PanelSpec("point_info", fields=[
    FieldSpec("point_name", WidgetType.SPINBOX, label=UILabels.POINT_NAME, on_change="commit_if_editing"),
    FieldSpec("point_name_sp", WidgetType.LINEEDIT, label=UILabels.POINT_NAME,
              visible_when="is_sp", validator=SP_NAME_REGEX, on_change="commit_if_editing"),
    FieldSpec("branch_no", WidgetType.LINEEDIT, label=UILabels.BRANCH_NO, on_change="commit_if_editing"),
], rules=[ModeVisibilityRule(...), RealtimeCommitRule(...)])
```
```python
# ui/tab2_plot.py 側（呼び出し側）
self.point_info_panel = CoreUIBuilder.build(POINT_INFO_PANEL, parent=container)
self.point_info_panel.bind("commit_if_editing", self._commit_point_identity_if_editing)
layout.addWidget(self.point_info_panel.widget)
```

これが「構築元を判別するマーカー(=schema/panel_id)・接続要素(=bind)・付随させる業務ロジック(=rules)を
指定するのみ」という要件に対応する。

### CoreUI logic（汎用業務ロジック、`src/ui/core/rules.py`）
tab2の「モードに応じた表示切替」「編集中フィールドのリアルタイムコミット」「重複バリデーション」のような
**パターン自体**を汎用ルールとして切り出す（`ModeVisibilityRule`/`RealtimeCommitRule`/
`DuplicateValidationRule`等）。GeoPackage書き込みや座標変換そのもの（`logic/core.py`）は対象外。
将来tab1にも「新規/編集モード」的な概念が生まれた場合、同じルールを再利用できる。

## 正直な評価（メリット・デメリット、ユーザーに提示済み）

**メリット**:
- UI構築コードが表形式の宣言に圧縮され、単純コンポーネント化より削減効果が大きい
- 画面間で挙動パターンが構造的に統一される
- 将来v2で新しいパネル・画面を追加するコストが大きく下がる（長期的に一番効く）

**デメリット**:
- 「リファクタ」ではなく「小さな自作フレームワークの新設」。エンジン自体にバグがあれば全画面に波及する
  （個別コンポーネント化なら影響範囲は1パネルに閉じる）
- tab2は「SP属性だけ挙動が違う」「解除モードだけダイアログを出す」等、画面固有の例外が多く、宣言だけ
  では表現しきれない部分が必ず残る。CoreUIの外で素のPyQtコードを書く逃げ道を最初から用意する
  （`qgis-plugin-code-reduction`スキルの「フレームワークの制約に当たったらその部分だけ独自実装に寄せる」
  という注意点と同じ考え方）
- 実装規模が大きく、implementer/verifierサイクルも複数回に分かれる見込み

## タスク分割

### T-0045: CoreUI試作、tab1_image.pyへ適用
- `src/ui/core/`パッケージ（field_spec.py/builder.py/rules.py）を新設
- `FieldSpec`/`PanelSpec`のデータクラス設計、`CoreUIBuilder`の実装
- tab1_image.pyの既存パネル（画像管理フォーム・情報パネル等）をCoreUI経由の構築に置き換える
- 目的: エンジンが実際に動作し、行数削減効果があるかをtab1で検証してから残り2画面に展開する
- 成功基準: tab1_image.pyの行数削減、QGIS上での動作が従来と同等であることの人手確認

### T-0046: start_dialog.py等その他画面への展開
- T-0045で検証されたCoreUIパターンをstart_dialog.pyへ適用
- T-0045の実装で得られた知見（エンジンの過不足、逃げ道の必要性等）を反映してCoreUI自体も調整してよい

### T-0047: tab2_plot.pyへの適用
- 最も複雑で密結合度の高い画面。T-0045/T-0046で確立したパターンを適用しつつ、画面固有の例外
  （新規/編集モード、自動連番/解除、SP属性、リアルタイムコミット等）はCoreUI logicの汎用ルールとして
  切り出すか、素のPyQtコードとして残すかを都度判断する
- 1000行を切れない場合の対応方針は、T-0045/T-0046の実測値をもとに改めて検討する
  （業務ロジックのファイル分割等も選択肢。ただしui/フォルダ内での分割であり、過去の「ファイル分割が
  多く管理しづらい」という懸念には該当しない）

## T-0045 追加スコープ: 業務ロジック共通化の第一段階（値の抜き出し/書き込み）

T-0045完了後、ユーザーから「tab1〜3で共通する業務ロジックの汎用化も行うこと。inputからの情報抜き出しと
格納/upload部分の共通化」という追加指示を受け、以下の切り分けで対応する。

### 汎用化する部分: 値の抜き出し/書き込み（今回対応）
`BuiltPanel`（`src/ui/core/builder.py`）に以下を追加する。
- `get_value(field_id) -> Any`: フィールドのwidget_typeに応じた値取得
  （LINEEDIT_ROW→`.text()`, COMBOBOX_ROW→`.currentText()`, SEGMENTED_TOGGLE→選択中インデックス）
- `set_value(field_id, value) -> None`: 対称的な書き込み
- `collect_values() -> Dict[str, Any]`: 登録済み値系フィールドを全て`get_value`して辞書化
- TABLE型は行構造が複雑なため対象外（個別ロジックのまま）。
- `tab1_image.py`側の既存handler（`_on_rename_layer_clicked`/`_on_confirm_image_clicked`/
  `_on_export_layer_clicked`等）を、キャッシュしたウィジェット参照への直接`.text()`/`.currentText()`
  呼び出しから、`panel.get_value()`/`collect_values()`経由に置き換える。

### 汎用化を据え置く部分: 格納/upload（storage）
`rules.py`のRule抽象基底のdocstringに既に明記されている「1画面（tab1）だけの実例から形を決め打ちせず、
2〜3画面目（tab2のリアルタイムコミット・重複バリデーション等）が揃ってから確定する」という方針を踏襲する。
tab1には複雑な「格納」パターン（リアルタイムコミット等）が存在せず、ここで汎用Ruleを作ると
tab2の実例に合わず手戻りするリスクが高いため、CommitRule等のstorage側汎用ルールはT-0047まで据え置く。

### スキーマファイル統合
`src/ui/tab1_image_schema.py`は単独ファイルのまま画面ごとに増やすと再度のファイル分散を招くため、
`src/ui/schemas.py`という単一ファイルに統合する。`TAB1_*`（今回）/`TAB2_*`/`TAB3_*`/`START_DIALOG_*`
（T-0046/T-0047で追記）とセクション分けして1ファイルに集約する。

## T-0045-b: tab1におけるCoreUI化・機能分離の追加試行

T-0045完了後、explorerによる総合調査（①基準点系分割／②座標変換後ダイアログ廃止／③バリデーション
ヘルパー汎用化／④レイヤー管理共通部品化／⑤全体総合）を踏まえ、②③④をT-0045-bとして実施する。
①（基準点系の別ファイル分割）は結合度が高く効果も薄いため見送り。

### ②座標変換後ダイアログの廃止
`tab1_image.py`の`_on_transform_clicked()`内、座標変換完了時に表示される`QMessageBox.information()`
（回転角度・アスペクト比の表示、約11行）を廃止する。同内容は既に情報パネル（`TAB1_INFO_PANEL_SPEC`の
line3_6残差サマリ行）に表示済みで完全重複しており、ダイアログでしか提供できない機能はない
（ユーザーの選択・確認応答は不要）。messageBar()の成功通知＋ステータス行更新で完了通知は維持する。

### ③バリデーションヘルパーの汎用化
`src/ui/core/validators.py`を新設し、tab1/tab2/start_dialogで共通する「必須チェック」「重複チェック」
「正規表現チェック」パターンをValidatorクラス群として汎用化する。今回はtab1_image.pyへの適用のみ試行し、
tab2/start_dialogへの展開はT-0046/T-0047で判断する（1画面の実例だけで形を決め打ちしない、という
rules.pyと同じ方針）。

### ④レイヤー管理の共通部品化
tab1_image.pyの`_on_delete_layer_clicked`/`_on_rename_layer_clicked`が`point_layer`に対して直接
`startEditing`/`changeAttributeValue`/`commitChanges`を呼んでいる箇所を、`src/layer/manager.py`
（LayerManager）に`clear_drawing_name_for_layer(layer_name)`/`rename_drawing_name(old_name, new_name)`
という高レベルAPIとして切り出し、tab1_image.py側はそれらを呼ぶだけにする。

### ⑤tab2改修（T-0046）への申し送り事項
explorer総合調査の⑤で判明した、tab2_plot.py(1906行)関連の所見をここに記録する。T-0046着手時に参照すること。
- tab2_plot.pyの肥大化要因はデジタイジング入力の状態管理の複雑さ（フォーカスモード/カテゴリフィルタ/
  既存点編集・新規点作成の分岐等、15〜20メソッド）そのものであり、単純なファイル分割では不十分。
  内部構造の明確化（Mixinのさらなる細分化、またはlogic層への移行）が必要。
- エラー表示（QMessageBox/ステータスパネル/フィールド赤枠）がタブごとに混在している。統一APIとしての
  検討余地あり（UIStyleHelper側への統合候補）。
- tab2の属性コミット（`_commit_fields_to_feature`）は既にstartEditing/changeAttributeValue/commitChanges
  パターンを使っており、T-0045-bで④として切り出すLayerManagerの高レベルAPIと統合できる可能性がある
  （tab1のパターンをtab2にも展開できないか確認すること）。
- ③のバリデーションヘルパー（`src/ui/core/validators.py`）は、tab1適用の実例を踏まえてtab2の
  重複チェック（`check_point_duplicate`呼び出し箇所）・必須チェックへの展開を検討する。

## 確定済みの技術的制約（CoreUI実装時に必ず守ること）

- **QSpinBoxへのQSS適用パターン**: `docs/integrated_master_design.md` 1.2節「OSネイティブUIの保護と
  QSpinBoxへのQSS適用パターン」を参照。CoreUIがQSpinBox系フィールドを統一スタイリングする場合、必ず
  この検証済みパターンに従うこと（subcontrol-position必須、矢印はborder-triangleハック/base64データURI
  禁止で実SVGファイル参照、状態変化フィードバックは背景色でなくアイコン色変更、状態変化時のプロパティ
  再宣言）。
- 新規開発時、`docs/integrated_master_design.md`は「現状のコードのみを正とする」という記述原則がある
  ため、CoreUI関連の設計判断が固まり次第、随時1.4節（モジュール構成）等に追記すること。
