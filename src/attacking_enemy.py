from __future__ import annotations

from pathlib import Path

import pygame

from src.combat_config import PARRY_STUN_DURATION
from src.dummy import Dummy


class AttackingEnemy(Dummy):
    """Reusable base for enemies that can attack and be stunned by parries."""

    def __init__(
        self,
        assets_directory: Path,
        position: tuple[float, float],
        max_health: int = 1000,
    ) -> None:
        super().__init__(assets_directory, position, max_health)
        self.stun_timer = 0.0
        self.stun_visual_timer = 0.0

    @property
    def is_stunned(self) -> bool:
        """Whether this enemy is currently unable to attack."""
        return self.stun_timer > 0.0

    def update_stun(self, delta_time: float) -> bool:
        """Advance stun state; return True when the enemy must skip its attack update."""
        self.stun_timer = max(0.0, self.stun_timer - delta_time)
        self.stun_visual_timer = max(0.0, self.stun_visual_timer - delta_time)
        return self.is_stunned

    def apply_stun(self, duration: float = PARRY_STUN_DURATION) -> None:
        """Interrupt the current attack and stun this enemy."""
        self.stun_timer = max(self.stun_timer, duration)
        self.stun_visual_timer = self.stun_timer
        self.attack_timer = 0.0
        self.attack_cooldown_timer = max(self.attack_cooldown_timer, self.attack_interval)
        self.attack_has_hit = True

    def draw_stun_indicator(self, surface: pygame.Surface, camera) -> None:
        """Draw the shared compact yellow stun indicator."""
        if self.stun_visual_timer <= 0.0:
            return
        screen_position = camera.world_to_screen(self.position)
        zoom = camera.zoom
        radius = max(4, round(6 * zoom))
        pygame.draw.circle(
            surface,
            (255, 220, 70),
            (round(screen_position.x), round(screen_position.y - 18 * zoom)),
            radius,
            max(1, round(2 * zoom)),
        )
