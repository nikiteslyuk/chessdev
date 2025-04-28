import tkinter as tk
import math


class DraggableCircle:
    def __init__(self, canvas, x, y, r):
        self.canvas = canvas
        self.center_x = x
        self.center_y = y
        self.r = r
        self.circle = canvas.create_oval(
            x - r, y - r, x + r, y + r, fill="skyblue", outline="black"
        )
        self.drag_data = {"x": 0, "y": 0, "dragging": False}

        canvas.tag_bind(self.circle, "<ButtonPress-1>", self.on_start)
        canvas.tag_bind(self.circle, "<B1-Motion>", self.on_drag)
        canvas.tag_bind(self.circle, "<ButtonRelease-1>", self.on_release)

    def on_start(self, event):
        self.drag_data["dragging"] = True
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag(self, event):
        if self.drag_data["dragging"]:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.canvas.move(self.circle, dx, dy)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def on_release(self, event):
        self.drag_data["dragging"] = False
        self.animate_back_to_center()

    def animate_back_to_center(self):
        # Получаем текущие координаты круга
        x1, y1, x2, y2 = self.canvas.coords(self.circle)
        current_x = (x1 + x2) / 2
        current_y = (y1 + y2) / 2

        # Вычисляем вектор движения к центру
        dx = self.center_x - current_x
        dy = self.center_y - current_y
        distance = math.hypot(dx, dy)

        # Если далеко от центра, продолжаем анимацию
        if distance > 1:
            step_x = dx * 0.2
            step_y = dy * 0.2
            self.canvas.move(self.circle, step_x, step_y)
            self.canvas.after(16, self.animate_back_to_center)
        else:
            # Ставим ровно в центр
            self.canvas.coords(
                self.circle,
                self.center_x - self.r,
                self.center_y - self.r,
                self.center_x + self.r,
                self.center_y + self.r,
            )


def main():
    root = tk.Tk()
    root.title("Магнитящийся круг")

    width, height = 600, 400
    canvas = tk.Canvas(root, width=width, height=height, bg="white")
    canvas.pack()

    circle = DraggableCircle(canvas, width // 2, height // 2, 50)

    root.mainloop()


if __name__ == "__main__":
    main()
