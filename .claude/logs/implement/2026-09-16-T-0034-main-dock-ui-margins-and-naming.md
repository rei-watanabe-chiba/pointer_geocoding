## タスクID
T-0034: main_dockのUI/余白調整とタブ名称変更（3点セット、いずれもUI/表示のみでロジック変更なし）

## 変更ファイル一覧
- `src/main_dock.py`
- `src/main_dock_constants.py`
- `src/tab2_digitizing_mixin.py`
- `src/main_dock_dialogs.py`（コメントのみ）

## 変更概要

### ① top_row と tab2_container の視覚的区別
`main_dock.py` の `_init_ui()` 内、`root_layout.addWidget(top_row)` の直後・
`self.tab1_container = self._create_tab1_ui()` の前に、
`UIStyleHelper.build_separator(root_widget)` で生成した `QFrame(HLine)` を
`root_layout.addWidget()` で1本追加した。背景色等のスタイル変更は行っていない。

### ② 余白定数の新設と適用
`main_dock_constants.py` の `UIConfig` に以下の定数を追加した（既存の書き方
（`UIConfig` に定数を並べるフラットな形）に合わせ、新規クラスは設けなかった）。

- `DOCK_OUTER_MARGIN = 6`（旧 `root_layout.setContentsMargins(6, 6, 6, 6)`）
- `TOP_ROW_BUTTON_SPACING = 6`（旧 `top_layout.setSpacing(6)`）
- `SECTION_GAP = 6`（旧 `root_layout.setSpacing(6)`）
- `PANEL_CONTAINER_MARGIN_LEFT = 4` / `PANEL_CONTAINER_MARGIN_TOP = 4` /
  `PANEL_CONTAINER_MARGIN_RIGHT = 16` / `PANEL_CONTAINER_MARGIN_BOTTOM = 4`
  （旧 `tab2_digitizing_mixin.py` の `layout.setContentsMargins(4, 4, 16, 4)`。
  依頼文では「LR/TB」の2定数と書かれていたが、右マージンのみスクロールバー
  避けで非対称という既存コメントの意図を保ったまま個別に調整可能にするため、
  実装では左右上下を4つの独立した定数に分解した）
- `PANEL_GROUP_SPACING = 8`（旧 `layout.setSpacing(8)`、4パネル間の縦間隔）
- `PANEL_INNER_SPACING = 6`（旧 `info_layout`/`attr_layout`/`focus_layout` の
  それぞれの `setSpacing(6)`。3箇所とも同一値だったため単一定数に集約）
- `SEPARATOR_MARGIN_TOP = 4` / `SEPARATOR_MARGIN_BOTTOM = 4`（新設。
  `PANEL_GROUP_SPACING`（8）の半分を初期値とした）

区切り線（`UIStyleHelper.build_separator()`）を独立余白で囲むため、
`tab2_digitizing_mixin.py` の3箇所（点情報パネル/属性パネル/フォーカスモード
パネルの各前段）と `main_dock.py` の新設1箇所、計4箇所すべてで
`layout.addSpacing(SEPARATOR_MARGIN_TOP)` → `layout.addWidget(separator)` →
`layout.addSpacing(SEPARATOR_MARGIN_BOTTOM)` の形に変更した
（`main_dock.py` 側は `root_layout` に対して同様の形で追加）。
これにより区切り線の上下余白は `PANEL_GROUP_SPACING`（パネル間隔）から独立し、
今後は `SEPARATOR_MARGIN_TOP`/`BOTTOM` のみを調整すればよい状態にした。

### ③ タブ名称の表示文字列変更
`main_dock_constants.py` の `UILabels`:
- `TAB_1_TITLE`: "画像管理" → "IMG"
- `TAB_2_TITLE`: "遺物点作成" → "PLOT"
- `TAB_3_TITLE`: "設定" → "SET"
- `OUTPUT_DIALOG_TITLE` を `TAB_4_TITLE` にリネームし、値を "CSV出力" → "OUT"
  に変更。

内部識別子のリネーム（4点、依頼スコープ通り）:
- `main_dock.py`: `self.output_container` → `self.tab4_container`
- `tab2_digitizing_mixin.py`: `_create_output_ui()` → `_create_tab4_ui()`
  （呼び出し元 `main_dock.py` の `self._create_output_ui()` も
  `self._create_tab4_ui()` に追従）
- `main_dock_constants.py`: `UILabels.OUTPUT_DIALOG_TITLE` →
  `UILabels.TAB_4_TITLE`

`output_dialog`/`_show_output_dialog`/`btn_top_output` はスコープ指示通り
変更していない（`image_dialog`/`settings_dialog` と同じ命名系統のため対象外）。

`output_container`/`_create_output_ui`/`OUTPUT_DIALOG_TITLE` への
コメント・docstring言及は `grep` で全て洗い出し、`main_dock.py` /
`main_dock_dialogs.py` / `tab2_digitizing_mixin.py` の該当箇所を
「T-0034でリネームされた」旨の注記付きで追従修正した
（履歴として旧名を残す注記コメント自体は意図的に残置）。

## 自動テスト実行結果
自動テストなし（プロジェクトに自動テストコマンドは未設定）。
代わりに `python3 -m py_compile src/main_dock.py src/main_dock_constants.py
src/tab2_digitizing_mixin.py src/main_dock_dialogs.py` による構文チェックを
実施し、エラーなく完了した。

## スコープ外変更の有無
なし。対象ファイルは依頼で指定された4ファイル（`main_dock.py`,
`main_dock_constants.py`, `tab2_digitizing_mixin.py`,
`main_dock_dialogs.py`（コメントのみ））のみを変更した。ロジック（信号接続、
ハンドラの処理内容、フィールド名等）は一切変更していない。

---

## 追記: 区切り線マージンの二重加算修正（同一タスクID内フォローアップ）

### 経緯
verifierの静的検証により、上記②で採用した実装
（`layout.addSpacing(SEPARATOR_MARGIN_TOP)` →
`layout.addWidget(separator)` → `layout.addSpacing(SEPARATOR_MARGIN_BOTTOM)`
を、`layout.setSpacing(PANEL_GROUP_SPACING)` 済みのレイアウトに対して
そのまま追加していた点）が、設計意図（区切り線の余白を狭める）と逆方向に
働く不整合として指摘された。

### 原因（コードロジック上の説明）
Qtの `QBoxLayout`（`QVBoxLayout`含む）は `setSpacing(s)` 設定時、その
レイアウトが管理する**隣接する2アイテムの間すべて**にギャップ`s`を挿入する。
これは `addSpacing()` で追加された `QSpacerItem` も「1つのレイアウトアイテム」
として扱われるため対象になる。
そのため旧実装（`tab2_digitizing_mixin.py` の3箇所、点情報パネル/属性パネル/
フォーカスモードパネルそれぞれの前段）では、以下の並びになっていた。

```
[前のウィジェット] -- setSpacing(8) -- [addSpacing(4)のスペーサー] -- setSpacing(8) -- [区切り線] ...
```

区切り線の直前だけで見ると、実際の余白は
`PANEL_GROUP_SPACING(8) + SEPARATOR_MARGIN_TOP(4) + PANEL_GROUP_SPACING(8)`
= 20px相当（スペーサーの前後両方にレイアウトの自動ギャップが乗る）となり、
意図していた「`PANEL_GROUP_SPACING + SEPARATOR_MARGIN` の1回分の合算」
（12px相当）の、さらに8px分過剰に膨らんだ状態になっていた。区切り線の
下側（`SEPARATOR_MARGIN_BOTTOM` 側）も同様の理屈で過剰倍加していた。

`main_dock.py`（top_row と tab2_container の間の区切り線、L264付近）は
現状のコードでは `root_layout.addWidget(UIStyleHelper.build_separator(...))`
のみで、前後に `addSpacing()` を伴っていないため、この二重加算は発生して
いない（この区切り線の前後の余白は `root_layout.setSpacing(SECTION_GAP)`
による通常の1回分のギャップのみ）。そのため今回の修正対象は
`tab2_digitizing_mixin.py` の3箇所のみとし、`main_dock.py`
は変更していない（依頼文には対象候補として挙げられていたが、対応する
不整合が実際には存在しなかったため対象外とした）。

### 修正内容
`tab2_digitizing_mixin.py` に `Tab2DigitizingMixin._build_padded_separator()`
（`@staticmethod`）を新設した。これは以下を行う。

1. `QWidget`（ラッパー）を1つ生成し、その中に `QVBoxLayout` を設定する。
2. ラッパー内の `QVBoxLayout` の `setContentsMargins()` に
   `(0, SEPARATOR_MARGIN_TOP, 0, SEPARATOR_MARGIN_BOTTOM)` を設定し、
   `setSpacing(0)` とする。
3. `UIStyleHelper.build_separator()` で生成した `QFrame(HLine)` を、この
   ラッパー内レイアウトに `addWidget()` する。
4. ラッパー自体を呼び出し元へ返す。

呼び出し元（3箇所）は、旧来の3行
（`addSpacing(TOP)`/`addWidget(separator)`/`addSpacing(BOTTOM)`）を、
`layout.addWidget(self._build_padded_separator(container))` の1行に置換した。

### 二重加算がどう解消されるか（コードロジック上の説明）
修正後、親レイアウト（`layout`, `setSpacing(PANEL_GROUP_SPACING)`設定済み）
から見ると、ラッパーウィジェットは他の通常ウィジェット（`group_point_info`等）
と同様に「1個のレイアウトアイテム」として扱われる。`addSpacing()`による
独立したスペーサーアイテムを追加していないため、親レイアウトの自動ギャップ
（`PANEL_GROUP_SPACING`）はラッパーの前後にそれぞれ1回ずつしか挿入されない
（スペーサーアイテムを介した二重適用が構造的に発生しなくなった）。
ラッパー内部の余白（`SEPARATOR_MARGIN_TOP`/`BOTTOM`）は、ラッパー自身の
`contentsMargins`として1回だけ加算される。
結果として、区切り線の実際の上下の見た目上の余白は
「`PANEL_GROUP_SPACING` 1回 + `SEPARATOR_MARGIN_TOP`（または`BOTTOM`）1回」
の合算値（現行値では 8+4=12px相当）に収束し、旧実装で発生していた
スペーサーアイテム経由の二重加算（8+4+8=20px相当）は解消される
（あくまでレイアウトアイテムの構成上の説明であり、QGIS実行時の見た目の
断定はしない）。

なお `SEPARATOR_MARGIN_TOP`/`SEPARATOR_MARGIN_BOTTOM` の値自体（各4px）は
依頼通り変更していない。`main_dock_constants.py` への変更も不要と判断し、
今回は行っていない（値の意味・使われ方に変更がないため）。

### 変更ファイル一覧（今回の追加修正分）
- `src/tab2_digitizing_mixin.py`
  （`Tab2DigitizingMixin._build_padded_separator()` の新設と、3箇所の
  区切り線構築コードの置換のみ。前回実装分（区切り線の存在自体・その他の
  余白定数・タブ名称変更）には触れていない）

`src/main_dock.py` / `src/main_dock_constants.py` は、上記「原因」欄の
理由により今回変更していない。

### 自動テスト実行結果（追加修正分）
自動テストなし（プロジェクトに自動テストコマンドは未設定）。代わりに
`python3 -m py_compile src/main_dock.py src/tab2_digitizing_mixin.py
src/main_dock_constants.py src/style_helper.py` を実行し、構文エラーなく
完了した。

### スコープ外変更の有無（追加修正分）
なし。依頼スコープ（区切り線マージンの二重加算問題のみ）に限定して
`tab2_digitizing_mixin.py` のみを変更した。前回実装（①区切り線追加/②
その他の余白定数/③タブ名称変更）のスコープには触れていない。

---

## 追記2: 点情報パネル直前の区切り線を削除（同一タスクID内フォローアップ）

`main_dock.py` 側に top_row と tab2_container の間の区切り線を新設した結果、
点情報パネル(`group_point_info`)直前の区切り線と近接して2本並んでしまう
視覚的重複が指摘されたため、`tab2_digitizing_mixin.py` の`_create_tab2_ui()`
内、`layout.addWidget(self._build_padded_separator(container))`（点情報
パネル直前の1箇所のみ）を削除した。属性パネル・フォーカスモードパネル前の
区切り線（他の2箇所）は維持している。直前の説明コメントも、区切り線が
存在しない旨がわかるよう文言を微修正した。

### 変更ファイル一覧（追記2分）
- `src/tab2_digitizing_mixin.py`（点情報パネル直前の区切り線1行削除＋
  直前コメントの微修正のみ）

### 自動テスト実行結果（追記2分）
自動テストなし。`python3 -m py_compile src/tab2_digitizing_mixin.py` を実行し、
構文エラーなく完了した。

### スコープ外変更の有無（追記2分）
なし。`src/tab2_digitizing_mixin.py` の該当1箇所（区切り線削除＋コメント）
以外は変更していない。
