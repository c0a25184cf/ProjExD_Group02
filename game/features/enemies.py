"""敵機能(担当: 
"""

from __future__ import annotations

from game.core import Feature, FPSGame, GameObject

class Enemies(Feature):

    name = "敵"

    def setup(self, game: FPSGame) -> None:
        self.game = game  
        self.enemies: list[GameObject] = []

        # 1. 敵の種類ごとの設定を辞書（データテーブル）として定義する
        # マップ文字: {スタイル, HP, 移動速度, 撃破スコア, 色, 高さ}
        enemy_configs = {
            "E": {"style": "grunt",  "hp": 3,  "speed": 1.4, "score": 100,  "color": (180, 45, 40),  "height": None},
            "I": {"style": "imp",    "hp": 1,  "speed": 2.2, "score": 100,  "color": (140, 50, 160), "height": None}, # 足が速い
            "B": {"style": "brute",  "hp": 5,  "speed": 0.7, "score": 300,  "color": (29, 80, 162),  "height": 1.8},  # タフで大型
            "T": {"style": "turret", "hp": 4,  "speed": 1.0, "score": 200,  "color": (0, 169, 104), "height": 1.1}, # 動かない砲台
            "O": {"style": "boss",   "hp": 12, "speed": 1.2, "score": 1000, "color": (33, 33, 33),     "height": 2.2},  # 超大型ボス
        }

        for char, config in enemy_configs.items():
            for x, z in game.find_cells("E"):
                enemy = game.spawn_character(x, z, color=(180, 45, 40), style="grunt", name="enemy")

                enemy.data["mode"] = "patrol"
                enemy.data["patrol_target"] = game.random_open_cell()  # 最初の巡回先を決める

                enemy.data["hp"] = config["hp"]
                enemy.data["speed"] = config["speed"]
                enemy.data["score"] = config["score"]
                enemy.data["base_color"] = config["color"] # 点滅から元の色に戻すために記憶
                enemy.data["attack_cooldown"] = 0.0

                # enemy.data["hp"] = 3
                # enemy.data["attack_cooldown"] = 0.0
                
                if config["height"] is not None:
                    game.add_target(enemy, height=config["height"], on_hit=self.on_shot)
                else:
                    game.add_target(enemy, on_hit=self.on_shot)
                
                self.enemies.append(enemy)

                # game.add_target(enemy, on_hit=self.on_shot) 
                # self.enemies.append(enemy)

    def update(self, game: FPSGame, dt: float) -> None:
        for enemy in self.enemies:
            enemy.data["attack_cooldown"] = max(0.0, enemy.data["attack_cooldown"] - dt)

            dist = game.distance_to_player(enemy)
            can_see = game.can_see(enemy, game.player)

            if can_see:
                # プレイヤーが見えたら追跡モードに切り替え
                enemy.data["mode"] = "chase"
            else:
                # プレイヤーを見失ったら巡回モードに戻す
                enemy.data["mode"] = "patrol"

            if enemy.data["mode"] == "chase":
                # 【追跡モードの挙動】
                # ※前回の遠距離攻撃タスクが残っている場合は、ここに遠距離攻撃の処理を挟んでもOKです
                
                # 距離が 1.0 より離れているならプレイヤーに向かって近づく
                if dist > 1.0:
                    enemy.move_towards(game.player.x, game.player.z, speed=enemy.data["speed"], dt=dt)

            elif enemy.data["mode"] == "patrol":
                # 【巡回モードの挙動】
                # 現在設定されている巡回先の座標 (x, z) を取得
                target_cell = enemy.data["patrol_target"]
                
                if target_cell is not None:
                    tx, tz = target_cell
                    enemy.move_towards(tx, tz, speed=enemy.data["speed"] * 0.7, dt=dt)

                    # 巡回先に十分近づいたかどうかを判定（例: 距離が 0.5 未満になったら到着）
                    # 敵の現在地からターゲット座標までの距離を計算
                    dx = tx - enemy.x
                    dz = tz - enemy.z
                    dist_to_target = (dx**2 + dz**2)**0.5

                    if dist_to_target < 0.5:
                        # 目的地に到着したので、新しい巡回先をランダムに設定する
                        enemy.data["patrol_target"] = game.random_open_cell()

                if enemy.data["mode"] == "chase" and game.near_player(enemy, 1.1) and enemy.data["attack_cooldown"] <= 0.0:
                    game.damage_player(12)
                enemy.data["attack_cooldown"] = 0.9

            if can_see and 3.0 <= dist <= 9.0:
                # クールダウンが終わっていれば射撃
                if enemy.data["attack_cooldown"] <= 0.0:
                    game.enemy_fire(enemy, damage=8)
                    # 射撃後のクールダウン（例: 5秒間は次の弾を撃てない）
                    enemy.data["attack_cooldown"] = 5 
                continue

            if game.can_see(enemy, game.player) and game.distance_to_player(enemy) > 1.0:
                enemy.move_towards(game.player.x, game.player.z, speed=enemy.data["speed"], dt=dt)

            if game.near_player(enemy, 1.1) and enemy.data["attack_cooldown"] <= 0.0:
                game.damage_player(12)
                enemy.data["attack_cooldown"] = 0.9

    def on_shot(self, enemy: GameObject, damage: int) -> None:
        game = self.game
        enemy.data["hp"] -= damage
        if enemy.data["hp"] > 0:
            enemy.set_color((255, 255, 255))
            game.after(0.1, lambda: enemy.set_color(enemy.data["base_color"]))
            return

        game.spawn_particles(enemy.x, 1.0, enemy.z, color=(255, 120, 40), count=16, speed=4.0)
        enemy.remove()
        self.enemies.remove(enemy)
        game.score += enemy.data["score"]
        game.emit("enemy_defeated", {"remaining": len(self.enemies)})
        if not self.enemies:
            game.win("EZLOL")
