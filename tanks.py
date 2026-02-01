import arcade
import random
import math
import json
import os
from enum import Enum

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Танчики"
TANK_SPEED = 4
BULLET_SPEED = 8
ENEMY_SPEED = 1.5
ENEMY_SHOOT_INTERVAL = 90


class GameState(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"


class PowerUpType(Enum):
    HEALTH = "health"
    SPEED = "speed"
    DAMAGE = "damage"
    RAPID_FIRE = "rapid_fire"


class Explosion(arcade.Sprite):
    def __init__(self, center_x, center_y, enemy_type=None):
        super().__init__()
        self.textures = []
        # Разные цвета взрывов для разных типов врагов
        if enemy_type == "fast":
            # Ярко-зеленые взрывы для быстрых врагов
            colors = [
                (0, 255, 0),  # Ярко-зеленый
                (144, 238, 144),  # Светло-зеленый
                (255, 255, 255)  # Белый
            ]
        elif enemy_type == "heavy":
            # Фиолетовые взрывы для тяжелых врагов
            colors = [
                (128, 0, 128),  # Пурпурный
                (216, 191, 216),  # Бледно-фиолетовый
                (255, 255, 255)  # Белый
            ]
        else:
            # Оранжевые взрывы для обычных врагов
            colors = [
                (255, 165, 0),  # Оранжевый
                (255, 215, 0),  # Золотой
                (255, 255, 255)  # Белый
            ]

        for i in range(5):
            radius = 15 + i * 5
            color = colors[min(i // 2, len(colors) - 1)]
            texture = arcade.make_circle_texture(radius * 2, color)
            self.textures.append(texture)
        self.texture = self.textures[0]
        self.current_texture = 0
        self.lifetime = 15
        self.center_x = center_x
        self.center_y = center_y

    def update(self, delta_time=1 / 60):
        self.lifetime -= 1
        if self.lifetime > 0:
            frame = (self.lifetime // 3) % len(self.textures)
            self.texture = self.textures[frame]
        else:
            self.remove_from_sprite_lists()


class Particle(arcade.SpriteCircle):
    def __init__(self, radius, color):
        super().__init__(radius, color)
        self.lifetime = 20
        self.velocity_x = random.uniform(-1, 1)
        self.velocity_y = random.uniform(-1, 1)

    def update(self, delta_time=1 / 60):
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.remove_from_sprite_lists()
        self.center_x += self.velocity_x
        self.center_y += self.velocity_y


class ParticleSystem:
    def __init__(self):
        self.particles = arcade.SpriteList()

    def create_trail(self, x, y, color):
        for _ in range(3):
            particle = Particle(3, color)
            particle.center_x = x + random.uniform(-5, 5)
            particle.center_y = y + random.uniform(-5, 5)
            self.particles.append(particle)

    def update(self):
        self.particles.update()

    def draw(self):
        self.particles.draw()


class Obstacle(arcade.SpriteSolidColor):
    def __init__(self, width, height, color):
        super().__init__(width, height, color)
        self.is_destructible = random.choice([True, False])
        self.health = 2 if self.is_destructible else 999


class Bullet(arcade.SpriteCircle):
    def __init__(self, radius, color, damage=1):
        super().__init__(radius, color)
        self.damage = damage

    def update(self, delta_time=1 / 60):
        self.center_x += self.change_x
        self.center_y += self.change_y
        if (self.center_x < 0 or self.center_x > SCREEN_WIDTH or
                self.center_y < 0 or self.center_y > SCREEN_HEIGHT):
            self.remove_from_sprite_lists()


class Tank(arcade.Sprite):
    def __init__(self, sprite_file, scale=1.0, health=3):
        super().__init__(sprite_file, scale)
        self.direction = "UP"
        self.health = health
        self.max_health = health
        self.is_alive = True
        self.shoot_cooldown = 0
        self.shoot_delay = 15
        self.speed_multiplier = 1.0
        self.damage_multiplier = 1.0
        self.textures_by_direction = {}
        self.load_directional_textures()

    def load_directional_textures(self):
        """Загружаем текстуры для разных направлений"""
        # Это заглушка, переопределим в дочерних классах
        pass

    def update_direction_texture(self):
        """Обновляем текстуру в зависимости от направления"""
        if self.direction in self.textures_by_direction:
            self.texture = self.textures_by_direction[self.direction]

        # Поворачиваем спрайт в зависимости от направления
        if self.direction == "UP":
            self.angle = 0
        elif self.direction == "RIGHT":
            self.angle = 90
        elif self.direction == "DOWN":
            self.angle = 180
        elif self.direction == "LEFT":
            self.angle = 270

    def can_shoot(self):
        return self.shoot_cooldown <= 0

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.is_alive = False

    def update(self):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        self.update_direction_texture()

    def check_obstacle_collision(self, new_x, new_y, obstacle_list):
        """Проверка столкновения с препятствиями"""
        old_x = self.center_x
        old_y = self.center_y
        self.center_x = new_x
        self.center_y = new_y
        collision = arcade.check_for_collision_with_list(self, obstacle_list)
        self.center_x = old_x
        self.center_y = old_y
        return collision

    def move_with_collision(self, dx, dy, obstacle_list):
        """Движение с проверкой столкновений"""
        # Проверяем по X
        new_x = self.center_x + dx
        if not self.check_obstacle_collision(new_x, self.center_y, obstacle_list):
            self.center_x = new_x
        else:
            # Пробуем двигаться на меньшее расстояние
            step = 1 if dx > 0 else -1
            for i in range(1, int(abs(dx)) + 1):
                test_x = self.center_x + step
                if not self.check_obstacle_collision(test_x, self.center_y, obstacle_list):
                    self.center_x = test_x
                else:
                    break

        # Проверяем по Y
        new_y = self.center_y + dy
        if not self.check_obstacle_collision(self.center_x, new_y, obstacle_list):
            self.center_y = new_y
        else:
            # Пробуем двигаться на меньшее расстояние
            step = 1 if dy > 0 else -1
            for i in range(1, int(abs(dy)) + 1):
                test_y = self.center_y + step
                if not self.check_obstacle_collision(self.center_x, test_y, obstacle_list):
                    self.center_y = test_y
                else:
                    break

    def shoot(self, bullet_list, bullet_color, bullet_radius=8):
        if self.can_shoot():
            damage = int(1 * self.damage_multiplier)
            bullet = Bullet(bullet_radius, bullet_color, damage)
            bullet.center_x = self.center_x
            bullet.center_y = self.center_y

            if self.direction == "UP":
                bullet.change_x = 0
                bullet.change_y = BULLET_SPEED
            elif self.direction == "DOWN":
                bullet.change_x = 0
                bullet.change_y = -BULLET_SPEED
            elif self.direction == "LEFT":
                bullet.change_x = -BULLET_SPEED
                bullet.change_y = 0
            elif self.direction == "RIGHT":
                bullet.change_x = BULLET_SPEED
                bullet.change_y = 0

            bullet_list.append(bullet)
            self.shoot_cooldown = self.shoot_delay
            return True
        return False

    def draw_health_bar(self):
        health_width = self.width
        health_height = 6
        health_ratio = self.health / self.max_health

        left = self.center_x - health_width / 2
        right = self.center_x + health_width / 2
        bottom = self.center_y + self.height / 2 + 5
        top = bottom + health_height

        arcade.draw_lrbt_rectangle_filled(
            left, right, bottom, top, arcade.color.BLACK
        )

        if health_ratio > 0:
            right_health = left + health_width * health_ratio
            arcade.draw_lrbt_rectangle_filled(
                left, right_health, bottom, top, arcade.color.LIME_GREEN
            )


class PlayerTank(Tank):
    def __init__(self):
        # Используем спрайт для игрока
        sprite_path = os.path.join("images", "player_tank.png")
        if os.path.exists(sprite_path):
            super().__init__(sprite_path, scale=0.5, health=5)
        else:
            # Если файла нет, создаем временный спрайт
            super().__init__(None, scale=1.0, health=5)
            self.texture = arcade.make_soft_square_texture(40, (0, 255, 255), 255, 255)
            self.textures_by_direction = {
                "UP": self.texture,
                "DOWN": self.texture,
                "LEFT": self.texture,
                "RIGHT": self.texture
            }
        self.textures_by_direction = {
            "UP": self.texture,
            "DOWN": self.texture,
            "LEFT": self.texture,
            "RIGHT": self.texture
        }


class EnemyTank(Tank):
    def __init__(self, player_tank, enemy_type="normal"):
        self.enemy_type = enemy_type

        if enemy_type == "normal":
            sprite_path = os.path.join("images", "enemy_normal.png")
            scale = 0.5
            health = 2
            self.speed_multiplier = 1.0
        elif enemy_type == "fast":
            sprite_path = os.path.join("images", "enemy_fast.png")
            scale = 0.45
            health = 1
            self.speed_multiplier = 2.0
        elif enemy_type == "heavy":
            sprite_path = os.path.join("images", "enemy_heavy.png")
            scale = 0.6
            health = 5
            self.speed_multiplier = 0.5
            self.damage_multiplier = 2.0

        if os.path.exists(sprite_path):
            super().__init__(sprite_path, scale=scale, health=health)
        else:
            # Если файла нет, создаем временные спрайты
            super().__init__(None, scale=1.0, health=health)
            if enemy_type == "normal":
                color = (255, 140, 0)  # Темно-оранжевый
                size = 40
            elif enemy_type == "fast":
                color = (50, 205, 50)  # Салатовый
                size = 35
            else:  # heavy
                color = (138, 43, 226)  # Фиолетовый
                size = 50
            self.texture = arcade.make_soft_square_texture(size, color, 255, 255)

        self.player = player_tank
        self.shoot_timer = random.randint(30, ENEMY_SHOOT_INTERVAL)
        self.direction = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
        self.change_direction_timer = random.randint(30, 90)
        self.obstacle_list = None

        self.textures_by_direction = {
            "UP": self.texture,
            "DOWN": self.texture,
            "LEFT": self.texture,
            "RIGHT": self.texture
        }

    def update(self):
        super().update()
        if not self.is_alive:
            return

        original_direction = self.direction
        self.change_direction_timer -= 1
        if self.change_direction_timer <= 0:
            self.direction = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
            self.change_direction_timer = random.randint(30, 90)

        speed = ENEMY_SPEED * self.speed_multiplier
        dx, dy = 0, 0

        if self.direction == "UP":
            dy = speed
        elif self.direction == "DOWN":
            dy = -speed
        elif self.direction == "LEFT":
            dx = -speed
        elif self.direction == "RIGHT":
            dx = speed

        if self.obstacle_list:
            self.move_with_collision(dx, dy, self.obstacle_list)
        else:
            self.center_x += dx
            self.center_y += dy

        self.center_x = max(30, min(SCREEN_WIDTH - 30, self.center_x))
        self.center_y = max(30, min(SCREEN_HEIGHT - 30, self.center_y))

        self.shoot_timer -= 1
        if self.shoot_timer <= 0 and self.player.is_alive:
            dx_to_player = self.player.center_x - self.center_x
            dy_to_player = self.player.center_y - self.center_y

            if abs(dx_to_player) > abs(dy_to_player):
                self.direction = "RIGHT" if dx_to_player > 0 else "LEFT"
            else:
                self.direction = "UP" if dy_to_player > 0 else "DOWN"

            # Определяем цвет пуль в зависимости от типа врага
            if self.enemy_type == "normal":
                bullet_color = (255, 140, 0)  # Оранжевый
                bullet_size = 8
            elif self.enemy_type == "fast":
                bullet_color = (0, 255, 0)  # Зеленый
                bullet_size = 6
            else:  # heavy
                bullet_color = (255, 0, 255)  # Фиолетовый
                bullet_size = 12

            super().shoot(self.enemy_bullet_list, bullet_color, bullet_size)

            if self.enemy_type == "fast":
                self.shoot_timer = ENEMY_SHOOT_INTERVAL // 2
            elif self.enemy_type == "heavy":
                self.shoot_timer = ENEMY_SHOOT_INTERVAL * 2
            else:
                self.shoot_timer = ENEMY_SHOOT_INTERVAL

            self.direction = original_direction


class PowerUp(arcade.SpriteCircle):
    def __init__(self, powerup_type):
        self.type = powerup_type
        colors = {
            PowerUpType.HEALTH: arcade.color.LIME_GREEN,  # Ярко-зеленый
            PowerUpType.SPEED: arcade.color.SKY_BLUE,  # Небесно-голубой
            PowerUpType.DAMAGE: arcade.color.RED_ORANGE,  # Красно-оранжевый
            PowerUpType.RAPID_FIRE: arcade.color.GOLD  # Золотой
        }
        super().__init__(20, colors[powerup_type])
        self.lifetime = 300

    def update(self, delta_time=1 / 60):
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.remove_from_sprite_lists()


class TankGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.player_list = None
        self.enemy_list = None
        self.bullet_list = None
        self.enemy_bullet_list = None
        self.obstacle_list = None
        self.explosion_list = None
        self.powerup_list = None
        self.particle_system = None
        self.player_bullet_color = (255, 215, 0)  # Золотой
        self.player = None
        self.score = 0
        self.high_score = 0
        self.wave = 1
        self.enemies_per_wave = 3
        self.enemies_to_spawn = 0
        self.game_state = GameState.MENU
        self.left = False
        self.right = False
        self.up = False
        self.down = False
        self.space_pressed = False
        self.can_shoot = True
        self.mouse_x = 0
        self.mouse_y = 0
        self.powerup_timer = 0
        self.load_high_score()
        # Темный фон для контраста с яркими цветами
        arcade.set_background_color((30, 30, 30))

        # Создаем папку для спрайтов если её нет
        if not os.path.exists("images"):
            os.makedirs("images")
            self.create_default_sprites()

        self.setup()

    def create_default_sprites(self):
        """Создаем простые спрайты если файлов нет"""
        import pygame

        # Спрайт игрока (синий танк)
        size = 64
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surface, (0, 200, 255), (10, 10, 44, 44), border_radius=5)
        pygame.draw.rect(surface, (0, 150, 220), (22, 40, 20, 20))
        pygame.draw.rect(surface, (0, 100, 180), (15, 15, 34, 30), border_radius=3)
        arcade.save_png(arcade.pyglet_to_arcade_texture(surface), "images/player_tank.png")

        # Обычный враг (оранжевый)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surface, (255, 140, 0), (10, 10, 44, 44), border_radius=5)
        pygame.draw.rect(surface, (220, 100, 0), (22, 40, 20, 20))
        pygame.draw.rect(surface, (200, 80, 0), (15, 15, 34, 30), border_radius=3)
        arcade.save_png(arcade.pyglet_to_arcade_texture(surface), "images/enemy_normal.png")

        # Быстрый враг (зеленый)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surface, (50, 205, 50), (8, 8, 48, 48), border_radius=5)
        pygame.draw.rect(surface, (30, 180, 30), (20, 38, 24, 24))
        pygame.draw.rect(surface, (20, 160, 20), (13, 13, 38, 34), border_radius=3)
        arcade.save_png(arcade.pyglet_to_arcade_texture(surface), "images/enemy_fast.png")

        # Тяжелый враг (фиолетовый)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surface, (138, 43, 226), (5, 5, 54, 54), border_radius=7)
        pygame.draw.rect(surface, (100, 20, 200), (24, 44, 16, 16))
        pygame.draw.rect(surface, (80, 10, 180), (10, 10, 44, 40), border_radius=5)
        arcade.save_png(arcade.pyglet_to_arcade_texture(surface), "images/enemy_heavy.png")

        pygame.quit()

    def load_high_score(self):
        try:
            with open("highscore.json", "r") as f:
                data = json.load(f)
                self.high_score = data.get("high_score", 0)
        except:
            self.high_score = 0

    def save_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
            with open("highscore.json", "w") as f:
                json.dump({"high_score": self.high_score}, f)

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.enemy_bullet_list = arcade.SpriteList()
        self.obstacle_list = arcade.SpriteList()
        self.explosion_list = arcade.SpriteList()
        self.powerup_list = arcade.SpriteList()
        self.particle_system = ParticleSystem()

        self.player = PlayerTank()  # Игрок с спрайтом
        self.player.center_x = SCREEN_WIDTH // 2
        self.player.center_y = 100
        self.player_list.append(self.player)

        self.score = 0
        self.wave = 1
        self.enemies_to_spawn = self.enemies_per_wave + self.wave
        self.create_obstacles()
        self.spawn_wave()

    def create_obstacles(self):
        # НЕРАЗРУШАЕМЫЕ ПРЕПЯТСТВИЯ - стальные серые
        for x in range(50, SCREEN_WIDTH - 50, 60):
            for y in [50, SCREEN_HEIGHT - 50]:
                obstacle = Obstacle(60, 60, (169, 169, 169))  # Стальной серый
                obstacle.center_x = x
                obstacle.center_y = y
                obstacle.is_destructible = False
                self.obstacle_list.append(obstacle)

        for y in range(110, SCREEN_HEIGHT - 110, 60):
            for x in [50, SCREEN_WIDTH - 50]:
                obstacle = Obstacle(60, 60, (169, 169, 169))  # Стальной серый
                obstacle.center_x = x
                obstacle.center_y = y
                obstacle.is_destructible = False
                self.obstacle_list.append(obstacle)

        # РАЗРУШАЕМЫЕ ПРЕПЯТСТВИЯ - кирпичный красный
        for _ in range(8):
            obstacle = Obstacle(60, 60, (178, 34, 34))  # Кирпично-красный
            obstacle.is_destructible = True
            while True:
                x = random.randint(100, SCREEN_WIDTH - 100)
                y = random.randint(150, SCREEN_HEIGHT - 150)
                if (abs(x - self.player.center_x) > 100 and
                        abs(y - self.player.center_y) > 100):
                    break
            obstacle.center_x = x
            obstacle.center_y = y
            self.obstacle_list.append(obstacle)

    def spawn_enemy(self):
        enemy_type = random.choices(
            ["normal", "fast", "heavy"],
            weights=[0.6, 0.25, 0.15],
            k=1
        )[0]

        enemy = EnemyTank(self.player, enemy_type)

        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            enemy.center_x = random.randint(100, SCREEN_WIDTH - 100)
            enemy.center_y = SCREEN_HEIGHT - 100
            enemy.direction = "DOWN"
        elif side == "bottom":
            enemy.center_x = random.randint(100, SCREEN_WIDTH - 100)
            enemy.center_y = 100
            enemy.direction = "UP"
        elif side == "left":
            enemy.center_x = 100
            enemy.center_y = random.randint(150, SCREEN_HEIGHT - 150)
            enemy.direction = "RIGHT"
        else:
            enemy.center_x = SCREEN_WIDTH - 100
            enemy.center_y = random.randint(150, SCREEN_HEIGHT - 150)
            enemy.direction = "LEFT"

        enemy.enemy_bullet_list = self.enemy_bullet_list
        enemy.obstacle_list = self.obstacle_list
        self.enemy_list.append(enemy)

    def spawn_wave(self):
        self.wave += 1
        self.enemies_to_spawn = self.enemies_per_wave + self.wave
        for _ in range(self.enemies_to_spawn):
            self.spawn_enemy()

    def spawn_powerup(self, x, y):
        powerup_type = random.choice(list(PowerUpType))
        powerup = PowerUp(powerup_type)
        powerup.center_x = x
        powerup.center_y = y
        self.powerup_list.append(powerup)

    def apply_powerup(self, powerup):
        if powerup.type == PowerUpType.HEALTH:
            self.player.health = min(
                self.player.max_health, self.player.health + 2
            )
        elif powerup.type == PowerUpType.SPEED:
            self.player.speed_multiplier = 1.5
            arcade.schedule(self.reset_speed, 10.0)
        elif powerup.type == PowerUpType.DAMAGE:
            self.player.damage_multiplier = 2.0
            arcade.schedule(self.reset_damage, 15.0)
        elif powerup.type == PowerUpType.RAPID_FIRE:
            self.player.shoot_delay = 5
            arcade.schedule(self.reset_fire_rate, 10.0)

    def reset_speed(self, delta_time):
        self.player.speed_multiplier = 1.0

    def reset_damage(self, delta_time):
        self.player.damage_multiplier = 1.0

    def reset_fire_rate(self, delta_time):
        self.player.shoot_delay = 15

    def on_draw(self):
        self.clear()
        self.obstacle_list.draw()
        self.powerup_list.draw()
        self.player_list.draw()
        self.enemy_list.draw()
        self.bullet_list.draw()
        self.enemy_bullet_list.draw()
        self.explosion_list.draw()
        self.particle_system.draw()

        for enemy in self.enemy_list:
            enemy.draw_health_bar()

        if self.player.is_alive:
            self.player.draw_health_bar()

        self.draw_hud()

        if self.game_state == GameState.GAME_OVER:
            self.draw_death_screen()
        elif self.game_state == GameState.MENU:
            self.draw_menu()
        elif self.game_state == GameState.PAUSED:
            self.draw_pause_screen()

    def draw_hud(self):
        health_text = f"Здоровье: {self.player.health}/{self.player.max_health}"
        arcade.draw_text(
            health_text, 10, SCREEN_HEIGHT - 30, arcade.color.WHITE, 20
        )

        score_text = f"Очки: {self.score}"
        arcade.draw_text(
            score_text, 10, SCREEN_HEIGHT - 60, arcade.color.WHITE, 20
        )

        high_score_text = f"Рекорд: {self.high_score}"
        arcade.draw_text(
            high_score_text, 10, SCREEN_HEIGHT - 90, arcade.color.GOLD, 20
        )

        enemies_text = f"Врагов: {len(self.enemy_list)}"
        arcade.draw_text(
            enemies_text, 10, SCREEN_HEIGHT - 120, arcade.color.WHITE, 20
        )

        wave_text = f"Волна: {self.wave}"
        arcade.draw_text(
            wave_text, SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30,
            arcade.color.WHITE, 20, anchor_x="right"
        )

        ammo_text = "Патроны: ∞"
        arcade.draw_text(
            ammo_text, 10, SCREEN_HEIGHT - 150, arcade.color.LIME_GREEN, 20
        )

        control_text = "WASD - движение, ЛКМ/ПРОБЕЛ - стрельба"
        arcade.draw_text(
            control_text, SCREEN_WIDTH // 2, 30,
            arcade.color.LIGHT_GRAY, 16, anchor_x="center"
        )

        pause_text = "P - пауза"
        arcade.draw_text(
            pause_text, SCREEN_WIDTH - 10, SCREEN_HEIGHT - 60,
            arcade.color.LIGHT_GRAY, 16, anchor_x="right"
        )

    def draw_menu(self):
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (0, 0, 0, 200)
        )

        arcade.draw_text(
            "ТАНЧИКИ", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100,
            arcade.color.CYAN, 60, anchor_x="center", bold=True
        )

        start_text = "Нажмите ПРОБЕЛ для начала игры"
        arcade.draw_text(
            start_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
            arcade.color.WHITE, 30, anchor_x="center"
        )

        controls_text = "Управление: WASD - движение, ЛКМ/ПРОБЕЛ - стрельба"
        arcade.draw_text(
            controls_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50,
            arcade.color.LIGHT_GRAY, 20, anchor_x="center"
        )

        high_score_text = f"Текущий рекорд: {self.high_score}"
        arcade.draw_text(
            high_score_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
            arcade.color.GOLD, 25, anchor_x="center"
        )

        quit_text = "ESC - выход из игры"
        arcade.draw_text(
            quit_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150,
            arcade.color.WHITE, 20, anchor_x="center"
        )

    def draw_pause_screen(self):
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (0, 0, 0, 180)
        )

        arcade.draw_text(
            "ПАУЗА", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50,
            arcade.color.CYAN, 60, anchor_x="center", bold=True
        )

        continue_text = "Нажмите P для продолжения"
        arcade.draw_text(
            continue_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50,
            arcade.color.WHITE, 30, anchor_x="center"
        )

        quit_text = "ESC - выход в меню"
        arcade.draw_text(
            quit_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
            arcade.color.WHITE, 25, anchor_x="center"
        )

    def draw_death_screen(self):
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (0, 0, 0, 200)
        )

        arcade.draw_text(
            "ВЫ ПРОИГРАЛИ!", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100,
            arcade.color.RED, 60, anchor_x="center", bold=True
        )

        score_text = f"Ваш счет: {self.score}"
        arcade.draw_text(
            score_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40,
            arcade.color.WHITE, 40, anchor_x="center"
        )

        high_score_text = f"Рекорд: {self.high_score}"
        arcade.draw_text(
            high_score_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
            arcade.color.GOLD, 35, anchor_x="center"
        )

        killed_text = f"Убито врагов: {self.score // 100}"
        arcade.draw_text(
            killed_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40,
            arcade.color.WHITE, 30, anchor_x="center"
        )

        restart_text = "Нажмите ENTER или R чтобы начать заново"
        arcade.draw_text(
            restart_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
            arcade.color.WHITE, 25, anchor_x="center"
        )

        menu_text = "Нажмите ESC чтобы выйти в меню"
        arcade.draw_text(
            menu_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 140,
            arcade.color.WHITE, 25, anchor_x="center"
        )

    def on_update(self, delta_time):
        if self.game_state != GameState.PLAYING:
            self.explosion_list.update()
            self.powerup_list.update()
            return

        if not self.player.is_alive:
            self.game_state = GameState.GAME_OVER
            self.save_high_score()
            return

        self.player.update()
        self.particle_system.update()
        self.powerup_list.update()

        if len(self.enemy_list) == 0:
            self.spawn_wave()

        dx = self.mouse_x - self.player.center_x
        dy = self.mouse_y - self.player.center_y
        angle = math.degrees(math.atan2(dy, dx))

        if -45 <= angle <= 45:
            self.player.direction = "RIGHT"
        elif 45 < angle <= 135:
            self.player.direction = "UP"
        elif angle > 135 or angle < -135:
            self.player.direction = "LEFT"
        else:
            self.player.direction = "DOWN"

        new_x = self.player.center_x
        new_y = self.player.center_y
        speed = TANK_SPEED * self.player.speed_multiplier

        if self.left:
            new_x -= speed
        if self.right:
            new_x += speed
        if self.up:
            new_y += speed
        if self.down:
            new_y -= speed

        can_move = True
        temp_x = self.player.center_x
        temp_y = self.player.center_y
        self.player.center_x = new_x
        self.player.center_y = new_y

        if arcade.check_for_collision_with_list(self.player, self.obstacle_list):
            can_move = False

        self.player.center_x = temp_x
        self.player.center_y = temp_y

        if can_move:
            dx_move = 0
            dy_move = 0
            if self.left:
                dx_move = -speed
            if self.right:
                dx_move = speed
            if self.up:
                dy_move = speed
            if self.down:
                dy_move = -speed

            self.player.move_with_collision(dx_move, dy_move, self.obstacle_list)

            if self.left:
                self.particle_system.create_trail(
                    self.player.center_x + 20,
                    self.player.center_y,
                    (0, 255, 255)  # Циановый цвет игрока
                )
            if self.right:
                self.particle_system.create_trail(
                    self.player.center_x - 20,
                    self.player.center_y,
                    (0, 255, 255)  # Циановый цвет игрока
                )
            if self.up:
                self.particle_system.create_trail(
                    self.player.center_x,
                    self.player.center_y - 20,
                    (0, 255, 255)  # Циановый цвет игрока
                )
            if self.down:
                self.particle_system.create_trail(
                    self.player.center_x,
                    self.player.center_y + 20,
                    (0, 255, 255)  # Циановый цвет игрока
                )

            self.player.center_x = max(
                30, min(SCREEN_WIDTH - 30, self.player.center_x)
            )
            self.player.center_y = max(
                30, min(SCREEN_HEIGHT - 30, self.player.center_y)
            )

        for enemy in self.enemy_list:
            enemy.update()

        self.bullet_list.update()
        self.enemy_bullet_list.update()
        self.explosion_list.update()

        for bullet in self.bullet_list[:]:
            hit_obstacles = arcade.check_for_collision_with_list(
                bullet, self.obstacle_list
            )
            for obstacle in hit_obstacles:
                if obstacle.is_destructible:
                    obstacle.health -= bullet.damage
                    if obstacle.health <= 0:
                        explosion = Explosion(
                            obstacle.center_x, obstacle.center_y
                        )
                        self.explosion_list.append(explosion)
                        obstacle.remove_from_sprite_lists()
                        self.score += 10
                        if random.random() < 0.2:
                            self.spawn_powerup(
                                obstacle.center_x, obstacle.center_y
                            )
                bullet.remove_from_sprite_lists()
                break

        for bullet in self.enemy_bullet_list[:]:
            hit_obstacles = arcade.check_for_collision_with_list(
                bullet, self.obstacle_list
            )
            for obstacle in hit_obstacles:
                if obstacle.is_destructible:
                    obstacle.health -= bullet.damage
                    if obstacle.health <= 0:
                        explosion = Explosion(
                            obstacle.center_x, obstacle.center_y
                        )
                        self.explosion_list.append(explosion)
                        obstacle.remove_from_sprite_lists()
                bullet.remove_from_sprite_lists()
                break

        enemies_to_remove = []
        for bullet in self.bullet_list:
            hit_list = arcade.check_for_collision_with_list(
                bullet, self.enemy_list
            )
            for enemy in hit_list:
                enemy.take_damage(bullet.damage)
                if not enemy.is_alive:
                    self.score += 100
                    enemies_to_remove.append(enemy)
                    explosion = Explosion(enemy.center_x, enemy.center_y, enemy.enemy_type)
                    self.explosion_list.append(explosion)
                    if random.random() < 0.1:
                        self.spawn_powerup(enemy.center_x, enemy.center_y)
                bullet.remove_from_sprite_lists()
                break

        for enemy in enemies_to_remove:
            if enemy in self.enemy_list:
                self.enemy_list.remove(enemy)

        for bullet in self.enemy_bullet_list:
            if self.player.is_alive and arcade.check_for_collision(
                    bullet, self.player
            ):
                damage = bullet.damage
                self.player.take_damage(damage)
                bullet.remove_from_sprite_lists()
                if self.player.health > 0:
                    explosion = Explosion(
                        self.player.center_x, self.player.center_y
                    )
                    explosion.textures = [
                        arcade.make_circle_texture(
                            20, arcade.color.RED
                        )
                    ]
                    self.explosion_list.append(explosion)

        for powerup in self.powerup_list:
            if arcade.check_for_collision(self.player, powerup):
                self.apply_powerup(powerup)
                powerup.remove_from_sprite_lists()

        self.powerup_timer += 1
        if self.powerup_timer >= 600:
            x = random.randint(50, SCREEN_WIDTH - 50)
            y = random.randint(50, SCREEN_HEIGHT - 50)
            self.spawn_powerup(x, y)
            self.powerup_timer = 0

    def shoot(self):
        if (self.player.is_alive and self.player.can_shoot() and
                self.game_state == GameState.PLAYING):
            self.player.shoot(self.bullet_list, self.player_bullet_color)

    def on_key_press(self, key, modifiers):
        if self.game_state == GameState.MENU:
            if key == arcade.key.SPACE:
                self.game_state = GameState.PLAYING
            elif key == arcade.key.ESCAPE:
                arcade.close_window()
            return

        if self.game_state == GameState.GAME_OVER:
            if key == arcade.key.ENTER or key == arcade.key.R:
                self.game_state = GameState.PLAYING
                self.setup()
            elif key == arcade.key.ESCAPE:
                self.game_state = GameState.MENU
            return

        if self.game_state == GameState.PAUSED:
            if key == arcade.key.P:
                self.game_state = GameState.PLAYING
            elif key == arcade.key.ESCAPE:
                self.game_state = GameState.MENU
            return

        if key == arcade.key.P:
            if self.game_state == GameState.PLAYING:
                self.game_state = GameState.PAUSED
            elif self.game_state == GameState.PAUSED:
                self.game_state = GameState.PLAYING
            return

        if key == arcade.key.A:
            self.left = True
        elif key == arcade.key.D:
            self.right = True
        elif key == arcade.key.W:
            self.up = True
        elif key == arcade.key.S:
            self.down = True
        elif key == arcade.key.SPACE:
            if not self.space_pressed:
                self.space_pressed = True
                self.shoot()

    def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.left = False
        elif key == arcade.key.D:
            self.right = False
        elif key == arcade.key.W:
            self.up = False
        elif key == arcade.key.S:
            self.down = False
        elif key == arcade.key.SPACE:
            self.space_pressed = False

    def on_mouse_press(self, x, y, button, modifiers):
        if (button == arcade.MOUSE_BUTTON_LEFT and
                self.game_state == GameState.PLAYING):
            self.shoot()

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x
        self.mouse_y = y


if __name__ == "__main__":
    game = TankGame()
    arcade.run()