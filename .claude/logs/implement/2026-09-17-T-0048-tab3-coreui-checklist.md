## 人手確認チェックリスト

### 確認手順
1. QGISでプラグインを起動し、セッション（新規または既存）を開いて、右ドックの
   「設定」タブ（Tab 3）を開く。
2. タブ内の表示（「基準点」「遺物点」「ラベル」「表示縮尺」の4セクション見出しと、
   各セクション内の入力欄）が表示されることを確認する。
3. 「基準点」セクションの「サイズ」「線幅」スピンボックスの値を変更し、「線色」の
   カラースウォッチボタンをクリックしてカラーピッカーが開くこと、色を選択すると
   ボタンの背景色が選択した色に変わることを確認する。
4. 「遺物点」セクションで同様に「サイズ」「線幅」を変更し、「線色」ボタンで色を
   選択、「塗りあり」「塗りなし」ラジオボタンを切り替えられることを確認する。
5. 「ラベル」セクションで「サイズ」「間隔」スピンボックスを変更し、「白線あり」
   「白線なし」ラジオボタンを切り替えられることを確認する。
6. 「表示縮尺」セクションで「大グリッド:」「小グリッド:」それぞれの
   「常時」/「指定」ラジオボタンを切り替え、「指定」を選んだ時だけ隣接する
   閾値スピンボックスが編集可能（有効）になり、「常時」を選ぶと無効化される
   ことを確認する。
7. 上記の値をいくつか変更したうえで「適用」ボタンを押し、エラーが出ずに
   処理が完了することを確認する。
8. 適用後、図面上のグリッド・遺物点・ラベルの見た目（サイズ・線幅・色・塗り・
   白線の有無）が変更内容通りに反映されることを確認する。
9. 一度タブを閉じて（別タブへ切り替えて）再度「設定」タブを開き直すか、
   セッションを保存後に再読み込みし、直前に「適用」した設定値が
   設定タブの各ウィジェットに正しく復元表示されることを確認する
   （`update_settings_ui_from_dict` の動作確認。特に「指定」モードで保存した
   閾値スピンボックスの数値が正しく復元されること、「常時」モードで保存した
   場合に閾値スピンボックスが無効状態で復元されることの両方を確認）。
10. セッションフォルダ内の `settings.json` を直接確認し、保存された値
    （`ref_symbol_size`/`ref_symbol_line_width`/`ref_symbol_line_color`/
    `point_symbol_size`/`point_symbol_line_width`/`point_symbol_fill_enabled`/
    `point_symbol_line_color`/`label_size`/`label_halo`/`label_offset`/
    `scale_major_grid`/`scale_minor_grid`）がUI操作と整合していることを確認する。

### 各手順で期待される挙動（設計書ベース）
- 手順2-6: `dcs/integrated_master_design.md`および`.claude/state/v2-coreui-plan.md`の
  CoreUI方針（宣言的スキーマからUIを構築し、既存の見た目・操作性を変えない）に基づき、
  T-0045〜T-0047同様、外部から見た挙動（表示項目・初期値・操作可能性）はCoreUI適用前と
  同一であるべき。
- 手順6: 元のコード（`radio_always.toggled.connect(lambda chk: spin.setEnabled(not chk))`）
  と同じ「常時/指定」トグル連動を`tab3_settings.py`の`_on_major_scale_mode_changed`/
  `_on_minor_scale_mode_changed`に移設したのみであり、挙動は変更していない前提。
- 手順7-8: `LayerManager.settings_changed`シグナル経由で`_on_layer_manager_settings_changed`
  が発火し、基準点・遺物点シンボロジーの再適用とキャンバス再描画が行われる設計
  （`tab3_settings.py`のdocstring「Step3-B」の記述に基づく）。CoreUI化はこの経路自体には
  手を入れていないため、適用後の反映挙動もこれまで通りのはず。
- 手順9-10: `update_settings_ui_from_dict`はsettings.json（またはメモリ上のdict）から
  各ウィジェットへ値を反映する既存の責務を持つ。CoreUI化により手動`hasattr`ガード付き
  `.setValue()`の連鎖を`BuiltPanel.set_values()`一括呼び出しに置き換えたが、
  「指定」時のみ閾値スピンボックス値を上書きする条件（`sc_maj > 0`のときのみ反映）は
  実装ログに記載の通り維持している。

### 注意喚起
- 今回のCoreUI適用に伴い、`src/ui/core/field_spec.py`/`core/builder.py`に
  `SECTION_HEADER`/`DOUBLE_SPINBOX_ROW`/`COLOR_BUTTON_ROW`/`ROW_GROUP`の
  4種類の新規WidgetTypeを追加した。特に`ROW_GROUP`は`CoreUIBuilder.build()`の
  ループ内でサブフィールドの`field_types`登録処理を追加しており、他のCoreUI適用済み
  画面（tab1_image.py/start_dialog.py/dialogs.py）のビルド処理にも同じ`build()`関数を
  経由するため、影響範囲としてはtab3だけでなく`core/builder.py`を利用する全画面が
  対象になる（ただし他画面は`ROW_GROUP`を使用しないため、既存動作への影響はない設計）。
  念のため、Tab1（画像追加/ジオリファレンス）・start_dialog（セッション開始ダイアログ）・
  dialogs.py（グリッド入力/新規遺構作成/点名入力ダイアログ）についても、通常操作で
  表示・動作に変化がないことを合わせて確認することを推奨する。
- カラーピッカー（`_on_color_pick`）は、選択前の現在色を`btn._color_hex`という
  QPushButtonへの動的属性経由で保持する実装にしている（既存の`_build_radio_row`の
  `row._button_group`と同じパターン）。QGISのPyQtバインディング側でこの種の動的属性
  付与が問題を起こさないかは、カラーピッカーを複数回開閉して色が正しく保持・反映
  され続けるかで確認できる。
