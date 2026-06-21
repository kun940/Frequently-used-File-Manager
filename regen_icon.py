from PIL import Image, ImageDraw, ImageFont
import os, struct, io
import numpy as np


def render_icon_1024() -> Image.Image:
    """在 1024x1024 下绘制高清图标。"""
    size = 1024
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))

    margin = int(size * 0.06)
    radius = int(size * 0.18)
    bg_rect = [margin, margin, size - margin, size - margin]

    grad = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    for y in range(size):
        t = y / size
        r = int(26 + (15 - 26) * t)
        g = int(26 + (52 - 26) * t)
        b = int(46 + (96 - 46) * t)
        for x in range(size):
            if margin <= x < size - margin and margin <= y < size - margin:
                grad.putpixel((x, y), (r, g, b, 255))

    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(bg_rect, radius=radius, fill=255)

    bg_layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    bg_layer.paste(grad, (0, 0), mask)
    img.paste(bg_layer, (0, 0), mask)

    draw = ImageDraw.Draw(img)
    border_w = max(int(size * 0.025), 2)
    draw.rounded_rectangle(bg_rect, radius=radius, outline=(233, 69, 96, 200), width=border_w)

    folder_w = int(size * 0.52)
    folder_h = int(size * 0.40)
    folder_x = (size - folder_w) // 2
    folder_y = int(size * 0.30)
    tab_w = int(folder_w * 0.40)
    tab_h = int(folder_h * 0.22)
    draw.rounded_rectangle([folder_x, folder_y - tab_h, folder_x + tab_w, folder_y],
                            radius=max(int(size * 0.015), 2), fill=(233, 69, 96, 255))
    draw.rounded_rectangle([folder_x, folder_y, folder_x + folder_w, folder_y + folder_h],
                            radius=max(int(size * 0.025), 3), fill=(233, 69, 96, 255))

    bar_y1 = folder_y + int(folder_h * 0.35)
    bar_w1 = int(folder_w * 0.65)
    bar_h1 = max(int(size * 0.025), 2)
    bar_x1 = folder_x + (folder_w - bar_w1) // 2
    draw.rounded_rectangle([bar_x1, bar_y1, bar_x1 + bar_w1, bar_y1 + bar_h1],
                            radius=bar_h1 // 2, fill=(255, 255, 255, 150))
    bar_y2 = bar_y1 + bar_h1 * 3
    bar_w2 = int(folder_w * 0.45)
    bar_x2 = folder_x + (folder_w - bar_w2) // 2
    draw.rounded_rectangle([bar_x2, bar_y2, bar_x2 + bar_w2, bar_y2 + bar_h1],
                            radius=bar_h1 // 2, fill=(255, 255, 255, 100))

    badge_size = int(size * 0.30)
    badge_x = folder_x + folder_w - int(badge_size * 0.35)
    badge_y = folder_y + folder_h - int(badge_size * 0.35)
    draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                 fill=(78, 204, 163, 255), outline=(26, 26, 46, 255), width=max(int(size * 0.02), 1))

    try:
        font = ImageFont.truetype('arialbd.ttf', int(badge_size * 0.55))
    except Exception:
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', int(badge_size * 0.55))
        except Exception:
            font = ImageFont.load_default()
    text = 'F'
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = badge_x + (badge_size - tw) // 2
    ty = badge_y + (badge_size - th) // 2 - int(size * 0.01)
    draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

    return img


def img_to_icon_dib(img: Image.Image) -> bytes:
    """将 RGBA 图像转换为 Windows ICO 规范的 BMP DIB。
    关键：ICO 中的 biHeight 必须是实际高度的 2 倍（XOR mask + AND mask）。
    对于 32bpp（含 alpha 通道），AND mask 可以省略或全 0，由 alpha 通道承担透明信息。"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    w, h = img.size
    arr = np.array(img)

    # BMP 像素格式：BGRA，bottom-up
    arr = arr[::-1, :, [2, 1, 0, 3]].copy()

    # 每行对齐到 4 字节边界（32bpp 下 w*4 天然 4 字节对齐）
    row_size = (w * 4 + 3) // 4 * 4

    # XOR mask（h 行）
    xor_data = bytearray()
    for y in range(h):
        xor_data.extend(arr[y].tobytes())
        # 32bpp 下 row_size == w*4，不需要 padding

    # AND mask（h 行，1bpp，每行对齐到 4 字节）
    # 使用 alpha 通道生成 AND mask：alpha > 128 为不透明(0)，否则透明(1)
    and_row_bytes = (w + 31) // 32 * 4  # 每行字节数
    and_data = bytearray()
    for y in range(h):
        row_out = bytearray(and_row_bytes)
        for x in range(w):
            alpha = arr[y, x, 3]  # BGRA 的 A
            if alpha >= 128:
                bit_index = x
                byte_idx = bit_index // 8
                bit_pos = 7 - (bit_index % 8)  # MSB first
                row_out[byte_idx] |= (1 << bit_pos)
        and_data.extend(row_out)

    pixel_data = bytes(xor_data) + bytes(and_data)

    # BITMAPINFOHEADER (40 bytes)
    # biHeight = 2 * h （ICO 规范要求）
    bih = struct.pack('<IiiHHIIiiII',
        40,                 # biSize
        w,                  # biWidth
        2 * h,              # biHeight (ICO 规范：XOR + AND = 2 倍)
        1,                  # biPlanes
        32,                 # biBitCount
        0,                  # biCompression (BI_RGB)
        len(pixel_data),    # biSizeImage
        0,                  # biXPelsPerMeter
        0,                  # biYPelsPerMeter
        0,                  # biClrUsed
        0)                  # biClrImportant
    return bih + pixel_data


def build_ico_bmp(src_img: Image.Image, out_ico: str, sizes=(16, 24, 32, 48, 64, 128, 256)):
    """从大图像生成多尺寸 BMP 格式 ICO 文件（符合 ICO 规范）。"""
    dibs = []
    for s in sizes:
        small = src_img.resize((s, s), Image.LANCZOS)
        dibs.append(img_to_icon_dib(small))

    n = len(dibs)
    header = struct.pack('<HHH', 0, 1, n)
    first_offset = len(header) + 16 * n
    current_offset = first_offset

    entries = bytearray()
    body = bytearray()
    for i, dib in enumerate(dibs):
        s = sizes[i]
        w = s if s < 256 else 0
        h = s if s < 256 else 0
        entries.extend(struct.pack('<BBBBHHII',
            w, h, 0, 0, 1, 32, len(dib), current_offset))
        current_offset += len(dib)
        body.extend(dib)

    with open(out_ico, 'wb') as f:
        f.write(header)
        f.write(entries)
        f.write(body)

    total = len(header) + len(entries) + len(body)
    print(f'ICO: {out_ico}, {total} bytes, {n} sizes: {list(sizes)}')

    with open(out_ico, 'rb') as f:
        data = f.read()
    idReserved, idType, idCount = struct.unpack_from('<HHH', data, 0)
    print(f'  idReserved={idReserved}, idType={idType}, idCount={idCount}')
    off = 6
    for i in range(idCount):
        bWidth, bHeight, bColorCount, bReserved, wPlanes, wBitCount, dwBytesInRes, dwImageOffset = struct.unpack_from('<BBBBHHII', data, off)
        w = bWidth if bWidth else 256
        h = bHeight if bHeight else 256
        biSize = struct.unpack_from('<I', data, dwImageOffset)[0]
        biWidth, biHeight_raw = struct.unpack_from('<ii', data, dwImageOffset + 4)
        is_png = data[dwImageOffset:dwImageOffset + 8] == b'\x89PNG\r\n\x1a\n'
        print(f'  [{i}] {w}x{h}x{wBitCount}, data_size={dwBytesInRes}, DIB: biSize={biSize}, biWidth={biWidth}, biHeight={biHeight_raw} (actual={h}x2), PNG={is_png}')
        off += 16


if __name__ == '__main__':
    project_dir = r'd:\MyProjectCode\Vibe Coding Program\高频文件夹管理器'
    png_path = os.path.join(project_dir, 'app_icon.png')
    ico_path = os.path.join(project_dir, 'app_icon.ico')

    img = render_icon_1024()
    img.save(png_path, 'PNG')
    print(f'PNG saved: {png_path}, size={os.path.getsize(png_path)} bytes')

    build_ico_bmp(img, ico_path)
