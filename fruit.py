
import pygame, random, sys, math, json, os, time

# Optional numpy for runtime sound generation
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception:
    NUMPY_AVAILABLE = False

# ---------- CONFIG ----------
WIN_W, WIN_H = 820, 820
FPS = 60

PLAYER_SPEED_BASE = 420
FRUIT_SPEED_BASE = 190
BOMB_SPEED_BASE = 260

DIFFICULTY = {
    "Easy":    (1.2, 0.90, 0.90, 4),
    "Medium":  (0.9, 1.00, 1.00, 3),
    "Hard":    (0.7, 1.15, 1.25, 2)
}

BONUS_DURATION = 8.0
HIGHSCORE_FILE = "highscores.json"

# Colors
BG_SKY = (200, 235, 255)
PANEL = (250, 250, 250)
UI_TEXT = (20, 20, 30)
BUTTON = (40, 160, 80)
BUTTON_H = (64, 210, 110)
TEXTBOX_COLOR = (255,255,255)
CURSOR_COLOR = (20,20,20)

pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("Fruit Catcher - Aligned Start")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
big_font = pygame.font.SysFont(None, 44)
title_font = pygame.font.SysFont(None, 60)

# ---------- Sounds ----------
def make_sound_tone(freq=440.0, dur=0.12, vol=0.4, sr=44100):
    if not NUMPY_AVAILABLE:
        return None
    t = np.linspace(0, dur, int(sr*dur), False)
    tone = np.sin(2*np.pi*freq*t)
    # simple envelope
    env = np.exp(-3*t)
    samples = (tone * env * vol * (2**15-1)).astype(np.int16)
    stereo = np.column_stack((samples, samples))
    try:
        return pygame.mixer.Sound(stereo)
    except Exception:
        return None

catch_sound = make_sound_tone(880.0,0.09,0.25)
explosion_sound = make_sound_tone(120.0,0.35,0.7)
gameover_sound = make_sound_tone(200.0,0.6,0.6)
def play_sound(s):
    try:
        if s: s.play()
    except Exception:
        pass

# ---------- Highscore helpers ----------
def load_highscores():
    try:
        if os.path.isfile(HIGHSCORE_FILE):
            with open(HIGHSCORE_FILE,"r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_highscores(scores):
    try:
        with open(HIGHSCORE_FILE,"w") as f:
            json.dump(scores,f,indent=2)
    except Exception:
        pass

def add_highscore(name, score, diff):
    scores = load_highscores()
    scores.append({"name":name,"score":score,"difficulty":diff,"time":time.strftime("%Y-%m-%d %H:%M")})
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:5]
    save_highscores(scores)

# ---------- UI helpers ----------
def draw_button(surface, rect, text, mouse_pos):
    x,y,w,h = rect
    hovered = x < mouse_pos[0] < x+w and y < mouse_pos[1] < y+h
    color = BUTTON_H if hovered else BUTTON
    pygame.draw.rect(surface, color, rect, border_radius=8)
    txt = font.render(text, True, (0,0,0))
    surface.blit(txt, (x + (w - txt.get_width())//2, y + (h - txt.get_height())//2))
    return hovered

def draw_panel(surface, rect):
    pygame.draw.rect(surface, PANEL, rect, border_radius=10)
    pygame.draw.rect(surface, (220,220,220), rect, width=1, border_radius=10)

# ---------- Clouds ----------
class Cloud:
    def __init__(self):
        self.w = random.randint(120,260)
        self.h = self.w//3
        self.x = random.randint(-self.w, WIN_W)
        self.y = random.randint(10, WIN_H//2)
        self.speed = random.uniform(8, 36)
        self.alpha = random.randint(120,220)
    def update(self, dt, wind=1.0):
        self.x += self.speed * dt * wind
        if self.x - self.w > WIN_W:
            self.x = -self.w - random.randint(0,100)
            self.y = random.randint(10, WIN_H//2)
    def draw(self,s):
        surf = pygame.Surface((self.w,self.h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (255,255,255,self.alpha), (0,0,self.w,self.h))
        s.blit(surf, (self.x, self.y))

clouds = [Cloud() for _ in range(6)]

# ---------- Player ----------
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.frames = [self.make_frame(0), self.make_frame(1)]
        self.frame_idx = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.12
        self.image = self.frames[0]
        self.rect = self.image.get_rect(midbottom=(WIN_W//2, WIN_H-40))
        self.vx = 0
    def make_frame(self, stance=0):
        surf = pygame.Surface((80,90), pygame.SRCALPHA)
        pygame.draw.circle(surf, (240,200,170),(40,22),12)
        pygame.draw.rect(surf, (60,130,200),(24,36,32,36), border_radius=6)
        if stance==0:
            pygame.draw.line(surf,(240,200,170),(24,46),(10,60),6)
            pygame.draw.line(surf,(240,200,170),(56,46),(70,60),6)
            pygame.draw.line(surf,(30,30,80),(34,72),(34,86),6)
            pygame.draw.line(surf,(30,30,80),(46,72),(46,86),6)
        else:
            pygame.draw.line(surf,(240,200,170),(24,46),(6,56),6)
            pygame.draw.line(surf,(240,200,170),(56,46),(74,56),6)
            pygame.draw.line(surf,(30,30,80),(30,72),(24,86),6)
            pygame.draw.line(surf,(30,30,80),(50,72),(56,86),6)
        return surf
    def update(self, dt):
        keys=pygame.key.get_pressed()
        moving=False; self.vx=0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -PLAYER_SPEED_BASE
            moving=True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = PLAYER_SPEED_BASE
            moving=True
        self.rect.x += int(self.vx * dt)
        self.rect.x = max(6, min(WIN_W - self.rect.width - 6, self.rect.x))
        if moving:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer -= self.anim_speed
                self.frame_idx = (self.frame_idx +1) % len(self.frames)
        else:
            self.frame_idx = 0; self.anim_timer=0
        self.image = self.frames[self.frame_idx]

# ---------- Explosion ----------
class Explosion(pygame.sprite.Sprite):
    def __init__(self,pos):
        super().__init__()
        self.pos = pos; self.timer=0.0; self.duration=0.6; self.maxr=80
        self.image = pygame.Surface((self.maxr*2,self.maxr*2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
    def update(self, dt):
        self.timer += dt
        t = self.timer / self.duration
        if t>=1.0: self.kill(); return
        r = int(self.maxr * t); a = int(255*(1-t))
        self.image.fill((0,0,0,0))
        pygame.draw.circle(self.image,(255,255,200,a),(self.maxr,self.maxr),int(r*0.5))
        pygame.draw.circle(self.image,(255,160,0,a),(self.maxr,self.maxr),int(r*0.8))
        pygame.draw.circle(self.image,(220,40,40,a),(self.maxr,self.maxr),r)

# ---------- Fruit drawing ----------
def draw_apple(surf,color):
    pygame.draw.ellipse(surf,color,(6,8,28,26))
    pygame.draw.rect(surf,(120,70,20),(19,0,4,8))
    pygame.draw.ellipse(surf,(255,255,255,90),(14,12,8,6))
def draw_banana(surf,color):
    pygame.draw.ellipse(surf,color,(2,10,36,18))
    pygame.draw.arc(surf,(200,160,20),(2,8,36,22),math.radians(200),math.radians(340),4)
def draw_orange(surf,color):
    pygame.draw.circle(surf,color,(20,20),18)
    pygame.draw.circle(surf,(255,255,255,70),(16,16),6)
def draw_grape(surf,color):
    pos=[(12,22),(18,16),(26,18),(22,26),(14,12)]
    for (x,y) in pos: pygame.draw.circle(surf,color,(x,y),6)
    pygame.draw.circle(surf,(255,255,255,60),(18,16),3)
def draw_cherry(surf,color):
    pygame.draw.circle(surf,color,(12,22),8); pygame.draw.circle(surf,color,(26,22),8)
    pygame.draw.line(surf,(120,70,20),(18,6),(18,18),3)

FRUITS = [("Apple",(200,40,40),draw_apple),
          ("Banana",(240,220,60),draw_banana),
          ("Orange",(255,140,0),draw_orange),
          ("Grape",(120,30,120),draw_grape),
          ("Cherry",(220,20,60),draw_cherry)]

# ---------- Fruit/Bomb sprites ----------
class Fruit(pygame.sprite.Sprite):
    def __init__(self, speed_mult=1.0):
        super().__init__()
        typ = random.choice(FRUITS)
        self.name=typ[0]; color=typ[1]; fn=typ[2]
        self.image=pygame.Surface((44,44), pygame.SRCALPHA)
        fn(self.image,color)
        self.rect=self.image.get_rect(midtop=(random.randint(28, WIN_W-28), -40))
        self.speed=int(FRUIT_SPEED_BASE*speed_mult + random.randint(-30,30))
    def update(self,dt=1/FPS):
        self.rect.y += int(self.speed * dt)
        if self.rect.top > WIN_H: self.kill()

class Bomb(pygame.sprite.Sprite):
    def __init__(self, speed_mult=1.0):
        super().__init__()
        self.image=pygame.Surface((40,40), pygame.SRCALPHA)
        pygame.draw.circle(self.image,(40,40,40),(20,20),16); pygame.draw.rect(self.image,(255,170,70),(18,2,4,7))
        self.rect=self.image.get_rect(midtop=(random.randint(28, WIN_W-28), -40))
        self.speed = int(BOMB_SPEED_BASE*speed_mult + random.randint(-30,30))
    def update(self,dt=1/FPS):
        self.rect.y += int(self.speed * dt)
        if self.rect.top > WIN_H: self.kill()

# ---------- Game manager ----------
class Game:
    def __init__(self, name, diff):
        self.name=name; self.diff=diff
        self.spawn_interval, self.fruit_mult, self.bomb_mult, self.lives = DIFFICULTY[diff]
        self.player=Player()
        self.all_sprites=pygame.sprite.Group(self.player)
        self.fruits=pygame.sprite.Group(); self.bombs=pygame.sprite.Group(); self.expl=pygame.sprite.Group()
        self.score=0; self.spawn_timer=0.0; self.game_over=False; self.pause=False
        self.bonus=False; self.bonus_timer=0.0
        self.cloud_wind = 0.6 + (0.4 if diff=="Easy" else (0.9 if diff=="Medium" else 1.2))
    def update(self,dt):
        if self.pause:
            self.expl.update(dt); return
        if self.game_over:
            self.expl.update(dt); return
        interval = max(0.3, self.spawn_interval - min(0.4, self.score/600.0))
        if self.bonus: interval = max(0.18, interval*0.6)
        self.spawn_timer += dt
        if self.spawn_timer >= interval:
            self.spawn_timer = 0.0
            if (not self.bonus) and random.random() > 0.75:
                b=Bomb(speed_mult=self.bomb_mult); self.bombs.add(b); self.all_sprites.add(b)
            else:
                f=Fruit(speed_mult=self.fruit_mult); self.fruits.add(f); self.all_sprites.add(f)
        for c in clouds: c.update(dt, wind=self.cloud_wind)
        self.player.update(dt)
        for s in list(self.fruits)+list(self.bombs)+list(self.expl):
            s.update(dt)
        hits = pygame.sprite.spritecollide(self.player, self.fruits, dokill=True)
        if hits:
            self.score += 10*len(hits); play_sound(catch_sound)
            if (self.score // 100) > ((self.score - 10*len(hits))//100):
                self.bonus = True; self.bonus_timer = BONUS_DURATION
        bomb_hit = pygame.sprite.spritecollideany(self.player, self.bombs)
        if bomb_hit:
            expl = Explosion(self.player.rect.center); self.expl.add(expl); self.all_sprites.add(expl)
            for b in list(self.bombs): b.kill()
            self.lives -= 1; play_sound(explosion_sound)
            if self.lives <= 0:
                self.game_over = True; play_sound(gameover_sound); add_highscore(self.name,self.score,self.diff)
        self.expl.update(dt)
        if self.bonus:
            self.bonus_timer -= dt
            if self.bonus_timer <= 0: self.bonus=False; self.bonus_timer=0.0
    def draw(self,surf):
        surf.fill((180,220,255))
        for c in clouds: c.draw(surf)
        pygame.draw.rect(surf,(72,170,90),(0,WIN_H-36,WIN_W,36))
        self.all_sprites.draw(surf)
        surf.blit(font.render(f"{self.name}  Score: {self.score}", True, UI_TEXT),(12,8))
        surf.blit(font.render(f"Difficulty: {self.diff}", True, UI_TEXT),(12,34))
        surf.blit(font.render(f"Lives: {self.lives}", True, UI_TEXT),(WIN_W-120,8))
        if self.bonus:
            txt = font.render(f"BONUS! {int(self.bonus_timer)}s",True,(200,30,30))
            surf.blit(txt,(WIN_W//2 - txt.get_width()//2,8))
        if self.pause:
            draw_panel(surf,(WIN_W//2-200,WIN_H//2-80,400,120))
            surf.blit(big_font.render("PAUSED",True,(60,60,60)),(WIN_W//2-80,WIN_H//2-50))
            surf.blit(font.render("Press P to resume",True,(60,60,60)),(WIN_W//2-80,WIN_H//2+5))
        if self.game_over:
            draw_panel(surf,(WIN_W//2-260,WIN_H//2-120,520,220))
            surf.blit(big_font.render("GAME OVER",True,(200,40,40)),(WIN_W//2-150,WIN_H//2-80))
            surf.blit(font.render(f"Final Score: {self.score}",True,(40,40,40)),(WIN_W//2-60,WIN_H//2-20))
            surf.blit(font.render("Press R to Restart or ESC to Quit",True,(40,40,40)),(WIN_W//2-160,WIN_H//2+30))

# ---------- Pages ----------
def instructions_page():
    waiting=True
    while waiting:
        dt=clock.tick(FPS)/1000.0; mx,my=pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: waiting=False
            if ev.type==pygame.MOUSEBUTTONDOWN and 320<mx<500 and 680<my<740: waiting=False
        screen.fill((250,250,255)); draw_panel(screen,(60,40,WIN_W-120,WIN_H-120))
        screen.blit(big_font.render("How To Play",True,(30,30,30)),(120,80))
        lines=["Catch fruits to score (+10 each).","Avoid bombs - collision causes explosion and lose a life.",
               "Every 100 points starts a BONUS ROUND (fruits only).","Difficulty affects spawn and speed.",
               "Use Left/Right or A/D to move.","Press P to pause/resume.","High scores saved locally (top 5).",
               "Press ESC or Back to return."]
        for i,ln in enumerate(lines): screen.blit(font.render(ln,True,(40,40,40)),(120,150+i*30))
        # sample visuals
        sf = pygame.Surface((60,60), pygame.SRCALPHA); draw_apple(sf,(200,40,40)); screen.blit(sf,(WIN_W-220,170))
        screen.blit(font.render("Sample Fruit",True,(30,30,30)),(WIN_W-320,230))
        sb = pygame.Surface((60,60), pygame.SRCALPHA); pygame.draw.circle(sb,(40,40,40),(30,30),22); screen.blit(sb,(WIN_W-220,260))
        screen.blit(font.render("Bomb",True,(30,30,30)),(WIN_W-320,320))
        draw_button(screen,(320,680,180,60),"Back",(mx,my)); pygame.display.flip()

def show_highscores():
    waiting=True
    while waiting:
        dt=clock.tick(FPS)/1000.0; mx,my=pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.MOUSEBUTTONDOWN and 320<mx<500 and 680<my<740: waiting=False
        screen.fill((245,245,250)); draw_panel(screen,(60,40,WIN_W-120,WIN_H-120))
        screen.blit(big_font.render("High Scores",True,(30,30,30)),(120,80))
        scores=load_highscores()
        if not scores: screen.blit(font.render("No high scores yet. Play to set a record!",True,(40,40,40)),(120,150))
        else:
            for i,e in enumerate(scores): screen.blit(font.render(f"{i+1}. {e['name']} - {e['score']} ({e['difficulty']}) on {e['time']}",True,(30,30,30)),(120,150+i*40))
        draw_button(screen,(320,680,180,60),"Back",(mx,my)); pygame.display.flip()

def start_page():
    nickname=""; cursor_vis=True; cursor_t=0.0; difficulty="Medium"
    # layout math: centered panel
    panel_w = 680; panel_h = 480
    panel_x = (WIN_W - panel_w)//2; panel_y = 120
    # left col (difficulty) inside panel
    left_w = 240; left_x = panel_x + 28; left_y = panel_y + 36
    # right col (controls) inside panel
    right_x = left_x + left_w + 32; right_w = panel_w - (left_w + 32) - 56
    # nickname box inside right col (centered horizontally in right col)
    input_w, input_h = 360, 46
    input_x = right_x + (right_w - input_w)//2
    input_y = panel_y + 48
    # buttons: arranged vertically in right col
    btn_w, btn_h = 200, 60
    btn_x = right_x + (right_w - btn_w)//2
    start_btn_y = input_y + 120; how_btn_y = start_btn_y + btn_h + 18; high_btn_y = how_btn_y + btn_h + 18
    while True:
        dt = clock.tick(FPS)/1000.0; mx,my = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_RETURN and nickname.strip()!="": return nickname,difficulty
                if ev.key==pygame.K_BACKSPACE: nickname=nickname[:-1]
                elif ev.unicode and len(nickname) < 18 and ev.unicode.isprintable(): nickname += ev.unicode
            if ev.type==pygame.MOUSEBUTTONDOWN:
                # main buttons
                if btn_x < mx < btn_x+btn_w and start_btn_y < my < start_btn_y+btn_h and nickname.strip()!="":
                    return nickname,difficulty
                if btn_x < mx < btn_x+btn_w and how_btn_y < my < how_btn_y+btn_h:
                    instructions_page()
                if btn_x < mx < btn_x+btn_w and high_btn_y < my < high_btn_y+btn_h:
                    show_highscores()
                # difficulty buttons
                if left_x < mx < left_x + left_w and left_y + 56 < my < left_y + 56 + 48:
                    difficulty = "Easy"
                if left_x < mx < left_x + left_w and left_y + 56 + 64 < my < left_y + 56 + 64 + 48:
                    difficulty = "Medium"
                if left_x < mx < left_x + left_w and left_y + 56 + 128 < my < left_y + 56 + 128 + 48:
                    difficulty = "Hard"
        cursor_t += dt
        if cursor_t >= 0.5: cursor_t = 0.0; cursor_vis = not cursor_vis
        # draw background & clouds
        screen.fill((200,230,255))
        for c in clouds: c.draw(screen)
        # central panel
        draw_panel(screen,(panel_x,panel_y,panel_w,panel_h))
        # title (centered over panel)
        title_s = title_font.render("Bomb & Berry", True, (200,40,60))
        
   
        screen.blit(title_s, ((WIN_W - title_s.get_width())//2, panel_y - 80))
        # left difficulty column
        draw_panel(screen,(left_x - 8, left_y - 8, left_w + 16, 260))
        screen.blit(font.render("Difficulty", True, UI_TEXT),(left_x + 12, left_y))
        # difficulty buttons (stacked with even spacing)
        d_w = left_w - 24; d_h = 48; d_x = left_x + 12
        d1_y = left_y + 56; d2_y = d1_y + d_h + 16; d3_y = d2_y + d_h + 16
        draw_button(screen,(d_x,d1_y,d_w,d_h),"Easy",(mx,my))
        draw_button(screen,(d_x,d2_y,d_w,d_h),"Medium",(mx,my))
        draw_button(screen,(d_x,d3_y,d_w,d_h),"Hard",(mx,my))
        # mark selected difficulty with a small tick box
        tick_x = d_x + d_w + 12
        sel_map = {"Easy":d1_y,"Medium":d2_y,"Hard":d3_y}
        pygame.draw.rect(screen,(245,245,210),(tick_x, sel_map[difficulty], 18, d_h), border_radius=4)
        screen.blit(font.render(f"Selected: {difficulty}", True, UI_TEXT),(left_x + 12, d3_y + d_h + 20))
        # right column: nickname textbox
        screen.blit(font.render("Enter your nickname:", True, UI_TEXT),(input_x, input_y - 28))
        pygame.draw.rect(screen,TEXTBOX_COLOR,(input_x,input_y,input_w,input_h), border_radius=8)
        name_surf = font.render(nickname, True, (20,20,20))
        screen.blit(name_surf,(input_x + 12, input_y + 12))
        if cursor_vis and (pygame.time.get_ticks()//250)%2==0:
            cx = input_x + 12 + name_surf.get_width()
            pygame.draw.line(screen, CURSOR_COLOR, (cx, input_y+12), (cx, input_y+input_h-12), 2)
        # right column buttons
        draw_button(screen,(btn_x,start_btn_y,btn_w,btn_h),"Start Game",(mx,my))
        draw_button(screen,(btn_x,how_btn_y,btn_w,btn_h),"How To Play",(mx,my))
        draw_button(screen,(btn_x,high_btn_y,btn_w,btn_h),"High Scores",(mx,my))
        # footer tip centered under panel
        tip = "Tip: Use Left/Right arrows or A/D to move. Press P to pause."
        screen.blit(font.render(tip, True, UI_TEXT), ((WIN_W - font.size(tip)[0])//2, panel_y + panel_h + 12))
        pygame.display.flip()

# ---------- Main ----------
def main():
    nickname, difficulty = start_page()
    game = Game(nickname, difficulty)
    running=True; p_down=False
    while running:
        dt = clock.tick(FPS)/1000.0; mx,my=pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_p:
                    if not p_down:
                        game.pause = not game.pause
                        p_down = True
                if ev.key==pygame.K_r and game.game_over:
                    game = Game(nickname, difficulty)
                if ev.key==pygame.K_ESCAPE:
                    running=False
            if ev.type==pygame.KEYUP:
                if ev.key==pygame.K_p: p_down=False
        for c in clouds: c.update(dt, wind=game.cloud_wind if hasattr(game,"cloud_wind") else 1.0)
        game.update(dt)
        game.draw(screen)
        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__=="__main__":
    main()
