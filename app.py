import chess
import chess.svg
import streamlit as st
import streamlit.components.v1 as components
import random

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Schach", page_icon="♟️", layout="centered")

# ── Session state init ─────────────────────────────────────────────────────────
def init_state():
    if "board" not in st.session_state:
        st.session_state.board = chess.Board()
    if "selected" not in st.session_state:
        st.session_state.selected = None
    if "player_color" not in st.session_state:
        st.session_state.player_color = chess.WHITE
    if "difficulty" not in st.session_state:
        st.session_state.difficulty = 3
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

def render_board(board: chess.Board, selected_sq=None, legal_targets=None):
    arrows = []
    if board.move_stack:
        last = board.peek()
        arrows.append(chess.svg.Arrow(last.from_square, last.to_square, color="#88888855"))

    fill = {}
    if selected_sq is not None:
        fill[selected_sq] = "#f6f669"
    if legal_targets:
        for sq in legal_targets:
            fill[sq] = "#ccff88"

    flipped = st.session_state.player_color == chess.BLACK
    svg = chess.svg.board(
        board,
        arrows=arrows,
        fill=fill,
        flipped=flipped,
        size=480,
    )
    components.html(f'<div style="display: flex; justify-content: center;">{svg}</div>', height=500)


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
    color_choice = st.radio("Spielen als", ["Weiß", "Schwarz"], index=0)
    st.session_state.player_color = chess.WHITE if color_choice == "Weiß" else chess.BLACK

    diff = st.slider("KI-Stärke (Tiefe)", 1, 5, st.session_state.difficulty)
    st.session_state.difficulty = diff

    if st.button("Neues Spiel"):
        st.session_state.board = chess.Board()
        st.session_state.selected = None
        st.session_state.message = ""
        st.session_state.game_over = False
        st.rerun()

    st.divider()
    st.caption("Klicke auf eine Figur, dann auf das Zielfeld um einen Zug zu machen.")

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

# Compute legal targets for selected piece
selected = st.session_state.selected
legal_targets = None
if selected is not None:
    legal_targets = [m.to_square for m in board.legal_moves if m.from_square == selected]

render_board(board, selected, legal_targets)

# Square input via text box
st.write("")
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    from_sq_str = st.text_input("Von (z.B. e2)", key="from_sq", placeholder="e2").strip().lower()
with col2:
    to_sq_str = st.text_input("Nach (z.B. e4)", key="to_sq", placeholder="e4").strip().lower()
with col3:
    st.write("")
    st.write("")
    move_btn = st.button("Zug", use_container_width=True)

if move_btn and from_sq_str and to_sq_str and not st.session_state.game_over:
    try:
        from_sq = chess.parse_square(from_sq_str)
        to_sq = chess.parse_square(to_sq_str)
        # Handle promotion
        promotion = None
        piece = board.piece_at(from_sq)
        if piece and piece.piece_type == chess.PAWN:
            if (piece.color == chess.WHITE and chess.square_rank(to_sq) == 7) or \
               (piece.color == chess.BLACK and chess.square_rank(to_sq) == 0):
                promotion = chess.QUEEN
        move = chess.Move(from_sq, to_sq, promotion=promotion)
        if move in board.legal_moves and board.turn == st.session_state.player_color:
            board.push(move)
            check_game_over()
            st.rerun()
        else:
            st.error("Ungültiger Zug!")
    except ValueError:
        st.error("Ungültige Feldangabe (z.B. e2, d7)")

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
