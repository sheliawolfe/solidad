import pygame
import random
import sys
import math
import os

pygame.init()

card_faces = None
card_back  = None

# ---------- Config ----------
SCREEN_W, SCREEN_H = 1100, 800
FPS = 60

# art pack is 58x97 px
CARD_SRC_W, CARD_SRC_H = 58, 97
CARD_H = 110
CARD_W = round(CARD_H * CARD_SRC_W / CARD_SRC_H)  # -> 66

CARD_SPACING_Y = 28   # vertical offset in stacks
PADDING = 16

ASSETS_DIR = "assets/cards"

# gradient green breath
COLOR_A = (12, 110, 38)
COLOR_B = (4, 60, 20)

CARD_BACK_CANDIDATES = [
    "back.png", "card_back.png", "backside.png",
]

RANKS = ['A','2','3','4','5','6','7','8','9','10','J','Q','K']
SUITS = ['hearts','diamonds','clubs','spades']


RANK_NAME_MAP = {
    'A': ['A','a','ace','1'],
    'J': ['J','j','jack'],
    'Q': ['Q','q','queen'],
    'K': ['K','k','king'],
}

STACKS_X0 = 100
STACKS_Y = 200
STACKS_GAP_X = 140

# change to draw 3 later
DRAW_COUNT = 1

WASTE_FAN_X = 16
STOCK_POS  = (PADDING, PADDING)
WASTE_POS  = (PADDING + CARD_W + 20, PADDING)
REDEAL_LIMIT = None  # change to 10 later

ACES_X0 = SCREEN_W - (4 * (CARD_W + 20)) - PADDING
ACES_Y  = PADDING
ACES_GAP_X = CARD_W + 20

# ---------- lil helpers ----------
def lerp(a, b, t):
    return int(a + (b - a) * t)

def blend_color(c1, c2, t):
    return (
        lerp(c1[0], c2[0], t),
        lerp(c1[1], c2[1], t),
        lerp(c1[2], c2[2], t),
    )

def fill_gradient(surface, top_color, bottom_color):
    """bckgrnd gradient fill"""
    height = surface.get_height()
    for y in range(height):
        t = y / height
        color = blend_color(top_color, bottom_color, t)
        pygame.draw.line(surface, color, (0, y), (surface.get_width(), y))

def _rank_candidates(r):
    # card images named 1-13
    RANK_NAME_MAP = {
        'A': ['A','a','ace','1'],
        'J': ['J','j','jack', '11'],
        'Q': ['Q','q','queen', '12'],
        'K': ['K','k','king', '13'],
    }
    return RANK_NAME_MAP.get(r, [r, r.lower()])  # numbers only

def _suit_dir(s):
    return s  # 'hearts', 'diamonds', 'clubs', 'spades'

def _candidate_paths(base_dir, suit, rank):
    names = []
    for rr in _rank_candidates(rank):
        names += [
            f"{rr}_of_{suit}.png",  # ace_of_hearts.png
            f"{rr}of{suit}.png",    # 1ofhearts.png
            f"{rr}.png",            
        ]
    nested = [os.path.join(base_dir, _suit_dir(suit), n) for n in names]
    flat   = [os.path.join(base_dir, n) for n in names]
    return nested + flat

def load_card_images():
    """impport and scale all 52 faces. Returns (faces_dict, back_surface)."""
    imgs = {}

    # 1) missing a back image
    back_img = None
    for cand in CARD_BACK_CANDIDATES:
        p = os.path.join(ASSETS_DIR, cand)
        if os.path.exists(p):
            back_img = pygame.image.load(p).convert_alpha()
            break
    if back_img is None:
        back_img = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        back_img.fill((60, 60, 90))
        pygame.draw.rect(back_img, (230,230,255), back_img.get_rect(), width=2, border_radius=10)
        back_img = pygame.transform.smoothscale(back_img, (CARD_W, CARD_H))

    # 2) load each face
    for suit in SUITS:
        for rank in RANKS:
            found = None
            for path in _candidate_paths(ASSETS_DIR, suit, rank):
                if os.path.exists(path):
                    found = path
                    break
            if not found:
                raise FileNotFoundError(f"Missing image for {rank} of {suit} in '{ASSETS_DIR}'.")
            surf = pygame.image.load(found).convert_alpha()
            surf = pygame.transform.smoothscale(surf, (CARD_W, CARD_H))
            imgs[(rank, suit)] = surf

    return imgs, back_img


# ---------- Models ----------
class Card:
    def __init__(self, rank, suit, face_up=False):
        self.rank = rank
        self.suit = suit
        self.face_up = face_up
        self.x, self.y = 0, 0
        self.drag_dx, self.drag_dy = 0, 0  # for dragging
        self.w, self.h = CARD_W, CARD_H
        self.parent_pile = None  # pile this card currently belongs to

    @property
    def color(self):
        # inline: no external helper needed
        return 'red' if self.suit in ('hearts', 'diamonds') else 'black'

    @property
    def value(self):
        # inline rank → number
        if self.rank == 'A': return 1
        if self.rank == 'J': return 11
        if self.rank == 'Q': return 12
        if self.rank == 'K': return 13
        return int(self.rank)

    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)

    def draw(self, surf, font):
        # if img imported, use
        if card_faces is not None and card_back is not None:
            img = card_faces[(self.rank, self.suit)] if self.face_up else card_back
            surf.blit(img, (self.x, self.y))
            return

        # Fallback
        r = self.rect()
        if self.face_up:
            pygame.draw.rect(surf, (245, 245, 245), r, border_radius=10)
            pygame.draw.rect(surf, (0, 0, 0), r, width=2, border_radius=10)
            suit_char = {'hearts':'♥','diamonds':'♦','clubs':'♣','spades':'♠'}[self.suit]
            color = (200, 0, 0) if self.color == 'red' else (0, 0, 0)
            text = f"{self.rank}{suit_char}"
            img = font.render(text, True, color)
            surf.blit(img, (r.x + 8, r.y + 6))
            img2 = font.render(text, True, color)
            surf.blit(img2, (r.right - img2.get_width() - 8, r.bottom - img2.get_height() - 6))
        else:
            pygame.draw.rect(surf, (60, 60, 90), r, border_radius=10)
            pygame.draw.rect(surf, (230, 230, 255), r, width=2, border_radius=10)


class Pile:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.cards = []

    def top(self):
        return self.cards[-1] if self.cards else None

    def rect(self):
        return pygame.Rect(self.x, self.y, CARD_W, CARD_H)

    def add_cards(self, cards):
        for c in cards:
            c.parent_pile = self
            self.cards.append(c)
        self.layout()

    def remove_from(self, card):
        """Remove and return list from 'card' to top."""
        if card not in self.cards:
            return []
        idx = self.cards.index(card)
        moving = self.cards[idx:]
        self.cards = self.cards[:idx]
        self.layout()
        return moving

    def layout(self):
        # overlapping stacks
        for i, c in enumerate(self.cards):
            c.x, c.y = self.x, self.y

    def draw_empty_slot(self, surf):
        # pile outline
        rr = self.rect()
        pygame.draw.rect(surf, (0,0,0), rr, width=2, border_radius=10)

class stacks(Pile):
    def layout(self):
        for i, c in enumerate(self.cards):
            c.x = self.x
            c.y = self.y + i * CARD_SPACING_Y

    def can_accept(self, moving_cards):
        if not moving_cards:
            return False
        head = moving_cards[0]
        # alternating suits in stacks
        if not is_valid_stack(moving_cards):
            return False
        if not self.cards:
            # accept only kings in empty row
            return head.value == 13
        top = self.top()
        return top.face_up and (top.value == head.value + 1) and (top.color != head.color)

class aces(Pile):
    def can_accept(self, moving_cards):
        # for only moving one card at a time
        if len(moving_cards) != 1:
            return False
        c = moving_cards[0]
        if not c.face_up:
            return False
        if not self.cards:
            # only aces on top 
            return c.value == 1
        top = self.top()
        # Aces pile same suit rule
        return (c.suit == top.suit) and (c.value == top.value + 1)

class StockPile(Pile):
    pass

class WastePile(Pile):
    pass

# ---------- Rules helpers ----------
def is_valid_stack(cards):
    """make sure the moving stack is face_up and descending w alternating colors."""
    if not cards:
        return False
    for c in cards:
        if not c.face_up:
            return False
    for i in range(len(cards)-1):
        a, b = cards[i], cards[i+1]
        if not (a.value == b.value + 1 and a.color != b.color):
            return False
    return True

def deal_new_game():
    deck = [Card(rank, suit, face_up=False) for suit in SUITS for rank in RANKS]
    random.shuffle(deck)

    # pile variables
    tableau = []
    for i in range(7):
        x = STACKS_X0 + i * STACKS_GAP_X
        tableau.append(stacks(x, STACKS_Y))

    foundation = [aces(ACES_X0 + i*ACES_GAP_X, ACES_Y) for i in range(4)]
    stock = StockPile(*STOCK_POS)
    waste = WastePile(*WASTE_POS)

    # create tableau 1..7 with top face_up
    for col in range(7):
        for row in range(col+1):
            card = deck.pop()
            tableau[col].add_cards([card])
        tableau[col].top().face_up = True
        tableau[col].layout()

    # send rest to stock
    stock.add_cards(deck)  # all face_down
    return tableau, foundation, stock, waste

def recycle_waste_to_stock(stock, waste):
    # reset waste pile to stock (face_down, reversed order so top becomes last dealt)
    moving = list(reversed(waste.cards))
    waste.cards.clear()
    for c in moving:
        c.face_up = False
        c.parent_pile = stock
        stock.cards.append(c)
    stock.layout()

def try_autoflip_tableau_top(stacks):
    if stacks.cards and not stacks.top().face_up:
        stacks.top().face_up = True

def has_won(foundation):
    return sum(len(f.cards) for f in foundation) == 52

# ---------- MAIN ----------
def main():
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Klondike (minimal)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    big = pygame.font.SysFont(None, 48)
    
    global card_faces, card_back
    try:
        card_faces, card_back = load_card_images()
    except Exception as e:
        print("⚠️ Card image load failed, using fallback draw:", e)
        card_faces, card_back = None, None


    tableau, foundation, stock, waste = deal_new_game()

    dragging = False
    drag_cards = []
    drag_from_pile = None
    drag_offset = (0,0)

    running = True
    win_banner_ticks = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # click to draw 1 to waste (or recycle if empty)
                if stock.rect().collidepoint(mx, my):
                    if stock.cards:
                        n = min(DRAW_COUNT, len(stock.cards))  # DRAW_COUNT = 1
                        for _ in range(n):
                            card = stock.cards.pop()
                            card.face_up = True
                            waste.add_cards([card])
                    else:
                        if waste.cards:
                            recycle_waste_to_stock(stock, waste)
                    continue  # handled click

                # if picked up from waste
                if waste.cards and waste.top().rect().collidepoint(mx, my):
                    c = waste.top()
                    moving = waste.remove_from(c)
                    dragging = True
                    drag_cards = moving
                    drag_from_pile = waste
                    drag_offset = (mx - c.x, my - c.y)
                    continue 

                # try to pick up from tableau 
                picked = False
                for pile in tableau:
                    # iterate from topmost down to find clicked face_up card
                    for c in reversed(pile.cards):
                        if c.face_up and c.rect().collidepoint(mx, my):
                            moving = pile.remove_from(c)
                            dragging = True
                            drag_cards = moving
                            drag_from_pile = pile
                            drag_offset = (mx - c.x, my - c.y)
                            picked = True
                            break
                    if picked:
                        break

                # then pick up from aces (allow moving back single cards if needed)
                if not picked:
                    for f in aces:
                        if f.cards and f.top().rect().collidepoint(mx, my):
                            c = f.top()
                            moving = f.remove_from(c)
                            dragging = True
                            drag_cards = moving
                            drag_from_pile = f
                            drag_offset = (mx - c.x, my - c.y)
                            break

            elif event.type == pygame.MOUSEMOTION and dragging:
                mx, my = event.pos
                dx, dy = drag_offset
                # keep stack offset
                for i, c in enumerate(drag_cards):
                    c.x = mx - dx
                    c.y = my - dy + i * CARD_SPACING_Y

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and dragging:
                mx, my = event.pos

                # try to drop on aces pile first
                dropped = False
                for f in foundation:
                    if f.rect().collidepoint(mx, my) and f.can_accept(drag_cards):
                        f.add_cards(drag_cards)
                        dropped = True
                        break

                # if not, tableau
                if not dropped:
                    best_target = None

                    for pile in tableau:
                        # Intersection with pile rect OR with top card rect makes sense
                        hit_rect = pile.top().rect() if pile.cards else pile.rect()
                        if hit_rect.collidepoint(mx, my) and pile.can_accept(drag_cards):
                            best_target = pile
                            break
                    if best_target:
                        best_target.add_cards(drag_cards)
                        dropped = True

                # if drop failed, return to pile
                if not dropped:
                    drag_from_pile.add_cards(drag_cards)

                # if success, flip new card
                if dropped and isinstance(drag_from_pile, stacks):
                    try_autoflip_tableau_top(drag_from_pile)

                # drag reset
                dragging = False
                drag_cards = []
                drag_from_pile = None

        # breathing gradient
        t = (math.sin(pygame.time.get_ticks() * 0.00025) + 1) / 2  # oscillates 0→1→0
        top = blend_color(COLOR_A, COLOR_B, t)
        bottom = blend_color(COLOR_B, COLOR_A, t)
        fill_gradient(screen, top, bottom)

        #  empty slots for stock, waste, aces
        for pile in [stock, waste, *foundation]:
            if not pile.cards:
                pile.draw_empty_slot(screen)

        # Draw stock back (face-down)
        if stock.cards:
            stock.top().face_up = False  # lock in back "img"
            stock.top().draw(screen, font)
            
        if waste.cards:
            show = waste.cards[-min(DRAW_COUNT, len(waste.cards)):]
            base_x, base_y = waste.x, waste.y
            for i, c in enumerate(show):
                c.x = base_x + i * WASTE_FAN_X  # harmless even when i==0
                c.y = base_y
                c.draw(screen, font)

        # draw from ace pile
        for f in foundation:
            for c in f.cards:
                c.draw(screen, font)

        # draw tableau piles
        for pile in tableau:
            if not pile.cards:
                pile.draw_empty_slot(screen)
            for c in pile.cards:
                c.draw(screen, font)

        # Draw dragging on top
        if dragging:
            for c in drag_cards:
                c.draw(screen, font)

        # WIN CHECK
        if has_won (foundation):
            win_banner_ticks += 1
            msg = "You win!"
            img = big.render(msg, True, (255,255,255))
            pygame.draw.rect(screen, (0,0,0), (SCREEN_W//2-150, SCREEN_H//2-40, 300, 80), border_radius=12)
            screen.blit(img, (SCREEN_W//2 - img.get_width()//2, SCREEN_H//2 - img.get_height()//2))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
