import random
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Rectangle, Line
from kivy.utils import get_color_from_hex

# Размеры окна
Window.size = (380, 740)
Window.clearcolor = get_color_from_hex("#121212")

GRID_WIDTH = 10
GRID_HEIGHT = 20

# Цвета
COLOR_BG = get_color_from_hex("#1A1A1A")
COLOR_TEXT = get_color_from_hex("#E0E0E0")
COLOR_GRID = get_color_from_hex("#2A2A2A")
COLOR_BORDER = get_color_from_hex("#555555")
COLOR_BLOCK = get_color_from_hex("#CCCCCC")

# Строго выбранный набор фигур
SHAPES = {
    'SQUARE_2X2': [[1, 1], [1, 1]],            # Квадрат 2x2
    'PYRAMID': [[0, 1, 0], [1, 1, 1]],         # Пирамида (база 3, высота 2)
    'CHOCO_L': [[1, 0], [1, 0], [1, 1]],       # Часть шоколадки (||_)
    # Классика:
    'STICK_I': [[1, 1, 1, 1]],                 # Линия 1x4
    'S_SHAPE': [[0, 1, 1], [1, 1, 0]],          # S-фигура
    'Z_SHAPE': [[1, 1, 0], [0, 1, 1]],          # Z-фигура
    'J_SHAPE': [[0, 1], [0, 1], [1, 1]]         # Обратная L
}

class NextPiecePreview(Widget):
    """Виджет для показа следующей фигуры."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.piece = None
        self.bind(pos=self.draw, size=self.draw)

    def set_piece(self, piece):
        self.piece = piece
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Фон блока NEXT
            Color(*COLOR_BG)
            Rectangle(pos=self.pos, size=self.size)
            Color(*COLOR_BORDER)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=1.5)

            if self.piece:
                rows = len(self.piece)
                cols = len(self.piece[0])
                cell_size = min((self.width - 16) / 4, (self.height - 16) / 4)
                
                # Центровка фигуры внутри блока
                start_x = self.x + (self.width - cols * cell_size) / 2
                start_y = self.y + (self.height - rows * cell_size) / 2

                Color(*COLOR_BLOCK)
                for r, row in enumerate(self.piece):
                    for c, val in enumerate(row):
                        if val:
                            draw_y = start_y + (rows - 1 - r) * cell_size
                            draw_x = start_x + c * cell_size
                            Rectangle(pos=(draw_x + 1, draw_y + 1), size=(cell_size - 2, cell_size - 2))

class TetrisCanvas(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw)
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_piece = None
        self.piece_x = 0
        self.piece_y = 0

    def draw(self, *args):
        self.canvas.clear()
        
        cell_size = min(self.width / GRID_WIDTH, self.height / GRID_HEIGHT)
        board_w = cell_size * GRID_WIDTH
        board_h = cell_size * GRID_HEIGHT
        
        start_x = self.x + (self.width - board_w) / 2
        start_y = self.y + (self.height - board_h) / 2

        with self.canvas:
            Color(*COLOR_BG)
            Rectangle(pos=(start_x, start_y), size=(board_w, board_h))

            Color(*COLOR_GRID)
            for x in range(GRID_WIDTH + 1):
                Line(points=[start_x + x * cell_size, start_y, start_x + x * cell_size, start_y + board_h], width=1)
            for y in range(GRID_HEIGHT + 1):
                Line(points=[start_x, start_y + y * cell_size, start_x + board_w, start_y + y * cell_size], width=1)

            Color(*COLOR_BORDER)
            Line(rectangle=(start_x, start_y, board_w, board_h), width=2)

            Color(*COLOR_BLOCK)
            for row in range(GRID_HEIGHT):
                for col in range(GRID_WIDTH):
                    if self.grid[row][col]:
                        draw_y = start_y + (GRID_HEIGHT - 1 - row) * cell_size
                        draw_x = start_x + col * cell_size
                        Rectangle(pos=(draw_x + 1, draw_y + 1), size=(cell_size - 2, cell_size - 2))

            if self.current_piece:
                for r, row in enumerate(self.current_piece):
                    for c, val in enumerate(row):
                        if val:
                            board_r = self.piece_y + r
                            board_c = self.piece_x + c
                            if 0 <= board_r < GRID_HEIGHT and 0 <= board_c < GRID_WIDTH:
                                draw_y = start_y + (GRID_HEIGHT - 1 - board_r) * cell_size
                                draw_x = start_x + board_c * cell_size
                                Rectangle(pos=(draw_x + 1, draw_y + 1), size=(cell_size - 2, cell_size - 2))

class TerminalTetrisApp(App):
    def build(self):
        self.score = 0
        self.game_over = False
        self.is_paused = False
        self.is_fast_drop = False
        self.next_piece = None

        # Загрузка музыки из файла
        self.sound = SoundLoader.load('tetris_theme.mp3')
        if not self.sound:
            self.sound = SoundLoader.load('tetris_theme.wav')
            
        if self.sound:
            self.sound.loop = True
            self.sound.volume = 0.5
            self.sound.play()

        main_layout = BoxLayout(orientation='vertical', padding=12, spacing=8)

        # --- ШАПКА: СЧЕТ, NEXT БЛОК И ПАУЗА ---
        top_bar = BoxLayout(orientation='horizontal', size_hint=(1, 0.12), spacing=10)
        
        # Левая часть шапки: Счет
        self.score_label = Label(
            text=f"SCORE: {self.score}",
            font_size='18sp',
            bold=True,
            color=COLOR_TEXT,
            halign='left',
            valign='middle',
            size_hint=(0.4, 1)
        )
        self.score_label.bind(size=self.score_label.setter('text_size'))

        # Средняя часть: Блок "NEXT"
        next_box = BoxLayout(orientation='vertical', size_hint=(0.35, 1))
        next_title = Label(text="NEXT", font_size='12sp', bold=True, color=COLOR_TEXT, size_hint=(1, 0.3))
        self.next_preview = NextPiecePreview(size_hint=(1, 0.7))
        next_box.add_widget(next_title)
        next_box.add_widget(self.next_preview)

        # Правая часть: Кнопка Паузы
        btn_pause = Button(
            text="||",
            font_size='18sp',
            bold=True,
            size_hint=(0.25, 1),
            background_normal='',
            background_color=get_color_from_hex("#333333"),
            color=COLOR_TEXT
        )
        btn_pause.bind(on_press=self.open_pause_menu)

        top_bar.add_widget(self.score_label)
        top_bar.add_widget(next_box)
        top_bar.add_widget(btn_pause)
        main_layout.add_widget(top_bar)

        # --- ИГРОВОЕ ПОЛЕ ---
        self.board = TetrisCanvas(size_hint=(1, 0.62))
        main_layout.add_widget(self.board)

        # --- УПРАВЛЕНИЕ ---
        controls_layout = BoxLayout(orientation='vertical', spacing=8, size_hint=(1, 0.26))

        btn_rotate = self.create_button("↻ ROTATE", self.on_rotate)
        controls_layout.add_widget(btn_rotate)

        bottom_row = BoxLayout(orientation='horizontal', spacing=8)
        btn_left = self.create_button("◄ LEFT", self.on_move_left)
        btn_right = self.create_button("RIGHT ►", self.on_move_right)
        
        btn_drop = Button(
            text="▼ DOWN",
            font_size='16sp',
            bold=True,
            background_normal='',
            background_color=get_color_from_hex("#252525"),
            color=COLOR_TEXT
        )
        btn_drop.bind(on_press=self.start_fast_drop, on_release=self.stop_fast_drop)

        bottom_row.add_widget(btn_left)
        bottom_row.add_widget(btn_drop)
        bottom_row.add_widget(btn_right)

        controls_layout.add_widget(bottom_row)
        main_layout.add_widget(controls_layout)

        # Старт игры
        self.next_piece = random.choice(list(SHAPES.values()))
        self.spawn_piece()
        
        self.current_speed = 0.40
        self.game_tick = Clock.schedule_interval(self.game_loop, self.current_speed)

        return main_layout

    def create_button(self, text, callback):
        btn = Button(
            text=text,
            font_size='16sp',
            bold=True,
            background_normal='',
            background_color=get_color_from_hex("#252525"),
            color=COLOR_TEXT
        )
        btn.bind(on_press=callback)
        return btn

    def get_drop_interval(self):
        level = self.score // 30
        return max(0.10, 0.40 - (level * 0.02))

    def spawn_piece(self):
        # Достаем заранее сгенерированную фигуру
        self.board.current_piece = self.next_piece
        # Генерируем следующую для блока NEXT
        self.next_piece = random.choice(list(SHAPES.values()))
        self.next_preview.set_piece(self.next_piece)

        self.board.piece_x = GRID_WIDTH // 2 - len(self.board.current_piece[0]) // 2
        self.board.piece_y = 0

        if self.check_collision(self.board.current_piece, self.board.piece_x, self.board.piece_y):
            self.game_over = True

    def check_collision(self, piece, offset_x, offset_y):
        for r, row in enumerate(piece):
            for c, cell in enumerate(row):
                if cell:
                    new_x = offset_x + c
                    new_y = offset_y + r
                    if new_x < 0 or new_x >= GRID_WIDTH or new_y >= GRID_HEIGHT:
                        return True
                    if new_y >= 0 and self.board.grid[new_y][new_x]:
                        return True
        return False

    def merge_piece(self):
        for r, row in enumerate(self.board.current_piece):
            for c, cell in enumerate(row):
                if cell:
                    self.board.grid[self.board.piece_y + r][self.board.piece_x + c] = 1
        self.clear_lines()
        self.spawn_piece()

    def clear_lines(self):
        lines_cleared = 0
        new_grid = []
        for row in self.board.grid:
            if all(cell == 1 for cell in row):
                lines_cleared += 1
            else:
                new_grid.append(row)

        for _ in range(lines_cleared):
            new_grid.insert(0, [0 for _ in range(GRID_WIDTH)])
            self.score += 10

        self.board.grid = new_grid
        self.score_label.text = f"SCORE: {self.score}"
        self.update_game_speed()

    def update_game_speed(self):
        if not self.is_fast_drop and not self.is_paused:
            self.current_speed = self.get_drop_interval()
            Clock.unschedule(self.game_tick)
            self.game_tick = Clock.schedule_interval(self.game_loop, self.current_speed)

    def game_loop(self, dt):
        if self.game_over:
            self.score_label.text = f"GAME OVER\nSCORE: {self.score}"
            if self.sound:
                self.sound.stop()
            return False

        if self.is_paused:
            return

        if not self.check_collision(self.board.current_piece, self.board.piece_x, self.board.piece_y + 1):
            self.board.piece_y += 1
        else:
            self.merge_piece()

        self.board.draw()

    # --- ПАУЗА И МЕНЮ ---
    def open_pause_menu(self, instance):
        if self.game_over:
            return
            
        self.is_paused = True
        if self.sound:
            self.sound.stop()

        content = BoxLayout(orientation='vertical', padding=20, spacing=15)
        pause_label = Label(text="PAUSE", font_size='26sp', bold=True, color=COLOR_TEXT)
        
        btn_resume = Button(
            text="ПРОДОЛЖИТЬ", font_size='18sp', bold=True,
            background_normal='', background_color=get_color_from_hex("#333333"),
            color=COLOR_TEXT, size_hint=(1, 0.4)
        )
        btn_exit = Button(
            text="ВЫЙТИ", font_size='18sp', bold=True,
            background_normal='', background_color=get_color_from_hex("#662222"),
            color=COLOR_TEXT, size_hint=(1, 0.4)
        )

        content.add_widget(pause_label)
        content.add_widget(btn_resume)
        content.add_widget(btn_exit)

        self.pause_popup = ModalView(size_hint=(0.75, 0.4), auto_dismiss=False)
        self.pause_popup.add_widget(content)

        btn_resume.bind(on_press=self.resume_game)
        btn_exit.bind(on_press=self.exit_game)
        self.pause_popup.open()

    def resume_game(self, instance):
        self.pause_popup.dismiss()
        self.is_paused = False
        if self.sound:
            self.sound.play()

    def exit_game(self, instance):
        self.pause_popup.dismiss()
        App.get_running_app().stop()

    # --- УПРАВЛЕНИЕ ---
    def start_fast_drop(self, instance):
        if not self.is_fast_drop and not self.is_paused:
            self.is_fast_drop = True
            Clock.unschedule(self.game_tick)
            self.game_tick = Clock.schedule_interval(self.game_loop, 0.05)

    def stop_fast_drop(self, instance):
        if self.is_fast_drop:
            self.is_fast_drop = False
            self.update_game_speed()

    def on_move_left(self, instance):
        if not self.game_over and not self.is_paused and not self.check_collision(self.board.current_piece, self.board.piece_x - 1, self.board.piece_y):
            self.board.piece_x -= 1
            self.board.draw()

    def on_move_right(self, instance):
        if not self.game_over and not self.is_paused and not self.check_collision(self.board.current_piece, self.board.piece_x + 1, self.board.piece_y):
            self.board.piece_x += 1
            self.board.draw()

    def on_rotate(self, instance):
        if self.game_over or self.is_paused:
            return
        rotated = [list(reversed(col)) for col in zip(*self.board.current_piece)]
        if not self.check_collision(rotated, self.board.piece_x, self.board.piece_y):
            self.current_piece = rotated
            self.board.current_piece = rotated
            self.board.draw()

if __name__ == "__main__":
    TerminalTetrisApp().run()