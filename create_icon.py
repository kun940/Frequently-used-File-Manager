from PIL import Image, ImageDraw, ImageFont


def create_icon(output_path: str, size: int = 256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(size * 0.06)
    radius = int(size * 0.18)
    bg_rect = [margin, margin, size - margin, size - margin]

    for y in range(margin, size - margin):
        t = (y - margin) / (size - 2 * margin)
        r = int(26 + (15 - 26) * t)
        g = int(26 + (52 - 26) * t)
        b = int(46 + (96 - 46) * t)
        x_start = margin
        x_end = size - margin
        draw.line([(x_start, y), (x_end, y)], fill=(r, g, b, 255))

    corner_mask = Image.new("L", (size, size), 0)
    cm_draw = ImageDraw.Draw(corner_mask)
    cm_draw.rounded_rectangle(bg_rect, radius=radius, fill=255)

    bg_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(margin, size - margin):
        t = (y - margin) / (size - 2 * margin)
        r = int(26 + (15 - 26) * t)
        g = int(26 + (52 - 26) * t)
        b = int(46 + (96 - 46) * t)
        x_start = margin
        x_end = size - margin
        for x in range(x_start, x_end):
            if corner_mask.getpixel((x, y)) > 0:
                bg_layer.putpixel((x, y), (r, g, b, 255))

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(bg_layer, (0, 0), corner_mask)

    draw = ImageDraw.Draw(img)

    border_w = max(int(size * 0.025), 2)
    draw.rounded_rectangle(
        bg_rect, radius=radius, outline=(233, 69, 96, 200), width=border_w
    )

    folder_w = int(size * 0.52)
    folder_h = int(size * 0.40)
    folder_x = (size - folder_w) // 2
    folder_y = int(size * 0.30)

    tab_w = int(folder_w * 0.40)
    tab_h = int(folder_h * 0.22)
    tab_rect = [folder_x, folder_y - tab_h, folder_x + tab_w, folder_y]

    draw.rounded_rectangle(
        tab_rect, radius=max(int(size * 0.015), 2), fill=(233, 69, 96, 255)
    )

    folder_rect = [folder_x, folder_y, folder_x + folder_w, folder_y + folder_h]
    draw.rounded_rectangle(
        folder_rect, radius=max(int(size * 0.025), 3), fill=(233, 69, 96, 255)
    )

    bar_y1 = folder_y + int(folder_h * 0.35)
    bar_w1 = int(folder_w * 0.65)
    bar_h1 = max(int(size * 0.025), 2)
    bar_x1 = folder_x + (folder_w - bar_w1) // 2
    draw.rounded_rectangle(
        [bar_x1, bar_y1, bar_x1 + bar_w1, bar_y1 + bar_h1],
        radius=bar_h1 // 2,
        fill=(255, 255, 255, 150),
    )

    bar_y2 = bar_y1 + bar_h1 * 3
    bar_w2 = int(folder_w * 0.45)
    bar_x2 = folder_x + (folder_w - bar_w2) // 2
    draw.rounded_rectangle(
        [bar_x2, bar_y2, bar_x2 + bar_w2, bar_y2 + bar_h1],
        radius=bar_h1 // 2,
        fill=(255, 255, 255, 100),
    )

    badge_size = int(size * 0.30)
    badge_x = folder_x + folder_w - int(badge_size * 0.35)
    badge_y = folder_y + folder_h - int(badge_size * 0.35)

    draw.ellipse(
        [badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
        fill=(78, 204, 163, 255),
        outline=(26, 26, 46, 255),
        width=max(int(size * 0.02), 1),
    )

    try:
        font = ImageFont.truetype("arialbd.ttf", int(badge_size * 0.55))
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", int(badge_size * 0.55))
        except OSError:
            font = ImageFont.load_default()

    text = "F"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = badge_x + (badge_size - tw) // 2
    ty = badge_y + (badge_size - th) // 2 - int(size * 0.01)
    draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

    img.save(output_path, "PNG")
    print(f"PNG saved: {output_path}")

    ico_path = output_path.replace(".png", ".ico")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [img.resize(s, Image.LANCZOS) for s in sizes]
    ico_images[0].save(ico_path, format="ICO", sizes=sizes, append_images=ico_images[1:])
    print(f"ICO saved: {ico_path}")


if __name__ == "__main__":
    import os

    icon_dir = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "FreqFolderManager",
    )
    os.makedirs(icon_dir, exist_ok=True)
    icon_path = os.path.join(icon_dir, "app_icon.png")
    create_icon(icon_path)
