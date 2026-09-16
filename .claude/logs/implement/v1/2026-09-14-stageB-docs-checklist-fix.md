## タスクID
Stage B差し戻し: 設計書・チェックリストの記述不整合修正

## 変更ファイル一覧
- `docs/integrated_master_design.md`
- `.claude/logs/implement/2026-09-14-stageB-main-dock-mixin-split-checklist.md`

## 変更概要
verifierの静的検証指摘（Stage B: main_dock.pyのMixin分割後もドキュメント側に分割前の記述が残存）を受け、以下の記述を実装済みの所属先に合わせて修正した。コード（`src/`配下の`.py`ファイル）は一切変更していない。

### `docs/integrated_master_design.md`
- §2.3（144行目付近）: 「GeoPackageへの書き込みは、すべて`main_dock.py`の`_on_canvas_clicked()`が行う」という記述を、「GeoPackageへの書き込みは、すべて`tab2_digitizing_mixin.py`の`Tab2DigitizingMixin._on_canvas_clicked()`が行う」に修正。
- §2.4（163行目付近）: 「`main_dock.py`側の`_on_layer_manager_settings_changed()`がこれを購読して」という記述を、「`tab3_settings_mixin.py`の`Tab3SettingsMixin._on_layer_manager_settings_changed()`がこれを購読して」に修正。
- 修正後、ドキュメント内で`_on_canvas_clicked`/`_on_layer_manager_settings_changed`に言及している全箇所（72, 76, 144, 163行目）を再度grepし、既にStage Bで更新済みだった§1.4（72行目・77行目付近）の記述（`tab2_digitizing_mixin.py`側の`_on_canvas_clicked()`、`tab3_settings_mixin.py`の記述）と、今回修正した§2.3・§2.4の記述との間に矛盾がないことを確認した。それ以外の箇所（見出し行の「起点: main_dock.py (Tab 2)」等）は元々`_on_canvas_clicked`/`_on_layer_manager_settings_changed`という関数名に直接言及していないため、指示範囲外として変更していない。
- 上記2箇所以外の文言・情報粒度は変更していない（冒頭の編集規約「情報粒度を削減・削除しない、矛盾箇所のみ改訂」を遵守）。

### `.claude/logs/implement/2026-09-14-stageB-main-dock-mixin-split-checklist.md`
- 30行目付近「`_on_layer_manager_settings_changed()`（今回の分割後は`main_dock.py`本体に残置）」という誤った記述を、「`_on_layer_manager_settings_changed()`（今回の分割後は`tab3_settings_mixin.py`の`Tab3SettingsMixin`に配置）」に修正。
- なお29行目の`_on_canvas_clicked()`に関する記述は、既に「今回の分割後は`tab2_digitizing_mixin.py`の`Tab2DigitizingMixin._on_canvas_clicked()`」と正しく記載されていたため変更していない。
- 確認手順（1〜7）自体は変更していない。

## 自動テスト実行結果（なければ「自動テストなし」）
自動テストなし（プロジェクトにpytest等のテスト設定ファイルは存在せず、従来通りテストコマンドは未設定）。

## スコープ外変更の有無
なし。`src/`配下の`.py`ファイルは一切編集していない。上記2ファイル（設計書・チェックリスト）のみを修正した。
