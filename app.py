import streamlit as st
from PIL import Image, ImageOps
from io import BytesIO
import datetime
import os
import tempfile ### <<< 変更・追加点 (一時ファイル作成用)

# --- 番組ごとの設定 ---
# 各番組情報に保存先のパス 'save_path' を追加
# SDGsを削除
PROGRAM_SPECS = {
    'ドローン紀行': {
        'size': (1200, 680),
        'name_format': '{date}',
        'save_path': '/Volumes/アルバイト用/サーバー/tv/drone/backnumber/image'
    },
    'ハンザキラジオ': {
        'size': (1000, 563),
        'name_format': '{date}',
        'save_path': '/Volumes/アルバイト用/サーバー/radio/hanzaki/backnumber/image'
    },
    'もんすけ調査隊': {
        'size': (1280, 720),
        'name_format': '{date}',
        'save_path': '/Volumes/アルバイト用/サーバー/news/chousatai/image'
    },
    'bravo!ファイターズ': {
        'size': (600, 600),
        'name_format': 'guest-{last_name}',
        'save_path': '/Volumes/アルバイト用/サーバー/tv/bravo/image'
    },
    '快適ドキドキライフ': {
        'size': (1000, 560),
        'name_format': 'item{date}-{count}',
        'save_path': '/Volumes/アルバイト用/サーバー/tv/doki-life/image'
    }
}


# --- 画像処理関数 ---
def resize_and_crop(image: Image.Image, target_size: tuple[int, int], position: str) -> Image.Image:
    """
    画像をアスペクト比を維持してリサイズし、指定サイズになるようにクロップする関数。
    元画像が指定サイズより小さい場合も、拡大して余白なしでフィットさせます。
    """
    position_map = {
        '中央': (0.5, 0.5),
        '左上': (0.0, 0.0),
        '右上': (1.0, 0.0),
        '左下': (0.0, 1.0),
        '右下': (1.0, 1.0),
    }
    centering = position_map.get(position, (0.5, 0.5))
    
    processed_image = ImageOps.fit(image, target_size, Image.Resampling.LANCZOS, centering=centering)
    
    return processed_image

# --- メインの画像処理ロジックを関数化 --- ### <<< 変更・追加点
def process_image(uploaded_file, program_name, params, position, output_format, quality):
    if uploaded_file is None:
        return None, None, None, None

    spec = PROGRAM_SPECS[program_name]
    original_image = Image.open(uploaded_file)
    
    # PNGの透過情報(RGBA)をJPGに変換すると背景が黒くなる問題に対応
    if original_image.mode == 'RGBA':
        background = Image.new('RGB', original_image.size, (255, 255, 255))
        background.paste(original_image, (0, 0), original_image)
        original_image = background
    
    # RGBモードに変換（JPGで保存するため）
    original_image = original_image.convert('RGB')

    # --- メイン処理 ---
    processed_image = resize_and_crop(original_image, spec['size'], position)

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
    
    return processed_image, final_filename, mime_type, image_bytes, spec['save_path']

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
    
    # keyを追加して、選択が変更されたときにStreamlitが再実行されるようにする
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
        # 日付が不要な番組の場合、デフォルト値を設定（エラー回避のため）
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
        '画像の位置を選択してください (クロップの基準点になります)',
        ['中央', '左上', '右上', '左下', '右下'],
        key='position_select'
    )

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

    # --- 保存場所の選択 --- ### <<< 変更・追加点
    st.header("3. ファイル保存オプション")
    save_location = st.radio(
        "画像をどこに保存しますか？",
        ('ダウンロード', '指定フォルダ'),
        horizontal=True,
        key='save_location_radio'
    )

    # 必須入力チェック（last_nameがある場合）
    is_last_name_required = '{last_name}' in spec['name_format']
    last_name_is_empty = is_last_name_required and (not params.get('last_name'))
    
    if is_last_name_required and last_name_is_empty:
        st.error('ゲストの苗字を入力してください。')

    # --- 自動更新プレビュー部分 --- ### <<< 変更・追加点
    # 何らかの入力があり、かつ必須入力が満たされている場合にのみプレビューを生成
    if uploaded_file and not last_name_is_empty:
        processed_image, final_filename, mime_type, image_bytes, server_save_path = \
            process_image(uploaded_file, program_name, params, position, output_format, quality)
        
        if processed_image: # 画像処理が成功した場合のみ表示
            with col2:
                st.header("プレビューと処理結果")
                st.markdown("""
                <style>
                    .image-container-with-border img {
                        border: 2px solid #ccc;
                        border-radius: 4px;
                        max-width: 100%; /* 画面サイズに合わせて調整 */
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

                # ダウンロードボタン (常に表示し、ユーザーが手動でダウンロードできるようにする)
                st.download_button(
                    label="ブラウザでダウンロード",
                    data=image_bytes,
                    file_name=final_filename,
                    mime=mime_type,
                    key='download_button_browser'
                )
                
                # 指定フォルダへの保存ボタン（プレビューが生成されていて、かつ必須入力が満たされている場合のみ表示）
                if save_location == '指定フォルダ' and st.button('指定フォルダに保存', type="primary", key='save_to_folder_button'):
                    # 1. 保存先のディレクトリパスを取得
                    
                    # 2. ディレクトリが存在しない場合は作成
                    os.makedirs(server_save_path, exist_ok=True)
                    
                    # 3. 保存するファイルのフルパスを作成
                    file_path = os.path.join(server_save_path, final_filename)
                    
                    # 4. 画像をファイルとして保存
                    try:
                        with open(file_path, "wb") as f:
                            f.write(image_bytes)
                        st.success(f"サーバーの **{file_path}** に画像を保存しました。")
                    except Exception as e:
                        st.error(f"ファイル保存中にエラーが発生しました: {e}")
                        st.warning("指定フォルダへの書き込み権限があるか確認してください。")

    elif not uploaded_file:
        with col2:
            st.info("画像をアップロードしてください。")
    elif last_name_is_empty:
        with col2:
            st.warning("必要な情報が入力されていません。")
# streamlit run app.py