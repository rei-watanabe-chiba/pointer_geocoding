## タスクID
T-0047（追加修正: dialogs.pyへのCoreUI適用の人手確認中に発見された2件の動作修正）

## 変更ファイル一覧
- `src/ui/tab2_plot.py`
- `src/ui/dialogs.py`
- `.claude/state/tasks.md`（状態更新のみ）

## 変更概要

### 修正①: 属性がSPから別の属性に切り替わった時、自動連番モードへ自動復帰
対象: `src/ui/tab2_plot.py` の `Tab2DigitizingMixin._update_autonum_toggle_for_sp()`

- 変更前は、SP選択時に自動連番/解除トグルを強制的に「解除」+両ボタン無効化するだけで、
  非SP属性へ戻った際は両ボタンを再度有効化するのみで、モード自体（`tab2_autonum_mode`）は
  「解除」のまま復帰していなかった。
- 変更後は、`is_sp` が `True→False` へ切り替わる直前の状態（＝この関数呼び出し前に
  `tab2_autonum_buttons[0]`（自動連番側ボタン）が無効化されていたかどうか＝
  `was_forced_by_sp`）を判定し、SPによって強制的に解除状態にされていたケースに限り、
  自動連番側ボタン (`tab2_autonum_buttons[0]`) を `setChecked(True)` する。
- `tab2_autonum_buttons[0].toggled` シグナルは既存の `lambda checked: self._on_tab2_autonum_mode_changed(0) if checked else None`
  に接続済みであり、`setChecked(True)` 呼び出しにより `QButtonGroup`（`setExclusive(True)`）が
  自動連番ボタンをチェック状態にし、解除ボタンを自動的にアンチェックするため、これが
  `_on_tab2_autonum_mode_changed(0)` を1回発火させ、`tab2_autonum_mode = "auto"` の設定と
  `edit_point_name.setValue(self._get_next_point_number())` による採番を自動的に行う。
  新規のシグナル接続追加やdisconnect処理は不要（既存の接続を「トリガーする」実装のため）。

**設計判断: 「常に自動へ強制復帰」させるべきか**
- ユーザー要望は「SPから別属性に切り替えたら自動連番に戻す」であり、「非SP属性間
  （S↔P↔C）で切り替えた場合にユーザーが意図的に選んだ解除まで自動に戻す」ことは
  意図されていないと判断した。
- そのため、復帰処理は `was_forced_by_sp`（この呼び出し直前に自動連番ボタンが
  無効化されていた＝直前がSPだった、という状態）が真の場合にのみ発動するようにした。
  非SP属性間の切り替え時は `_update_autonum_toggle_for_sp(False)` が呼ばれても
  ボタンは既に有効化済み（`was_forced_by_sp` が偽）であるため、ユーザーが選択した
  「解除」状態はそのまま維持される。

**懸念点の検証と対策**
- 二重採番: `_apply_next_point_number()` は内部で `_update_point_name_widget_visibility()`
  （→ `_update_autonum_toggle_for_sp()` → 上記の `setChecked(True)` トリガー）を呼んだ後、
  続けて `tab2_autonum_mode == "auto"` の分岐で再度 `_get_next_point_number()` を呼び出す
  ため、同じ値が2回計算・代入される場合がある。ただし `_get_next_point_number()` は
  `core_logic.get_next_point_number()` を呼ぶ純粋な問い合わせ関数であり、レイヤへの
  書き込みや内部カウンタの消費を伴わないため、2回呼んでも同じ値が返るだけで実害はない
  （QSpinBoxの表示値が同じ値で2回setValueされるのみ）。
- 既存点名の上書き: `selected_edit_point_id is not None`（既存点を選択して編集中）の間は、
  `is_editing_existing` フラグで復帰処理自体をスキップするようにした。編集モードでは
  自動連番/解除トグル(`tab2_autonum_container`)自体が非表示（`widget_new_mode_actions`は
  新規モードのみ表示、`_on_tab2_mode_changed`参照）だが、`_update_point_name_widget_visibility()`
  は編集中でも呼ばれうる（`_on_category_changed`の `selected_edit_point_id is not None` 分岐）
  ため、念のため明示的にガードした。これにより、既存点の属性をSP→他属性に変更した際に
  `edit_point_name` の値が意図せず次の採番値で上書きされることを防いでいる。
- 重複判定タイミング: `_get_next_point_number()`自体は重複判定を行わない（採番候補の算出のみ）
  ため、本修正による重複判定タイミングへの影響はない。

### 修正②: PointNameEntryDialogのバリデーションをリアルタイムインライン表示に変更
対象: `src/ui/dialogs.py` の `PointNameEntryDialog`

- `GridInputDialog`のTier4パターン（`UIStyleHelper.create_status_panel()` /
  `update_status_panel()`）を踏襲し、`self.panel_status` / `self.lbl_status` を
  点名/枝番入力パネル (`input_panel`) の直下・OK/キャンセルボタン (`actions_panel`) の
  直前に配置した。
- SP属性選択時のみ `edit_point_name_sp.textChanged` を新規に `_on_realtime_validate()` へ
  接続し（非SPのQSpinBoxは常に有効な整数値を保持するため、ライブでの必須チェック対象外）、
  入力の都度 `RequiredValidator` を実行してインラインパネルにエラー/クリア状態を反映する。
  ダイアログ生成時にも初期状態を設定するため `__init__` の最後で1回呼び出している。
- `_on_ok_clicked()`からは、確定時の`QMessageBox.warning`によるエラー表示
  (`show_validation_error`呼び出し)を廃止し、`RequiredValidator`/`DuplicateValidator`
  いずれの失敗時も `UIStyleHelper.update_status_panel()` でインラインパネルに反映するよう
  変更した。SP必須チェックの再実行は、ライブ検証が正しく機能していれば通常到達しない
  防御的なコードとして残した（`btn_ok`が無効化されているため通常はクリックできない）。
- `show_validation_error` のインポート自体は同ファイル内の他クラス（`FeatureCreateDialog`）
  で引き続き使用されているため削除していない。

**設計判断: 必須チェックのみリアルタイム、重複チェックは確定時のみ**
- `DuplicateValidator`は`core_logic.check_point_duplicate`（`self._point_layer`への問い合わせ）
  を伴うため、`textChanged`のたびに毎回実行するとパフォーマンス影響が懸念される。
  一方`RequiredValidator`は文字列の空判定のみで負荷がなく、リアルタイムに適する。
  そのため、指示内で示唆された「必須チェックはリアルタイム、重複チェックは確定時のみ」の
  設計分離をそのまま採用した。

**設計判断: 確定ボタンの有効/無効をリアルタイムバリデーション結果に連動させるか**
- SP属性の必須チェック失敗時（点名未入力）は `btn_ok.setEnabled(False)` とし、入力されると
  `setEnabled(True)` に戻す方式を採用した。理由は、`GridInputDialog`の`btn_confirm`も同様に
  リアルタイム検証結果に応じて有効/無効を切り替えるパターンをすでに採用しており、
  一貫性を優先したため。ただし、重複チェックは確定時のみ実行されるため、
  ボタンが有効であっても確定時に重複エラーがインラインパネルに表示され得る
  （＝ボタン有効=必ず成功、を意味しない）点に留意。

## 自動テスト実行結果
自動テストなし（本プロジェクトには自動テストコマンドが設定されていない）。
`python3 -m py_compile src/ui/tab2_plot.py src/ui/dialogs.py` および `ast.parse()` による
構文チェックのみ実施し、いずれもエラーなし。

## スコープ外変更の有無
なし。変更ファイルは依頼で想定された `src/ui/tab2_plot.py` / `src/ui/dialogs.py` および
状態管理ファイル `.claude/state/tasks.md`（本文中の状態遷移更新のみ）にとどまる。
`src/ui/style.py` は変更不要と判断した（既存の `create_status_panel`/`update_status_panel`
をそのまま呼び出すのみで、スタイル側の変更は発生していない）。
