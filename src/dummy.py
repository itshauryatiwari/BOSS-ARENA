from pathlib import Path

import pygame


class Dummy:
    """Stationary training dummy used to test player attacks."""

    def __init__(
        self,
        assets_directory: Path,
        position: tuple[float, float],
        max_health: int = 1000,
    ) -> None:
        self.position = pygame.Vector2(position)
        self.max_health = max_health
        self.health = max_health
        self.sprite = self._load_sprite(assets_directory)
        self.sprite_size = pygame.Vector2(self.sprite.get_size())
        self.collision_radii = pygame.Vector2(
            self.sprite_size.x * 0.16,
            self.sprite_size.y * 0.31,
        )
        self.hurt_flash_duration = 0.14
        self.hurt_flash_timer = 0.0

    def _load_sprite(self, assets_directory: Path) -> pygame.Surface:
        dummy_path = assets_directory / "entity" / "dummy.png"
        return pygame.image.load(dummy_path).convert_alpha()

    @property
    def hitbox(self) -> pygame.Rect:
        """Return a compatibility rectangle around the circular body collider."""
        return pygame.Rect(
            round(self.position.x - self.collision_radii.x),
            round(self.position.y - self.collision_radii.y),
            round(self.collision_radii.x * 2),
            round(self.collision_radii.y * 2),
        )

    @property
    def collision_ellipse(self) -> tuple[pygame.Vector2, pygame.Vector2]:
        """Return the dummy's oval body collision geometry."""
        return self.position, self.collision_radii

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: int) -> int:
        previous_health = self.health
        self.health = max(0, self.health - amount)
        dealt_damage = previous_health - self.health
        if dealt_damage > 0:
            self.hurt_flash_timer = self.hurt_flash_duration
        return dealt_damage

    def update(self, delta_time: float) -> None:
        self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - delta_time)

    def draw(self, surface: pygame.Surface, camera) -> None:
        screen_position = camera.world_to_screen(self.position)
        zoom = camera.zoom
        sprite_to_draw = self.sprite
        if self.hurt_flash_timer > 0.0:
            sprite_to_draw = pygame.mask.from_surface(self.sprite).to_surface(
                setcolor=(255, 70, 70, 235),
                unsetcolor=(0, 0, 0, 0),
            )

        scaled_sprite = pygame.transform.scale(
            sprite_to_draw,
            (
                round(sprite_to_draw.get_width() * zoom),
                round(sprite_to_draw.get_height() * zoom),
            ),
        )
        draw_position = screen_position - pygame.Vector2(scaled_sprite.get_size()) / 2
        surface.blit(scaled_sprite, (round(draw_position.x), round(draw_position.y)))

        self._draw_health_bar(surface, screen_position, zoom)

    def _draw_health_bar(
        self,
        surface: pygame.Surface,
        screen_position: pygame.Vector2,
        zoom: float,
    ) -> None:
        bar_width = round(56 * zoom)
        bar_height = max(4, round(6 * zoom))
        bar_x = round(screen_position.x - bar_width / 2)
        bar_y = round(screen_position.y - 28 * zoom)
        background_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(surface, (40, 18, 18), background_rect)

        health_ratio = self.health / self.max_health if self.max_health else 0.0
        health_rect = pygame.Rect(
            bar_x,
            bar_y,
            round(bar_width * health_ratio),
            bar_height,
        )
        pygame.draw.rect(surface, (205, 50, 50), health_rect)
        pygame.draw.rect(surface, (245, 225, 225), background_rect, max(1, round(zoom)))
