import math
from pathlib import Path

import pygame

from src.dummy import Dummy
from src.player import DIRECTIONS


class AttackingDummy(Dummy):
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
        self.attack_duration = 0.24
        self.attack_timer = 0.0
        self.attack_interval = 1.0
        self.attack_cooldown_timer = self.attack_interval
        self.attack_has_hit = False
        self.sword_hand_sprites = self._load_sword_hand_sprites(assets_directory)

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

    def update(self, delta_time: float, target_position: pygame.Vector2) -> None:
        super().update(delta_time)
        self._face_target(target_position)
        self.attack_timer = max(0.0, self.attack_timer - delta_time)
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - delta_time)

        if self.attack_timer == 0.0 and self.attack_cooldown_timer == 0.0:
            self.attack_timer = self.attack_duration
            self.attack_cooldown_timer = self.attack_interval
            self.attack_has_hit = False

    def get_attack_hitbox(self) -> pygame.Rect | None:
        if self.attack_timer <= 0.0:
            return None

        direction_vectors = {
            "north": pygame.Vector2(0, -1),
            "north-east": pygame.Vector2(1, -1).normalize(),
            "east": pygame.Vector2(1, 0),
            "south-east": pygame.Vector2(1, 1).normalize(),
            "south": pygame.Vector2(0, 1),
            "south-west": pygame.Vector2(-1, 1).normalize(),
            "west": pygame.Vector2(-1, 0),
            "north-west": pygame.Vector2(-1, -1).normalize(),
        }
        direction = direction_vectors[self.facing_direction]
        hitbox_center = self.position + direction * 18
        hitbox_size = 12
        return pygame.Rect(
            round(hitbox_center.x - hitbox_size / 2),
            round(hitbox_center.y - hitbox_size / 2),
            hitbox_size,
            hitbox_size,
        )

    def draw(self, surface: pygame.Surface, camera) -> None:
        super().draw(surface, camera)
        screen_position = camera.world_to_screen(self.position)
        zoom = camera.zoom
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
