import streamlit as st
from PIL import Image
from io import BytesIO
import datetime

# --- 番組ごとの設定 ---
# ファイル名の拡張子(.jpg)を削除し、選択された形式に応じて動的に付与するように変更
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
def resize_and_pad(image: Image.Image, target_size: tuple[int, int], position: str) -> Image.Image:
    """
    画像をアスペクト比を維持してリサイズし、指定サイズに合わせて白枠を追加（パディング）する関数
    """
    img_copy = image.copy()
    img_copy.thumbnail(target_size, Image.Resampling.LANCZOS)
    
    # PNGの透過チャンネルを考慮し、背景を白色に設定
    background = Image.new('RGB', target_size, (255, 255, 255))
    
    target_w, target_h = target_size
    img_w, img_h = img_copy.size
    
    if position == '中央':
        paste_pos = ((target_w - img_w) // 2, (target_h - img_h) // 2)
    elif position == '左上':
        paste_pos = (0, 0)
    elif position == '右上':
        paste_pos = (target_w - img_w, 0)
    elif position == '左下':
        paste_pos = (0, target_h - img_h)
    elif position == '右下':
        paste_pos = (target_w - img_w, target_h - img_h)
    else:
        paste_pos = ((target_w - img_w) // 2, (target_h - img_h) // 2)

    # 元画像が透過情報(RGBA)を持つ場合、そのまま貼り付けるとエラーになることがあるため、
    # マスクとしてアルファチャンネルを指定して貼り付け
    if img_copy.mode == 'RGBA':
        background.paste(img_copy, paste_pos, img_copy)
    else:
        background.paste(img_copy, paste_pos)
    
    return background

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
            '画像の位置を選択してください',
            ['中央', '左上', '右上', '左下', '右下']
        )

        output_format = st.radio(
            "出力形式を選択",
            ('JPG', 'PNG'),
            horizontal=True
        )

        # JPG選択時のみ品質スライダーを表示
        if output_format == 'JPG':
            quality = st.slider('JPG圧縮品質', 1, 100, 85)
            st.info("品質の値を下げるとファイルサイズは小さくなりますが、画質も低下します。\n100KB前後を目安に調整してください。")
        else:
            quality = None # PNGの場合は使用しない
            st.info("PNGは画質が劣化しない形式です。一般的にファイルサイズはJPGより大きくなります。")
        
        if st.button('画像をリサイズする', type="primary"):
            if '{last_name}' in spec['name_format'] and not last_name:
                st.error('ゲストの苗字を入力してください。')
            else:
                original_image = Image.open(uploaded_file)
                
                # --- メイン処理 ---
                processed_image = resize_and_pad(original_image, spec['size'], position)

                base_filename = spec['name_format'].format(**params)
                
                buffer = BytesIO()
                if output_format == 'JPG':
                    final_filename = f"{base_filename}.jpg"
                    mime_type = "image/jpeg"
                    processed_image.save(buffer, format='JPEG', quality=quality, optimize=True)
                else: # PNG
                    final_filename = f"{base_filename}.png"
                    mime_type = "image/png"
                    processed_image.save(buffer, format='PNG', optimize=True)
                
                image_bytes = buffer.getvalue()
                
                # --- 処理結果を右カラムに表示 ---
                with col2:
                    st.header("処理結果")
                    # カスタムCSSを適用するためのHTML要素を挿入
                    st.markdown("""
                    <style>
                        .image-container-with-border img {
                            border: 2px solid #ccc; /* 枠線の太さ、種類、色を調整 */
                            border-radius: 4px; /* 角を少し丸める（任意） */
                        }
                    </style>
                    <div class="image-container-with-border">
                    """, unsafe_allow_html=True)
                    
                    st.image(
                        processed_image, 
                        caption=f'プレビュー: {spec["size"][0]}x{spec["size"][1]}px'
                    )

                    # divタグを閉じる
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.info(f"ファイル名: **{final_filename}**")
                    st.info(f"ファイルサイズ: **{len(image_bytes) / 1024:.1f} KB**")

                    st.download_button(
                        label="画像をダウンロード",
                        data=image_bytes,
                        file_name=final_filename,
                        mime=mime_type
                    )
