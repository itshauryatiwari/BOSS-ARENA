from __future__ import annotations

from pathlib import Path

import pygame

from src.camera import Camera
from src.attacking_dummy import AttackingDummy
from src.damage_feedback import DamageFeedback
from src.dummy import Dummy
from src.player import Player


SCREEN_SIZE = (1280, 720)
WORLD_SIZE = (3200, 2200)
WINDOW_TITLE = "Boss Arena - Player Sandbox"


class Game:
    """Coordinates the first playable Player Sandbox scene."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.debug_collision_boxes = False
        self.debug_font = pygame.font.Font(None, 24)
        self.hud_font = pygame.font.Font(None, 28)
        self.damage_font = pygame.font.Font(None, 30)
        self.damage_feedback = DamageFeedback()

        self.project_directory = Path(__file__).resolve().parent.parent
        self.assets_directory = self.project_directory / "assets"
        self.floor_tile = self._load_floor_tile()

        self.world_rect = pygame.Rect(0, 0, WORLD_SIZE[0], WORLD_SIZE[1])
        self.player = Player(
            assets_directory=self.assets_directory,
            start_position=(WORLD_SIZE[0] / 2 - 140, WORLD_SIZE[1] / 2),
        )
        self.dummy = Dummy(
            assets_directory=self.assets_directory,
            position=(WORLD_SIZE[0] / 2, WORLD_SIZE[1] / 2),
            max_health=1000,
        )
        self.attacking_dummy = AttackingDummy(
            assets_directory=self.assets_directory,
            position=(WORLD_SIZE[0] / 2 + 80, WORLD_SIZE[1] / 2),
            max_health=1000,
        )
        self.camera = Camera(SCREEN_SIZE)
        self.camera.follow(self.player.position)

    def _load_floor_tile(self) -> pygame.Surface:
        floor_path = self.assets_directory / "tiles" / "floor1.png"
        return pygame.image.load(floor_path).convert()

    def run(self) -> None:
        while self.running:
            delta_time = self.clock.tick(60) / 1000.0
            delta_time = min(delta_time, 0.1)
            self._handle_events()
            self._update(delta_time)
            self._draw()

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                self.debug_collision_boxes = not self.debug_collision_boxes
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    self.player.start_attack()
                elif event.button == pygame.BUTTON_RIGHT:
                    self.player.start_block()
            elif event.type == pygame.MOUSEWHEEL:
                self.camera.adjust_zoom(event.y * 0.25)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == pygame.BUTTON_RIGHT:
                self.player.stop_block()

    def _update(self, delta_time: float) -> None:
        mouse_screen_position = pygame.Vector2(pygame.mouse.get_pos())
        mouse_world_position = self.camera.screen_to_world(mouse_screen_position)

        self.player.update_facing(mouse_world_position)
        self.player.update(delta_time, self.world_rect)
        self.dummy.update(delta_time)
        self.attacking_dummy.update(delta_time, self.player.position)
        self.damage_feedback.update(delta_time)
        self._check_dummy_hit()
        self._check_attacking_dummy_hit()
        self.camera.follow(self.player.position)

    def _check_dummy_hit(self) -> None:
        """Apply one player damage instance per sword swing to each target."""
        if self.player.attack_has_hit:
            return

        attack_hitbox = self.player.get_attack_hitbox()
        if attack_hitbox is None:
            return

        hit_registered = False
        if self.dummy.is_alive and self._ellipses_overlap(
            attack_hitbox,
            self.dummy.collision_ellipse,
        ):
            dealt_damage = self.dummy.take_damage(self.player.attack_damage)
            if dealt_damage > 0:
                self.damage_feedback.add_damage(self.dummy.position, dealt_damage)
            hit_registered = True

        if self.attacking_dummy.is_alive and self._ellipses_overlap(
            attack_hitbox,
            self.attacking_dummy.collision_ellipse,
        ):
            dealt_damage = self.attacking_dummy.take_damage(self.player.attack_damage)
            if dealt_damage > 0:
                self.damage_feedback.add_damage(self.attacking_dummy.position, dealt_damage)
            hit_registered = True

        self.player.attack_has_hit = hit_registered

    def _check_attacking_dummy_hit(self) -> None:
        """Apply one attacking-dummy hit to the player per enemy swing."""
        if not self.attacking_dummy.is_alive or self.attacking_dummy.attack_has_hit:
            return

        attack_hitbox = self.attacking_dummy.get_attack_hitbox()
        if attack_hitbox is not None and self._ellipses_overlap(
            attack_hitbox,
            self.player.collision_ellipse,
        ):
            dealt_damage = self.player.take_damage(self.attacking_dummy.attack_damage)
            if dealt_damage > 0:
                self.damage_feedback.add_damage(self.player.position, dealt_damage)
            self.attacking_dummy.attack_has_hit = True

    @staticmethod
    def _ellipses_overlap(
        first_shape: pygame.Rect | tuple[pygame.Vector2, pygame.Vector2],
        second_shape: pygame.Rect | tuple[pygame.Vector2, pygame.Vector2],
    ) -> bool:
        """Return overlap for a rectangular attack and an oval body."""
        if isinstance(first_shape, pygame.Rect):
            rectangle = first_shape
            ellipse_position, ellipse_radii = second_shape
        else:
            ellipse_position, ellipse_radii = first_shape
            rectangle = second_shape

        if ellipse_radii.x <= 0 or ellipse_radii.y <= 0:
            return False

        nearest_x = max(rectangle.left, min(ellipse_position.x, rectangle.right))
        nearest_y = max(rectangle.top, min(ellipse_position.y, rectangle.bottom))
        normalized_x = (nearest_x - ellipse_position.x) / ellipse_radii.x
        normalized_y = (nearest_y - ellipse_position.y) / ellipse_radii.y
        return normalized_x * normalized_x + normalized_y * normalized_y <= 1.0

    def _draw(self) -> None:
        self.screen.fill((24, 24, 24))
        self._draw_tiled_arena()
        if self.dummy.is_alive:
            self.dummy.draw(self.screen, self.camera)
        if self.attacking_dummy.is_alive:
            self.attacking_dummy.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        self.damage_feedback.draw(self.screen, self.camera, self.damage_font)
        if self.debug_collision_boxes:
            self._draw_debug_collision_boxes()
        self._draw_player_hud()
        pygame.display.flip()

    def _draw_player_hud(self) -> None:
        """Draw the player's health bar in fixed screen-space coordinates."""
        margin = 20
        bar_width = 260
        bar_height = 24
        label = self.hud_font.render("PLAYER HEALTH", True, (245, 245, 245))
        self.screen.blit(label, (margin, margin))

        bar_rect = pygame.Rect(
            margin,
            margin + label.get_height() + 6,
            bar_width,
            bar_height,
        )
        pygame.draw.rect(self.screen, (45, 18, 18), bar_rect)

        health_ratio = 0.0
        if self.player.max_health > 0:
            health_ratio = max(0.0, min(1.0, self.player.health / self.player.max_health))
        health_rect = pygame.Rect(
            bar_rect.left,
            bar_rect.top,
            round(bar_rect.width * health_ratio),
            bar_rect.height,
        )
        pygame.draw.rect(self.screen, (205, 48, 48), health_rect)
        pygame.draw.rect(self.screen, (245, 225, 225), bar_rect, 2)

        value_text = self.hud_font.render(
            f"{self.player.health} / {self.player.max_health}",
            True,
            (255, 255, 255),
        )
        value_position = (
            bar_rect.centerx - value_text.get_width() // 2,
            bar_rect.centery - value_text.get_height() // 2,
        )
        self.screen.blit(value_text, value_position)

    def _draw_debug_collision_boxes(self) -> None:
        """Draw collision geometry for player combat testing."""
        player_position, player_radii = self.player.collision_ellipse
        self._draw_world_ellipse(player_position, player_radii, (70, 170, 255), "PLAYER")

        attack_hitbox = self.player.get_attack_hitbox()
        if attack_hitbox is not None:
            self._draw_world_rect(attack_hitbox, (245, 80, 70), "ATTACK")

        if self.dummy.is_alive:
            self._draw_world_ellipse(*self.dummy.collision_ellipse, (255, 215, 70), "DUMMY")
        if self.attacking_dummy.is_alive:
            self._draw_world_ellipse(*self.attacking_dummy.collision_ellipse, (255, 145, 55), "ATTACKER")
            attacker_hitbox = self.attacking_dummy.get_attack_hitbox()
            if attacker_hitbox is not None:
                self._draw_world_rect(attacker_hitbox, (255, 80, 180), "ENEMY ATTACK")

        debug_text = self.debug_font.render(
            "F3: hide collision boxes",
            True,
            (245, 245, 245),
        )
        self.screen.blit(debug_text, (16, 16))

    def _draw_world_rect(
        self,
        world_rect: pygame.Rect,
        color: tuple[int, int, int],
        label: str,
    ) -> None:
        top_left = self.camera.world_to_screen(pygame.Vector2(world_rect.topleft))
        bottom_right = self.camera.world_to_screen(pygame.Vector2(world_rect.bottomright))
        screen_rect = pygame.Rect(
            round(top_left.x),
            round(top_left.y),
            round(bottom_right.x - top_left.x),
            round(bottom_right.y - top_left.y),
        )
        pygame.draw.rect(self.screen, color, screen_rect, max(1, round(self.camera.zoom)))
        label_surface = self.debug_font.render(label, True, color)
        self.screen.blit(label_surface, (screen_rect.left, screen_rect.top - label_surface.get_height()))

    def _draw_world_ellipse(
        self,
        world_position: pygame.Vector2,
        world_radii: pygame.Vector2,
        color: tuple[int, int, int],
        label: str,
    ) -> None:
        screen_position = self.camera.world_to_screen(world_position)
        screen_size = (
            max(2, round(world_radii.x * 2 * self.camera.zoom)),
            max(2, round(world_radii.y * 2 * self.camera.zoom)),
        )
        screen_rect = pygame.Rect(0, 0, *screen_size)
        screen_rect.center = (round(screen_position.x), round(screen_position.y))
        pygame.draw.ellipse(
            self.screen,
            color,
            screen_rect,
            max(1, round(self.camera.zoom)),
        )
        label_surface = self.debug_font.render(label, True, color)
        self.screen.blit(
            label_surface,
            (
                round(screen_position.x - label_surface.get_width() / 2),
                screen_rect.top - label_surface.get_height(),
            ),
        )

    def _draw_tiled_arena(self) -> None:
        tile_width, tile_height = self.floor_tile.get_size()
        camera_position = self.camera.position
        visible_world_width = SCREEN_SIZE[0] / self.camera.zoom
        visible_world_height = SCREEN_SIZE[1] / self.camera.zoom
        scaled_tile = pygame.transform.scale(
            self.floor_tile,
            (
                round(tile_width * self.camera.zoom),
                round(tile_height * self.camera.zoom),
            ),
        )

        first_tile_x = max(
            0,
            int((camera_position.x - visible_world_width / 2) // tile_width) - 1,
        )
        last_tile_x = min(
            self.world_rect.width // tile_width,
            int((camera_position.x + visible_world_width / 2) // tile_width) + 2,
        )
        first_tile_y = max(
            0,
            int((camera_position.y - visible_world_height / 2) // tile_height) - 1,
        )
        last_tile_y = min(
            self.world_rect.height // tile_height,
            int((camera_position.y + visible_world_height / 2) // tile_height) + 2,
        )

        for tile_y in range(first_tile_y, last_tile_y):
            for tile_x in range(first_tile_x, last_tile_x):
                world_position = pygame.Vector2(tile_x * tile_width, tile_y * tile_height)
                screen_position = self.camera.world_to_screen(world_position)
                self.screen.blit(
                    scaled_tile,
                    (round(screen_position.x), round(screen_position.y)),
                )
