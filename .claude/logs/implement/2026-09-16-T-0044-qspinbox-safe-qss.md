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

---

## 4回目のフォローアップ修正（2026-09-16）

### 不具合内容
3回目のフォローアップで採用したbase64データURI方式（`image: url(data:image/svg+xml;base64,...)`）が、人手確認で矢印が完全に非表示（データURI自体がロードされていない）という結果になった。Web調査の結果、QtのQSSにおける`url()`はbase64データURIの読み込みに既知の制限があり（QTBUG-51081）、信頼できる形でサポートされていないことが判明した。

### 修正概要
base64データURI方式を廃止し、Qt標準のurl()によるファイルパス参照方式（本ファイル内の既存の`image.svg`/`setting.svg`等と同じ方式）へ転換した。

**新規追加ファイル**:
- `src/icon/spin_up_arrow.svg`（8x6の上向き三角形、`fill="#6B6B6B"`）
- `src/icon/spin_down_arrow.svg`（8x6の下向き三角形、`fill="#6B6B6B"`）

**`src/ui/style.py`の変更**:
- `import os` を追加（既存の import 群の先頭）。
- `get_style_sheet()` の冒頭で、`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` により `src/` ディレクトリの絶対パスを求め、`icon/spin_up_arrow.svg` / `icon/spin_down_arrow.svg` への絶対パスを算出。Qtの`url()`がバックスラッシュ区切りのWindowsパスを正しく解釈できない場合があるため、`os.sep` を `/` に置換した文字列（`up_arrow_path` / `down_arrow_path`）を用意した。
- QSS本体はf-string化せず、プレーンな三重引用符文字列のまま維持した。理由: QSS全体には多数のルールブロックがリテラルの`{`/`}`を含んでおり、f-stringや`str.format()`化するとそれら全てを`{{`/`}}`にエスケープする必要が生じ、可読性・保守性を大きく損なうため。代わりに、`QSpinBox::up-arrow`/`QSpinBox::down-arrow`の`image: url(...)`内に一意なプレースホルダ文字列`__UP_ARROW_PATH__`/`__DOWN_ARROW_PATH__`を埋め込み、テンプレート文字列の直後で`.replace("__UP_ARROW_PATH__", up_arrow_path).replace("__DOWN_ARROW_PATH__", down_arrow_path)`により置換する方式を採った。
- 3回目のフォローアップで追加したbase64データURI（`image: url(data:image/svg+xml;base64,...)`）は完全に削除した。
- `QSpinBox::up-arrow`/`QSpinBox::down-arrow`直前のコメント（3回目のフォローアップの経緯説明）を更新し、QTBUG-51081の制限と実ファイル参照への転換理由を追記した。
- 依頼通り、色は引き続きニュートラルグレー `#6B6B6B` 固定（SVGファイル内の`fill`属性）で、テーマ非追従のままとした。
- `get_style_sheet()` のシグネチャ（`@classmethod`、引数なし）は変更していない。呼び出し元 `apply_theme()`（`cls.get_style_sheet()` を呼び出すのみ）にも変更は不要だった。
- `QSpinBox` 本体・`QSpinBox:focus`・`QSpinBox::up-button`/`QSpinBox::down-button`（`subcontrol-position`含む）・`create_spinbox()` には変更を加えていない。

### 自動テスト実行結果（4回目のフォローアップ）
自動テストなし。`python3 -m py_compile src/ui/style.py` を実行し、構文エラーがないことを確認した（成功、エラーなし）。

あわせて、`qgis.PyQt` モジュールをスタブ化したPython単体スクリプトで `UIStyleHelper.get_style_sheet()` を直接呼び出し、生成されたQSS文字列中の `QSpinBox::up-arrow`/`QSpinBox::down-arrow` ルールに埋め込まれた `image: url(...)` のパスが、それぞれ `/home/user/pointer_geocoding/src/icon/spin_up_arrow.svg` / `spin_down_arrow.svg`（実行環境の絶対パス）に正しく置換されており、`os.path.exists()` でいずれも実在するファイルであることを確認した（構文・パス解決の静的確認であり、QGIS上での実際の描画結果を保証するものではない）。

### スコープ外変更の有無（4回目のフォローアップ）
なし。`src/ui/style.py` の `get_style_sheet()` メソッド内（矢印画像参照方式の変更・パス計算ロジックの追加・importの追加）と、`src/icon/` 配下への新規SVGファイル2件の追加のみ。他ファイル・`create_spinbox()` 自体・矢印以外の既存ルールには手を加えていない。

## 押下フィードバック追加（2026-09-16）

### 不具合内容
ユーザーから「ボタンを押しても見た目が変わらず押した感がない」との要望があった。`QSpinBox::up-button`/`down-button`には`:pressed`擬似状態のルールが存在せず、押下時の視覚フィードバックがなかった。

### 修正概要
`src/ui/style.py`の`get_style_sheet()`内、既存の`QSpinBox::down-button { ... }`ルールの直後（`QSpinBox::up-arrow`前のコメントブロックの前）に、以下のルールを追加した。

```css
/* T-0044 5th follow-up: pressed-state feedback for the up/down
   buttons. Previously the buttons gave no visual response on
   click. Tone matched to the existing QPushButton:pressed rule
   (rgba(128, 128, 128, 0.28) below), kept simpler here per the
   requested palette(midlight) approach since QSpinBox buttons
   have no separate hover rule to stay consistent with. */
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
    background-color: palette(midlight);
}
```

既存の`QPushButton:hover`/`QPushButton:pressed`ルールは`rgba(128, 128, 128, 0.15)`/`rgba(128, 128, 128, 0.28)`という半透明グレーの背景色指定方式を採用していることを確認したが、依頼指示で明示された`palette(midlight)`をそのまま採用した（QSSの`palette()`関数はテーマ追従色を返すQt標準の指定方式であり、`QSpinBox`本体・`focus`ルールも同様に`palette(...)`系を使用しているため、トーンとして矛盾しない）。

`QSpinBox`本体・`QSpinBox:focus`・`up-button`/`down-button`の`subcontrol-position`・矢印画像参照(`image: url(...)`)には一切変更を加えていない。`create_spinbox()`のロジックも変更していない。

### 自動テスト実行結果（押下フィードバック追加）
自動テストなし。`python3 -m py_compile src/ui/style.py`を実行し、構文エラーがないことを確認した（成功、エラーなし）。

### スコープ外変更の有無（押下フィードバック追加）
なし。変更は`src/ui/style.py`の`get_style_sheet()`内、`QSpinBox::up-button:pressed, QSpinBox::down-button:pressed`ルールの追加のみ。

## 押下フィードバックの角丸修正（2026-09-16）

### 不具合内容
上記「押下フィードバック追加」で導入した`QSpinBox::up-button:pressed, QSpinBox::down-button:pressed`の共通ルールが`background-color`のみを指定し角丸(`border-top-right-radius`/`border-bottom-right-radius`)を再宣言していなかったため、ユーザーがQGIS上で確認したところ、押下時の背景色がボタンの角丸を無視して四角形のまま描画され、入力ボックスのボーダーからはみ出して見える不具合が判明した。

### 修正概要
`src/ui/style.py`の`get_style_sheet()`内、`QSpinBox::up-button:pressed, QSpinBox::down-button:pressed`の共通セレクタを、`QSpinBox::up-button`/`QSpinBox::down-button`（非pressed）と同様に個別セレクタへ分離し、それぞれ対応する角丸を再宣言した。

```css
QSpinBox::up-button:pressed {
    background-color: palette(midlight);
    border-top-right-radius: 4px;
}

QSpinBox::down-button:pressed {
    background-color: palette(midlight);
    border-bottom-right-radius: 4px;
}
```

角丸の値`4px`は、既存の`QSpinBox::up-button`/`QSpinBox::down-button`（非pressed）ルールで使用されている`border-top-right-radius: 4px;`/`border-bottom-right-radius: 4px;`と一致させた。

`QSpinBox`本体・`QSpinBox:focus`・`up-button`/`down-button`（非pressed）・矢印画像参照(`image: url(...)`)には一切変更を加えていない。`create_spinbox()`のロジックも変更していない。

### 自動テスト実行結果（押下フィードバックの角丸修正）
自動テストなし。`python3 -m py_compile src/ui/style.py`を実行し、構文エラーがないことを確認した（成功、エラーなし）。

### スコープ外変更の有無（押下フィードバックの角丸修正）
なし。変更は`src/ui/style.py`の`get_style_sheet()`内、`QSpinBox::up-button:pressed`/`QSpinBox::down-button:pressed`ルールをそれぞれ個別セレクタに分離し角丸を再宣言した点のみ。

## フォーカスボーダー幅の統一修正（2026-09-16）

### 不具合内容
ユーザーがQGIS上で確認したところ、フォーカス時の青いボーダー（`QSpinBox:focus { border: 1.5px solid palette(highlight); }`）の上に、上下ボタンの背景色（`::up-button`/`::down-button`、押下時は`:pressed`）がオーバーラップして表示され、フォーカス枠が一部隠れてしまう不具合が判明した。

### 原因
ベースの`QSpinBox`ルールは`border: 1px solid palette(mid);`で1px幅。フォーカス時のみ`1.5px`へ太くなるため、あらかじめ1px基準で配置されているup-button/down-buttonサブコントロールのジオメトリとズレが生じ、太くなった分のボーダー領域にボタンの背景色が重なって見えていたと考えられる。

### 修正概要
`src/ui/style.py`の`get_style_sheet()`内、`QSpinBox:focus`ルールのボーダー幅をベースと同じ`1px`に変更した（色は`palette(highlight)`のまま）。

```css
QSpinBox:focus {
    border: 1px solid palette(highlight);
}
```

依頼の制約通り、このボーダー幅の値以外は変更していない。`QSpinBox`本体・`::up-button`/`::down-button`（`:pressed`含む）・矢印画像参照(`image: url(...)`)には一切手を加えていない。他ウィジェット（`QLineEdit`/`QgsFilterLineEdit`/`QComboBox`の`:focus`ルール、`1.5px`のまま）にも変更はない。`create_spinbox()`のロジックも変更していない。

### 自動テスト実行結果（フォーカスボーダー幅の統一修正）
自動テストなし。`python3 -m py_compile src/ui/style.py`を実行し、構文エラーがないことを確認した（成功、エラーなし）。

### スコープ外変更の有無（フォーカスボーダー幅の統一修正）
なし。変更は`src/ui/style.py`の`get_style_sheet()`内、`QSpinBox:focus`ルールのボーダー幅を`1.5px`から`1px`に変更した1点のみ。他ファイル・他ウィジェットの`:focus`ルールには手を加えていない。

## フォーカス+押下の複合状態修正（2026-09-16）

### 不具合内容
直前の「フォーカスボーダー幅の統一修正」（`1.5px`→`1px`）を試みたが、ユーザーから改めて、フォーカスボーダー幅は`1.5px`（太いまま）を維持したいとの指示があった。あわせて、問題の本質は「フォーカス中のQSpinBoxの上下ボタンを押した時（フォーカス+pressedが同時に起きる状態）」だけボタンの押下背景色がフォーカス枠にオーバーラップする点にあり、単純にフォーカスのみ・押下のみの状態では問題が発生しないことが判明した。原因として、既存の`QSpinBox::up-button:pressed`/`QSpinBox::down-button:pressed`ルールが`background-color`と角丸のみを指定し、`border-left`（非pressedの`up-button`/`down-button`ルールには存在する）を再宣言していないため、フォーカス状態が重なった際にQtがボックス情報を正しく引き継げていない可能性が高いと判断した。

### 修正概要
`src/ui/style.py`の`get_style_sheet()`内で以下の2点を修正した。

1. `QSpinBox:focus`のボーダー幅を`1px`から`1.5px`へ差し戻した（直前のフォローアップを取り消し）。
```css
QSpinBox:focus {
    border: 1.5px solid palette(highlight);
}
```

2. 既存の`QSpinBox::up-button:pressed`/`QSpinBox::down-button:pressed`ルール（フォーカスなしの押下状態、変更なし）の直後に、フォーカス+押下の複合セレクタ`QSpinBox:focus::up-button:pressed`/`QSpinBox:focus::down-button:pressed`を新規追加し、`background-color`・`border-left`・角丸を明示的に再宣言した。
```css
QSpinBox:focus::up-button:pressed {
    background-color: palette(midlight);
    border-left: 1px solid palette(mid);
    border-top-right-radius: 4px;
}

QSpinBox:focus::down-button:pressed {
    background-color: palette(midlight);
    border-left: 1px solid palette(mid);
    border-bottom-right-radius: 4px;
}
```

既存の`QSpinBox::up-button:pressed`/`QSpinBox::down-button:pressed`ルール自体は削除せず維持した（フォーカスなしの押下状態はこれまで通り）。`QSpinBox`本体・`::up-button`/`::down-button`（非pressed）・矢印画像参照(`image: url(...)`)には一切手を加えていない。`create_spinbox()`のロジックも変更していない。

### 自動テスト実行結果（フォーカス+押下の複合状態修正）
自動テストなし。`python3 -m py_compile src/ui/style.py`を実行し、構文エラーがないことを確認した（成功、エラーなし）。

### スコープ外変更の有無（フォーカス+押下の複合状態修正）
なし。変更は`src/ui/style.py`の`get_style_sheet()`内、`QSpinBox:focus`のボーダー幅差し戻しと、`QSpinBox:focus::up-button:pressed`/`QSpinBox:focus::down-button:pressed`ルールの新規追加の2点のみ。他ファイル・他ウィジェットの`:focus`ルールには手を加えていない。
