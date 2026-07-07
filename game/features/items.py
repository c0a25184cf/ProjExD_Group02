"""アイテム機能(担当:吉荒倖汰 
"""
import math
from __future__ import annotations

from typing import Any

from game.core import Feature, FPSGame, GameObject
class Items(Feature):
    """マップのHに回復パック、Aに弾薬パックを置き、触れたら拾えるようにする。"""

    name = "アイテム"

    def setup(self, game: FPSGame) -> None:
        self.game = game
        self.health_packs: list[GameObject] = [
            game.spawn_pickup(x, z, color=(74, 220, 92), name="health")
            for x, z in game.find_cells("H")
        ]
        self.ammo_packs: list[GameObject] = [
            game.spawn_pickup(x, z, color=(85, 172, 255), name="ammo")
            for x, z in game.find_cells("A")
        ]

    def update(self, game: FPSGame, dt: float) -> None:
        # 追記: 全てのアイテム（回復パックと弾薬パック）をふわふわ回転させる
        for pack in self.health_packs + self.ammo_packs:
            pack.yaw += dt * 2.0
            pack.y = 0.3 + math.sin(game.time * 3.0) * 0.08

        for pack in self.health_packs[:]:
            if game.near_player(pack, 0.7) and game.player.health < game.player.max_health:
                game.heal_player(25)
                self._take(pack, self.health_packs)

        for pack in self.ammo_packs[:]:
            if game.near_player(pack, 0.7) and game.player.ammo < game.player.max_ammo:
                game.player.ammo = min(game.player.max_ammo, game.player.ammo + 15)
                game.flash((70, 170, 255), 0.25)
                self._take(pack, self.ammo_packs)

    def _take(self, pack: GameObject, group: list[GameObject]) -> None:

        self.game.spawn_particles(pack.x, 0.5, pack.z, color=(240, 240, 240), count=8, speed=2.0)
        self.game.emit("item_picked", {"kind": pack.name})
        pack.remove()
        group.remove(pack)
