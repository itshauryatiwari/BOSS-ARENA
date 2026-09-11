import math
from pathlib import Path

import pygame

from src.attacking_enemy import AttackingEnemy
from src.player import DIRECTIONS
from src.combat_config import ENEMY_ATTACK_DURATION, ENEMY_ATTACK_INTERVAL


class AttackingDummy(AttackingEnemy):
    """Training dummy that periodically swings toward the player."""

    def __init__(
        self,
        assets_directory: Path,
        position: tuple[float, float],
        max_health: int = 1000,
    ) -> None:
        super().__init__(assets_directory, position, max_health)
        self.facing_direction = "west"
        self.attack_damage = 10
        self.attack_duration = ENEMY_ATTACK_DURATION
        self.attack_timer = 0.0
        self.attack_interval = ENEMY_ATTACK_INTERVAL
        self.attack_cooldown_timer = self.attack_interval
        self.attack_has_hit = False
        self.sword_hand_sprites = self._load_sword_hand_sprites(assets_directory)
        self.sword_swing_sprites = self._load_sword_swing_sprites(assets_directory)

    def _load_sword_hand_sprites(self, assets_directory: Path) -> dict[str, pygame.Surface]:
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

    def _face_target(self, target_position: pygame.Vector2) -> None:
        direction_to_target = target_position - self.position
        if direction_to_target.length_squared() == 0:
            return

        angle = math.degrees(math.atan2(-direction_to_target.y, direction_to_target.x)) % 360
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

    def update(self, delta_time: float, target_position: pygame.Vector2) -> None:
        super().update(delta_time)
        if self.update_stun(delta_time):
            self.attack_timer = 0.0
            self.attack_cooldown_timer = max(self.attack_cooldown_timer, self.attack_interval)
            self.attack_has_hit = True
            return

        self._face_target(target_position)
        self.attack_timer = max(0.0, self.attack_timer - delta_time)
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - delta_time)

        if self.attack_timer == 0.0 and self.attack_cooldown_timer == 0.0:
            self.attack_timer = self.attack_duration
            self.attack_cooldown_timer = self.attack_interval
            self.attack_has_hit = False

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

    def draw(self, surface: pygame.Surface, camera) -> None:
        super().draw(surface, camera)
        screen_position = camera.world_to_screen(self.position)
        zoom = camera.zoom

        self.draw_stun_indicator(surface, camera)

        if self.attack_timer > 0.0:
            elapsed_attack_time = self.attack_duration - self.attack_timer
            swing_frame_index = min(
                3,
                int((elapsed_attack_time / self.attack_duration) * 4),
            )
            sword_swing = self.sword_swing_sprites[self.facing_direction][swing_frame_index]
            if self.hurt_flash_timer > 0.0:
                sword_swing = pygame.mask.from_surface(sword_swing).to_surface(
                    setcolor=(255, 70, 70, 235),
                    unsetcolor=(0, 0, 0, 0),
                )
            scaled_sword_swing = pygame.transform.scale(
                sword_swing,
                (
                    round(sword_swing.get_width() * zoom),
                    round(sword_swing.get_height() * zoom),
                ),
            )
            draw_position = screen_position - pygame.Vector2(scaled_sword_swing.get_size()) / 2
            surface.blit(scaled_sword_swing, (round(draw_position.x), round(draw_position.y)))
        else:
            sword_hands = self.sword_hand_sprites[self.facing_direction]
            if self.hurt_flash_timer > 0.0:
                sword_hands = pygame.mask.from_surface(sword_hands).to_surface(
                    setcolor=(255, 70, 70, 235),
                    unsetcolor=(0, 0, 0, 0),
                )
            scaled_sword_hands = pygame.transform.scale(
                sword_hands,
                (
                    round(sword_hands.get_width() * zoom),
                    round(sword_hands.get_height() * zoom),
                ),
            )
            draw_position = screen_position - pygame.Vector2(scaled_sword_hands.get_size()) / 2
            surface.blit(scaled_sword_hands, (round(draw_position.x), round(draw_position.y)))
