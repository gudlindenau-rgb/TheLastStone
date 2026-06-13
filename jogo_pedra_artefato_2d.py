import math
import random
import sys

import pygame


def clamp(x, a, b):
    return a if x < a else b if x > b else x


# Jogo 2D: você é uma "pedra de óculos" (personagem). Ela atira e mata "gravetos".
# Controles:
#   - Setas/A/D/W/S: movimento
#   - ESPAÇO: disparar (tiro rápido)
#   - R: reiniciar
# Objetivo: sobreviver e eliminar gravetos.


W, H = 960, 540
FPS = 60


BG = (10, 12, 18)
HUD = (220, 230, 255)
GRID = (18, 22, 34)


def main():
    pygame.init()
    pygame.display.set_caption(" Pedra de Óculos vs Gravêtos (2D)")


    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 24)
    big = pygame.font.SysFont(None, 44)

    rng = random.Random(7)

    # Player
    p = {
        "x": W / 2,
        "y": H / 2,
        "r": 18,
        "hp": 100,
        "speed": 330.0,
    }

    # Tiros
    bullets = []
    # Gravêtos (inimigos)
    enemies = []

    # Efeitos visuais
    sparks = []

    # Estado
    state = "MENU"  # MENU, PLAY, GAMEOVER
    score = 0
    wave_time = 0.0

    # Evolução/escala: contagem de kills
    kill_streak = 0
    next_unlock = 30

    # Boss: a cada 100 gravêtos eliminados aparece o "graveto líder"
    BOSS_EVERY = 100
    boss = None
    boss_phase = 0
    boss_attack_cd = 0.0
    boss_attack_name = ""

    # Ataques auxiliares do boss
    spikes = []          # espinhos no chão: {x,y,life,r,dmg}
    electric_zaps = []  # raios ativos: {x1,y1,x2,y2,life}
    elec_explosions = []# explosões: {x,y,life,stage}

    # Escolha (melhoria/maldição) - mantido, mas atualmente desativado
    choice_pending = False
    choice_options = []  # lista de strings
    choice_row = 0
    choice_cooldown = 0.0

    # Efeitos no player
    effects = {
        "damage_mult": 1.0,   # dano das balas
        "fire_rate_mult": 1.0, # cadência
        "speed_mult": 1.0,     # velocidade do player
        "hp_regen": 0.0,        # HP/s
    }



    def reset():
        nonlocal bullets, enemies, sparks, state, score, wave_time, p
        bullets = []
        enemies = []
        sparks = []
        state = "PLAY"
        score = 0
        wave_time = 0.0
        p = {
            "x": W / 2,
            "y": H / 2,
            "r": 18,
            "hp": 100,
            "speed": 330.0,
        }

    def spawn_enemy():
        # Spawn fora do raio do jogador
        for _ in range(200):
            side = rng.choice([0, 1, 2, 3])
            if side == 0:
                x, y = rng.uniform(0, W), -30
            elif side == 1:
                x, y = rng.uniform(0, W), H + 30
            elif side == 2:
                x, y = -30, rng.uniform(0, H)
            else:
                x, y = W + 30, rng.uniform(0, H)

            d = math.hypot(x - p["x"], y - p["y"])
            if d > 220:
                # Graveto: velocidade/HP variam com base no tempo
                base_speed = 85.0
                hp = 1
                spd = base_speed + 10.0 * (wave_time / 20.0)
                if rng.random() < 0.18:
                    hp = 2
                    spd *= 1.25
                enemies.append({"x": x, "y": y, "r": 10, "hp": hp, "spd": spd})
                return

        # fallback
        enemies.append({"x": rng.uniform(0, W), "y": rng.uniform(0, H), "r": 10, "hp": 1, "spd": 95.0})

    def shoot():
        # Tiro "ray" com pequenas variações
        # A direção é para o mouse.
        mx, my = pygame.mouse.get_pos()
        dx = mx - p["x"]
        dy = my - p["y"]
        ang = math.atan2(dy, dx)

        # Spread leve estilo DOOM
        spread = rng.uniform(-0.02, 0.02)
        ang += spread

        speed = 720.0
        damage = 1
        bullet_r = 4
        bullets.append(
            {
                "x": p["x"],
                "y": p["y"],
                "vx": math.cos(ang) * speed,
                "vy": math.sin(ang) * speed,
                "r": bullet_r,
                "damage": damage,
                "life": 0.95,
            }
        )

    # Cooldown de tiro
    shoot_cd = 0.0
    shoot_rate = 0.085  # segundos (base)

        # Recarga do tiro bomba (botão direito)
    bomb_fire_time = 0.0  # tempo acumulado de abuso/uso
    bomb_overheat_threshold = 10.0  # após 10s usando, entra recarga
    bomb_cooldown = 0.0
    bomb_reload_time = 20.0

    # Munição do tiro bomba: 100/100 (recarrega quando bomb_cooldown > 0)
    bomb_ammo_max = 100
    bomb_ammo = bomb_ammo_max




    # Menu
    menu_options = ["JOGAR", "CONFIGURAÇÕES", "SAIR"]
    menu_row = 0

    # Controles
    def handle_input(dt):
        nonlocal shoot_cd, choice_pending, choice_options, choice_row, choice_cooldown, bomb_fire_time, bomb_cooldown, bomb_overheat_threshold, bomb_reload_time, bomb_ammo, bomb_ammo_max




        # MENU ATIVO: pausa total (sem mover player, sem cooldown, sem tiro)
        if choice_pending:
            pygame.event.clear((pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN))
            for event in pygame.event.get([pygame.KEYDOWN]):
                if event.key in (pygame.K_w, pygame.K_UP):
                    if choice_options:
                        choice_row = (choice_row - 1) % len(choice_options)
                if event.key in (pygame.K_s, pygame.K_DOWN):
                    if choice_options:
                        choice_row = (choice_row + 1) % len(choice_options)

                if event.key == pygame.K_SPACE:
                    # confirma
                    if choice_cooldown <= 0.0:
                        selected = choice_options[choice_row] if choice_options else None
                        choice_pending = False
                        choice_cooldown = 0.6

                        # aplica melhorias/maldições
                        if selected:
                            if "MELHORIA" in selected:
                                if "DANO" in selected:
                                    effects["damage_mult"] *= 1.25
                                elif "CAD" in selected:
                                    effects["fire_rate_mult"] *= 1.15
                                elif "VEL" in selected:
                                    effects["speed_mult"] *= 1.12
                                elif "HP" in selected:
                                    p["hp"] = min(100, p["hp"] + 30)
                            else:
                                if "DANO" in selected:
                                    effects["damage_mult"] *= 0.8
                                elif "CAD" in selected:
                                    effects["fire_rate_mult"] *= 0.85
                                elif "VEL" in selected:
                                    effects["speed_mult"] *= 0.9
                                elif "HP" in selected:
                                    p["hp"] = max(1, p["hp"] - 25)

            return

        keys = pygame.key.get_pressed()

        vx = 0.0
        vy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            vy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            vy += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            vx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            vx += 1.0

        # Normaliza diagonal
        if vx != 0.0 or vy != 0.0:
            mag = math.hypot(vx, vy)
            vx /= mag
            vy /= mag

        p["x"] += vx * p["speed"] * dt
        p["y"] += vy * p["speed"] * dt
        p["x"] = clamp(p["x"], p["r"], W - p["r"])
        p["y"] = clamp(p["y"], p["r"], H - p["r"])

        if shoot_cd > 0:
            shoot_cd -= dt

        # Cadência/tiro
        mouse_pressed = pygame.mouse.get_pressed(num_buttons=3)
        left_down = mouse_pressed[0]
        right_down = mouse_pressed[2]

        # recarga do tiro bomba: enquanto NÃO estiver usando (botão direito solto), o sistema recarrega.
        # Ao apertar/segurar o botão direito, a recarga pausa (e o tiro só acontece se houver ammo).
        # Isso cria o comportamento desejado: “quando eu não estiver usando o tiro bomba ele entra em modo de recarga”.

        using_bomb = right_down and bomb_cooldown <= 0.0

        # sempre reduz cooldown (se estiver ativo)
        if bomb_cooldown > 0:
            bomb_cooldown -= dt
            if bomb_cooldown < 0:
                bomb_cooldown = 0.0

        # recarga só quando não está usando o botão direito
        if (not right_down) and bomb_cooldown <= 0.0 and bomb_ammo < bomb_ammo_max:
            bomb_ammo = min(
                bomb_ammo_max,
                bomb_ammo + (bomb_ammo_max / bomb_reload_time) * dt,
            )

        # “abuso”/acúmulo de uso (mantido mas não bloqueia o comportamento de recarga)
        if using_bomb:
            bomb_fire_time += dt
        else:
            bomb_fire_time = max(0.0, bomb_fire_time - dt * 0.5)



        # botão esquerdo/SPACE: tiro normal

        if (keys[pygame.K_SPACE] or left_down) and shoot_cd <= 0.0 and state == "PLAY":
            shoot()
            shoot_cd = shoot_rate

        # botão direito: tiro especial que explode (carrega “bomba”)
        # (para manter simples, faz um projétil com dano maior que também destrói orbs 'bomba')
        # BUGFIX: consumir munição e não atirar com ammo=0.
        if (
            right_down
            and shoot_cd <= 0.0
            and state == "PLAY"
            and bomb_ammo > 0
        ):
            # gasta 1 munição por tiro
            bomb_ammo -= 1

            # usa a mesma função shoot(), mas aumenta damage para parecer “tiro explosivo”
            mx, my = pygame.mouse.get_pos()
            dx = mx - p["x"]
            dy = my - p["y"]
            ang = math.atan2(dy, dx)


            spread = rng.uniform(-0.01, 0.01)
            ang += spread

            speed = 720.0
            damage = 1.0
            bullet_r = 5
            # aplica flag no bullet
            bullets.append(
                {
                    "x": p["x"],
                    "y": p["y"],
                    "vx": math.cos(ang) * speed,
                    "vy": math.sin(ang) * speed,
                    "r": bullet_r,
                    "damage": damage,
                    "life": 0.95,
                    "is_explosive": True,
                }
            )
            shoot_cd = shoot_rate * 1.2




    orbs = []

    orb_timer = 0.0

    # tipos: "regen", "bomba", "invoca"
    def spawn_orb():

        # tenta não spawnar perto do player
        for _ in range(30):
            x = rng.uniform(40, W - 40)
            y = rng.uniform(40, H - 40)
            if math.hypot(x - p["x"], y - p["y"]) > 140:
                orb_type = rng.choices(["regen", "bomba", "invoca"], weights=[0.45, 0.35, 0.20], k=1)[0]
                orbs.append({"x": x, "y": y, "type": orb_type, "r": 10})
                return
        # fallback: spawn central se falhar
        orb_type = rng.choices(["regen", "bomba", "invoca"], weights=[0.45, 0.35, 0.20], k=1)[0]
        orbs.append({"x": W / 2, "y": H / 2, "type": orb_type, "r": 10})

    def update(dt):
        nonlocal wave_time, score, state, choice_pending, choice_options, choice_row, choice_cooldown, orbs, orb_timer, kill_streak, next_unlock



        wave_time += dt



        # Spawn baseado em onda
        if state == "PLAY":
            # aumenta gradualmente
            spawn_rate = 0.65 + 0.08 * (wave_time / 20.0)  # gravetos por segundo (aprox)
            if rng.random() < spawn_rate * dt:
                spawn_enemy()

            # Orbs aparecem a cada 30s (Ultrawash)
            orb_timer += dt
            if orb_timer >= 30.0:
                spawn_orb()
                orb_timer = 0.0


        # bullets
        for b in bullets:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["life"] -= dt

            # bomba (tiro especial): gera “explosão” pelo caminho e destrói tudo que encostar
            if b.get("is_explosive"):
                boom_r = 28

                # remove enemies no raio e contabiliza kills
                # (não damos dano contínuo no player; só remove inimigos/orbs)
                alive_enemies_tmp = []
                for e in enemies:
                    if e["hp"] <= 0:
                        continue
                    if math.hypot(e["x"] - b["x"], e["y"] - b["y"]) <= boom_r:
                        e["hp"] = 0
                        score += 1
                        # kill_streak/next_unlock: ignorados neste efeito para evitar dependência de nonlocal

                        if kill_streak >= next_unlock:
                            next_unlock += 30
                            wave_time += 2.5
                            choice_pending = False
                            choice_row = 0
                            choice_options = []
                    else:
                        alive_enemies_tmp.append(e)
                enemies[:] = alive_enemies_tmp


                # elimina orbs no raio (todo tipo)
                orbs[:] = [o for o in orbs if math.hypot(o["x"] - b["x"], o["y"] - b["y"]) > boom_r]

                # partículas do “boom”
                for _ in range(18):
                    ang = rng.uniform(0, 2 * math.pi)
                    spd = rng.uniform(160, 420)
                    sparks.append(
                        {
                            "x": b["x"],
                            "y": b["y"],
                            "vx": math.cos(ang) * spd,
                            "vy": math.sin(ang) * spd,
                            "life": rng.uniform(0.12, 0.22),
                            "r": rng.uniform(2, 6),
                        }
                    )


        # remove bullets velhas ou fora
        bullets[:] = [b for b in bullets if b["life"] > 0 and -20 < b["x"] < W + 20 and -20 < b["y"] < H + 20]

        # enemies movement + collision
        # (durante o menu de escolha, o jogo fica pausado via loop; este update não roda)
        for e in enemies:

            # se stun/impact no futuro: manter simples
            dx = p["x"] - e["x"]
            dy = p["y"] - e["y"]
            distp = math.hypot(dx, dy)
            if distp > 1e-6:
                dx /= distp
                dy /= distp
            e["x"] += dx * e["spd"] * dt
            e["y"] += dy * e["spd"] * dt

            # colide com player
            if distp < (e["r"] + p["r"]):
                # dano por contato
                p["hp"] -= 18 * dt
                # empurra um pouco
                e["x"] -= dx * 25 * dt
                e["y"] -= dy * 25 * dt

        # orbs collide (com player e com tiros)
        alive_orbs = []
        for o in orbs:
            # player coleta orb
            if math.hypot(o["x"] - p["x"], o["y"] - p["y"]) < (o["r"] + p["r"]):
                # simples: regen cura; bomba remove gravetos próximos; invoca adiciona gravetos
                if o["type"] == "regen":
                    p["hp"] = min(100, p["hp"] + 40)
                elif o["type"] == "bomba":
                    # efeito de explosão (partículas bem visíveis)
                    for _ in range(70):
                        ang = rng.uniform(0, 2 * math.pi)
                        spd = rng.uniform(220, 520)
                        sparks.append(
                            {
                                "x": o["x"],
                                "y": o["y"],
                                "vx": math.cos(ang) * spd,
                                "vy": math.sin(ang) * spd,
                                "life": rng.uniform(0.20, 0.45),
                                "r": rng.uniform(3, 7),
                            }
                        )

                    # um anel/flash visual (cria “pseudo-partículas” maiores)
                    for _ in range(10):
                        ang = rng.uniform(0, 2 * math.pi)
                        sparks.append(
                            {
                                "x": o["x"] + math.cos(ang) * 6,
                                "y": o["y"] + math.sin(ang) * 6,
                                "vx": 0.0,
                                "vy": 0.0,
                                "life": 0.25,
                                "r": 10,
                            }
                        )

                    # remove inimigos num raio
                    new_enemies = []
                    for e in enemies:
                        if math.hypot(e["x"] - o["x"], e["y"] - o["y"]) > 140:
                            new_enemies.append(e)
                    enemies[:] = new_enemies


                else:  # invoca
                    # adiciona 3 gravetos
                    for _ in range(3):
                        spawn_enemy()
                continue

            # tiro destrói orb e gera o efeito (mesmo tipo do player)
            orb_killed = False
            for b in bullets:
                if b["life"] > 0 and math.hypot(b["x"] - o["x"], b["y"] - o["y"]) < (b["r"] + o["r"]):
                    b["life"] = 0.0
                    orb_killed = True
                    if o["type"] == "regen":
                        p["hp"] = min(100, p["hp"] + 20)
                    elif o["type"] == "bomba":
                        # explosão também ao orb `bomba` ser atingida pelo tiro
                        for _ in range(90):
                            ang = rng.uniform(0, 2 * math.pi)
                            spd = rng.uniform(240, 620)
                            sparks.append(
                                {
                                    "x": o["x"],
                                    "y": o["y"],
                                    "vx": math.cos(ang) * spd,
                                    "vy": math.sin(ang) * spd,
                                    "life": rng.uniform(0.18, 0.42),
                                    "r": rng.uniform(4, 10),
                                }
                            )

                        # flash/anel
                        for _ in range(14):
                            ang = rng.uniform(0, 2 * math.pi)
                            sparks.append(
                                {
                                    "x": o["x"] + math.cos(ang) * 8,
                                    "y": o["y"] + math.sin(ang) * 8,
                                    "vx": 0.0,
                                    "vy": 0.0,
                                    "life": 0.28,
                                    "r": 14,
                                }
                            )

                        new_enemies = []
                        for e in enemies:
                            if math.hypot(e["x"] - o["x"], e["y"] - o["y"]) > 140:
                                new_enemies.append(e)
                        enemies[:] = new_enemies

                    else:  # invoca
                        for _ in range(2):
                            spawn_enemy()

                    break

            if not orb_killed:
                alive_orbs.append(o)

        orbs[:] = alive_orbs

        # bullets vs enemies
        alive_enemies = []

        for e in enemies:
            if e["hp"] <= 0:
                continue

            for b in bullets:
                if math.hypot(b["x"] - e["x"], b["y"] - e["y"]) < (b["r"] + e["r"]):
                    e["hp"] -= b["damage"]
                    b["life"] = 0.0

                    # Se matou, contabiliza kill e evolui a cada 50
                    if e["hp"] <= 0:
                        kill_streak += 1
                        score += 1



                    if kill_streak >= next_unlock:
                            next_unlock += 30
                            wave_time += 2.5
                            # Menu removido: sem melhorias/maldições. Apenas acelera a onda.
                            # (Mantive a estrutura de kill_streak para preservar ritmo do jogo.)
                            choice_pending = False
                            choice_row = 0
                            choice_options = []






                    # sparks
                    for _ in range(6):
                        ang = rng.uniform(0, 2 * math.pi)
                        spd = rng.uniform(80, 240)
                        sparks.append(
                            {
                                "x": b["x"],
                                "y": b["y"],
                                "vx": math.cos(ang) * spd,
                                "vy": math.sin(ang) * spd,
                                "life": rng.uniform(0.15, 0.35),
                                "r": rng.uniform(1, 3),
                            }
                        )
                    break

            if e["hp"] > 0:
                alive_enemies.append(e)

        enemies[:] = alive_enemies

        # Handle gameover
        if state == "PLAY" and p["hp"] <= 0:
            p["hp"] = 0
            state = "GAMEOVER"

        # sparks update
        for s in sparks:
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["vy"] += 500 * dt
            s["life"] -= dt

        sparks[:] = [s for s in sparks if s["life"] > 0]

    def draw_grid():
        # grid sutil
        step = 40
        for x in range(0, W + 1, step):
            pygame.draw.line(screen, GRID, (x, 0), (x, H))
        for y in range(0, H + 1, step):
            pygame.draw.line(screen, GRID, (0, y), (W, y))

    def draw():
        # UI MENU inicial
        if state == "MENU":
            screen.fill(BG)
            draw_grid()
            title = big.render("TheLastStone", True, (130, 210, 255))
            screen.blit(title, (W // 2 - title.get_width() // 2, 120))

            subtitle = font.render("Pedra de oculos vs gravetos", True, (210, 230, 255))
            screen.blit(subtitle, (W // 2 - subtitle.get_width() // 2, 170))

            # Botões
            btn_w = 420
            btn_h = 44
            btn_x = W // 2 - btn_w // 2
            base_y = 265
            for i, opt in enumerate(menu_options):
                y = base_y + i * 58
                is_sel = (i == menu_row)

                bg_col = (70, 90, 160) if is_sel else (35, 45, 85)
                border_col = (255, 230, 120) if is_sel else (160, 170, 220)
                text_col = (255, 255, 255)

                rect = pygame.Rect(btn_x, y, btn_w, btn_h)
                pygame.draw.rect(screen, bg_col, rect, border_radius=10)
                pygame.draw.rect(screen, border_col, rect, width=3, border_radius=10)

                t = font.render(opt, True, text_col)
                screen.blit(t, (btn_x + btn_w // 2 - t.get_width() // 2, y + btn_h // 2 - t.get_height() // 2))

            help_txt = font.render("W/S ou setas: navegar | ENTER/ESPAÇO: confirmar | ESC: sair", True, (190, 190, 190))
            screen.blit(help_txt, (W // 2 - help_txt.get_width() // 2, H - 90))

            pygame.display.flip()
            return
        # Menu/Escolhas
        if False and choice_pending and state == "PLAY":

            # tela escura
            screen.fill((0, 0, 0))
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            title = big.render("ULTRAWASH", True, (130, 210, 255))
            screen.blit(title, (W // 2 - title.get_width() // 2, 90))

            prompt = font.render("Escolha 1 melhoria ou maldição", True, (240, 240, 240))
            screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 145))

            # opções
            for i in range(len(choice_options)):
                y = 210 + i * 48
                is_sel = (i == choice_row)
                col = (255, 230, 120) if is_sel else (220, 230, 255)
                t = font.render(choice_options[i], True, col)
                screen.blit(t, (W // 2 - t.get_width() // 2, y))

            help_txt = font.render("W/S ou SETAS: navegar | ESPAÇO: confirmar", True, (190, 190, 190))
            screen.blit(help_txt, (W // 2 - help_txt.get_width() // 2, H - 70))

            if choice_cooldown > 0:
                cd = font.render(f"Confirmar em: {choice_cooldown:.1f}", True, (255, 140, 140))
                screen.blit(cd, (W // 2 - cd.get_width() // 2, H - 35))

            pygame.display.flip()
            return

        # normal draw
        screen.fill(BG)
        draw_grid()


        # retículo
        mx, my = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (120, 170, 255), (int(mx), int(my)), 6, 2)

        # player: pedra de óculos (desenho simples)
        # corpo (pedra)
        pygame.draw.circle(screen, (120, 150, 255), (int(p["x"]), int(p["y"])), p["r"])
        # borda
        pygame.draw.circle(screen, (30, 60, 140), (int(p["x"]), int(p["y"])), p["r"], 3)
        # “óculos”
        lens_r = 7
        eye_dx = 8
        pygame.draw.circle(screen, (210, 230, 255), (int(p["x"] - eye_dx), int(p["y"])), lens_r, 2)
        pygame.draw.circle(screen, (210, 230, 255), (int(p["x"] + eye_dx), int(p["y"])), lens_r, 2)
        # ponte
        pygame.draw.line(
            screen,
            (210, 230, 255),
            (int(p["x"] - 3), int(p["y"])),
            (int(p["x"] + 3), int(p["y"])),
            3,
        )

        # bullets
        for b in bullets:
            pygame.draw.circle(screen, (255, 235, 120), (int(b["x"]), int(b["y"])), b["r"])

        # orbs
        for o in orbs:
            col = (130, 210, 255) if o["type"] == "regen" else (255, 120, 120) if o["type"] == "bomba" else (220, 140, 255)
            pygame.draw.circle(screen, col, (int(o["x"]), int(o["y"])), o["r"])

        # enemies (gravetos)
        for e in enemies:


            # graveto é “haste” + ponto
            ang = math.atan2(p["y"] - e["y"], p["x"] - e["x"])
            seg_len = 26
            x1 = e["x"] + math.cos(ang) * seg_len * 0.5
            y1 = e["y"] + math.sin(ang) * seg_len * 0.5
            x0 = e["x"] - math.cos(ang) * seg_len * 0.5
            y0 = e["y"] - math.sin(ang) * seg_len * 0.5
            col = (170, 120, 70) if e["hp"] == 1 else (200, 150, 90)
            pygame.draw.line(screen, col, (int(x0), int(y0)), (int(x1), int(y1)), 4)
            pygame.draw.circle(screen, (90, 60, 35), (int(e["x"]), int(e["y"])), e["r"])

        # sparks
        for s in sparks:
            pygame.draw.circle(screen, (255, 180, 60), (int(s["x"]), int(s["y"])), int(s["r"]))

        # HUD
        hp = int(p["hp"])
        txt = font.render(f"HP: {hp:3d}   Gravêtos: {len(enemies):3d}   Score: {score}", True, HUD)
        screen.blit(txt, (12, 12))

        # Contador de munição do tiro bomba (canto superior direito): 100/100
        # bomb_cooldown > 0 significa que o tiro bomba está em recarga; ammo é consumida ao usar
        # (para manter simples, recarga repõe 100 ao terminar).
        bomb_ammo_label = f"{int(bomb_ammo):3d}/{bomb_ammo_max:3d}"
        ammo_txt = font.render(f"BOMBA AMMO: {bomb_ammo_label}", True, (255, 220, 120))
        screen.blit(ammo_txt, (W - ammo_txt.get_width() - 12, 12))


        # HP bar
        bar_w = 240
        bar_h = 16
        fill = int(bar_w * (hp / 100.0))
        pygame.draw.rect(screen, (60, 60, 60), (12, 40, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(screen, (80, 220, 120), (12, 40, fill, bar_h), border_radius=6)
        pygame.draw.rect(screen, (180, 180, 180), (12, 40, bar_w, bar_h), 2, border_radius=6)

        if state == "GAMEOVER":
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))
            t1 = big.render("VOCÊ QUEBROU!", True, (240, 90, 90))
            t2 = font.render("Pressione R para reiniciar", True, (240, 240, 240))
            screen.blit(t1, (W // 2 - t1.get_width() // 2, H // 2 - 60))
            screen.blit(t2, (W // 2 - t2.get_width() // 2, H // 2 + 10))

        pygame.display.flip()

    # Main loop
    while True:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.KEYDOWN:
                if state == "MENU":
                    if event.key in (pygame.K_w, pygame.K_UP):
                        menu_row = (menu_row - 1) % len(menu_options)
                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        menu_row = (menu_row + 1) % len(menu_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        sel = menu_options[menu_row]
                        if sel == "JOGAR":
                            state = "PLAY"
                            # reinicia bullets/inimigos
                            reset()
                        elif sel == "SAIR":
                            pygame.quit()
                            sys.exit(0)
                    elif event.key == pygame.K_ESCAPE:
                        # ESC em jogo abre um menu de pausa simples (sem fechar o programa)
                        # Aqui usamos o mesmo state="MENU" para trocar o comportamento.
                        state = "MENU"
                        menu_options = ["Voltar ao jogo", "Configurações", "Voltar ao menu principal"]
                        menu_row = 0

                else:
                    if event.key == pygame.K_r:
                        reset()


        if state == "PLAY":
            # Quando o menu estiver ativo: não atualiza gravetos (update feito com freeze), mas mantém tiros/padrões do player
            handle_input(dt)
            update(dt if not choice_pending else 0.0)
        else:

            # só input para reiniciar
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                reset()

        draw()


if __name__ == "__main__":
    main()

