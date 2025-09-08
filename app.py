import streamlit as st
from PIL import Image, ImageOps
from io import BytesIO
import datetime

# --- 番組ごとの設定 ---
PROGRAM_SPECS = {
    'ドローン紀行': {
        'size': (1200, 680),
        'name_format': '{date}'
    },
    'ハンザキラジオ': {
        'size': (1000, 563),
        'name_format': '{date}'
    },
    'もんすけ調査隊': {
        'size': (1280, 720),
        'name_format': '{date}'
    },
    'bravo!ファイターズ': {
        'size': (600, 600),
        'name_format': 'guest-{last_name}'
    },
    '快適ドキドキライフ': {
        'size': (1000, 560),
        'name_format': 'item{date}-{count}'
    }
}


# --- 画像処理関数 ---
# オフセット引数を追加
def resize_and_crop(image: Image.Image, target_size: tuple[int, int], position: str, offset_x: int = 0, offset_y: int = 0) -> Image.Image:
    """
    画像をアスペクト比を維持してリサイズし、指定サイズになるようにクロップする関数。
    元画像が指定サイズより小さい場合も、拡大して余白なしでフィットさせます。
    オフセット値を使って、クロップ位置をピクセル単位で微調整できます。
    """
    # まずは元のアスペクト比を保ちつつ、ターゲットサイズを埋めるようにリサイズ
    # ImageOps.contain と似ているが、ImageOps.fit は余白を埋めるように拡大/縮小し、
    # その後ターゲットサイズになるようにクロップする。
    # ここでは、ImageOps.fitが内部で実行するリサイズ・クロップ処理を模倣して、
    # オフセットを適用できるようにする。

    img_width, img_height = image.size
    target_width, target_height = target_size

    # ターゲットアスペクト比と画像のアスペクト比を比較
    target_aspect = target_width / target_height
    image_aspect = img_width / img_height

    if image_aspect > target_aspect:
        # 画像がターゲットよりも横長の場合、高さを基準にリサイズ
        scale = target_height / img_height
        resize_width = int(img_width * scale)
        resize_height = target_height
    else:
        # 画像がターゲットよりも縦長または同じアスペクト比の場合、幅を基準にリサイズ
        scale = target_width / img_width
        resize_width = target_width
        resize_height = int(img_height * scale)
    
    # LANCZOSフィルタでリサイズ
    resized_image = image.resize((resize_width, resize_height), Image.Resampling.LANCZOS)

    # クロップ範囲の計算
    left, top, right, bottom = 0, 0, target_width, target_height

    # 基準位置の計算 (0.0～1.0の正規化座標)
    position_map = {
        '中央': (0.5, 0.5),
        '左上': (0.0, 0.0),
        '右上': (1.0, 0.0),
        '左下': (0.0, 1.0),
        '右下': (1.0, 1.0),
    }
    base_centering_x, base_centering_y = position_map.get(position, (0.5, 0.5))

    # クロップ領域の左上座標を計算
    # リサイズ後の画像からのクロップ開始点
    crop_x_start = int((resize_width - target_width) * base_centering_x)
    crop_y_start = int((resize_height - target_height) * base_centering_y)

    # オフセットを適用
    crop_x_start -= offset_x # 正のXオフセットは画像を左に動かす (=クロップ領域を右に動かす)
    crop_y_start -= offset_y # 正のYオフセットは画像を上に動かす (=クロップ領域を下に動かす)

    # クロップ領域が画像からはみ出さないように調整
    crop_x_start = max(0, min(crop_x_start, resize_width - target_width))
    crop_y_start = max(0, min(crop_y_start, resize_height - target_height))

    crop_box = (crop_x_start, crop_y_start, crop_x_start + target_width, crop_y_start + target_height)

    # 実際にクロップ
    processed_image = resized_image.crop(crop_box)
    
    return processed_image


# --- メインの画像処理ロジックを関数化 ---
# オフセット引数を追加
def process_image(uploaded_file, program_name, params, position, offset_x, offset_y, output_format, quality):
    if uploaded_file is None:
        return None, None, None, None

    spec = PROGRAM_SPECS[program_name]
    original_image = Image.open(uploaded_file)
    
    if original_image.mode == 'RGBA':
        background = Image.new('RGB', original_image.size, (255, 255, 255))
        background.paste(original_image, (0, 0), original_image)
        original_image = background
    
    original_image = original_image.convert('RGB')

    # オフセット引数を渡す
    processed_image = resize_and_crop(original_image, spec['size'], position, offset_x, offset_y)
    
    base_filename = spec['name_format'].format(**params)
    
    buffer = BytesIO()
    if output_format == 'JPG':
        final_filename = f"{base_filename}.jpg"
        mime_type = "image/jpeg"
        processed_image.save(buffer, format='JPEG', quality=quality, optimize=True)
    else:
        final_filename = f"{base_filename}.png"
        mime_type = "image/png"
        processed_image.save(buffer, format='PNG', optimize=True)
    
    image_bytes = buffer.getvalue()
    
    return processed_image, final_filename, mime_type, image_bytes

# --- Streamlit UI部分 ---
st.set_page_config(page_title="番組用画像リサイズ", layout="wide")
st.title('番組用画像リサイズ')
st.write("画像をアップロードし、番組名を選択するだけで、規定のサイズとファイル名に自動で変換します。")

col1, col2 = st.columns(2)

with col1:
    st.header("1. 画像と情報を入力")
    
    uploaded_file = st.file_uploader(
        "画像ファイルを選択してください",
        type=['jpg', 'jpeg', 'png']
    )
    
    program_name = st.selectbox(
        '番組を選択してください',
        list(PROGRAM_SPECS.keys()),
        key='program_select'
    )
    
    spec = PROGRAM_SPECS[program_name]
    params = {}
    
    if '{date}' in spec['name_format']:
        broadcast_date = st.date_input(
            '放送日を選択してください',
            datetime.date.today(),
            key='broadcast_date'
        )
        params['date'] = broadcast_date.strftime('%y%m%d')
    else:
        params['date'] = '' 

    if '{last_name}' in spec['name_format']:
        last_name = st.text_input('ゲストの苗字（ローマ字）を入力してください 例: Suzuki', key='last_name_input')
        params['last_name'] = last_name
    else:
        params['last_name'] = ''

    if '{count}' in spec['name_format']:
        count = st.number_input('枚数を入力してください', min_value=1, value=1, step=1, key='count_input')
        params['count'] = str(count)
    else:
        params['count'] = ''

    st.header("2. 出力設定")
    
    position = st.selectbox(
        'クロップの基準位置',
        ['中央', '左上', '右上', '左下', '右下'],
        key='position_select'
    )

    # オフセット（微調整）入力部分を追加
    st.subheader('位置の微調整（ピクセル単位）')
    col_offset1, col_offset2 = st.columns(2)
    with col_offset1:
        offset_x = st.number_input(
            '左右オフセット (X軸)',
            min_value=-500, # 必要に応じて範囲調整
            max_value=500,  # 必要に応じて範囲調整
            value=0,
            step=1,
            help='正の値で画像を左へ、負の値で画像を右へ動かします。',
            key='offset_x_input'
        )
    with col_offset2:
        offset_y = st.number_input(
            '上下オフセット (Y軸)',
            min_value=-500, # 必要に応じて範囲調整
            max_value=500,  # 必要に応じて範囲調整
            value=0,
            step=1,
            help='正の値で画像を上へ、負の値で画像を下へ動かします。',
            key='offset_y_input'
        )
    st.markdown("""<small><b>ヒント:</b> オフセットは、クロップの基準位置からの追加の移動量です。</small>""", unsafe_allow_html=True)


    output_format = st.radio(
        "出力形式を選択",
        ('JPG', 'PNG'),
        horizontal=True,
        key='output_format_radio'
    )

    quality = None
    if output_format == 'JPG':
        quality = st.slider('JPG圧縮品質', 1, 100, 85, key='quality_slider')
        st.info("品質の値を下げるとファイルサイズは小さくなりますが、画質も低下します。\n100KB前後を目安に調整してください。")
    else:
        st.info("PNGは画質が劣化しない形式です。一般的にファイルサイズはJPGより大きくなります。")
    
    is_last_name_required = '{last_name}' in spec['name_format']
    last_name_is_empty = is_last_name_required and (not params.get('last_name'))
    
    if is_last_name_required and last_name_is_empty:
        st.error('ゲストの苗字を入力してください。')

    if uploaded_file and not last_name_is_empty:
        # オフセット引数を渡す
        processed_image, final_filename, mime_type, image_bytes = \
            process_image(uploaded_file, program_name, params, position, offset_x, offset_y, output_format, quality)
        
        if processed_image:
            with col2:
                st.header("プレビューと処理結果")
                st.markdown("""
                <style>
                    .image-container-with-border img {
                        border: 2px solid #ccc;
                        border-radius: 4px;
                        max-width: 100%;
                        height: auto;
                    }
                </style>
                <div class="image-container-with-border">
                """, unsafe_allow_html=True)
                
                st.image(
                    processed_image, 
                    caption=f'プレビュー: {spec["size"][0]}x{spec["size"][1]}px'
                )

                st.markdown("</div>", unsafe_allow_html=True)
                st.info(f"ファイル名: **{final_filename}**")
                st.info(f"ファイルサイズ: **{len(image_bytes) / 1024:.1f} KB**")

                st.download_button(
                    label="ブラウザでダウンロード",
                    data=image_bytes,
                    file_name=final_filename,
                    mime=mime_type,
                    key='download_button_browser'
                )
                
    elif not uploaded_file:
        with col2:
            st.info("画像をアップロードしてください。")
    elif last_name_is_empty:
        with col2:
            st.warning("必要な情報が入力されていません。")
# streamlit run app.py