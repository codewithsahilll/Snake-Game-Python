# snake.py — Full Snake Game 

import math
import pygame, random, os, time, sys
pygame.init()
try:
    pygame.mixer.init()
except:
    pass

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 800, 600
SNAKE_BLOCK = 20
INITIAL_SPEED = 6.0
FPS_MIN = 5

BASE_DIR = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
HIGHSCORE_FILE = os.path.join(BASE_DIR, "highscore.txt")

# Colors
WHITE = (255,255,255)
RED = (213,50,80)
YELLOW = (255,215,0)
GREEN_HEAD = (0,200,120)
BLACK = (0,0,0)

# Fonts
TITLE_FONT = pygame.font.SysFont("comicsansms", 60, bold=True)
BIG_FONT = pygame.font.SysFont("comicsansms", 50, bold=True)
SCORE_FONT = pygame.font.SysFont("comicsansms", 28)
UI_FONT = pygame.font.SysFont("bahnschrift", 22)

# Pygame setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Game Deluxe")
clock = pygame.time.Clock()

# ---------------- SAFE LOADERS ----------------
def safe_load_image(name, fallback_size=(40,40), col=(120,120,120)):
    path = os.path.join(BASE_DIR, name)
    try:
        img = pygame.image.load(path).convert_alpha()
        return img
    except Exception:
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill(col)
        return surf

def safe_load_sound(name):
    path = os.path.join(BASE_DIR, name)
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        class _D:
            def play(self, *a, **k): pass
        return _D()

# ---------------- ASSETS (filenames from your folder) ----------------
backgrounds = {
    1: pygame.transform.scale(safe_load_image("background_forest.jpg"), (WIDTH, HEIGHT)),
    2: pygame.transform.scale(safe_load_image("background_desert.jpg"), (WIDTH, HEIGHT)),
    3: pygame.transform.scale(safe_load_image("background_space.jpg"), (WIDTH, HEIGHT)),
}
menu_background = pygame.transform.scale(safe_load_image("menu_background.jpg"), (WIDTH, HEIGHT))

apple_img = safe_load_image("apple.png")
banana_img = safe_load_image("banana.png")
berry_img = safe_load_image("berry.png")
golden_img = safe_load_image("golden_apple.png")
rock_img = pygame.transform.scale(safe_load_image("rock.png"), (30,30))
shield_img = pygame.transform.scale(safe_load_image("shield.png"), (25,25))
slow_img = pygame.transform.scale(safe_load_image("slow.png"), (25,25))

chomp_sound = safe_load_sound("chomp.wav")
crash_sound = safe_load_sound("crash.wav")
levelup_sound = safe_load_sound("levelup.wav")

# FRUITS: (image, display_size, points)
FRUITS = [
    (apple_img, 20, 10),
    (banana_img, 25, 20),
    (berry_img, 18, 30),
    (golden_img, 30, 50),
]

# ---------------- HELPERS ----------------
def read_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_highscore(v):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(int(v)))
    except:
        pass

def blit_centered_text(text, font, color, y):
    surf = font.render(text, True, color)
    screen.blit(surf, (WIDTH//2 - surf.get_width()//2, y))

def spawn_fruit_or_power():
    # 12% chance for powerup (shield or slow), else a fruit
    if random.random() < 0.12:
        if random.random() < 0.5:
            size = 25
            fx = random.randint(0, (WIDTH - size)//SNAKE_BLOCK) * SNAKE_BLOCK
            fy = random.randint(0, (HEIGHT - size)//SNAKE_BLOCK) * SNAKE_BLOCK
            return ("shield", fx, fy, shield_img, size, 0, "shield")
        else:
            size = 25
            fx = random.randint(0, (WIDTH - size)//SNAKE_BLOCK) * SNAKE_BLOCK
            fy = random.randint(0, (HEIGHT - size)//SNAKE_BLOCK) * SNAKE_BLOCK
            return ("slow", fx, fy, slow_img, size, 0, "slow")
    else:
        img, size, pts = random.choice(FRUITS)
        fx = random.randint(0, (WIDTH - size)//SNAKE_BLOCK) * SNAKE_BLOCK
        fy = random.randint(0, (HEIGHT - size)//SNAKE_BLOCK) * SNAKE_BLOCK
        return ("fruit", fx, fy, img, size, pts, None)

def spawn_obstacles(n, avoid_positions=None):
    avoid_positions = avoid_positions or []
    obs = []
    tries = 0
    while len(obs) < n and tries < n*15:
        ox = random.randint(0, (WIDTH-30)//SNAKE_BLOCK) * SNAKE_BLOCK
        oy = random.randint(0, (HEIGHT-30)//SNAKE_BLOCK) * SNAKE_BLOCK
        ok = True
        for (ax,ay) in avoid_positions:
            if abs(ax-ox) < SNAKE_BLOCK*2 and abs(ay-oy) < SNAKE_BLOCK*2:
                ok = False; break
        if ok and (ox,oy) not in obs:
            obs.append((ox,oy))
        tries += 1
    return obs

# ---------------- PARTICLES ----------------
particles = []
def spawn_particles(x, y, color=(255,215,0)):
    for _ in range(14):
        particles.append({
            "x": x + SNAKE_BLOCK//2,
            "y": y + SNAKE_BLOCK//2,
            "dx": random.uniform(-2.5, 2.5),
            "dy": random.uniform(-2.5, 2.5),
            "life": random.randint(18,36),
            "size": random.randint(2,5),
            "color": color
        })

def update_particles():
    for p in particles[:]:
        p["x"] += p["dx"]; p["y"] += p["dy"]; p["life"] -= 1
        alpha = int(255 * (p["life"]/36)) if p["life"]>0 else 0
        surf = pygame.Surface((p["size"]*2, p["size"]*2), pygame.SRCALPHA)
        c = p["color"] + (alpha,)
        pygame.draw.circle(surf, c, (p["size"], p["size"]), p["size"])
        screen.blit(surf, (int(p["x"]-p["size"]), int(p["y"]-p["size"])))
        if p["life"] <= 0:
            particles.remove(p)

# ---------------- SNAKE DRAW (real snake look) ----------------
def draw_snake(snake_list, head_dir=(0,0), shield_strength=0):
    length = len(snake_list)
    for i, (sx, sy) in enumerate(snake_list):
        cx, cy = sx + SNAKE_BLOCK//2, sy + SNAKE_BLOCK//2
        ratio = i / max(1, length-1)

        # Gradient color: bright green at head, darker green tail
        g = int(200 - ratio*120)
        r = int(30 + ratio*50)
        b = int(30 + ratio*20)
        color = (r, g, b)

        # Make snake body slightly wavy (sin curve)
        wave_offset = int(3 * math.sin(pygame.time.get_ticks()/150 + i))
        if i != length - 1:  # body segment
            pygame.draw.circle(screen, color, (cx+wave_offset, cy), SNAKE_BLOCK//2)
        else:
            # HEAD (bigger, with eyes & tongue)
            pygame.draw.circle(screen, color, (cx, cy), SNAKE_BLOCK//2 + 2)

            # Eyes based on head_dir
            eye_offset = 6
            if head_dir[0] != 0:   # moving horizontally
                eye_y = cy - 4
                pygame.draw.circle(screen, WHITE, (cx - eye_offset, eye_y), 3)
                pygame.draw.circle(screen, WHITE, (cx + eye_offset, eye_y), 3)
                pygame.draw.circle(screen, BLACK, (cx - eye_offset, eye_y), 1)
                pygame.draw.circle(screen, BLACK, (cx + eye_offset, eye_y), 1)
            else:   # moving vertically
                eye_x = cx - 4
                pygame.draw.circle(screen, WHITE, (eye_x, cy - eye_offset), 3)
                pygame.draw.circle(screen, WHITE, (eye_x+8, cy - eye_offset), 3)
                pygame.draw.circle(screen, BLACK, (eye_x, cy - eye_offset), 1)
                pygame.draw.circle(screen, BLACK, (eye_x+8, cy - eye_offset), 1)

            # Tongue (red fork)
            if head_dir != (0,0):
                tongue_len = 12
                tx, ty = cx + head_dir[0]*tongue_len, cy + head_dir[1]*tongue_len
                pygame.draw.line(screen, (220,30,30), (cx, cy), (tx, ty), 2)
                # fork
                if head_dir[0] != 0:  # left/right fork
                    pygame.draw.line(screen, (220,30,30), (tx, ty), (tx, ty-4), 2)
                    pygame.draw.line(screen, (220,30,30), (tx, ty), (tx, ty+4), 2)
                else:  # up/down fork
                    pygame.draw.line(screen, (220,30,30), (tx, ty), (tx-4, ty), 2)
                    pygame.draw.line(screen, (220,30,30), (tx, ty), (tx+4, ty), 2)

            # Shield bubble
            if shield_strength > 0:
                bubble = pygame.Surface((SNAKE_BLOCK*3, SNAKE_BLOCK*3), pygame.SRCALPHA)
                pygame.draw.circle(bubble, (0,200,255,90),
                                   (SNAKE_BLOCK*3//2, SNAKE_BLOCK*3//2),
                                   SNAKE_BLOCK+8)
                screen.blit(bubble, (sx - SNAKE_BLOCK, sy - SNAKE_BLOCK))

# ---------------- MENUS / SCREENS ----------------
sound_enabled = True

def main_menu():
    while True:
        screen.blit(menu_background, (0,0))
        blit_centered_text("SNAKE GAME", TITLE_FONT, RED, HEIGHT//6)
        blit_centered_text("ENTER - Start    I - Instructions    Q - Quit", UI_FONT, WHITE, HEIGHT//2)
        pygame.display.update()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN: return
                if ev.key == pygame.K_q: pygame.quit(); sys.exit()
                if ev.key == pygame.K_i: instructions()
                if ev.key == pygame.K_s: settings_menu()

def instructions():
    showing = True
    while showing:
        screen.fill((20,20,20))
        blit_centered_text("HOW TO PLAY", TITLE_FONT, RED, HEIGHT//8)
        lines = [
            "Arrow keys to move",
            "Eat fruits to score (different fruits = different points)",
            "Pick Shield to block one crash. Pick Slow to slow for 5s.",
            "Avoid rocks & walls. Levels at 100/200/300 points.",
            "P to Pause. During Game Over press C to restart or Q to quit.",
            "Press ESC to return."
        ]
        for i, l in enumerate(lines):
            screen.blit(UI_FONT.render(l, True, WHITE), (WIDTH//2 - 300//2, HEIGHT//3 + i*30))
        pygame.display.update()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                showing = False

def settings_menu():
    global sound_enabled
    waiting = True
    while waiting:
        screen.blit(menu_background, (0,0))
        blit_centered_text("SETTINGS", TITLE_FONT, YELLOW, HEIGHT//6)
        sound_text = UI_FONT.render(f"Sound: {'ON' if sound_enabled else 'OFF'}  (press M to toggle)", True, WHITE)
        back_text = UI_FONT.render("Press ESC to go back", True, WHITE)
        screen.blit(sound_text, (WIDTH//2 - sound_text.get_width()//2, HEIGHT//2))
        screen.blit(back_text, (WIDTH//2 - back_text.get_width()//2, HEIGHT//2 + 40))
        pygame.display.update()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: waiting = False
                if ev.key == pygame.K_m:
                    sound_enabled = not sound_enabled

def draw_hud(score, highscore, level):
    # semi-transparent black bar
    hud_bg = pygame.Surface((WIDTH, 60), pygame.SRCALPHA)
    hud_bg.fill((0, 0, 0, 120))
    screen.blit(hud_bg, (0, 0))

    # render score, highscore, level
    score_surf = SCORE_FONT.render(f"Score: {score}", True, (255, 215, 0))
    hs_surf = SCORE_FONT.render(f"High Score: {highscore}", True, (255, 215, 0))
    lvl_surf = SCORE_FONT.render(f"Level: {level}", True, (255, 215, 0))

    screen.blit(score_surf, (10, 10))
    screen.blit(hs_surf, (10, 30))
    screen.blit(lvl_surf, (WIDTH - lvl_surf.get_width() - 10, 10))

# ---------------- MAIN GAME LOOP ----------------
def game_loop():
    highscore = read_highscore()

    # local game state to avoid UnboundLocal issues
    snake_speed = float(INITIAL_SPEED)
    x = WIDTH//2; y = HEIGHT//2
    dx = 0; dy = 0
    snake = []
    snake_len = 1
    score = 0
    level = 1
    level_thresholds = [100,200,300]
    shield_strength = 0
    slow_end = 0.0

    # spawn initial item and obstacles (avoid starting near center)
    item_type, fx, fy, item_img, item_size, item_pts, item_effect = spawn_fruit_or_power()
    obstacles = spawn_obstacles(5, avoid_positions=[(WIDTH//2, HEIGHT//2)])

    paused = False
    game_close = False
    faded = False
    final_game_over_surf = None

    head_dir = (0,0)

    while True:
        # event loop
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if not game_close:
                    # prevent 180-degree turns
                    if ev.key == pygame.K_LEFT and dx == 0:
                        dx, dy = -SNAKE_BLOCK, 0
                        head_dir = (-1,0)
                    elif ev.key == pygame.K_RIGHT and dx == 0:
                        dx, dy = SNAKE_BLOCK, 0
                        head_dir = (1,0)
                    elif ev.key == pygame.K_UP and dy == 0:
                        dx, dy = 0, -SNAKE_BLOCK
                        head_dir = (0,-1)
                    elif ev.key == pygame.K_DOWN and dy == 0:
                        dx, dy = 0, SNAKE_BLOCK
                        head_dir = (0,1)
                    elif ev.key == pygame.K_p:
                        paused = not paused
                else:
                    if ev.key == pygame.K_c:
                        # restart: return to menu loop (menu will call game_loop again)
                        if score > highscore:
                            save_highscore(score)
                        return
                    if ev.key == pygame.K_q:
                        if score > highscore:
                            save_highscore(score)
                            pygame.mixer.music.stop()
                        pygame.quit(); sys.exit()

        # paused screen
        while paused:
            screen.blit(backgrounds.get(level, backgrounds[1]), (0,0))
            blit_centered_text("PAUSED", BIG_FONT, YELLOW, HEIGHT//3)
            blit_centered_text("Press P to resume", UI_FONT, WHITE, HEIGHT//2)
            pygame.display.update()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_p:
                    paused = False

        # If game over (death), show Game Over screen (fade-in once) and wait for C/Q
        if game_close:
            if not faded:
                # fade in GAME OVER once
                for alpha in range(0,256,6):
                    screen.blit(backgrounds.get(level, backgrounds[1]), (0,0))
                    surf = BIG_FONT.render("GAME OVER", True, RED)
                    surf.set_alpha(alpha)
                    screen.blit(surf, (WIDTH//2 - surf.get_width()//2, HEIGHT//4))
                    pygame.display.update()
                    pygame.time.delay(8)
                faded = True
                final_game_over_surf = BIG_FONT.render("GAME OVER", True, RED)

            screen.blit(backgrounds.get(level, backgrounds[1]), (0,0))
            screen.blit(final_game_over_surf, (WIDTH//2 - final_game_over_surf.get_width()//2, HEIGHT//4))
            fs = SCORE_FONT.render(f"Your Score: {score}", True, WHITE)
            hs = SCORE_FONT.render(f"High Score: {max(score, highscore)}", True, WHITE)
            screen.blit(fs, (WIDTH//2 - fs.get_width()//2, HEIGHT//2))
            screen.blit(hs, (WIDTH//2 - hs.get_width()//2, HEIGHT//2 + 40))
            screen.blit(UI_FONT.render("Press C to Play Again or Q to Quit", True, WHITE), (WIDTH//2 - 240//2, HEIGHT*3//4))
            pygame.display.update()
            # small event handling loop (top-level will handle actual keys)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            clock.tick(10)
            continue

        # NORMAL gameplay update
        x += dx; y += dy

        # boundary collision
        if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
            if shield_strength > 0:
                shield_strength = 0
                # clamp inside and reset movement
                x = max(0, min(WIDTH - SNAKE_BLOCK, x))
                y = max(0, min(HEIGHT - SNAKE_BLOCK, y))
                dx, dy = 0, 0
            else:
                if sound_enabled: crash_sound.play()
                game_close = True
                if score > highscore:
                    highscore = score
                    save_highscore(highscore)
                continue

        # draw background for level
        screen.blit(backgrounds.get(level, backgrounds[1]), (0,0))

        # obstacles
        for ox, oy in obstacles:
            screen.blit(rock_img, (ox, oy))
            if abs(x - ox) < SNAKE_BLOCK and abs(y - oy) < SNAKE_BLOCK:
                if shield_strength > 0:
                    shield_strength = 0
                    try: obstacles.remove((ox,oy))
                    except: pass
                else:
                    if sound_enabled: crash_sound.play()
                    game_close = True
                    if score > highscore:
                        highscore = score
                        save_highscore(highscore)
                    break

        if game_close:
            continue

        # draw current item (fruit or power)
        screen.blit(pygame.transform.scale(item_img, (item_size, item_size)), (fx, fy))

        # snake mechanics
        head = (x,y)
        snake.append(head)
        if len(snake) > snake_len:
            del snake[0]

        # self collision
        hit_self = False
        for seg in snake[:-1]:
            if seg == head:
                hit_self = True
                break
        if hit_self:
            if shield_strength > 0:
                shield_strength = 0
            else:
                if sound_enabled: crash_sound.play()
                game_close = True
                if score > highscore:
                    highscore = score
                    save_highscore(highscore)
                continue

        # draw snake (provide head_dir for eye orientation)
        draw_snake(snake, head_dir=head_dir, shield_strength=shield_strength)

        # draw UI
        score_surf = SCORE_FONT.render(f"Score: {score}", True, YELLOW)
        screen.blit(score_surf, (10,10))
        hs_surf = SCORE_FONT.render(f"High Score: {highscore}", True, YELLOW)
        screen.blit(hs_surf, (10,40))
        lvl_surf = SCORE_FONT.render(f"Level: {level}", True, YELLOW)
        screen.blit(lvl_surf, (WIDTH - lvl_surf.get_width() - 10, 10))

        # update and draw particles
        update_particles()

        pygame.display.update()

        # EATING / PICKUPS (we used exact-grid spawning, so equality is OK)
        if x == fx and y == fy:
            # powerups or fruit
            if item_effect == "shield":
                shield_strength = 1
            elif item_effect == "slow":
                slow_end = time.time() + 5.0
            else:
                snake_len += 1
                score += item_pts
                snake_speed += (item_pts / 40.0)
            # spawn particles & sound
            spawn_particles(x, y, color=(255,215,0))
            if sound_enabled: chomp_sound.play()
            # spawn next and maybe add obstacle
            item_type, fx, fy, item_img, item_size, item_pts, item_effect = spawn_fruit_or_power()
            if random.randint(1,3) == 1:
                obstacles.extend(spawn_obstacles(1, avoid_positions=[(x,y),(fx,fy)]))

        # level up at 100,200,300...
        if level <= len(level_thresholds) and score >= level_thresholds[level-1]:
            level += 1
            obstacles.extend(spawn_obstacles(2))
            if sound_enabled: levelup_sound.play()
            # show small level up message
            lvmsg = SCORE_FONT.render(f"Level {level}!", True, (255,215,0))
            screen.blit(lvmsg, (WIDTH//2 - lvmsg.get_width()//2, HEIGHT//2 - 40))
            pygame.display.update()
            pygame.time.delay(700)

        # FPS calculation (account for slow powerup)
        fps = max(FPS_MIN, int(round(snake_speed)))
        if slow_end > time.time():
            fps = max(5, int(round(snake_speed / 2.0)))
        clock.tick(fps)

# ---------------- RUN ----------------
if __name__ == "__main__":
    pygame.mixer.music.load(os.path.join(BASE_DIR, "background_music.mp3"))
pygame.mixer.music.play(-1)  # -1 means loop forever
while True:
        main_menu()
        game_loop()
