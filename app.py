import streamlit as st
from PIL import Image, ImageOps
from io import BytesIO
import datetime

# --- 番組ごとの設定 ---
# (このセクションは変更ありません)
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
    },
    'SDGs': {
        'size': (1280, 720),
        'name_format': 'sdgs_{date}'
    }
}


# --- 画像処理関数 ---
# (このセクションは変更ありません)
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
    
    if uploaded_file:
        program_name = st.selectbox(
            '番組を選択してください',
            list(PROGRAM_SPECS.keys())
        )
        
        spec = PROGRAM_SPECS[program_name]
        params = {}
        
        if '{date}' in spec['name_format']:
            broadcast_date = st.date_input(
                '放送日を選択してください',
                datetime.date.today()
            )
            params['date'] = broadcast_date.strftime('%y%m%d')

        if '{last_name}' in spec['name_format']:
            last_name = st.text_input('ゲストの苗字（ローマ字）を入力してください 例: Suzuki')
            params['last_name'] = last_name

        if '{count}' in spec['name_format']:
            count = st.number_input('枚数を入力してください', min_value=1, value=1, step=1)
            params['count'] = str(count)

        st.header("2. 出力設定")
        
        position = st.selectbox(
            '画像の位置を選択してください (クロップの基準点になります)',
            ['中央', '左上', '右上', '左下', '右下']
        )

        output_format = st.radio(
            "出力形式を選択",
            ('JPG', 'PNG'),
            horizontal=True
        )

        if output_format == 'JPG':
            quality = st.slider('JPG圧縮品質', 1, 100, 85)
            st.info("品質の値を下げるとファイルサイズは小さくなりますが、画質も低下します。\n100KB前後を目安に調整してください。")
        else:
            quality = None
            st.info("PNGは画質が劣化しない形式です。一般的にファイルサイズはJPGより大きくなります。")
        
        if st.button('画像をリサイズする', type="primary"):
            if '{last_name}' in spec['name_format'] and not last_name:
                st.error('ゲストの苗字を入力してください。')
            else:
                original_image = Image.open(uploaded_file)
                
                # --- ★★★ ここからが修正箇所 ★★★ ---
                # PNGの透過情報(RGBA)をJPGに変換すると背景が黒くなる問題に対応
                if original_image.mode == 'RGBA':
                    # 白い背景の画像を作成
                    background = Image.new('RGB', original_image.size, (255, 255, 255))
                    # 元の画像を、そのアルファチャンネルをマスクとして背景に貼り付け
                    background.paste(original_image, (0, 0), original_image)
                    original_image = background # 処理対象の画像を、背景と合成したものに置き換える
                
                # 念のためRGBモードに変換（JPGで保存するため）
                original_image = original_image.convert('RGB')
                # --- ★★★ ここまでが修正箇所 ★★★ ---

                # --- メイン処理 ---
                processed_image = resize_and_crop(original_image, spec['size'], position)

                base_filename = spec['name_format'].format(**params)
                
                buffer = BytesIO()
                if output_format == 'JPG':
                    final_filename = f"{base_filename}.jpg"
                    mime_type = "image/jpeg"
                    # processed_imageはすでにRGBなのでそのまま保存
                    processed_image.save(buffer, format='JPEG', quality=quality, optimize=True)
                else:
                    final_filename = f"{base_filename}.png"
                    mime_type = "image/png"
                    processed_image.save(buffer, format='PNG', optimize=True)
                
                image_bytes = buffer.getvalue()
                
                with col2:
                    st.header("処理結果")
                    st.markdown("""
                    <style>
                        .image-container-with-border img {
                            border: 2px solid #ccc;
                            border-radius: 4px;
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
                        label="画像をダウンロード",
                        data=image_bytes,
                        file_name=final_filename,
                        mime=mime_type
                    )

# streamlit run app.py