from __future__ import annotations

import math
from pathlib import Path

import pygame


DIRECTIONS = (
    "north",
    "north-east",
    "east",
    "south-east",
    "south",
    "south-west",
    "west",
    "north-west",
)


class Player:
    """The player entity used by the sandbox prototype."""

    def __init__(self, assets_directory: Path, start_position: tuple[float, float]) -> None:
        self.position = pygame.Vector2(start_position)
        self.facing_direction = "south"
        self.sprite_size = pygame.Vector2(32, 32)
        self.collision_radii = pygame.Vector2(5.0, 10.0)
        self.speed = 70.0
        self.max_health = 100
        self.health = self.max_health
        self.attack_damage = 10
        self.state = "IDLE"
        self.attack_duration = 0.24
        self.attack_timer = 0.0
        self.attack_cooldown_duration = 0.36
        self.attack_cooldown_timer = 0.0
        self.attack_has_hit = False
        self.hurt_flash_duration = 0.14
        self.hurt_flash_timer = 0.0
        self.is_moving = False
        self.walk_frame_index = 0
        self.walk_frame_timer = 0.0
        self.walk_frame_duration = 0.10
        self.sprites = self._load_directional_sprites(assets_directory)
        self.walking_sprites = self._load_walking_sprites(assets_directory)
        self.sword_hand_sprites = self._load_sword_hand_sprites(assets_directory)
        self.sword_swing_sprites = self._load_sword_swing_sprites(assets_directory)
        self.shield_sprites = self._load_shield_sprites(assets_directory)

    def _load_directional_sprites(self, assets_directory: Path) -> dict[str, pygame.Surface]:
        """Crop the eight 32x32 directional frames from the handless spritesheet."""
        spritesheet_path = assets_directory / "player" / "playeridle.png"
        spritesheet = pygame.image.load(spritesheet_path).convert_alpha()
        frame_size = 32
        sprites: dict[str, pygame.Surface] = {}

        # The supplied sheet is a 4x2 grid in this order:
        # north, north-east, east, south-east / south, south-west, west, north-west.
        for index, direction in enumerate(DIRECTIONS):
            column = index % 4
            row = index // 4
            frame_rect = pygame.Rect(
                column * frame_size,
                row * frame_size,
                frame_size,
                frame_size,
            )
            sprites[direction] = spritesheet.subsurface(frame_rect).copy()

        return sprites

    def _load_walking_sprites(self, assets_directory: Path) -> dict[str, list[pygame.Surface]]:
        """Crop four horizontal walking frames for each of the eight directions."""
        spritesheet_path = assets_directory / "player" / "playerwalk.png"
        spritesheet = pygame.image.load(spritesheet_path).convert_alpha()
        frame_size = 32
        walking_sprites: dict[str, list[pygame.Surface]] = {}

        for row, direction in enumerate(DIRECTIONS):
            walking_sprites[direction] = []
            for column in range(4):
                frame_rect = pygame.Rect(
                    column * frame_size,
                    row * frame_size,
                    frame_size,
                    frame_size,
                )
                walking_sprites[direction].append(
                    spritesheet.subsurface(frame_rect).copy()
                )

        return walking_sprites

    def _load_sword_swing_sprites(self, assets_directory: Path) -> dict[str, list[pygame.Surface]]:
        """Crop four 64x64 sword-swing frames for each of the eight directions."""
        spritesheet_path = assets_directory / "player" / "swordswing.png"
        spritesheet = pygame.image.load(spritesheet_path).convert_alpha()
        frame_size = 64
        swing_sprites: dict[str, list[pygame.Surface]] = {}

        for row, direction in enumerate(DIRECTIONS):
            swing_sprites[direction] = []
            for column in range(4):
                frame_rect = pygame.Rect(
                    column * frame_size,
                    row * frame_size,
                    frame_size,
                    frame_size,
                )
                swing_sprites[direction].append(
                    spritesheet.subsurface(frame_rect).copy()
                )

        return swing_sprites

    def _load_shield_sprites(self, assets_directory: Path) -> dict[str, pygame.Surface]:
        """Crop one 32x32 held-block frame for each of the eight directions."""
        spritesheet_path = assets_directory / "player" / "shield.png"
        spritesheet = pygame.image.load(spritesheet_path).convert_alpha()
        frame_size = 32
        shield_sprites: dict[str, pygame.Surface] = {}

        for row, direction in enumerate(DIRECTIONS):
            frame_rect = pygame.Rect(0, row * frame_size, frame_size, frame_size)
            shield_sprites[direction] = spritesheet.subsurface(frame_rect).copy()

        return shield_sprites

    def _load_sword_hand_sprites(self, assets_directory: Path) -> dict[str, pygame.Surface]:
        """Crop the 3-3-2 sword-hands sheet in the agreed direction order."""
        spritesheet_path = assets_directory / "player" / "sword_hands_sheet.png"
        spritesheet = pygame.image.load(spritesheet_path).convert_alpha()
        frame_size = 32
        frame_positions = (
            (0, 0), (1, 0), (2, 0),
            (0, 1), (1, 1), (2, 1),
            (0, 2), (1, 2),
        )
        sprites: dict[str, pygame.Surface] = {}

        for direction, (column, row) in zip(DIRECTIONS, frame_positions):
            frame_rect = pygame.Rect(
                column * frame_size,
                row * frame_size,
                frame_size,
                frame_size,
            )
            sprites[direction] = spritesheet.subsurface(frame_rect).copy()

        return sprites

    def update_facing(self, mouse_world_position: pygame.Vector2) -> None:
        """Face the closest supplied sprite direction toward the mouse."""
        direction_to_mouse = mouse_world_position - self.position

        if direction_to_mouse.length_squared() == 0:
            return

        angle = math.degrees(math.atan2(-direction_to_mouse.y, direction_to_mouse.x))
        angle = angle % 360
        direction_index = int((angle + 22.5) // 45) % 8
        direction_order = (
            "east",
            "north-east",
            "north",
            "north-west",
            "west",
            "south-west",
            "south",
            "south-east",
        )
        self.facing_direction = direction_order[direction_index]

    def take_damage(self, amount: int) -> int:
        previous_health = self.health
        self.health = max(0, self.health - amount)
        dealt_damage = previous_health - self.health
        if dealt_damage > 0:
            self.hurt_flash_timer = self.hurt_flash_duration
        return dealt_damage

    def update_hurt(self, delta_time: float) -> None:
        self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - delta_time)

    def _apply_hurt_flash(self, sprite: pygame.Surface) -> pygame.Surface:
        if self.hurt_flash_timer <= 0.0:
            return sprite
        return pygame.mask.from_surface(sprite).to_surface(
            setcolor=(255, 70, 70, 235),
            unsetcolor=(0, 0, 0, 0),
        )

    def start_attack(self) -> bool:
        """Start one sword swing if the attack is ready."""
        if self.state == "BLOCKING" or self.attack_cooldown_timer > 0 or self.attack_timer > 0:
            return False

        self.state = "ATTACKING"
        self.attack_timer = self.attack_duration
        self.attack_cooldown_timer = self.attack_cooldown_duration
        self.attack_has_hit = False
        return True

    def get_attack_arc(self) -> tuple[pygame.Vector2, float, float, float] | None:
        """Return the current sword arc as center, angle, reach, and half-width."""
        if self.attack_timer <= 0.0:
            return None

        direction_angles = {
            "east": 0.0,
            "north-east": 45.0,
            "north": 90.0,
            "north-west": 135.0,
            "west": 180.0,
            "south-west": 225.0,
            "south": 270.0,
            "south-east": 315.0,
        }
        progress = 1.0 - self.attack_timer / self.attack_duration
        if progress < 0.15 or progress > 0.85:
            return None

        swing_progress = (progress - 0.15) / 0.70
        angle = direction_angles[self.facing_direction] - 55.0 + 110.0 * swing_progress
        return self.position, angle, 23.0, 18.0

    @property
    def collision_ellipse(self) -> tuple[pygame.Vector2, pygame.Vector2]:
        """Return the player's oval body collision geometry."""
        return self.position, self.collision_radii

    @property
    def hitbox(self) -> pygame.Rect:
        """Return a compatibility rectangle around the circular body collider."""
        return pygame.Rect(
            round(self.position.x - self.collision_radii.x),
            round(self.position.y - self.collision_radii.y),
            round(self.collision_radii.x * 2),
            round(self.collision_radii.y * 2),
        )

    def start_block(self) -> bool:
        """Enter the blocking state while the right mouse button is held."""
        if self.attack_timer > 0:
            return False

        self.state = "BLOCKING"
        return True

    def stop_block(self) -> None:
        """Leave the blocking state when the right mouse button is released."""
        if self.state == "BLOCKING":
            self.state = "IDLE"

    def update_attack(self, delta_time: float) -> None:
        """Advance attack and cooldown timers without tying them to frame rate."""
        self.attack_timer = max(0.0, self.attack_timer - delta_time)
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - delta_time)

        if self.attack_timer == 0.0 and self.state == "ATTACKING":
            self.state = "IDLE"

    def update(self, delta_time: float, world_rect: pygame.Rect) -> None:
        """Move the player and advance the walking animation using delta time."""
        self.update_attack(delta_time)
        self.update_hurt(delta_time)
        keys = pygame.key.get_pressed()
        movement = pygame.Vector2(
            float(keys[pygame.K_d]) - float(keys[pygame.K_a]),
            float(keys[pygame.K_s]) - float(keys[pygame.K_w]),
        )
        self.is_moving = movement.length_squared() > 0

        if self.is_moving:
            movement = movement.normalize()
            self.position += movement * self.speed * delta_time
            self.walk_frame_timer += delta_time
            while self.walk_frame_timer >= self.walk_frame_duration:
                self.walk_frame_timer -= self.walk_frame_duration
                self.walk_frame_index = (self.walk_frame_index + 1) % 4
        else:
            self.walk_frame_timer = 0.0
            self.walk_frame_index = 0

        half_width = self.sprite_size.x / 2
        half_height = self.sprite_size.y / 2
        self.position.x = max(
            world_rect.left + half_width,
            min(self.position.x, world_rect.right - half_width),
        )
        self.position.y = max(
            world_rect.top + half_height,
            min(self.position.y, world_rect.bottom - half_height),
        )

    def draw(self, surface: pygame.Surface, camera) -> None:
        """Draw the player and any active directional sword swing."""
        screen_position = camera.world_to_screen(self.position)

        zoom = camera.zoom

        if self.is_moving:
            sprite = self.walking_sprites[self.facing_direction][self.walk_frame_index]
        else:
            sprite = self.sprites[self.facing_direction]
        sprite = self._apply_hurt_flash(sprite)
        scaled_sprite = pygame.transform.scale(
            sprite,
            (round(sprite.get_width() * zoom), round(sprite.get_height() * zoom)),
        )
        draw_position = screen_position - pygame.Vector2(scaled_sprite.get_size()) / 2
        surface.blit(scaled_sprite, (round(draw_position.x), round(draw_position.y)))

        if self.attack_timer > 0:
            elapsed_attack_time = self.attack_duration - self.attack_timer
            swing_frame_index = min(
                3,
                int((elapsed_attack_time / self.attack_duration) * 4),
            )
            sword_swing = self.sword_swing_sprites[self.facing_direction][swing_frame_index]
            sword_swing = self._apply_hurt_flash(sword_swing)
            scaled_sword_swing = pygame.transform.scale(
                sword_swing,
                (
                    round(sword_swing.get_width() * zoom),
                    round(sword_swing.get_height() * zoom),
                ),
            )
            swing_position = screen_position - pygame.Vector2(scaled_sword_swing.get_size()) / 2
            surface.blit(
                scaled_sword_swing,
                (round(swing_position.x), round(swing_position.y)),
            )
        elif self.state != "BLOCKING":
            sword_hands = self.sword_hand_sprites[self.facing_direction]
            sword_hands = self._apply_hurt_flash(sword_hands)
            scaled_sword_hands = pygame.transform.scale(
                sword_hands,
                (
                    round(sword_hands.get_width() * zoom),
                    round(sword_hands.get_height() * zoom),
                ),
            )
            hands_position = screen_position - pygame.Vector2(scaled_sword_hands.get_size()) / 2
            surface.blit(
                scaled_sword_hands,
                (round(hands_position.x), round(hands_position.y)),
            )

        if self.state == "BLOCKING":
            self._draw_block(surface, screen_position, zoom)

    def _draw_block(
        self,
        surface: pygame.Surface,
        screen_position: pygame.Vector2,
        zoom: float,
    ) -> None:
        """Draw the supplied held-block frame for the current facing direction."""
        shield = self.shield_sprites[self.facing_direction]
        scaled_shield = pygame.transform.scale(
            shield,
            (
                round(shield.get_width() * zoom),
                round(shield.get_height() * zoom),
            ),
        )
        shield_position = screen_position - pygame.Vector2(scaled_shield.get_size()) / 2
        surface.blit(
            scaled_shield,
            (round(shield_position.x), round(shield_position.y)),
        )
