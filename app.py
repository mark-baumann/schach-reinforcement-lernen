import random

import chess
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Schach", page_icon="♟️", layout="centered")

# ── Session state init ─────────────────────────────────────────────────────────
def init_state():
    if "board" not in st.session_state:
        st.session_state.board = chess.Board()
    if "player_color" not in st.session_state:
        st.session_state.player_color = chess.WHITE
    if "selected_square" not in st.session_state:
        st.session_state.selected_square = None
    if "message" not in st.session_state:
        st.session_state.message = ""
    if "game_over" not in st.session_state:
        st.session_state.game_over = False

init_state()

# ── Piece value tables for evaluation ──────────────────────────────────────────
PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}

PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]
BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]
ROOK_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]
QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]
KING_TABLE_MID = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

PIECE_TABLES = {
    chess.PAWN:   PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK:   ROOK_TABLE,
    chess.QUEEN:  QUEEN_TABLE,
    chess.KING:   KING_TABLE_MID,
}


def piece_table_score(piece_type, square, color):
    table = PIECE_TABLES.get(piece_type)
    if table is None:
        return 0
    idx = square if color == chess.BLACK else chess.square_mirror(square)
    return table[idx]


def evaluate(board: chess.Board) -> int:
    if board.is_checkmate():
        return -20000 if board.turn == chess.WHITE else 20000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = 0
    for sq, piece in board.piece_map().items():
        val = PIECE_VALUES[piece.piece_type] + piece_table_score(piece.piece_type, sq, piece.color)
        score += val if piece.color == chess.WHITE else -val
    return score


def order_moves(board: chess.Board):
    """Simple move ordering: captures first, then checks."""
    def priority(move):
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                return PIECE_VALUES[victim.piece_type] - PIECE_VALUES[attacker.piece_type]
            return 50
        board.push(move)
        in_check = board.is_check()
        board.pop()
        return 10 if in_check else 0
    return sorted(board.legal_moves, key=priority, reverse=True)


def minimax(board: chess.Board, depth: int, alpha: int, beta: int, maximizing: bool) -> int:
    if depth == 0 or board.is_game_over():
        return evaluate(board)
    if maximizing:
        best = -99999
        for move in order_moves(board):
            board.push(move)
            best = max(best, minimax(board, depth - 1, alpha, beta, False))
            board.pop()
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = 99999
        for move in order_moves(board):
            board.push(move)
            best = min(best, minimax(board, depth - 1, alpha, beta, True))
            board.pop()
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


def best_ai_move(board: chess.Board, depth: int) -> chess.Move | None:
    moves = list(order_moves(board))
    if not moves:
        return None
    is_max = board.turn == chess.WHITE
    best_score = -99999 if is_max else 99999
    best_move = random.choice(moves)
    for move in moves:
        board.push(move)
        score = minimax(board, depth - 1, -99999, 99999, not is_max)
        board.pop()
        if (is_max and score > best_score) or (not is_max and score < best_score):
            best_score = score
            best_move = move
    return best_move


# ── Board rendering ────────────────────────────────────────────────────────────

# Filled piece glyphs; the CSS colours them white/black per side so they stay
# visible on both light and dark squares.
PIECE_GLYPH = {
    chess.PAWN: "♟",
    chess.KNIGHT: "♞",
    chess.BISHOP: "♝",
    chess.ROOK: "♜",
    chess.QUEEN: "♛",
    chess.KING: "♚",
}


def render_board(board: chess.Board):
    """Render the board as a native Streamlit grid of square buttons.

    Klick-Zug: eine Figur antippen, dann das Zielfeld antippen. Das funktioniert
    zuverlässig auf Desktop und Touch-Geräten, weil es ohne iframe/sandbox und
    ohne JavaScript-Bridge auskommt (die frühere Drag-and-drop-Variante lief in
    einem sandboxed components.html()-iframe, in dem das Senden des Zugs an die
    Python-Seite blockiert wurde).
    """
    player_color = st.session_state.player_color
    game_over = st.session_state.game_over
    flipped = player_color == chess.BLACK

    files = "abcdefgh"
    ranks = "12345678"
    display_files = files[::-1] if flipped else files
    display_ranks = ranks if flipped else ranks[::-1]

    legal_moves_map = {}
    if not game_over and board.turn == player_color:
        for m in board.legal_moves:
            frm = chess.square_name(m.from_square)
            to = chess.square_name(m.to_square)
            legal_moves_map.setdefault(frm, [])
            if to not in legal_moves_map[frm]:
                legal_moves_map[frm].append(to)

    selected = st.session_state.selected_square
    if selected and selected not in legal_moves_map:
        selected = None
        st.session_state.selected_square = None
    targets = legal_moves_map.get(selected, []) if selected else []

    last_move_squares = set()
    if board.move_stack:
        lm = board.peek()
        last_move_squares = {chess.square_name(lm.from_square), chess.square_name(lm.to_square)}

    check_square = chess.square_name(board.king(board.turn)) if board.is_check() else None

    # ── Per-square CSS (colours, pieces, highlights) ─────────────────────────
    css = [
        ".stButton > button, .stButton button { border-radius: 0 !important; padding: 0 !important; "
        "min-height: 52px; font-size: 30px; line-height: 1; }",
        ".board-labels { font-size: 12px; color: #555; text-align: center; padding: 3px 0; }",
    ]
    for r in ranks:
        for f in files:
            name = f + r
            is_light = (files.index(f) + ranks.index(r)) % 2 == 1
            bg = "#f0d9b5" if is_light else "#b58863"
            rule = f".st-key-sq_{name} button {{ background-color: {bg} !important; }}"
            piece = board.piece_at(chess.parse_square(name))
            if piece:
                if piece.color == chess.WHITE:
                    rule += f" color:#fafafa !important; text-shadow:0 1px 2px rgba(0,0,0,0.6) !important;"
                else:
                    rule += f" color:#181818 !important; text-shadow:0 1px 2px rgba(255,255,255,0.35) !important;"
            css.append(rule)
    for s in last_move_squares:
        css.append(f".st-key-sq_{s} button {{ box-shadow: inset 0 0 0 3px rgba(230,190,60,0.9) !important; }}")
    if check_square:
        css.append(f".st-key-sq_{check_square} button {{ box-shadow: inset 0 0 0 4px rgba(200,30,30,0.85) !important; }}")
    if selected:
        css.append(f".st-key-sq_{selected} button {{ background-color: #f6f669 !important; "
                   f"box-shadow: inset 0 0 0 3px rgba(0,0,0,0.25) !important; }}")
    for t in targets:
        css.append(f".st-key-sq_{t} button {{ box-shadow: inset 0 0 0 4px rgba(46,139,87,0.85) !important; }}")

    st.markdown("<style>" + "\n".join(css) + "</style>", unsafe_allow_html=True)

    clickable = not game_over and board.turn == player_color
    clicked = None

    with st.container():
        for r in display_ranks:
            cols = st.columns([0.55] + [1] * 8, gap="small")
            with cols[0]:
                st.markdown(f'<div class="board-labels">{r}</div>', unsafe_allow_html=True)
            for i, f in enumerate(display_files):
                name = f + r
                piece = board.piece_at(chess.parse_square(name))
                label = PIECE_GLYPH[piece.piece_type] if piece else "\u00a0"
                with cols[i + 1]:
                    if st.button(label, key=f"sq_{name}", disabled=not clickable, use_container_width=True):
                        clicked = name
        cols = st.columns([0.55] + [1] * 8, gap="small")
        with cols[0]:
            st.markdown('<div class="board-labels"></div>', unsafe_allow_html=True)
        for f in display_files:
            with cols[display_files.index(f) + 1]:
                st.markdown(f'<div class="board-labels">{f}</div>', unsafe_allow_html=True)

    if clicked:
        handle_square_click(clicked, legal_moves_map)


def apply_move(from_sq: str, to_sq: str) -> bool:
    """Validate and apply a move (with automatic queen promotion for pawns)."""
    board = st.session_state.board
    try:
        frm = chess.parse_square(from_sq)
        to = chess.parse_square(to_sq)
    except ValueError:
        return False
    promotion = None
    piece = board.piece_at(frm)
    if piece and piece.piece_type == chess.PAWN:
        if (piece.color == chess.WHITE and chess.square_rank(to) == 7) or \
           (piece.color == chess.BLACK and chess.square_rank(to) == 0):
            promotion = chess.QUEEN
    move = chess.Move(frm, to, promotion=promotion)
    if move in board.legal_moves and board.turn == st.session_state.player_color:
        board.push(move)
        check_game_over()
        return True
    return False


def handle_square_click(name: str, legal_moves_map: dict):
    """Click-to-move logic: select a piece, then pick a legal target square."""
    selected = st.session_state.selected_square
    if selected is None:
        if name in legal_moves_map:
            st.session_state.selected_square = name
            st.rerun()
        return
    if name == selected:
        st.session_state.selected_square = None
        st.rerun()
        return
    if name in legal_moves_map.get(selected, []):
        apply_move(selected, name)
        st.session_state.selected_square = None
        st.rerun()
        return
    if name in legal_moves_map:
        st.session_state.selected_square = name
        st.rerun()
        return
    st.session_state.selected_square = None
    st.rerun()


# ── Game status check ──────────────────────────────────────────────────────────

def check_game_over():
    board = st.session_state.board
    if board.is_checkmate():
        winner = "Schwarz" if board.turn == chess.WHITE else "Weiß"
        st.session_state.message = f"Schachmatt! {winner} gewinnt! 🏆"
        st.session_state.game_over = True
    elif board.is_stalemate():
        st.session_state.message = "Patt! Unentschieden. 🤝"
        st.session_state.game_over = True
    elif board.is_insufficient_material():
        st.session_state.message = "Unentschieden – unzureichendes Material. 🤝"
        st.session_state.game_over = True
    elif board.is_seventyfive_moves():
        st.session_state.message = "Unentschieden – 75-Züge-Regel. 🤝"
        st.session_state.game_over = True
    elif board.is_check():
        st.session_state.message = "Schach! ♚"
    else:
        st.session_state.message = ""


# ── Main UI ────────────────────────────────────────────────────────────────────

st.title("♟️ Schach")

with st.sidebar:
    st.header("Einstellungen")
    color_choice = st.radio("Spielen als", ["Weiß", "Schwarz"], index=0, key="color_choice")
    st.session_state.player_color = chess.WHITE if color_choice == "Weiß" else chess.BLACK

    st.slider("KI-Stärke (Tiefe)", 1, 5, 3, key="difficulty")

    if st.button("Neues Spiel", key="new_game"):
        st.session_state.board = chess.Board()
        st.session_state.message = ""
        st.session_state.game_over = False
        st.session_state.selected_square = None
        st.rerun()

    st.divider()
    st.caption("Tippe eine Figur an und danach das Zielfeld (Klick-Zug, Desktop und Touch).")

board = st.session_state.board

# Show message
if st.session_state.message:
    if st.session_state.game_over:
        st.success(st.session_state.message)
    else:
        st.warning(st.session_state.message)

# AI move (if it's the AI's turn and game not over)
ai_color = chess.BLACK if st.session_state.player_color == chess.WHITE else chess.WHITE
if not st.session_state.game_over and board.turn == ai_color:
    with st.spinner("KI denkt nach..."):
        move = best_ai_move(board, st.session_state.difficulty)
    if move:
        board.push(move)
        check_game_over()
        st.rerun()

render_board(board)

# Square input via text box
st.write("")
with st.form(key="move_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        from_sq_str = st.text_input("Von (z.B. e2)", placeholder="e2").strip().lower()
    with col2:
        to_sq_str = st.text_input("Nach (z.B. e4)", placeholder="e4").strip().lower()
    with col3:
        st.write("")
        st.write("")
        move_btn = st.form_submit_button("Zug", use_container_width=True)

if move_btn and from_sq_str and to_sq_str and not st.session_state.game_over:
    if apply_move(from_sq_str, to_sq_str):
        st.session_state.selected_square = None
        st.rerun()
    else:
        st.error("Ungültiger Zug!")

# Move history
with st.expander("Zughistorie"):
    moves_san = []
    tmp = chess.Board()
    for m in board.move_stack:
        moves_san.append(tmp.san(m))
        tmp.push(m)
    pairs = []
    for i in range(0, len(moves_san), 2):
        w = moves_san[i]
        b = moves_san[i + 1] if i + 1 < len(moves_san) else ""
        pairs.append(f"{i//2 + 1}. {w} {b}")
    st.text("\n".join(pairs) if pairs else "Noch keine Züge.")
