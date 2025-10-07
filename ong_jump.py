"""
ong_jump.py
Single-file Pygame "Ong jumping on stones" game.

Assets (put these files in the same folder as this script):
- ong.png            -> player sprite (recommended ~64x64)
- stone.png          -> stone obstacle sprite
- road.png           -> road/tile sprite to be repeated horizontally
- bg_day.png         -> background scenery for day (wide or tileable)
- bg_night.png       -> background scenery for night
- jump.wav           -> jump SFX (optional)
- hit.wav            -> collision SFX (optional)
- score.wav          -> milestone SFX (optional)
- bgm.mp3            -> background music (optional)

If assets are missing the game uses simple shapes.
"""

import pygame
import random
import os
import sys
from pathlib import Path

# --- Configuration ---
WIDTH, HEIGHT = 1000, 560
FPS = 60
GROUND_Y = HEIGHT - 120  # ground height
PLAYER_X = 140
GRAVITY = 1.2
JUMP_VELOCITY = -13
INITIAL_SPEED = 6.0
SPEED_INCREASE_RATE = 0.0009  # per frame, small increase for long runs
MAX_SPEED = 13.0  # Cap the speed to keep game fair
STONE_SPAWN_BASE = 1400  # ms base interval
STONE_GAP_VARIANCE = 700  # variance for spawn timing
FONT_NAME = None  # default font

ASSET_FILENAMES = {
    "player": "ong.png",
    "stone": "stone.png",
    "road": "road.png",
    "bg_day": "bg_day.png",
    "bg_night": "bg_night.png",
    "splash": "splash.png",
    "jump_sfx": "jump.wav",
    "hit_sfx": "hit.wav",
    "score_sfx": "score.wav",
    "bgm": "bgm.wav",
}
HIGHSCORE_FILE = "highscore.txt"

# --- Init Pygame ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ong Jump")
clock = pygame.time.Clock()

# load font
font = pygame.font.Font(FONT_NAME, 28)
big_font = pygame.font.Font(FONT_NAME, 48)

# utility for loading images with fallback
def load_image(name, fallback_size=None):
    path = Path(name)
    if path.is_file():
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            return img
        except Exception as e:
            print(f"Error loading image {name}: {e}")
    # fallback: colored rect surface
    w, h = fallback_size if fallback_size else (64, 64)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((200, 200, 200, 255))
    pygame.draw.rect(surf, (120, 120, 120), surf.get_rect(), 4)
    return surf

# load sounds with safe fallback
def load_sound(name):
    path = Path(name)
    if path.is_file():
        try:
            return pygame.mixer.Sound(str(path))
        except Exception as e:
            print(f"Error loading sound {name}: {e}")
    return None

# load assets
player_img = load_image(ASSET_FILENAMES["player"], fallback_size=(80, 80))
stone_img = load_image(ASSET_FILENAMES["stone"], fallback_size=(90, 48))
road_img = load_image(ASSET_FILENAMES["road"], fallback_size=(400, 120))

bg_day_img = load_image(ASSET_FILENAMES["bg_day"], fallback_size=(WIDTH, HEIGHT))
bg_night_img = load_image(ASSET_FILENAMES["bg_night"], fallback_size=(WIDTH, HEIGHT))
splash_img = load_image(ASSET_FILENAMES["splash"], fallback_size=(WIDTH, HEIGHT))

jump_sfx = load_sound(ASSET_FILENAMES["jump_sfx"])
hit_sfx = load_sound(ASSET_FILENAMES["hit_sfx"])
score_sfx = load_sound(ASSET_FILENAMES["score_sfx"])
bgm_path = Path(ASSET_FILENAMES["bgm"])
if bgm_path.is_file():
    try:
        pygame.mixer.music.load(str(bgm_path))
    except Exception as e:
        print("Could not load bgm:", e)

# --- Helper functions ---
def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(int(score)))
    except Exception as e:
        print("Error saving highscore:", e)

def load_highscore():
    if Path(HIGHSCORE_FILE).is_file():
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                return int(f.read().strip() or "0")
        except Exception:
            return 0
    return 0

# --- Game objects ---
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image_orig = pygame.transform.smoothscale(player_img, (80, 80))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(midbottom=(PLAYER_X, GROUND_Y))
        self.vel_y = 0.0
        self.on_ground = True
        self.jump_cooldown = 0

    def update(self):
        # apply gravity
        self.vel_y += GRAVITY
        self.rect.y += int(self.vel_y)
        # ground collision
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = False
        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1

    def jump(self):
        if self.on_ground and self.jump_cooldown == 0:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False
            self.jump_cooldown = 8
            if jump_sfx:
                jump_sfx.play()

    def draw(self, surf):
        surf.blit(self.image, self.rect)

class Stone(pygame.sprite.Sprite):
    def __init__(self, x, speed):
        super().__init__()
        # Make stone smaller (e.g., 60x32)
        self.image = pygame.transform.smoothscale(stone_img, (60, 32))
        self.rect = self.image.get_rect(bottomleft=(x, GROUND_Y))
        self.speed = speed

    def update(self, speed_multiplier, dt):
        # Move left using frame time for smooth, frame-independent movement
        move_x = self.speed * speed_multiplier * (dt / 16.67)  # 16.67ms = 60 FPS baseline
        self.rect.x -= int(move_x)
        # Remove if off screen
        if self.rect.right < -50:
            self.kill()

    def draw(self, surf):
        surf.blit(self.image, self.rect)

# Parallax background helper
class Parallax:
    def __init__(self, image, speed_factor, y_offset=0):
        self.image = image
        self.speed_factor = speed_factor
        self.y_offset = y_offset
        self.x1 = 0
        # scale background to window width (preserve ratio)
        w = image.get_width()
        h = image.get_height()
        scale = HEIGHT / h
        self.image = pygame.transform.smoothscale(image, (int(w * scale), HEIGHT))
        self.w = self.image.get_width()

    def update_and_draw(self, surf, global_speed):
        shift = global_speed * self.speed_factor
        self.x1 -= shift
        if self.x1 <= -self.w:
            self.x1 += self.w
        # draw two copies
        surf.blit(self.image, (int(self.x1), self.y_offset))
        surf.blit(self.image, (int(self.x1 + self.w), self.y_offset))

# Road tiling
class Road:
    def __init__(self, image):
        h = image.get_height()
        scale = 120 / h
        self.tile = pygame.transform.smoothscale(image, (int(image.get_width() * scale), 120))
        self.w = self.tile.get_width()
        self.x1 = 0

    def update_and_draw(self, surf, speed):
        self.x1 -= speed
        if self.x1 <= -self.w:
            self.x1 += self.w
        y = GROUND_Y
        # Draw enough tiles to fill the screen
        x = int(self.x1)
        while x < WIDTH:
            surf.blit(self.tile, (x, y))
            x += self.w
        # draw a darker overlay to simulate shadow
        shadow = pygame.Surface((WIDTH, int(8)), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 40))
        surf.blit(shadow, (0, y - 8))

# --- Game state functions ---
def spawn_stone_group(stone_group, current_speed):
    # Spawn stones at the right edge, moving left, with enough gap from last stone
    min_gap = 220  # minimum horizontal gap between stones (pixels)
    max_gap = 340  # maximum gap
    last_x = None
    if len(stone_group) > 0:
        # Find the rightmost stone
        last_x = max(stone.rect.right for stone in stone_group)
    else:
        last_x = WIDTH
    # Place new stone after last stone with a random gap
    gap = random.randint(min_gap, max_gap)
    x = max(WIDTH, last_x + gap)
    stone = Stone(x, speed=current_speed * 0.85 + random.uniform(0.0, 1.0))
    stone_group.add(stone)

def draw_text_center(surf, text, fontobj, y, color=(255,255,255)):
    txt = fontobj.render(text, True, color)
    r = txt.get_rect(center=(WIDTH // 2, y))
    surf.blit(txt, r)

# --- Main loop / menu ---
def main():
    # --- Splash screen ---
    splash_time = 0
    splash_loader_angle = 0
    splash_duration = 1800  # ms
    splash_running = True
    splash_start = pygame.time.get_ticks()
    while splash_running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        # Draw splash image full screen
        screen.blit(pygame.transform.smoothscale(splash_img, (WIDTH, HEIGHT)), (0, 0))
        # Draw loader (rotating arc) inside splash, right side, dark color
        loader_center = (WIDTH - 120, HEIGHT//2)
        loader_radius = 48
        loader_thickness = 10
        loader_color = (40, 40, 40)
        loader_angle = (pygame.time.get_ticks() // 6) % 360
        pygame.draw.circle(screen, (120,120,120), loader_center, loader_radius, loader_thickness)
        arc_rect = pygame.Rect(0,0,loader_radius*2,loader_radius*2)
        arc_rect.center = loader_center
        pygame.draw.arc(screen, loader_color, arc_rect, 0, (loader_angle/180)*3.14159, loader_thickness)
        pygame.display.flip()
        if pygame.time.get_ticks() - splash_start > splash_duration:
            splash_running = False
    running = True
    show_menu = True
    # Persist night_mode across restarts
    global _night_mode_state
    try:
        night_mode = _night_mode_state
    except NameError:
        night_mode = False
    highscore = load_highscore()

    # objects
    player = Player()
    stone_group = pygame.sprite.Group()

    # parallax - two layers
    day_bg = Parallax(bg_day_img, speed_factor=0.12)
    night_bg = Parallax(bg_night_img, speed_factor=0.12)
    road = Road(road_img)

    # Sun, moon, and birds (lego pixel style)
    def draw_sun(surf):
        pygame.draw.circle(surf, (255, 230, 80), (WIDTH-120, 90), 38)
        pygame.draw.circle(surf, (255, 255, 180), (WIDTH-120, 90), 28)

    def draw_moon(surf):
        pygame.draw.circle(surf, (220, 220, 255), (WIDTH-120, 90), 32)
        pygame.draw.circle(surf, (40, 40, 80), (WIDTH-110, 90), 24)

    def draw_bird(surf, x, y, scale=1.0):
        # Simple lego-pixel bird: body, wing, beak
        body = pygame.Rect(x, y, int(18*scale), int(8*scale))
        wing = pygame.Rect(x+7*scale, y-5*scale, int(10*scale), int(7*scale))
        pygame.draw.rect(surf, (60,60,60), body)
        pygame.draw.rect(surf, (120,120,120), wing)
        pygame.draw.rect(surf, (255,200,60), (x+15*scale, y+2*scale, int(4*scale), int(3*scale)))

    # spawn timer
    SPAWN_EVENT = pygame.USEREVENT + 1
    spawn_interval = max(450, STONE_SPAWN_BASE - int(INITIAL_SPEED * 60))
    pygame.time.set_timer(SPAWN_EVENT, spawn_interval)

    speed = INITIAL_SPEED
    distance = 0.0  # used for score
    score = 0
    run_time = 0
    last_score_milestone = 0

    # music
    # Always play bgm.mp3 as background music if available
    try:
        pygame.mixer.music.set_volume(0.45)
        if bgm_path.is_file():
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)
    except Exception:
        pass

    # Menu loop
    menu_selection = 0  # 0: start, 1: toggle day/night, 2: quit
    while show_menu and running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
                show_menu = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_UP, pygame.K_w):
                    menu_selection = (menu_selection - 1) % 3
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    menu_selection = (menu_selection + 1) % 3
                elif ev.key == pygame.K_RETURN:
                    if menu_selection == 0:
                        show_menu = False
                    elif menu_selection == 1:
                        night_mode = not night_mode
                        _night_mode_state = night_mode  # persist across restarts
                    elif menu_selection == 2:
                        running = False
                        show_menu = False
                elif ev.key == pygame.K_ESCAPE:
                    running = False
                    show_menu = False

        screen.fill((24, 24, 30))
        # draw a preview of day/night
        bg_preview = night_bg.image if night_mode else day_bg.image
        preview = pygame.transform.smoothscale(bg_preview, (int(WIDTH*0.9), int(HEIGHT*0.45)))
        screen.blit(preview, ((WIDTH - preview.get_width())//2, 40))

        draw_text_center(screen, "ONG JUMP", big_font, 48)
        draw_text_center(screen, f"Highscore: {highscore}", font, 110)
        # menu items
        menu_items = [
            f"Start Game",
            f"Mode: {'Night' if night_mode else 'Day'} (Press Enter to toggle)",
            "Quit"
        ]
        y = 320
        for i, item in enumerate(menu_items):
            color = (255, 230, 120) if i == menu_selection else (220, 220, 220)
            txt = font.render(item, True, color)
            rect = txt.get_rect(center=(WIDTH//2, y + i*40))
            screen.blit(txt, rect)

        draw_text_center(screen, "Controls: SPACE to jump, ESC to quit", font, HEIGHT - 30, color=(200,200,200))
        pygame.display.flip()
        clock.tick(FPS)

    # reset / start gameplay
    stone_group.empty()
    player.rect.midbottom = (PLAYER_X, GROUND_Y)
    player.vel_y = 0
    speed = INITIAL_SPEED
    distance = 0.0
    score = 0
    run_time = 0
    last_score_milestone = 0
    # Make stones spawn further apart and a bit slower
    pygame.time.set_timer(SPAWN_EVENT, random.randint(1400, 1800))

    # Main gameplay loop
    while running:
        dt = clock.tick(FPS)  # milliseconds since last tick
        run_time += dt
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == SPAWN_EVENT:
                spawn_stone_group(stone_group, current_speed=speed)
                # At higher speeds, keep spawn interval high enough for fair gaps
                min_spawn = max(700, int(1800 - speed * 80))
                max_spawn = max(1100, int(2200 - speed * 100))
                next_ms = random.randint(min_spawn, max_spawn)
                pygame.time.set_timer(SPAWN_EVENT, next_ms)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_SPACE:
                    player.jump()
                elif ev.key == pygame.K_ESCAPE:
                    # Return to menu
                    return

        # gradually increase speed
        speed += SPEED_INCREASE_RATE * dt
        if speed > MAX_SPEED:
            speed = MAX_SPEED
        # update distance/score
        distance += speed * (dt / 1000.0) * 100  # arbitrary distance units
        new_score = int(distance // 10)
        if new_score != score:
            score = new_score
            # milestone sound removed; now plays only on game over

        # update sprites
        player.update()
        for stone in list(stone_group):
            stone.update(speed_multiplier=speed/INITIAL_SPEED, dt=dt)

        # collision detection (simple rect-based but can be improved)
        collided = pygame.sprite.spritecollideany(player, stone_group, collided=pygame.sprite.collide_mask)
        if collided:
            if hit_sfx:
                hit_sfx.play()
            # game over
            if score > highscore:
                highscore = score
                save_highscore(highscore)
            # simple game over screen
            game_over_screen(score, highscore)
            # reset to menu
            main()
            return

        # draw background (parallax)
        if night_mode:
            night_bg.update_and_draw(screen, global_speed=speed * 0.4)
            draw_moon(screen)
        else:
            day_bg.update_and_draw(screen, global_speed=speed * 0.4)
            draw_sun(screen)

        # draw birds (lego pixel style, both modes)
        for i in range(3):
            bx = 180 + i*180 + int((run_time//7 + i*60) % 120)
            by = 80 + (i%2)*22
            draw_bird(screen, bx, by, scale=1.2 - 0.2*i)

        # draw road
        road.update_and_draw(screen, speed)

        # draw stones (obstacles)
        for stone in stone_group:
            stone.draw(screen)

        # draw player
        player.draw(screen)

        # UI: score & speed
        score_surf = font.render(f"Score: {score}", True, (255,255,255))
        speed_surf = font.render(f"Speed: {speed:.2f}", True, (255,255,255))
        hs_surf = font.render(f"High: {highscore}", True, (255,200,120))
        screen.blit(score_surf, (18, 18))
        screen.blit(speed_surf, (18, 50))
        screen.blit(hs_surf, (WIDTH - 140, 18))

        # small instruction
        screen.blit(font.render("Press SPACE to jump", True, (200,200,200)), (18, HEIGHT-34))

        pygame.display.flip()

def game_over_screen(score, highscore):
    # show result, allow restart or quit
    over = True
    timer = 0
    played_score_sfx = False
    while over:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN:
                    over = False
                elif ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        screen.fill((18, 18, 18))
        draw_text_center(screen, "GAME OVER", big_font, HEIGHT//2 - 80, color=(255,80,80))
        draw_text_center(screen, f"Score: {score}", font, HEIGHT//2 - 20)
        draw_text_center(screen, f"Highscore: {highscore}", font, HEIGHT//2 + 20)
        draw_text_center(screen, "Press Enter to play again or Esc to quit", font, HEIGHT//2 + 80, color=(200,200,200))
        if not played_score_sfx and score_sfx:
            score_sfx.play()
            played_score_sfx = True
        pygame.display.flip()
        clock.tick(30)
        timer += 1

# Run
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("An exception occurred:", e)
    finally:
        pygame.quit()
