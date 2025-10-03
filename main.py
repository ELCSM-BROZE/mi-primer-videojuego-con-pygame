import pygame
import random
import sys

# =========================
# Configuración general
# =========================
WIDTH, HEIGHT = 1280, 720  # 720p
FPS = 60
TITLE = "Invacion en el espacio XD"

# Colores
NEGRO   = (10, 10, 16)
BLANCO  = (240, 240, 240)
VERDE   = (80, 220, 100)
ROJO    = (235, 80, 80)
AZUL    = (80, 180, 235)
AMARILLO= (250, 220, 90)
GRIS    = (70, 70, 80)
MORADO  = (160, 100, 220)

# =========================
# Parámetros de juego
# =========================
PLAYER_W, PLAYER_H = 70, 18
PLAYER_SPEED = 7
PLAYER_COOLDOWN_MS = 250   # tiempo entre disparos

BULLET_W, BULLET_H = 6, 16
BULLET_SPEED = 11

ENEMY_W, ENEMY_H = 46, 22
ENEMY_HGAP = 18
ENEMY_VGAP = 16
ENEMY_START_ROWS = 4
ENEMY_START_COLS = 10
ENEMY_START_SPEED_X = 2.0
ENEMY_STEP_DOWN = 18
ENEMY_FIRE_BASE_CHANCE = 0.0018  # probabilidad por frame (ajustable por nivel)
ENEMY_BULLET_SPEED = 6

MARGEN_LATERAL = 60
TOP_BAND = 80  # banda superior con HUD

START_LIVES = 3

pygame.init()
pygame.display.set_caption(TITLE)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Fuentes
try:
    font_title = pygame.font.SysFont("arial", 64, bold=True)
    font_ui    = pygame.font.SysFont("consolas", 24)
    font_mid   = pygame.font.SysFont("arial", 36, bold=True)
except:
    font_title = pygame.font.Font(None, 64)
    font_mid   = pygame.font.Font(None, 36)
    font_ui    = pygame.font.Font(None, 24)

# =========================
# Utilidades
# =========================
def draw_text(surface, text, font, color, center_pos):
    render = font.render(text, True, color)
    rect = render.get_rect(center=center_pos)
    surface.blit(render, rect)

def rect_in_bounds(rect):
    return (rect.right >= 0 and rect.left <= WIDTH and rect.bottom >= 0 and rect.top <= HEIGHT)

# =========================
# Clases de juego
# =========================
class Player:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH//2 - PLAYER_W//2, HEIGHT - 60, PLAYER_W, PLAYER_H)
        self.color = VERDE
        self.lives = START_LIVES
        self.last_shot = 0
        self.invulnerable_timer = 0  # ms
        self.flash = False

    def reset_pos(self):
        self.rect.centerx = WIDTH // 2

    def update(self, keys, dt):
        if keys[pygame.K_LEFT]:
            self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            self.rect.x += PLAYER_SPEED

        self.rect.x = max(MARGEN_LATERAL//2, min(self.rect.x, WIDTH - MARGEN_LATERAL//2 - self.rect.width))

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt
            # destello visual mientras es invulnerable
            self.flash = (pygame.time.get_ticks() // 120) % 2 == 0
        else:
            self.flash = False

    def can_shoot(self):
        return (pygame.time.get_ticks() - self.last_shot) >= PLAYER_COOLDOWN_MS

    def shoot(self, bullets):
        if self.can_shoot():
            bx = self.rect.centerx - BULLET_W // 2
            by = self.rect.top - BULLET_H
            bullets.append(pygame.Rect(bx, by, BULLET_W, BULLET_H))
            self.last_shot = pygame.time.get_ticks()

    def hit(self):
        if self.invulnerable_timer <= 0:
            self.lives -= 1
            self.invulnerable_timer = 1400  # ms de invulnerabilidad tras impacto
            return True
        return False

    def draw(self, surface):
        color = AMARILLO if self.flash else self.color
        pygame.draw.rect(surface, color, self.rect)

class Enemy:
    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, ENEMY_W, ENEMY_H)
        self.alive = True
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)

class EnemyGroup:
    def __init__(self):
        self.enemies = []
        self.dir = 1  # 1 derecha, -1 izquierda
        self.speed_x = ENEMY_START_SPEED_X
        self.step_down = ENEMY_STEP_DOWN
        self.bounds = pygame.Rect(0, 0, 0, 0)
        self.fire_chance = ENEMY_FIRE_BASE_CHANCE
        self.bullet_speed = ENEMY_BULLET_SPEED

    def spawn_wave(self, level):
        self.enemies.clear()
        # Aumentar dificultad: más filas/cols y más rápido con el nivel
        rows = ENEMY_START_ROWS + min(level - 1, 3)  # hasta +3 filas
        cols = ENEMY_START_COLS + min((level - 1) // 2, 4)  # hasta +4 cols
        # recalcular tamaño de rejilla
        total_w = cols * ENEMY_W + (cols - 1) * ENEMY_HGAP
        offset_x = max(MARGEN_LATERAL, (WIDTH - total_w)//2)

        start_y = TOP_BAND + 40
        for r in range(rows):
            for c in range(cols):
                x = offset_x + c * (ENEMY_W + ENEMY_HGAP)
                y = start_y + r * (ENEMY_H + ENEMY_VGAP)
                # color por fila para variar
                color = [AZUL, MORADO, ROJO, AMARILLO, VERDE][r % 5]
                self.enemies.append(Enemy(x, y, color))

        self.dir = 1
        base = ENEMY_START_SPEED_X
        self.speed_x = base + 0.55 * (level - 1)  # incrementa por nivel
        self.step_down = ENEMY_STEP_DOWN + 2 * (level - 1)
        self.fire_chance = min(ENEMY_FIRE_BASE_CHANCE + 0.0006 * (level - 1), 0.012)
        self.bullet_speed = ENEMY_BULLET_SPEED + 0.35 * (level - 1)
        self.recalc_bounds()

    def recalc_bounds(self):
        alive_rects = [e.rect for e in self.enemies if e.alive]
        if alive_rects:
            left = min(r.left for r in alive_rects)
            right = max(r.right for r in alive_rects)
            top = min(r.top for r in alive_rects)
            bottom = max(r.bottom for r in alive_rects)
            self.bounds = pygame.Rect(left, top, right - left, bottom - top)
        else:
            self.bounds = pygame.Rect(0, 0, 0, 0)

    def update(self):
        alive = [e for e in self.enemies if e.alive]
        if not alive:
            return "cleared"

        # mover horizontal
        for e in alive:
            e.rect.x += int(self.dir * self.speed_x)

        self.recalc_bounds()
        stepped_down = False

        # rebotar en bordes
        if self.bounds.left <= MARGEN_LATERAL or self.bounds.right >= WIDTH - MARGEN_LATERAL:
            self.dir *= -1
            for e in alive:
                e.rect.y += self.step_down
            stepped_down = True

        # si tocaron el HUD o la parte baja, señal
        if self.bounds.bottom >= HEIGHT - 60:
            return "reached_bottom"

        # pequeña aceleración a medida que quedan menos
        total = len(self.enemies)
        count_alive = len(alive)
        if count_alive > 0:
            factor = 1.0 + (1.0 - count_alive / total) * 0.8  # hasta +80%
            # limitar para no descontrolar
            factor = min(factor, 2.0)
        else:
            factor = 1.0
        # actualizar speed_x “suavemente”
        base_speed = self.speed_x
        self.speed_x = base_speed * (0.98) + (base_speed * factor) * (0.02)

        if stepped_down:
            return "stepped_down"

        return None

    def choose_shooters(self):
        """Elige enemigos que disparan (solo ‘los más bajos’ por columna)."""
        # Agrupar por columna aproximada
        columns = {}
        for e in self.enemies:
            if not e.alive:
                continue
            # discretizar por posición X
            key = e.rect.x // (ENEMY_W + ENEMY_HGAP)
            if key not in columns or e.rect.y > columns[key].rect.y:
                columns[key] = e
        return list(columns.values())

    def maybe_fire(self, enemy_bullets):
        # Probabilidad de disparo por frame (escala con nivel)
        shooters = self.choose_shooters()
        for s in shooters:
            if random.random() < self.fire_chance:
                bx = s.rect.centerx - BULLET_W // 2
                by = s.rect.bottom
                enemy_bullets.append(pygame.Rect(bx, by, BULLET_W, BULLET_H))

    def draw(self, surface):
        for e in self.enemies:
            if e.alive:
                e.draw(surface)

# =========================
# Juego
# =========================
class Game:
    def __init__(self):
        self.state = "menu"  # "menu", "playing", "gameover"
        self.player = Player()
        self.level = 1
        self.score = 0
        self.bullets = []       # balas del jugador (Rects)
        self.enemy_bullets = [] # balas de enemigos (Rects)
        self.enemies = EnemyGroup()
        self.starfield = self.generate_stars()
        self.reset_game(full=True)

    def generate_stars(self, count=150):
        # Solo rectángulos pequeños para “estrellas”
        stars = []
        for _ in range(count):
            x = random.randint(0, WIDTH-1)
            y = random.randint(0, HEIGHT-1)
            w = random.randint(1, 3)
            h = w
            col = (random.randint(150, 255),) * 3
            stars.append((pygame.Rect(x, y, w, h), col))
        return stars

    def reset_game(self, full=False):
        if full:
            self.level = 1
            self.score = 0
            self.player = Player()
        self.player.reset_pos()
        self.bullets.clear()
        self.enemy_bullets.clear()
        self.enemies.spawn_wave(self.level)

    def next_level(self):
        self.level += 1
        self.reset_game(full=False)

    def handle_menu(self, events):
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and (e.key == pygame.K_RETURN or e.key == pygame.K_SPACE):
                self.reset_game(full=True)
                self.state = "playing"

    def handle_gameover(self, events):
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and (e.key == pygame.K_RETURN or e.key == pygame.K_SPACE):
                self.state = "menu"

    def update_playing(self, dt):
        keys = pygame.key.get_pressed()

        # Movimiento y disparo
        self.player.update(keys, dt)
        if keys[pygame.K_UP]:
            self.player.shoot(self.bullets)

        # Actualizar balas jugador
        for b in self.bullets:
            b.y -= BULLET_SPEED
        self.bullets = [b for b in self.bullets if rect_in_bounds(b)]

        # Enemigos
        result = self.enemies.update()
        if result == "reached_bottom":
            # castigo fuerte: perder vida
            life_lost = self.player.hit()
            if self.player.lives <= 0:
                self.state = "gameover"
            else:
                # replegar un poco la horda hacia arriba para evitar bucles
                for e in self.enemies.enemies:
                    if e.alive:
                        e.rect.y -= 80
        elif result == "cleared":
            self.next_level()

        # Disparos enemigos
        self.enemies.maybe_fire(self.enemy_bullets)
        for eb in self.enemy_bullets:
            eb.y += int(self.enemies.bullet_speed)
        self.enemy_bullets = [b for b in self.enemy_bullets if rect_in_bounds(b)]

        # Colisiones: balas jugador vs enemigos
        for b in self.bullets[:]:
            hit_any = False
            for e in self.enemies.enemies:
                if e.alive and b.colliderect(e.rect):
                    e.alive = False
                    hit_any = True
                    # puntuación: base 100 + bonus por nivel
                    self.score += 100 + (self.level - 1) * 20
                    break
            if hit_any:
                self.bullets.remove(b)

        # Colisiones: balas enemigas vs jugador
        for eb in self.enemy_bullets[:]:
            if eb.colliderect(self.player.rect):
                if self.player.hit():
                    # limpieza parcial de balas al ser dañado
                    self.enemy_bullets = [b for b in self.enemy_bullets if b.y < self.player.rect.y - 40]
                try:
                    self.enemy_bullets.remove(eb)
                except ValueError:
                    pass
                if self.player.lives <= 0:
                    self.state = "gameover"
                break

    def draw_hud(self, surface):
        # Fondo HUD superior
        hud_rect = pygame.Rect(0, 0, WIDTH, TOP_BAND)
        pygame.draw.rect(surface, GRIS, hud_rect)

        # Título y nivel
        draw_text(surface, f"{TITLE}", font_ui, BLANCO, (160, TOP_BAND//2))
        draw_text(surface, f"Nivel: {self.level}", font_ui, BLANCO, (WIDTH//2, TOP_BAND//2))
        draw_text(surface, f"Puntos: {self.score}", font_ui, AMARILLO, (WIDTH - 160, TOP_BAND//2))

        # Vidas como rectángulos
        start_x = 16
        for i in range(self.player.lives):
            life_rect = pygame.Rect(start_x + i*22, TOP_BAND - 26, 18, 10)
            pygame.draw.rect(surface, ROJO, life_rect)

    def draw_background(self, surface):
        surface.fill(NEGRO)
        # estrellas (rectángulos pequeños)
        for r, col in self.starfield:
            pygame.draw.rect(surface, col, r)

    def draw_menu(self, surface):
        self.draw_background(surface)
        draw_text(surface, TITLE, font_title, AMARILLO, (WIDTH//2, HEIGHT//2 - 80))
        draw_text(surface, "Flechas IZQ/DER para moverte", font_mid, BLANCO, (WIDTH//2, HEIGHT//2))
        draw_text(surface, "Flecha ARRIBA para disparar", font_mid, BLANCO, (WIDTH//2, HEIGHT//2 + 46))
        draw_text(surface, "Presiona [ENTER] para comenzar", font_mid, MORADO, (WIDTH//2, HEIGHT//2 + 120))

    def draw_gameover(self, surface):
        self.draw_background(surface)
        draw_text(surface, "GAME OVER", font_title, ROJO, (WIDTH//2, HEIGHT//2 - 40))
        draw_text(surface, f"Puntuación final: {self.score}", font_mid, AMARILLO, (WIDTH//2, HEIGHT//2 + 20))
        draw_text(surface, "Presiona [ENTER] para volver al menú", font_mid, BLANCO, (WIDTH//2, HEIGHT//2 + 80))

    def draw_playing(self, surface):
        self.draw_background(surface)
        self.draw_hud(surface)

        # Zona de juego (línea separadora)
        pygame.draw.rect(surface, (30, 30, 40), (0, TOP_BAND, WIDTH, 2))

        # Enemigos
        self.enemies.draw(surface)

        # Player
        self.player.draw(surface)

        # Balas
        for b in self.bullets:
            pygame.draw.rect(surface, BLANCO, b)
        for eb in self.enemy_bullets:
            pygame.draw.rect(surface, ROJO, eb)

    def game_loop(self):
        while True:
            dt = clock.tick(FPS)
            events = pygame.event.get()

            if self.state == "menu":
                self.handle_menu(events)
                self.draw_menu(screen)

            elif self.state == "playing":
                for e in events:
                    if e.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                self.update_playing(dt)
                self.draw_playing(screen)

            elif self.state == "gameover":
                self.handle_gameover(events)
                self.draw_gameover(screen)

            pygame.display.flip()

# =========================
# Main
# =========================
if __name__ == "__main__":
    Game().game_loop()