from __future__ import annotations

import pygame


class Camera:
    """Keeps the player near the center of the screen while the world scrolls."""

    def __init__(self, screen_size: tuple[int, int], zoom: float = 3.0) -> None:
        self.screen_width, self.screen_height = screen_size
        self.zoom = zoom
        self.position = pygame.Vector2(0, 0)

    def follow(self, target_position: pygame.Vector2) -> None:
        """Place the camera center on a world-space target position."""
        self.position.update(target_position)

    def adjust_zoom(self, amount: float) -> None:
        """Change zoom while keeping it within useful gameplay limits."""
        self.zoom = max(1.0, min(6.0, self.zoom + amount))

    def world_to_screen(self, world_position: pygame.Vector2) -> pygame.Vector2:
        """Convert a world-space position into a screen-space position."""
        screen_center = pygame.Vector2(self.screen_width / 2, self.screen_height / 2)
        return (world_position - self.position) * self.zoom + screen_center

    def screen_to_world(self, screen_position: pygame.Vector2) -> pygame.Vector2:
        """Convert a screen-space position into a world-space position."""
        screen_center = pygame.Vector2(self.screen_width / 2, self.screen_height / 2)
        return (screen_position - screen_center) / self.zoom + self.position

    def world_rect_to_screen(self, world_rect: pygame.Rect) -> pygame.Rect:
        """Convert a world-space rectangle into a screen-space rectangle."""
        screen_position = self.world_to_screen(pygame.Vector2(world_rect.topleft))
        return pygame.Rect(
            round(screen_position.x),
            round(screen_position.y),
            world_rect.width,
            world_rect.height,
        )
