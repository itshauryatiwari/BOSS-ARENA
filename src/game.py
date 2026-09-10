from __future__ import annotations

import math
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
        self.heart_sprites = self._load_heart_sprites()

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

    def _load_heart_sprites(self) -> dict[str, pygame.Surface]:
        """Load the full, half, and empty pixel-art heart HUD sprites."""
        heart_directory = self.assets_directory / "ui"
        return {
            state: pygame.image.load(heart_directory / f"heart_{state}.png").convert_alpha()
            for state in ("full", "half", "empty")
        }

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
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                self.player.start_roll()
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
        self.camera.update_shake(delta_time)
        self.camera.follow(self.player.position)

    def _check_dummy_hit(self) -> None:
        """Apply one player damage instance per sword swing to each target."""
        if self.player.attack_has_hit:
            return

        attack_arc = self.player.get_attack_arc()
        if attack_arc is None:
            return

        hit_registered = False
        if self.dummy.is_alive and self._arc_overlaps_ellipse(
            attack_arc,
            self.dummy.collision_ellipse,
        ):
            dealt_damage = self.dummy.take_damage(self.player.attack_damage)
            if dealt_damage > 0:
                self.damage_feedback.add_damage(self.dummy.position, dealt_damage)
            hit_registered = True

        if self.attacking_dummy.is_alive and self._arc_overlaps_ellipse(
            attack_arc,
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

        attack_arc = self.attacking_dummy.get_attack_arc()
        if attack_arc is not None and self._arc_overlaps_ellipse(
            attack_arc,
            self.player.collision_ellipse,
        ):
            if self.player.is_invulnerable:
                self.attacking_dummy.attack_has_hit = True
                return

            block_arc = self.player.get_block_arc()
            is_blocking_attack = block_arc is not None and self._arc_overlaps_ellipse(
                block_arc,
                self.attacking_dummy.collision_ellipse,
            )
            blocked_attack = is_blocking_attack and self.player.consume_block_stamina()
            if not blocked_attack:
                dealt_damage = self.player.take_damage(self.attacking_dummy.attack_damage)
                if dealt_damage > 0:
                    self.damage_feedback.add_damage(self.player.position, dealt_damage)
                    self.camera.shake(duration=0.14, strength=3.0)
            self.attacking_dummy.attack_has_hit = True

    @staticmethod
    def _arc_overlaps_ellipse(
        arc: tuple[pygame.Vector2, float, float, float],
        ellipse: tuple[pygame.Vector2, pygame.Vector2],
    ) -> bool:
        """Return whether an active sword arc reaches an oval body collider."""
        arc_center, arc_angle, reach, half_width = arc
        ellipse_position, ellipse_radii = ellipse
        if ellipse_radii.x <= 0 or ellipse_radii.y <= 0:
            return False

        offset = ellipse_position - arc_center
        distance = offset.length()
        if distance > reach + max(ellipse_radii.x, ellipse_radii.y):
            return False
        if distance <= 0.001:
            return True

        target_angle = math.degrees(math.atan2(-offset.y, offset.x)) % 360
        angle_delta = abs((target_angle - arc_angle + 180) % 360 - 180)
        angular_radius = math.degrees(
            math.atan2(max(ellipse_radii.x, ellipse_radii.y), max(distance, 0.001))
        )
        return angle_delta <= half_width + angular_radius

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
        """Draw ten Minecraft-style heart slots in fixed screen-space coordinates."""
        margin = 20
        label = self.hud_font.render("PLAYER HEALTH", True, (245, 245, 245))
        self.screen.blit(label, (margin, margin))

        heart_size = self.heart_sprites["full"].get_width()
        heart_gap = 2
        heart_y = margin + label.get_height() + 6
        health_points = max(0, min(self.player.max_health, self.player.health))
        hearts = max(1, (self.player.max_health + 9) // 10)

        for heart_index in range(hearts):
            heart_value = health_points - heart_index * 10
            if heart_value >= 10:
                state = "full"
            elif heart_value >= 5:
                state = "half"
            else:
                state = "empty"

            heart_x = margin + heart_index * (heart_size + heart_gap)
            self.screen.blit(self.heart_sprites[state], (heart_x, heart_y))

        stamina_label = self.hud_font.render("STAMINA", True, (245, 245, 245))
        stamina_label_y = heart_y + heart_size + 8
        self.screen.blit(stamina_label, (margin, stamina_label_y))

        segment_y = stamina_label_y + stamina_label.get_height() + 4
        segment_width = 56
        segment_height = 12
        segment_gap = 4
        stamina_ratio = 0.0
        if self.player.max_stamina > 0:
            stamina_ratio = max(0.0, min(1.0, self.player.stamina / self.player.max_stamina))
        segment_count = max(1, round(self.player.max_stamina))
        for segment_index in range(segment_count):
            segment_x = margin + segment_index * (segment_width + segment_gap)
            segment_rect = pygame.Rect(segment_x, segment_y, segment_width, segment_height)
            segment_start = segment_index / segment_count
            segment_end = (segment_index + 1) / segment_count
            fill_ratio = max(0.0, min(1.0, (stamina_ratio - segment_start) / (segment_end - segment_start)))
            pygame.draw.rect(self.screen, (32, 42, 52), segment_rect)
            pygame.draw.rect(
                self.screen,
                (62, 170, 220),
                pygame.Rect(segment_rect.left, segment_rect.top, round(segment_rect.width * fill_ratio), segment_rect.height),
            )
            pygame.draw.rect(self.screen, (210, 235, 245), segment_rect, 1)

    def _draw_debug_collision_boxes(self) -> None:
        """Draw collision geometry for player combat testing."""
        player_position, player_radii = self.player.collision_ellipse
        self._draw_world_ellipse(player_position, player_radii, (70, 170, 255), "PLAYER")

        attack_arc = self.player.get_attack_arc()
        if attack_arc is not None:
            self._draw_world_arc(attack_arc, (245, 80, 70), "ATTACK")

        block_arc = self.player.get_block_arc()
        if block_arc is not None:
            self._draw_world_arc(block_arc, (80, 180, 255), "BLOCK")

        if self.dummy.is_alive:
            self._draw_world_ellipse(*self.dummy.collision_ellipse, (255, 215, 70), "DUMMY")
        if self.attacking_dummy.is_alive:
            self._draw_world_ellipse(*self.attacking_dummy.collision_ellipse, (255, 145, 55), "ATTACKER")
            attacker_arc = self.attacking_dummy.get_attack_arc()
            if attacker_arc is not None:
                self._draw_world_arc(attacker_arc, (255, 80, 180), "ENEMY ATTACK")

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

    def _draw_world_arc(
        self,
        arc: tuple[pygame.Vector2, float, float, float],
        color: tuple[int, int, int],
        label: str,
    ) -> None:
        world_position, angle, reach, half_width = arc
        screen_position = self.camera.world_to_screen(world_position)
        start_angle = math.radians(angle - half_width)
        end_angle = math.radians(angle + half_width)
        points = [(round(screen_position.x), round(screen_position.y))]
        for step in range(13):
            current_angle = start_angle + (end_angle - start_angle) * step / 12
            world_point = world_position + pygame.Vector2(
                math.cos(current_angle) * reach,
                -math.sin(current_angle) * reach,
            )
            screen_point = self.camera.world_to_screen(world_point)
            points.append((round(screen_point.x), round(screen_point.y)))
        pygame.draw.lines(self.screen, color, False, points, max(1, round(self.camera.zoom)))
        label_surface = self.debug_font.render(label, True, color)
        self.screen.blit(
            label_surface,
            (round(screen_position.x), round(screen_position.y - label_surface.get_height())),
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
