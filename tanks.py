import arcade
import random

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Танчики (Arcade)"

TANK_SPEED = 4
BULLET_SPEED = 8

class Bullet(arcade.Sprite):
    def update(self, delta_time: float = 1/60):
        self.center_x += self.change_x
        self.center_y += self.change_y
        if (
            self.center_x < 0 or self.center_x > SCREEN_WIDTH or
            self.center_y < 0 or self.center_y > SCREEN_HEIGHT
        ):
            self.remove_from_sprite_lists()

class Tank(arcade.Sprite):
    def __init__(self, color):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(40, color, 255)
        self.direction = "UP"


class TankGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.DARK_GREEN)

        self.player_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()

        self.player = Tank(arcade.color.BLUE)
        self.player.center_x = 400
        self.player.center_y = 100
        self.player_list.append(self.player)

        for _ in range(5):
            enemy = Tank(arcade.color.RED)
            enemy.center_x = random.randint(50, 750)
            enemy.center_y = random.randint(300, 550)
            self.enemy_list.append(enemy)

        self.left = False
        self.right = False
        self.up = False
        self.down = False

    def on_draw(self):
        self.clear()
        self.player_list.draw()
        self.enemy_list.draw()
        self.bullet_list.draw()

    def on_update(self, delta_time):
        if self.left:
            self.player.center_x -= TANK_SPEED
            self.player.direction = "LEFT"
        if self.right:
            self.player.center_x += TANK_SPEED
            self.player.direction = "RIGHT"
        if self.up:
            self.player.center_y += TANK_SPEED
            self.player.direction = "UP"
        if self.down:
            self.player.center_y -= TANK_SPEED
            self.player.direction = "DOWN"

        self.bullet_list.update()

        for bullet in self.bullet_list:
            hit_list = arcade.check_for_collision_with_list(bullet, self.enemy_list)
            for enemy in hit_list:
                enemy.remove_from_sprite_lists()
                bullet.remove_from_sprite_lists()

    def shoot(self):
        bullet = Bullet()
        bullet.texture = arcade.make_circle_texture(8, arcade.color.YELLOW)
        bullet.center_x = self.player.center_x
        bullet.center_y = self.player.center_y

        if self.player.direction == "UP":
            bullet.change_x = 0
            bullet.change_y = BULLET_SPEED
        elif self.player.direction == "DOWN":
            bullet.change_x = 0
            bullet.change_y = -BULLET_SPEED
        elif self.player.direction == "LEFT":
            bullet.change_x = -BULLET_SPEED
            bullet.change_y = 0
        elif self.player.direction == "RIGHT":
            bullet.change_x = BULLET_SPEED
            bullet.change_y = 0

        self.bullet_list.append(bullet)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.A:
            self.left = True
        elif key == arcade.key.D:
            self.right = True
        elif key == arcade.key.W:
            self.up = True
        elif key == arcade.key.S:
            self.down = True
        elif key == arcade.key.SPACE:
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

if __name__ == "__main__":
    game = TankGame()
    arcade.run()
