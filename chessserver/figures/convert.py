import os
from PIL import Image

folder = "./"  # Папка с изображениями
target_color = (96, 17, 16)  # Цвет #601110 в RGB

for filename in os.listdir(folder):
    if filename.endswith(".png"):
        img_path = os.path.join(folder, filename)
        img = Image.open(img_path).convert("RGBA")
        pixels = img.load()

        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]

                if (r, g, b) != (0, 0, 0):  # Все НЕ чёрные пиксели
                    pixels[x, y] = (
                        *target_color,
                        a,
                    )  # Красим в #601110 с сохранением альфа

        # Меняем первую букву имени файла с 'w' на 'b'
        new_filename = "b" + filename[1:] if filename[0] == "w" else filename

        output_path = os.path.join(folder, new_filename)
        img.save(output_path)
        print(f"✅ {filename} → {new_filename}")
