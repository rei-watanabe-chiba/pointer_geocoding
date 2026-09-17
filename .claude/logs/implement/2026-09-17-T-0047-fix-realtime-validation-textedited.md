## タスクID
T-0047（追加修正: FeatureCreateDialog/PointNameEntryDialogのリアルタイムバリデーション不具合）

## 変更ファイル一覧
- `src/ui/dialogs.py`
- `.claude/state/tasks.md`

## 変更概要

### 事象
T-0047の人手確認で、`PointNameEntryDialog`(SP属性時の`edit_point_name_sp`)と
`FeatureCreateDialog`(`edit_name`)のリアルタイムバリデーションが実際には効かず、
確定ボタン押下時にしかエラー表示（`panel_status`/`lbl_status`）が切り替わらない、
という不具合が報告された。これは直前の修正コミット(`40205e6`
「PointNameEntryDialogのリアルタイム検証化」、`bb57308`
「FeatureCreateDialogのバリデーション表示をインライン方式に戻す」)を適用した
**後**の人手確認で再度検出されたものであり、`textChanged`接続による方式そのものが
実機で機能していないことを示唆している。

### 調査内容と結論
以下の観点でコードを精査したが、静的には明確な論理的不備は見つからなかった。

1. **接続タイミング**: `self.edit_name`/`self.edit_point_name_sp`は
   `CoreUIBuilder.build()`実行中に一度だけ生成され、`_update_point_name_widget_visibility`
   に相当する処理（`input_panel.get_row(...).hide()`）はウィジェットの`show()`/`hide()`のみで、
   再生成は行われていないことを確認した(`PointNameEntryDialog.__init__`)。
2. **`exec_()`呼び出し前後**: `tab2_plot.py`の`_on_create_feature_clicked`/
   `_on_canvas_clicked`(→`PointNameEntryDialog`生成箇所)とも、ダイアログ生成から
   `exec_()`呼び出しまでの間に別インスタンスへの差し替えや再接続漏れは見られなかった。
   両者とも`UIStyleHelper.apply_theme(dlg)`を`exec_()`直前に呼んでいるが、これは
   `__init__`完了後（＝`textChanged.connect()`実行後）に呼ばれるスタイルシート適用のみで、
   Python側のシグナル接続を破棄する処理は含まれていない。
3. **`QRegExpValidator`との相互作用**: `PointNameEntryDialog`のSP分岐では
   `setValidator()`が`textChanged.connect()`より前に呼ばれており、順序として問題はない。
   `FeatureCreateDialog.edit_name`にはそもそもバリデータが設定されておらず、
   両ダイアログに共通する要因ではないため、この観点は本事象の主因ではないと判断した。
4. **例外の握りつぶし**: `_on_realtime_validate`内で使用しているロジック
   (`RequiredValidator(...).validate(text)` → `UIStyleHelper.update_status_panel(...)`)は、
   `_on_ok_clicked`内でも同一の呼び出しパターンが使われており、そちらは確定時に
   正しく動作している（人手確認の報告内容とも整合）。同一コードパスが例外で
   落ちるなら確定時も失敗するはずであり、例外による握りつぶしの可能性は低いと判断した。
5. **既知の動作良好例との比較**: `GridInputDialog`（同ファイル内、Tier4ステータスパネル）は
   同様の「`textChanged` → 検証 → `update_status_panel`」方式だが、対象ウィジェットが
   `QLineEdit`(`edit_y`)である。一方`FeatureCreateDialog`/`PointNameEntryDialog`は
   `CoreUIBuilder`のLINEEDIT_ROWが生成する`QgsFilterLineEdit`が対象であり、唯一の
   構造的な違いはこの点であった。ただし`GridInputDialog`自体のリアルタイム挙動が
   実際に人手確認された記録は見当たらず、この差異が真因であると断定はできない。

以上の通り、**単一の確定的な論理バグをコード上で特定することはできなかった**。
そのため、依頼内容の項目5（フォールバック方針）に基づき、`textChanged`に加えて
`textEdited`（Qtの標準シグナルで、ユーザーのキー入力による変更でのみ確実に発火し、
プログラム的な`setText()`由来のsuppressionの影響を受けない）を同一ハンドラへ
併用接続する対応を実施した。

### 修正内容（`src/ui/dialogs.py`）
- `FeatureCreateDialog.__init__`: `self.edit_name.textChanged.connect(self._on_realtime_validate)`
  に加えて `self.edit_name.textEdited.connect(self._on_realtime_validate)` を追加。
- `PointNameEntryDialog.__init__`: SP属性時、
  `self.edit_point_name_sp.textChanged.connect(self._on_realtime_validate)`
  に加えて `self.edit_point_name_sp.textEdited.connect(self._on_realtime_validate)` を追加。
- いずれも既存の`_on_realtime_validate`実装・呼び出し初期化(`self._on_realtime_validate()`)
  はそのまま維持。シグナル接続の解除処理は追加していない（両ダイアログとも`QDialog`が
  `close`/ガベージコレクトされる際にPyQtがシグナル接続を自動解放する標準的なライフサイクルで、
  対称的な`disconnect`を明示管理していた既存コードも存在しないため、既存パターンを踏襲した）。

## 自動テスト実行結果
自動テストなし。`python3 -m py_compile src/ui/dialogs.py` による構文チェックのみ実施し、
エラーなしを確認した。

## スコープ外変更の有無
なし。変更は `src/ui/dialogs.py`（依頼対象の2ダイアログの`__init__`のみ）と、
状態管理ファイル `.claude/state/tasks.md` の該当行更新に限定した。
