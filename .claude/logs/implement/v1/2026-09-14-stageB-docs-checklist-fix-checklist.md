## 人手確認チェックリスト

対象タスク: Stage B差し戻し「設計書・チェックリストの記述不整合修正」（`.claude/logs/implement/2026-09-14-stageB-docs-checklist-fix.md` 参照）

### 確認手順
1. `docs/integrated_master_design.md` を開き、§2.3（144行目付近）の記述が「GeoPackageへの書き込みは、すべて`tab2_digitizing_mixin.py`の`Tab2DigitizingMixin._on_canvas_clicked()`が行う」となっていることを目視確認する。
2. 同ファイル §2.4（163行目付近）の記述が「`tab3_settings_mixin.py`の`Tab3SettingsMixin._on_layer_manager_settings_changed()`がこれを購読して」となっていることを目視確認する。
3. 同ファイル §1.4（72行目・77行目付近）の既存記述（`tab2_digitizing_mixin.py`側の`_on_canvas_clicked()`、`tab3_settings_mixin.py`の`Tab3SettingsMixin`に関する記述）と、手順1・2で確認した§2.3・§2.4の記述との間に矛盾がないことを確認する。
4. `.claude/logs/implement/2026-09-14-stageB-main-dock-mixin-split-checklist.md` の30行目付近が「`_on_layer_manager_settings_changed()`（今回の分割後は`tab3_settings_mixin.py`の`Tab3SettingsMixin`に配置）」に修正されていることを確認する。
5. `src/` 配下の `.py` ファイルに差分が一切ないこと（本タスクはドキュメント2件のみの修正であること）を確認する。

### 各手順で期待される挙動（設計書ベース）
- 手順1・2: 本タスクは `docs/integrated_master_design.md` 冒頭の編集規約（情報粒度を削減・削除しない、矛盾箇所のみ改訂）に基づき、Stage Bで実装済みの実際のクラス配置（`tab2_digitizing_mixin.py`の`Tab2DigitizingMixin`、`tab3_settings_mixin.py`の`Tab3SettingsMixin`）に記述を合わせる修正であるため、該当箇所がこの配置に一致している必要がある。
- 手順3: §1.4（72行目・77行目付近）は既にStage Bの実装時点で `tab2_digitizing_mixin.py`/`tab3_settings_mixin.py` への言及に更新済みであり、今回修正した§2.3・§2.4もこれと同じクラス・モジュールを指す必要がある（ドキュメント内での論理的整合性）。
- 手順4: 同チェックリストの29行目（`_on_canvas_clicked()`に関する記述）は元々正しく`tab2_digitizing_mixin.py`の`Tab2DigitizingMixin`を指しており、今回誤りが指摘された30行目のみが`main_dock.py`本体残置という誤記だったため、そこが`tab3_settings_mixin.py`への配置に修正されている必要がある。
- 手順5: 本タスクの依頼範囲は「設計書・チェックリストの記述不整合修正（コードは一切変更しない）」であるため、`src/`配下に差分があってはならない。

### 注意喚起
- 本タスクはドキュメントの文言修正のみであり、`src/`配下のコード・実行時の振る舞いには一切変更を加えていない。そのため、QGIS上でのプラグイン動作自体を再確認する必要はない（Stage B本体の人手確認は既存の `2026-09-14-stageB-main-dock-mixin-split-checklist.md` の確認手順で別途実施されるべきものであり、本チェックリストはその対象外）。
- 今回の修正はドキュメントの「実装済みコードとの整合性」を正すものであり、記載内容が実際の `src/tab2_digitizing_mixin.py` の `Tab2DigitizingMixin._on_canvas_clicked()` および `src/tab3_settings_mixin.py` の `Tab3SettingsMixin._on_layer_manager_settings_changed()` の実装と一致しているかは、静的検証（verifier）で別途確認されるべき事項である。
