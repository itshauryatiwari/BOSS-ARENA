import pygame


class FloatingDamageNumber:
    """A red damage value that rises and fades above a damaged entity."""

    def __init__(self, position: pygame.Vector2, amount: int) -> None:
        self.position = pygame.Vector2(position)
        self.amount = amount
        self.lifetime = 0.7
        self.remaining = self.lifetime
        self.rise_speed = 34.0

    def update(self, delta_time: float) -> None:
        self.remaining = max(0.0, self.remaining - delta_time)
        self.position.y -= self.rise_speed * delta_time

    @property
    def is_alive(self) -> bool:
        return self.remaining > 0.0

    def draw(self, surface: pygame.Surface, camera, font: pygame.font.Font) -> None:
        screen_position = camera.world_to_screen(self.position)
        alpha = round(255 * (self.remaining / self.lifetime))
        text_surface = font.render(str(self.amount), True, (255, 65, 65))
        text_surface.set_alpha(alpha)
        draw_position = (
            round(screen_position.x - text_surface.get_width() / 2),
            round(screen_position.y - text_surface.get_height() / 2),
        )
        surface.blit(text_surface, draw_position)


class DamageFeedback:
    """Reusable manager for floating damage numbers."""

    def __init__(self) -> None:
        self.numbers: list[FloatingDamageNumber] = []

    def add_damage(self, position: pygame.Vector2, amount: int) -> None:
        self.numbers.append(FloatingDamageNumber(position, amount))

    def update(self, delta_time: float) -> None:
        for number in self.numbers:
            number.update(delta_time)
        self.numbers = [number for number in self.numbers if number.is_alive]

    def draw(self, surface: pygame.Surface, camera, font: pygame.font.Font) -> None:
        for number in self.numbers:
            number.draw(surface, camera, font)
