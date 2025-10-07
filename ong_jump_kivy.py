# ong_jump_kivy.py
# Kivy version of Ong Jump for Android APK build
# This is a starter template. You will need to add your game logic and assets.

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse
import random

# Set window size for desktop testing
Window.size = (1000, 560)

class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(Label(text='ONG JUMP', font_size=48, pos_hint={'center_x':0.5,'center_y':0.7}))
        self.add_widget(Label(text='Loading...', font_size=24, pos_hint={'center_x':0.5,'center_y':0.4}))
        Clock.schedule_once(self.goto_menu, 2)
    def goto_menu(self, dt):
        self.manager.current = 'menu'

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=20, padding=80)
        layout.add_widget(Label(text='ONG JUMP', font_size=48))
        btn_start = Button(text='Start Game', font_size=32, size_hint=(1,0.2))
        btn_start.bind(on_release=self.start_game)
        layout.add_widget(btn_start)
        btn_quit = Button(text='Quit', font_size=32, size_hint=(1,0.2))
        btn_quit.bind(on_release=lambda x: App.get_running_app().stop())
        layout.add_widget(btn_quit)
        self.add_widget(layout)
    def start_game(self, instance):
        self.manager.current = 'game'

class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game = OngJumpWidget()
        self.add_widget(self.game)
    def on_enter(self):
        self.game.start()

class OngJumpWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Game constants
        self.WIDTH, self.HEIGHT = 1000, 560
        self.GROUND_Y = 120  # Distance from bottom
        self.PLAYER_X = 140
        self.PLAYER_SIZE = 80
        # Load images (use your original assets)
        from kivy.core.image import Image as CoreImage
        import os
        asset_path = os.path.dirname(__file__)
        def load_img(name, fallback_color):
            try:
                return CoreImage(os.path.join(asset_path, name)).texture
            except Exception:
                from kivy.graphics import Rectangle, Color
                return None
        self.player_img = load_img('ong.png', (1,0.8,0.2,1))
        self.stone_img = load_img('stone.png', (0.5,0.5,0.5,1))
        self.road_img = load_img('road.png', (0.3,0.3,0.3,1))
        self.bg_day_img = load_img('bg_day.png', (0.8,0.9,1,1))
        self.bg_night_img = load_img('bg_night.png', (0.08,0.09,0.18,1))
        self.GRAVITY = 1.2
        self.JUMP_VELOCITY = -13
        self.INITIAL_SPEED = 6.0
        self.SPEED_INCREASE_RATE = 0.0009
        self.MAX_SPEED = 13.0
        self.MIN_STONE_GAP = 220
        self.MAX_STONE_GAP = 340
        self.ROAD_HEIGHT = 120
        self.ROAD_TILE_W = 400
        self.ROAD_TILE_H = 120
        self.night_mode = False
        # Game state
        self.reset_game()
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        if self._keyboard:
            self._keyboard.bind(on_key_down=self._on_key_down)
        self.bind(size=self.update_canvas, pos=self.update_canvas)

    def reset_game(self):
        self.player_y = self.GROUND_Y
        self.vel_y = 0
        self.on_ground = True
        self.stones = []
        self.score = 0
        self.highscore = 0
        self.speed = self.INITIAL_SPEED
        self.distance = 0.0
        self.game_running = False
        self.game_over = False
        self.road_offset = 0
        self.spawn_timer = 0
        self.run_time = 0
        self.last_spawn_x = self.WIDTH
        self.stone_gap = random.randint(self.MIN_STONE_GAP, self.MAX_STONE_GAP)

    def start(self):
        self.reset_game()
        self.game_running = True
        self.game_over = False
        Clock.schedule_interval(self.update, 1/60)
    def update(self, dt):
        if not self.game_running:
            return
        self.run_time += dt * 1000
        # Gravity and jump
        self.vel_y += self.GRAVITY
        self.player_y += self.vel_y
        if self.player_y <= self.GROUND_Y:
            self.player_y = self.GROUND_Y
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = False
        # Stones movement and spawn
        self.speed += self.SPEED_INCREASE_RATE * (dt * 1000)
        if self.speed > self.MAX_SPEED:
            self.speed = self.MAX_SPEED
        for stone in self.stones:
            stone['x'] -= self.speed * (dt * 60 / 1000)
        self.stones = [s for s in self.stones if s['x'] + s['w'] > 0]
        # Spawn new stone if needed
        if len(self.stones) == 0 or (self.stones[-1]['x'] < self.WIDTH - self.stone_gap):
            stone_w, stone_h = 60, 32
            new_x = self.WIDTH + random.randint(20, 120)
            self.stones.append({'x': new_x, 'y': self.GROUND_Y - stone_h, 'w': stone_w, 'h': stone_h})
            self.stone_gap = random.randint(self.MIN_STONE_GAP, self.MAX_STONE_GAP)
        # Collision detection
        player_rect = (self.PLAYER_X, self.player_y, self.PLAYER_SIZE, self.PLAYER_SIZE)
        for stone in self.stones:
            stone_rect = (stone['x'], stone['y'], stone['w'], stone['h'])
            if self.rects_collide(player_rect, stone_rect):
                self.game_running = False
                self.game_over = True
                if self.score > self.highscore:
                    self.highscore = self.score
                break
        # Scoring
        self.distance += self.speed * dt * 100
        new_score = int(self.distance // 10)
        if new_score != self.score:
            self.score = new_score
        # Road movement
        self.road_offset -= self.speed * (dt * 60 / 1000)
        if self.road_offset <= -self.ROAD_TILE_W:
            self.road_offset += self.ROAD_TILE_W
        self.update_canvas()
    def update_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Background (day/night)
            if self.night_mode and self.bg_night_img:
                Rectangle(texture=self.bg_night_img, pos=self.pos, size=self.size)
            elif not self.night_mode and self.bg_day_img:
                Rectangle(texture=self.bg_day_img, pos=self.pos, size=self.size)
            else:
                Color(0.8, 0.9, 1)
                Rectangle(pos=self.pos, size=self.size)
            # Road tiling
            y = 0
            x = self.road_offset
            while x < self.WIDTH:
                if self.road_img:
                    Rectangle(texture=self.road_img, pos=(x, y), size=(self.ROAD_TILE_W, self.ROAD_TILE_H))
                else:
                    Color(0.3, 0.3, 0.3)
                    Rectangle(pos=(x, y), size=(self.ROAD_TILE_W, self.ROAD_TILE_H))
                x += self.ROAD_TILE_W
            # Stones
            for stone in self.stones:
                if self.stone_img:
                    Rectangle(texture=self.stone_img, pos=(stone['x'], stone['y']), size=(stone['w'], stone['h']))
                else:
                    Color(0.5, 0.5, 0.5)
                    Rectangle(pos=(stone['x'], stone['y']), size=(stone['w'], stone['h']))
            # Player
            if self.player_img:
                Rectangle(texture=self.player_img, pos=(self.PLAYER_X, self.player_y), size=(self.PLAYER_SIZE, self.PLAYER_SIZE))
            else:
                Color(1, 0.8, 0.2)
                Ellipse(pos=(self.PLAYER_X, self.player_y), size=(self.PLAYER_SIZE, self.PLAYER_SIZE))
            # Score
            Color(1,1,1,1)
            from kivy.core.text import Label as CoreLabel
            label = CoreLabel(text=f"Score: {self.score}", font_size=32)
            label.refresh()
            Rectangle(texture=label.texture, pos=(18, self.HEIGHT-50), size=label.texture.size)
            label2 = CoreLabel(text=f"High: {self.highscore}", font_size=28)
            label2.refresh()
            Rectangle(texture=label2.texture, pos=(self.WIDTH-180, self.HEIGHT-50), size=label2.texture.size)
            # Game over
            if self.game_over:
                label3 = CoreLabel(text="GAME OVER", font_size=64)
                label3.refresh()
                Rectangle(texture=label3.texture, pos=(self.WIDTH//2-180, self.HEIGHT//2), size=label3.texture.size)
                label4 = CoreLabel(text="Press SPACE to restart", font_size=32)
                label4.refresh()
                Rectangle(texture=label4.texture, pos=(self.WIDTH//2-180, self.HEIGHT//2-60), size=label4.texture.size)
    def _on_keyboard_closed(self):
        self._keyboard = None
    def _on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'spacebar':
            if self.game_over:
                self.start()
            elif self.on_ground:
                self.vel_y = self.JUMP_VELOCITY
        elif keycode[1] == 'n':
            self.night_mode = not self.night_mode
            self.update_canvas()
        return True

    @staticmethod
    def rects_collide(r1, r2):
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        return (x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2)

class OngJumpApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(GameScreen(name='game'))
        sm.current = 'splash'
        return sm

if __name__ == '__main__':
    OngJumpApp().run()
