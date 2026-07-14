"""敵機能(担当: 
"""

from __future__ import annotations

from game.core import Feature, FPSGame, GameObject

class Enemies(Feature):

    name = "敵"

    def setup(self, game: FPSGame) -> None:
        self.game = game  
        self.enemies: list[GameObject] = []

        self.defeated_count = 0     # プレイヤーが倒した敵の合計数
        self.required_kills = 12    # クリアに必要な討伐数

        # 敵の種類ごとの設定を辞書（データテーブル）として定義する
        enemy_configs = {
            "E": {"style": "grunt",  "hp": 3,  "speed": 1.4, "score": 100,  "color": (180, 45, 40),  "height": None},
            "I": {"style": "imp",    "hp": 1,  "speed": 2.2, "score": 100,  "color": (234, 96, 158), "height": None}, 
            "B": {"style": "brute",  "hp": 5,  "speed": 0.7, "score": 300,  "color": (29, 80, 162),  "height": 1.8},  
            "T": {"style": "turret", "hp": 4,  "speed": 0.0, "score": 200,  "color": (0, 169, 104),  "height": 1.1}, 
            "O": {"style": "boss",   "hp": 12, "speed": 1.2, "score": 1000, "color": (33, 33, 33),   "height": 2.2},  
        }

        for char, config in enemy_configs.items():
            for x, z in game.find_cells(char):
                enemy = game.spawn_character(x, z, color=config["color"], style=config["style"], name="enemy")

                enemy.data["mode"] = "patrol"
                enemy.data["patrol_target"] = game.random_open_cell()  

                enemy.data["style"] = config["style"]
                enemy.data["hp"] = config["hp"]
                enemy.data["speed"] = config["speed"]
                enemy.data["score"] = config["score"]
                enemy.data["base_color"] = config["color"] 
                enemy.data["attack_cooldown"] = 0.0
                
                if config["height"] is not None:
                    game.add_target(enemy, height=config["height"], on_hit=self.on_shot)
                else:
                    game.add_target(enemy, on_hit=self.on_shot)
                
                self.enemies.append(enemy)

    def update(self, game: FPSGame, dt: float) -> None:
        for enemy in self.enemies:
            enemy.data["attack_cooldown"] = max(0.0, enemy.data["attack_cooldown"] - dt)

            dist = game.distance_to_player(enemy)
            can_see = game.can_see(enemy, game.player)

            # 1. 状態遷移
            if can_see:
                enemy.data["mode"] = "chase"
            else:
                enemy.data["mode"] = "patrol"

            # 2. 遠距離攻撃
            if can_see and 3.0 <= dist <= 9.0:
                if enemy.data["attack_cooldown"] <= 0.0:
                    game.enemy_fire(enemy, damage=8)
                    enemy.data["attack_cooldown"] = 5.0 
                continue # 射程内にいる時は立ち止まって撃つため、以下の移動処理をスキップ

            # 3. 各モードの移動と近接攻撃
            if enemy.data["mode"] == "chase":
                # 追跡移動
                if dist > 1.0:
                    enemy.move_towards(game.player.x, game.player.z, speed=enemy.data["speed"], dt=dt)
                
                # 近接攻撃
                if game.near_player(enemy, 1.1) and enemy.data["attack_cooldown"] <= 0.0:
                    game.damage_player(12)
                    enemy.data["attack_cooldown"] = 0.9

            elif enemy.data["mode"] == "patrol":
                # 巡回移動
                target_cell = enemy.data["patrol_target"]
                
                if target_cell is not None:
                    tx, tz = target_cell
                    enemy.move_towards(tx, tz, speed=enemy.data["speed"] * 0.7, dt=dt)

                    dx = tx - enemy.x
                    dz = tz - enemy.z
                    dist_to_target = (dx**2 + dz**2)**0.5

                    if dist_to_target < 0.5:
                        enemy.data["patrol_target"] = game.random_open_cell()

    def on_shot(self, enemy: GameObject, damage: int) -> None:
        game = self.game
        enemy.data["hp"] -= damage
        if enemy.data["hp"] > 0:
            enemy.set_color((255, 255, 255))
            game.after(0.1, lambda: enemy.set_color(enemy.data["base_color"]))
            return

        game.spawn_particles(enemy.x, 1.0, enemy.z, color=(255, 120, 40), count=16, speed=4.0)

        # 記憶させておいたスタイルを変数に入れる
        e_style = enemy.data["style"]
        
        saved_config = {
            "style": e_style,
            "hp_max": 12 if e_style == "boss" else (5 if e_style == "brute" else (4 if e_style == "turret" else 3)),
            "speed": enemy.data["speed"],
            "score": enemy.data["score"],
            "color": enemy.data["base_color"],
            "height": 1.8 if e_style == "brute" else (1.1 if e_style == "turret" else (2.2 if e_style == "boss" else None))
        }
        
        game.after(5.0, lambda: self.respawn_enemy(saved_config))

        enemy.remove()
        self.enemies.remove(enemy)
        game.score += enemy.data["score"]
        
        self.defeated_count += 1 
        
        game.emit("enemy_defeated", {"defeated": self.defeated_count, "target": self.required_kills})
        
        if self.defeated_count >= self.required_kills:
            game.win("EZLOL")
    
    def respawn_enemy(self, config: dict) -> None:
        if self.defeated_count >= self.required_kills:
            return

        cell = self.game.random_open_cell()
        if cell is None:
            return
        x, z = cell

        enemy = self.game.spawn_character(x, z, color=config["color"], style=config["style"], name="enemy")

        enemy.data["mode"] = "patrol"
        enemy.data["patrol_target"] = self.game.random_open_cell()

        enemy.data["style"] = config["style"]
        enemy.data["hp"] = config["hp_max"]
        enemy.data["speed"] = config["speed"]
        enemy.data["score"] = config["score"]
        enemy.data["base_color"] = config["color"]
        enemy.data["attack_cooldown"] = 0.0

        if config["height"] is not None:
            self.game.add_target(enemy, height=config["height"], on_hit=self.on_shot)
        else:
            self.game.add_target(enemy, on_hit=self.on_shot)

        self.enemies.append(enemy)
        self.game.spawn_particles(x, 1.0, z, color=config["color"], count=8, speed=2.0)