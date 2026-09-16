## 人手確認チェックリスト

### 確認手順
1. QGISを起動し、「点群座標取得」(pointer_geocoding)プラグインを有効化する。プラグインパネル（ドック）がエラーダイアログなしで表示されることを確認する。
2. Tab1（画像管理・事前ジオリファレンス）を開く。「新規追加」モードで画像ファイルを「参照...」から選択し、レイヤ名を入力して「確定」ボタンを押す。プレビューダイアログが表示され、基準点設定プレビュー画面が開くことを確認する。
3. Tab1のプレビュー画面上で基準点を2点以上配置し、「座標変換」→「レイヤ出力」の順に実行する。世界ファイル書き込み・メタデータ更新・キャンバスへのレイヤ配置がエラーなく完了し、自動的にTab2へ切り替わることを確認する。
4. Tab1「編集削除」モードに切り替え、既存レイヤを選択して編集（レイヤ名変更含む）・削除の各操作がエラーなく行えることを確認する。
5. Tab2（遺物点打刻）を開き、「出土形態設定」グループ内の「出土形態」コンボボックスで「グリッド」「遺構」を切り替える。「遺構」選択時に遺構名セレクタ（新規作成含む）・新規遺構名入力欄・カラー選択欄が正しく表示/非表示切り替えされることを確認する。
6. Tab2でメインキャンバス上をクリックし、点名・枝番・属性記号を入力して打刻点を1件作成できることを確認する（出土形態=グリッド、出土形態=遺構の双方で試す）。

### 各手順で期待される挙動（設計書ベース）
- 手順1: `docs/integrated_master_design.md` 108行目「プラグイン起動時、現在開いているQGISプロジェクトに未保存の変更（Dirty状態）があれば保護ダイアログを表示。」の記述通り、起動処理自体はデッドコード削除の影響を受けないため、プラグインは通常通り起動しエラーが出ないこと。
- 手順2〜4: `docs/integrated_master_design.md` 81行目「tab1_georef_mixin.py: Tab1GeorefMixin。Tab1 (画像管理・事前ジオリファレンス) のUI構築(_create_tab1_ui)と、画像確定・基準点設定・プレビュー操作・座標変換・レイヤ出力までの一連のイベントハンドラを提供する」の記述通り、画像確定→基準点設定→座標変換→レイヤ出力の一連フローが、後方互換別名メソッド（`_on_show_preview_clicked`/`_on_execute_georef_clicked`）や`current_image_ext`属性の削除後も、実体メソッド（`_on_setup_ref_points_clicked`/`_on_export_layer_clicked`）経由で従来通り動作すること。
- 手順5〜6: `docs/integrated_master_design.md` 144行目「出土形態（遺構 / グリッド）、遺構名（新規作成対応）、属性（S/P/C/SP）、カラーを選択。」の記述通り、`group_excavation`/`group_feature`という未使用エイリアス属性の削除後も、実際にUIで使用されている`group_category`/`row_feature_selector`を通じて出土形態・遺構名の選択UIが従来通り機能すること。

### 注意喚起
- `src/tab1_georef_mixin.py`の`_browse_image_file()`と`_on_confirm_image_clicked()`から`self.current_image_ext = ext`のset処理を削除した。この属性はプラグイン内のどこからも読み取られていなかったことをgrepで確認済みだが、画像拡張子に依存する処理（世界ファイル拡張子の決定など）が本当に他の変数（`os.path.splitext`のローカル変数`ext`）だけで完結しているか、実際の画像追加操作で拡張子の異なる画像（.jpg/.png/.tif等）を試し、世界ファイルが正しい拡張子で生成されることを重点的に確認することが望ましい。
- `src/layer_manager.py`から`PluginSettings`/`RefPointMeta`/`ImageLayerMeta`/`get_local_crs`/`suppress_crs_prompt`のre-export importを削除した。`layer_manager.py`自身やmixin群はこれらを直接`layer_manager_models`からimportしているため理論上影響はないが、設定の保存・復元（`settings.json`）やCRS判定に関わる機能（Tab3の設定適用、プロジェクト保存/読込）は、プラグイン全体を一通り操作し、設定値が正しく保持・復元されることを合わせて確認するとより安全である。
- `src/main_dock_constants.py`から未使用UI定数5個を削除したが、これらは全てUI文言定数であり、削除された定数と同一の文言を持つ別の定数（例: `BTN_SETUP_REF_POINTS`/`GROUP_REF_POINTS`が`BTN_SHOW_PREVIEW`と同じ文言、`BTN_EXPORT_LAYER`が`BTN_EXECUTE_TRANSFORM`と同じ文言）が実際にUI構築で使用され続けている。UI上のボタン・グループラベルの表示文言に変化がないことを目視確認することが望ましい。
