import sys
import subprocess

try:
    import PyQt6
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])

import math
import random
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QPen, QRadialGradient
from PyQt6.QtWidgets import QApplication, QWidget

COLOR_PALETTES = {
    "Rainbow": ['#FF5733', '#FFC300', '#DAF7A6', '#33FF57', '#33FFF3', '#3380FF', '#9B33FF', '#FF33F3', '#FF3366', '#FF8F33'],
    "Monochrome": ['#212529', '#343A40', '#495057', '#6C757D', '#ADB5BD', '#CED4DA', '#DEE2E6', '#E9ECEF', '#333333', '#111111'],
    "Neon Cyberpunk": ['#FF007F', '#00FFCC', '#9D00FF', '#FFE600', '#00E5FF', '#FF3300', '#76FF03', '#D500F9', '#651FFF', '#00B0FF'],
    "Pastel Dream": ['#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF', '#E8BAFF', '#FFBAC8', '#CAFFBF', '#9BF6FF', '#FFD166'],
    "Sunset Gradient": ['#7209B7', '#560BAD', '#480CA8', '#3F37C9', '#4361EE', '#4895EF', '#4CC9F0', '#F72585', '#B5179E', '#7209B7']
}

class Ball:
    def __init__(self, x, y, color, is_cue=False):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = 14
        self.color = color
        self.is_cue = is_cue
        self.is_pocketed = False

    def update(self, width, height):
        if self.is_pocketed:
            return

        self.x += self.vx
        self.y += self.vy

        # Friction
        self.vx *= 0.985
        self.vy *= 0.985

        if abs(self.vx) < 0.05: self.vx = 0
        if abs(self.vy) < 0.05: self.vy = 0

        # Boundary bounces
        bounce = 0.7
        margin = 15
        if self.x - self.radius < margin:
            self.x = margin + self.radius
            self.vx *= -bounce
        elif self.x + self.radius > width - margin:
            self.x = width - margin - self.radius
            self.vx *= -bounce

        if self.y - self.radius < margin + 40:
            self.y = margin + 40 + self.radius
            self.vy *= -bounce
        elif self.y + self.radius > height - margin:
            self.y = height - margin - self.radius
            self.vy *= -bounce

    def draw(self, painter):
        if self.is_pocketed:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        base_color = QColor(self.color)
        
        # Outer Glow / Drop Shadow
        glow_grad = QRadialGradient(self.x, self.y, self.radius + 6)
        glow_color = QColor(base_color if not self.is_cue else QColor(255, 255, 255))
        glow_color.setAlpha(120 if self.is_cue else 90)
        glow_grad.setColorAt(0.0, glow_color)
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow_grad))
        painter.drawEllipse(int(self.x - self.radius - 6), int(self.y - self.radius - 6), int((self.radius + 6) * 2), int((self.radius + 6) * 2))

        # Ball Fill with distinct border for cue ball visibility
        painter.setBrush(QBrush(base_color))
        border_pen = QPen(QColor(255, 255, 255, 240) if self.is_cue else QColor(20, 20, 20, 200), 2.5 if self.is_cue else 1.5)
        painter.setPen(border_pen)
        painter.drawEllipse(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

        painter.restore()

class DesktopPoolWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        screen = QApplication.primaryScreen().geometry()
        self.screen_w = screen.width()
        self.screen_h = screen.height()
        self.setGeometry(0, 0, self.screen_w, self.screen_h)

        self.pocket_r = 32
        margin = 35
        self.pockets = [
            (margin, margin + 20),
            (self.screen_w - margin, margin + 20),
            (margin, self.screen_h - margin),
            (self.screen_w - margin, self.screen_h - margin)
        ]

        self.theme_colors = COLOR_PALETTES[random.choice(list(COLOR_PALETTES.keys()))]
        self.init_balls()

        self.is_aiming = False
        self.mouse_pos = (0, 0)
        self.max_indicator_len = 240

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(16)

    def init_balls(self):
        self.balls = []
        self.cue_ball = Ball(self.screen_w / 2, self.screen_h / 2, '#FFFFFF', is_cue=True)
        self.balls.append(self.cue_ball)

        start_x = self.screen_w / 2 + 150
        start_y = self.screen_h / 2
        spacing = 24

        rack_map = [
            (0, 0),
            (1, -1), (1, 1),
            (2, -2), (2, 0), (2, 2),
            (3, -3), (3, -1), (3, 1), (3, 3)
        ]

        for i, (row, col) in enumerate(rack_map):
            bx = start_x + row * (spacing * 0.866)
            by = start_y + col * (spacing / 2)
            color = self.theme_colors[i % len(self.theme_colors)]
            self.balls.append(Ball(bx, by, color))
            
        self.balls_left = len(self.balls) - 1
        self.turns = 0

    def game_loop(self):
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                b1, b2 = self.balls[i], self.balls[j]
                if b1.is_pocketed or b2.is_pocketed:
                    continue

                dx = b2.x - b1.x
                dy = b2.y - b1.y
                dist = math.hypot(dx, dy)
                min_dist = b1.radius + b2.radius

                if 0 < dist < min_dist:
                    overlap = min_dist - dist
                    nx, ny = dx / dist, dy / dist

                    b1.x -= nx * overlap * 0.5
                    b1.y -= ny * overlap * 0.5
                    b2.x += nx * overlap * 0.5
                    b2.y += ny * overlap * 0.5

                    kx = b1.vx - b2.vx
                    ky = b1.vy - b2.vy
                    p = (nx * kx + ny * ky)

                    b1.vx -= p * nx
                    b1.vy -= p * ny
                    b2.vx += p * nx
                    b2.vy += p * ny

        for b in self.balls:
            if b.is_pocketed:
                continue
            for px, py in self.pockets:
                if math.hypot(b.x - px, b.y - py) < self.pocket_r:
                    b.is_pocketed = True
                    b.vx, b.vy = 0, 0
                    if b.is_cue:
                        b.is_pocketed = False
                        b.vx, b.vy = 0, 0
                        if self.balls_left < 10:
                            # Add a new ball if less than 8 remain
                            new_color = random.choice(self.theme_colors)
                            angle = random.uniform(0, 2 * math.pi)
                            dist = random.uniform(30, 80)
                            nx = self.screen_w / 2 + math.cos(angle) * dist
                            ny = self.screen_h / 2 + math.sin(angle) * dist
                            self.balls.append(Ball(nx, ny, new_color))
                            self.balls_left += 1
                        
                        # Teleport white ball back to center in all cases
                        b.x = self.screen_w / 2
                        b.y = self.screen_h / 2
                    else:
                        self.balls_left = max(0, self.balls_left - 1)

        for b in self.balls:
            b.update(self.screen_w, self.screen_h)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw 4 Corner Holes
        for px, py in self.pockets:
            hole_grad = QRadialGradient(px, py, self.pocket_r)
            hole_grad.setColorAt(0.0, QColor(5, 5, 8, 255))
            hole_grad.setColorAt(0.8, QColor(15, 15, 25, 230))
            hole_grad.setColorAt(1.0, QColor(60, 60, 80, 100))
            
            painter.setBrush(QBrush(hole_grad))
            painter.setPen(QPen(QColor(80, 80, 100, 180), 2))
            painter.drawEllipse(int(px - self.pocket_r), int(py - self.pocket_r), self.pocket_r * 2, self.pocket_r * 2)

        # Aiming line indicator
        if self.is_aiming:
            painter.setPen(QPen(QColor(255, 255, 255, 200), 2, Qt.PenStyle.DashLine))
            mx, my = self.mouse_pos
            dx = mx - self.cue_ball.x
            dy = my - self.cue_ball.y
            dist = math.hypot(dx, dy)
            
            if dist > 0:
                capped_len = min(dist, self.max_indicator_len)
                end_x = self.cue_ball.x + (dx / dist) * capped_len
                end_y = self.cue_ball.y + (dy / dist) * capped_len
                painter.drawLine(int(self.cue_ball.x), int(self.cue_ball.y), int(end_x), int(end_y))

        for b in self.balls:
            b.draw(painter)

        # Centered HUD Overlay Text
        painter.setPen(QColor(240, 240, 255))
        painter.setFont(QFont('Segoe UI', 13, QFont.Weight.Bold))
        
        hud_text = f"Balls Left: {self.balls_left}   |   Turns: {self.turns}"
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(hud_text)
        
        painter.drawText(int((self.screen_w - text_width) / 2), 45, hud_text)
        
        painter.setFont(QFont('Segoe UI', 10))
        painter.setPen(QColor(180, 180, 200))
        painter.drawText(60, self.screen_h - 25, "Desktop Mode: Click & Drag White Ball to shoot. Press ESC to quit.")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            moving = any(b.vx != 0 or b.vy != 0 for b in self.balls)
            if not moving:
                mx, my = event.position().x(), event.position().y()
                if math.hypot(self.cue_ball.x - mx, self.cue_ball.y - my) < self.cue_ball.radius * 2:
                    self.is_aiming = True
                    self.mouse_pos = (mx, my)

    def mouseMoveEvent(self, event):
        if self.is_aiming:
            self.mouse_pos = (event.position().x(), event.position().y())

    def mouseReleaseEvent(self, event):
        if self.is_aiming:
            self.is_aiming = False
            mx, my = event.position().x(), event.position().y()
            dx = mx - self.cue_ball.x
            dy = my - self.cue_ball.y
            
            speed = math.hypot(dx, dy)
            if speed > self.max_indicator_len:
                dx = (dx / speed) * self.max_indicator_len
                dy = (dy / speed) * self.max_indicator_len

            self.cue_ball.vx = dx * 0.1 * 2.5
            self.cue_ball.vy = dy * 0.1 * 2.5
            self.turns += 1

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            sys.exit(0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DesktopPoolWindow()
    window.show()
    sys.exit(app.exec())