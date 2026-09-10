from __future__ import annotations

import random

import pygame


class Camera:
    """Keeps the player near the center of the screen while the world scrolls."""

    def __init__(self, screen_size: tuple[int, int], zoom: float = 3.0) -> None:
        self.screen_width, self.screen_height = screen_size
        self.zoom = zoom
        self.position = pygame.Vector2(0, 0)
        self.shake_timer = 0.0
        self.shake_duration = 0.0
        self.shake_strength = 0.0
        self.shake_offset = pygame.Vector2(0, 0)

    def follow(self, target_position: pygame.Vector2) -> None:
        """Place the camera center on a world-space target position."""
        self.position.update(target_position)

    def adjust_zoom(self, amount: float) -> None:
        """Change zoom while keeping it within useful gameplay limits."""
        self.zoom = max(1.0, min(6.0, self.zoom + amount))

    def shake(self, duration: float = 0.14, strength: float = 3.0) -> None:
        """Trigger a small screen-space shake, keeping the strongest active request."""
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_duration = max(self.shake_duration, duration)
        self.shake_strength = max(self.shake_strength, strength)

    def update_shake(self, delta_time: float) -> None:
        """Advance shake timing and calculate the current decaying offset."""
        if self.shake_timer <= 0.0:
            self.shake_offset.update(0, 0)
            self.shake_duration = 0.0
            self.shake_strength = 0.0
            return

        self.shake_timer = max(0.0, self.shake_timer - delta_time)
        decay = self.shake_timer / self.shake_duration if self.shake_duration else 0.0
        self.shake_offset.update(
            random.uniform(-1.0, 1.0) * self.shake_strength * decay,
            random.uniform(-1.0, 1.0) * self.shake_strength * decay,
        )

    def world_to_screen(self, world_position: pygame.Vector2) -> pygame.Vector2:
        """Convert a world-space position into a screen-space position."""
        screen_center = pygame.Vector2(self.screen_width / 2, self.screen_height / 2)
        return (world_position - self.position) * self.zoom + screen_center + self.shake_offset

    def screen_to_world(self, screen_position: pygame.Vector2) -> pygame.Vector2:
        """Convert a screen-space position into a world-space position."""
        screen_center = pygame.Vector2(self.screen_width / 2, self.screen_height / 2)
        return (screen_position - screen_center - self.shake_offset) / self.zoom + self.position

    def world_rect_to_screen(self, world_rect: pygame.Rect) -> pygame.Rect:
        """Convert a world-space rectangle into a screen-space rectangle."""
        screen_position = self.world_to_screen(pygame.Vector2(world_rect.topleft))
        return pygame.Rect(
            round(screen_position.x),
            round(screen_position.y),
            world_rect.width,
            world_rect.height,
        )
