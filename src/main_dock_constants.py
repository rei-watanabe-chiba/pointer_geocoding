"""
/***************************************************************************
 PointerGeocoding Plugin - Main Dock UI Constants
 ***************************************************************************/

Stage B split (mechanical, logic-preserving): extracted from main_dock.py.
Contains UI string/config constant classes shared across MainDockWidget,
its tab mixins, and the standalone dialog classes in main_dock_dialogs.py.

T-0017 (アプローチA): EXCAVATION_OPTIONS/ATTRIBUTE_OPTIONS は core_logic.py の
ExcavationType/AttributeType Enum の .value から構築し、コンボボックス文字列と
Enum定義の単一情報源化を図る（一覧の中身・順序は変更前と同一）。
"""

from .core_logic import ExcavationType, AttributeType

# UI Configuration dictionary and layout ratios
class UIConfig:
    MAIN_RATIO = (3, 7)
    ROW_HEIGHT = 32
    SCALE_THRESHOLD = 500
    LABEL_SIZE_REF = 10
    SYMBOL_SIZE_REF = 4.0
    SYMBOL_SIZE_POINT = 3.0

class UILabels:
    DOCK_TITLE = "点群座標取得パネル"
    BTN_SAVE_PROJECT = "💾 プロジェクトを保存"
    TAB_1_TITLE = "画像管理"
    TAB_2_TITLE = "遺物点作成"
    TAB_3_TITLE = "設定"
    # --- T-0020: Left icon rail navigation (collapsible side panel) ---
    NAV_DRAWING = "図面"
    NAV_SETTINGS = "設定"
    # --- Settings Tab ---
    TAB3_SECTION_REF_SYMBOL   = "基準点"
    TAB3_SECTION_POINT_SYMBOL = "遺物点"
    TAB3_SECTION_LABEL_SYMBOL = "ラベル"
    TAB3_SECTION_SCALE   = "表示縮尺"

    TAB3_LBL_SYMBOL = "シンボル:"
    TAB3_LBL_COLOR  = "カラー:"

    TAB3_LBL_SIZE       = "サイズ"
    TAB3_LBL_LINEWIDTH  = "線幅"
    TAB3_LBL_LINECOLOR  = "線色"
    TAB3_BTN_COLOR      = "カラーを選択..."
    TAB3_POINT_FILL_ON  = "塗りあり"
    TAB3_POINT_FILL_OFF = "塗りなし"

    TAB3_LABEL_SIZE      = "サイズ"
    TAB3_LABEL_HALO      = "白枠"
    TAB3_LABEL_HALO_ON   = "白線あり"
    TAB3_LABEL_HALO_OFF  = "白線なし"
    TAB3_LABEL_OFFSET    = "間隔"

    TAB3_SCALE_MAJOR     = "大グリッド:"
    TAB3_SCALE_MINOR     = "小グリッド:"
    TAB3_SCALE_ALWAYS    = "常時"
    TAB3_SCALE_SPECIFY   = "指定"
    TAB3_BTN_APPLY       = "✅ 適用"
    TAB3_APPLY_SUCCESS   = "設定を適用しました。"
    TAB3_APPLY_NO_SESSION = "セッションが開始されていません。"
    TAB1_INFO_HEADER = "📌 画像管理・事前配置ワークフロー"
    TAB1_INFO_STEP1 = "手順 1: 画像ファイルを選択し、「確定」を押してください。"
    TAB1_INFO_STEP2 = "手順 2: 「基準点設定」を押してプレビュー画面から基準点を配置してください。"
    TAB1_INFO_IMAGE_REF = "画像: {name} | 基準点: {count} / 4 点"
    TAB1_INFO_TRANSFORM_DONE = "状態: 変換済 (残差を確認してください)"
    TAB1_INFO_RESIDUAL_INIT = "残差: 未実行"
    IMAGE_FILE = "画像ファイル:"
    LAYER_NAME = "レイヤ名:"
    SAVE_IMAGE_NAME = "レイヤ名:"
    BTN_BROWSE = "参照..."
    BTN_CONFIRM_IMAGE = "確定"
    BTN_SETUP_REF_POINTS = "基準点設定"
    GROUP_REF_POINTS = "基準点設定"
    PREVIEW_DIALOG_TITLE = "基準点設定プレビュー"
    PREVIEW_HINT = "💡 プレビュー画像をクリックして基準点（最大4点）を配置してください。"
    REF_TABLE_HEADERS = ["基準点名", "画像ピクセル", "実座標 X (m)", "実座標 Y (m)"]
    BTN_DELETE_REF = "選択行を削除"
    BTN_CLEAR_REFS = "全基準点をクリア"
    GROUP_TRANSFORM = "2. 座標変換・実空間配置"
    TRANSFORM_INIT_STATUS = "状態: 未実行 (最低2点以上の基準点が必要です)"
    BTN_TRANSFORM = "座標変換"
    BTN_EXPORT_LAYER = "レイヤ出力"
    GRID_DIALOG_TITLE = "基準点グリッド設定"
    GRID_X_LABEL = "大グリッドＸ"
    GRID_Y_LABEL = "大グリッドＹ"
    GRID_SUB_LABEL = "小グリッド (00-99)"
    BTN_DELETE_SELECTED_POINT = "選択点を削除"
    BTN_CONFIRM = "確定"
    BTN_CANCEL = "キャンセル"
    ERR_GRID_NOT_FOUND = "エラー: グリッド '{grid}' の座標データがCSV内に存在しません。"
    ERR_GY_NOT_FOUND = "エラー: Yグリッド '{gy}' はグリッドCSVに存在しません。"
    ERR_GRID_DUPLICATE = "エラー: 基準点 '{grid}' は既に登録されています。"
    STATUS_GRID_FOUND = "グリッド: {grid}\n実座標: X = {rx:.3f} m, Y = {ry:.3f} m"
    MSG_LAYER_CONFIRMED = "レイヤ名を「{name}」に確定しました。「基準点設定」を押して基準点を配置してください。"
    ERR_TRANSFORM_NOT_CALCULATED = "先に「座標変換」を実行して残差を確認してください。"
    MSG_TRANSFORM_SUCCESS = "座標変換パラメータを計算しました。残差を確認して「レイヤ出力」を実行してください。"
    GROUP_FOCUS = "マスター制御: フォーカスモード"
    BTN_FOCUS_OFF = "🎯 フォーカスモード (OFF)"
    BTN_FOCUS_ON = "🎯 フォーカスモード (ON)"
    OPACITY_LABEL = "対象外透明度:"
    GROUP_CATEGORY = "入力カテゴリ設定 (フォーカス判定対象)"
    DRAWING_NAME = "対象図面:"
    GROUP_INDIVIDUAL = "個別入力設定 (フォーカス判定対象外)"
    EDIT_STATUS_INIT = "状態: 新規打刻モード (メインキャンバスをクリックして打刻)"
    BTN_RESET_SELECTION = "連番再開"
    BTN_DELETE_POINT = "削除"
    EXCAVATION_TYPE = "出土形態:"
    EXCAVATION_OPTIONS = [ExcavationType.GRID.value, ExcavationType.FEATURE.value]
    FEATURE_SELECTOR = "遺構名セレクタ:"
    FEATURE_NEW_OPTION = "新規作成"
    NEW_FEATURE_NAME = "新規遺構名:"
    GROUP_POINT_NAME = "点名・枝番設定"
    POINT_NAME = "点名 (半角数字):"
    BRANCH_NO = "枝番 (任意):"
    GROUP_ATTRIBUTE = "属性設定 & 透過強調表示"
    ATTRIBUTE_CODE = "属性記号:"
    ATTRIBUTE_OPTIONS = [
        AttributeType.S.value,
        AttributeType.P.value,
        AttributeType.C.value,
        AttributeType.SP.value,
    ]
    BTN_CONFIRM_ATTRIBUTE = "属性確定 (フォーカス有効化)"
    GROUP_COLOR = "遺構カラー設定"
    BTN_COLOR_PICKER = "カラー選択"
    BTN_APPLY_COLOR = "グループ一括適用"
    GROUP_CSV = "CSV出力設定"
    ENCODING = "文字コード:"
    RADIO_UTF8 = "UTF-8 (BOM付き)"
    RADIO_SJIS = "Shift-JIS"
    CSV_DESTINATION = "出力先:"
    BTN_EXPORT_CSV = "📄 CSV出力"
    UNLOADED = "未読み込み"
    TRANSFORM_HELMERT = "2点ヘルマート変換"
    TRANSFORM_AFFINE = "{count}点アフィン変換"
    STATUS_NEED_MORE_REFS = "基準点登録数: {count} 点 (※最低2点以上の基準点が必要です)"
    STATUS_INPUT_COORDS = "基準点登録数: {count} 点 (実座標 X, Y をテーブル内に入力してください)"
    STATUS_READY_TRANSFORM = "基準点登録数: {count} 点 ({mode}の実行準備が完了しました)"
    STATUS_DIGITIZE_SUCCESS = "直前に打刻成功: ID={id} (点名={name})"
    STATUS_EXISTING_POINT = "⚠️ 既存点を選択中: ID={id} (点名={name})"

class UIPlaceholders:
    IMAGE_PATH = "画像ファイルを選択してください"
    IMAGE_NAME = "例: plan_01"
    NEW_FEATURE = "例: SK01, Pit12"
    BRANCH_NO = "例: a, 1 (未入力可)"
    CSV_PATH = "CSV出力先ファイルを指定してください"

class UIDialogTitles:
    BROWSE_IMAGE = "図面画像ファイルを選択"
    IMAGE_FILTER = "画像ファイル (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;すべてのファイル (*.*)"
    COLOR_PICKER = "遺構カラーを選択"
    BROWSE_CSV = "CSV出力先を指定"
    CSV_FILTER = "CSVファイル (*.csv)"
    INPUT_REF_TITLE = "基準点名の入力"
    INPUT_REF_PROMPT = "基準点名を入力してください (例: K-1, Ref-1):"

class UIMessages:
    ERR_TITLE_INPUT = "入力エラー"
    ERR_TITLE_FILE = "ファイルエラー"
    ERR_TITLE_LOAD = "読み込みエラー"
    ERR_TITLE_DUPLICATE = "重複エラー"
    ERR_TITLE_GENERIC = "エラー"
    MSG_TITLE_INFO = "通知"
    MSG_TITLE_LIMIT = "上限通知"
    MSG_CONFIRM_TITLE = "削除確認"
    MSG_CONFIRM_IMAGE_FIRST = "編集対象のレイヤを選択してから「基準点設置」を実行してください。"
    ERR_INVALID_IMAGE = "有効な画像ファイルを選択してください。"
    ERR_SOURCE_HAS_WORLDFILE = (
        "選択した画像には既にワールドファイルが付随しています。"
        "本プラグインは座標変換により独自のワールドファイルを生成するため、"
        "既存のワールドファイルを持つ画像は使用できません。"
    )
    ERR_REQUIRED_IMAGE_NAME = "レイヤ名を入力してください。"
    ERR_INVALID_IMAGE_NAME = "レイヤ名に使用できない文字 (\\ / : * ? \" < > |) が含まれています。"
    MSG_IMAGE_LOADED_TITLE = "画像読み込み完了"
    MSG_IMAGE_LOADED = "画像をプレビュー表示しました: {name}"
    ERR_PREVIEW_FAILED = "プレビュー画像の読み込みに失敗しました:\n{msg}"
    MSG_LIMIT_REFS = "基準点は最大4点まで登録できます。\n不要な基準点を削除してください。"
    ERR_DUPLICATE_REF = "同名の基準点 '{name}' が既に存在します。\n別の名称を入力してください。"
    ERR_DUPLICATE_LAYER_NAME = "同名のレイヤ '{name}' が既に存在します。\n別の名称を入力してください。"
    MSG_SELECT_REF_ROW = "削除する基準点を行選択してください。"
    ERR_MIN_2_REFS = "最低2点以上の基準点が必要です。"
    ERR_INPUT_REAL_COORDS = "基準点 '{name}' の実座標 (X, Y) を入力してください。"
    ERR_WORLDFILE_FAILED = "ワールドファイル生成に失敗しました:\n{msg}"
    ERR_CANVAS_PLACEMENT_FAILED = "メインキャンバスへの画像配置に失敗しました:\n{msg}"
    MSG_GEOREF_COMPLETE_TITLE = "事前ジオリファレンス完了"
    MSG_GEOREF_COMPLETE = "ワールドファイルを生成し、画像を実空間に配置しました。「遺物点作成」タブで打刻を開始できます。"
    MSG_SAVE_TITLE = "プロジェクト保存"
    MSG_SAVE_SUCCESS = "プロジェクトとGeoPackageの変更を上書き保存しました。"
    MSG_SAVE_FAILED = "プロジェクトの保存に失敗しました。"
    MSG_SELECT_FEATURE_NAME = "対象の遺構名をセレクタから選択してください。"
    MSG_COLOR_APPLIED_TITLE = "カラー適用"
    MSG_COLOR_APPLIED = "遺構 '{feature}' の全打刻点 ({count}件) にカラー {color} を適用しました。"
    MSG_ATTR_CONFIRM_TITLE = "属性確定"
    MSG_ATTR_CONFIRMED = "属性 '{attr}' を確定し、フォーカスモードを更新しました。"
    MSG_RENAME_LAYER_SUCCESS = "レイヤ名を '{old}' から '{new}' に変更しました。"
    ERR_POINT_NAME_REQUIRED = "点名（点番号）を入力してください。"
    ERR_NEW_FEATURE_REQUIRED = "新規遺構名を入力してください。"
    MSG_DELETE_CONFIRM = "選択中のポイントを削除しますか？\nこの操作は元に戻せません。"
    MSG_DELETE_SUCCESS_TITLE = "ポイント削除"
    MSG_DELETE_SUCCESS = "ポイントを削除しました。"
    MSG_EXPORT_CSV_TITLE = "CSV出力完了"


MAIN_RATIO = UIConfig.MAIN_RATIO
