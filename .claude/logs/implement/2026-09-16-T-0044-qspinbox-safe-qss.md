## タスクID
T-0044

## 変更ファイル一覧
- src/ui/style.py

## 変更概要
`UIStyleHelper.get_style_sheet()` の QSS 文字列に、`QSpinBox` / `QSpinBox:focus` / `QSpinBox::up-button, QSpinBox::down-button` の3ルールを追加した（`QLineEdit, QgsFilterLineEdit, QComboBox` のフォーカスルールの直後に挿入）。

- `QSpinBox`: `background-color: palette(base)`, `color: palette(text)`, `border: 1px solid palette(mid)`, `border-radius: 4px`, `padding: 0px 4px`, `min-height: 28px`, `min-width: 70px`, `selection-background-color: palette(highlight)`, `selection-color: palette(highlighted-text)`。既存の `QLineEdit, QgsFilterLineEdit, QComboBox` ルールと同じ palette ロール参照方式に揃えた（依頼文中の `#B0B0B0` / `white` 等のハードコード色は、本ファイル内の入力系ウィジェットが一貫して palette ロール参照を採用しているため、既存パターンに合わせて palette(base)/palette(mid) 等に置き換えた）。
- `QSpinBox:focus`: `border: 1.5px solid palette(highlight)`（`QLineEdit:focus` 等と同じ幅・色指定に統一）。
- `QSpinBox::up-button, QSpinBox::down-button`: `subcontrol-origin: border; width: 18px;` のみ。依頼の制約通り、`QSpinBox::up-arrow` / `QSpinBox::down-arrow` に対するルールは一切追加していない（`image` プロパティ等も未指定）。矢印描画は完全にプラットフォームのベーススタイルに委ねている。

`min-width` は依頼のガイド値である70pxをそのまま採用した（`edit_point_name` / start_dialog.py のグリッド設定スピンボックス行はいずれも `build_flex_row`/`build_child_container` でストレッチ配分される構成であり、70px固定は最小幅の下限としてのみ機能し、レイアウト崩れの要因にはならないと判断した）。

`UIStyleHelper.create_spinbox()` 自体のロジックは変更していない（依頼通り、テーマQSS追加のみで対応可能と判断）。

## 自動テスト実行結果
自動テストなし。`python3 -m py_compile src/ui/style.py` で構文エラーがないことを確認した（成功、エラーなし）。

## スコープ外変更の有無
なし。`src/ui/style.py` の `get_style_sheet()` メソッド内へのQSS追加のみで、他ファイル（tab2_plot.py, tab1_image.py, start_dialog.py, dialogs.py, tab3_settings.py 等）や `create_spinbox()` 自体には手を加えていない。

---

## フォローアップ修正（2026-09-16）

### 不具合内容
ユーザーがQGIS上で確認した結果、`QSpinBox::up-button, QSpinBox::down-button` の共通ルールに `subcontrol-position` が指定されておらず、上下ボタンが視覚的にテキストボックス外側へ分離して表示され、マウスホバーでのカーソル変化・クリックが機能しない（クリック判定領域と見た目のズレ）不具合が判明した。矢印サブコントロール（`::up-arrow`/`::down-arrow`）自体は対象外で、T-0041の「矢印消失」とは別種の不具合。

### 修正概要
`src/ui/style.py` の `get_style_sheet()` 内、`QSpinBox` 関連ルールを以下の通り変更した。

- `QSpinBox` 本体: `padding-right: 20px` を追加し、ボタン列（幅18px）との重なりを避けるテキスト入力領域を確保した。
- `QSpinBox::up-button, QSpinBox::down-button` の共通ルールを廃止し、`QSpinBox::up-button` と `QSpinBox::down-button` をそれぞれ個別のセレクタに分離した。
  - `QSpinBox::up-button`: `subcontrol-origin: border; subcontrol-position: top right; width: 18px; border-left: 1px solid palette(mid); border-top-right-radius: 4px;`
  - `QSpinBox::down-button`: `subcontrol-origin: border; subcontrol-position: bottom right; width: 18px; border-left: 1px solid palette(mid); border-bottom-right-radius: 4px;`
  - `border-left` でテキスト領域とボタン列の間に薄い区切り線を追加し、`border-top-right-radius`/`border-bottom-right-radius` をそれぞれのボタンの外周角にのみ適用することで、ボタン列が本体のボーダー内に統合された見た目になるようにした。

依頼の制約通り、`QSpinBox::up-arrow` / `QSpinBox::down-arrow` に対するルール（`image` プロパティ含む）は今回も一切追加していない。矢印描画は引き続きQtのベーススタイルに完全に委ねている。`create_spinbox()` のロジックにも変更はない。

### 自動テスト実行結果（フォローアップ）
自動テストなし。`python3 -m py_compile src/ui/style.py` を実行し、構文エラーがないことを確認した（成功、エラーなし）。

### スコープ外変更の有無（フォローアップ）
なし。`src/ui/style.py` の `get_style_sheet()` メソッド内、`QSpinBox` 関連ルールの修正のみ。他ファイル・`create_spinbox()` 自体・矢印サブコントロールルールには手を加えていない。

---

## 2回目のフォローアップ修正（2026-09-16）

### 不具合内容
1回目のフォローアップでボタンの位置・クリック判定は正常化したが、2回目の人手確認で、ボタン領域自体は存在し上下クリックで値は増減するものの、**矢印グリフ自体が描画されない**（見た目上、ボタンの中に何も表示されない）ことが判明した。

### 修正概要
`src/ui/style.py` の `get_style_sheet()` 内、`QSpinBox::up-button, QSpinBox::down-button` ルールの直後に、`QSpinBox::up-arrow` / `QSpinBox::down-arrow` の2ルールを新規追加した。ボーダートリック（`border-left`/`border-right` を透明にし、片側のみ色付きボーダーを指定して三角形を形成する手法）で矢印を明示的に描画する。

- `QSpinBox::up-arrow`: `image: none; width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid palette(text);`
- `QSpinBox::down-arrow`: `image: none; width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid palette(text);`

色は `palette(text)` を参照しているため、ダークモード/ライトモードいずれのテーマでも自動追従する設計とした（他のルールと同じ palette ロール参照方式に統一）。

あわせて、`QSpinBox` ルール直前にあった「矢印サブコントロールには意図的に手を加えない」旨の古いコメント（T-0041での矢印描画の失敗経緯を記した注記）は、今回の方針転換により実態と矛盾するため、内容を更新した（矢印ルールは本フォローアップで追加済みである旨を記載）。

既存の `QSpinBox` 本体・`QSpinBox:focus`・`QSpinBox::up-button, QSpinBox::down-button`（1回目のフォローアップで分離済みの個別セレクタ）には変更を加えていない。`create_spinbox()` のロジックにも変更はない。

### 自動テスト実行結果（2回目のフォローアップ）
自動テストなし。`python3 -m py_compile src/ui/style.py` を実行し、構文エラーがないことを確認した（成功、エラーなし）。

### スコープ外変更の有無（2回目のフォローアップ）
なし。`src/ui/style.py` の `get_style_sheet()` メソッド内、矢印サブコントロールルールの追加と、それに伴う直前コメントの更新のみ。他ファイル・`create_spinbox()` 自体・矢印以外の既存ルールには手を加えていない。

---

## 3回目のフォローアップ修正（2026-09-16）

### 不具合内容
2回目のフォローアップで追加したボーダートリック方式（`border-left`/`border-right: transparent` + 片側のみ色付きボーダー）による矢印描画が、人手確認で三角形ではなく**黒塗りの四角形**として表示される不具合が判明した。Web調査の結果、QSSのボーダートリックによる三角形描画はQtの`QSpinBox`矢印サブコントロールに対して既知の不安定挙動であり（Qt Forum等で同様の報告あり）、公式に推奨される解決策は`image`プロパティで実際のアイコン画像を指定する方式であることが判明した。

### 修正概要
`src/ui/style.py` の `get_style_sheet()` 内、`QSpinBox::up-arrow` / `QSpinBox::down-arrow` ルールを、ボーダートリック方式からインラインSVG（base64データURI）を`image`プロパティで指定する方式へ置き換えた。

- `QSpinBox::up-arrow`: `border-left`/`border-right`/`border-bottom`を用いたボーダートリック記述を削除し、`image: url(data:image/svg+xml;base64,...)`（8x6の上向き三角形SVG、`fill="#6B6B6B"`）、`width: 8px; height: 6px;` に置き換えた。
- `QSpinBox::down-arrow`: 同様に`border-left`/`border-right`/`border-top`のボーダートリック記述を削除し、`image: url(data:image/svg+xml;base64,...)`（8x6の下向き三角形SVG、`fill="#6B6B6B"`）、`width: 8px; height: 6px;` に置き換えた。
- base64文字列は改行を含まない1行の値として埋め込んだ。QSS全体はPythonのプレーンな三重引用符文字列（f-stringではない）内にあるため、base64中の記号（`+`, `/`, `=`）とPython構文の衝突はない（該当のbase64値自体にはこれらの記号は含まれていない）。

**トレードオフ（依頼通り）**: 矢印の色は依頼指定のニュートラルグレー `#6B6B6B` にSVG内で固定した。2回目のフォローアップで採用していた `palette(text)` によるダーク/ライトモード自動追従は今回廃止しており、テーマに関わらず常に同じグレーで表示される。この点は依頼文の指示通り「テーマ非追従の固定色でよい」との承認に基づく仕様であり、今回はこれ以上の追従対応（動的SVG生成等）は行っていない。

既存の `QSpinBox` 本体・`QSpinBox:focus`・`QSpinBox::up-button`/`QSpinBox::down-button`（`subcontrol-position`含む）には変更を加えていない。`create_spinbox()` のロジックにも変更はない。

### 自動テスト実行結果（3回目のフォローアップ）
自動テストなし。`python3 -m py_compile src/ui/style.py` を実行し、構文エラーがないことを確認した（成功、エラーなし）。

### スコープ外変更の有無（3回目のフォローアップ）
なし。`src/ui/style.py` の `get_style_sheet()` メソッド内、`QSpinBox::up-arrow`/`QSpinBox::down-arrow` ルールの中身（矢印描画方式）の置き換えのみ。他ファイル・`create_spinbox()` 自体・矢印以外の既存ルールには手を加えていない。
