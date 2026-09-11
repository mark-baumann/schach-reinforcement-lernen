import json
import random

import chess
import streamlit as st
import streamlit.components.v1 as components

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Schach", page_icon="♟️", layout="centered")

# ── Session state init ─────────────────────────────────────────────────────────
def init_state():
    if "board" not in st.session_state:
        st.session_state.board = chess.Board()
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

PIECE_UNICODE = {
    (chess.PAWN, chess.WHITE): "♙",
    (chess.KNIGHT, chess.WHITE): "♘",
    (chess.BISHOP, chess.WHITE): "♗",
    (chess.ROOK, chess.WHITE): "♖",
    (chess.QUEEN, chess.WHITE): "♕",
    (chess.KING, chess.WHITE): "♔",
    (chess.PAWN, chess.BLACK): "♟",
    (chess.KNIGHT, chess.BLACK): "♞",
    (chess.BISHOP, chess.BLACK): "♝",
    (chess.ROOK, chess.BLACK): "♜",
    (chess.QUEEN, chess.BLACK): "♛",
    (chess.KING, chess.BLACK): "♚",
}


def render_board(board: chess.Board):
    """Render an interactive board that supports drag-and-drop as well as
    click-to-move (the latter also works on touch devices, where native HTML5
    drag-and-drop is unreliable).

    Since components.html() cannot return values to Python directly, a chosen
    move is sent back by navigating the parent page to `?move=<from><to>`,
    which the main script reads via st.query_params on the next run.
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

    last_move_squares = set()
    if board.move_stack:
        lm = board.peek()
        last_move_squares = {chess.square_name(lm.from_square), chess.square_name(lm.to_square)}

    check_square = chess.square_name(board.king(board.turn)) if board.is_check() else None

    squares_html = []
    for r_i, r in enumerate(display_ranks):
        for f_i, f in enumerate(display_files):
            name = f + r
            sq = chess.parse_square(name)
            piece = board.piece_at(sq)
            piece_char = PIECE_UNICODE.get((piece.piece_type, piece.color), "") if piece else ""
            is_light = (files.index(f) + ranks.index(r)) % 2 == 1

            classes = ["sq", "light" if is_light else "dark"]
            if name in last_move_squares:
                classes.append("last-move")
            if name == check_square:
                classes.append("in-check")
            if piece_char:
                classes.append("occ")
            draggable = "true" if name in legal_moves_map else "false"

            coord = ""
            if f_i == 0:
                coord += f'<span class="coord rank">{r}</span>'
            if r_i == 7:
                coord += f'<span class="coord file">{f}</span>'

            squares_html.append(
                f'<div id="sq-{name}" class="{" ".join(classes)}" '
                f'ondragover="allowDrop(event)" ondrop="dropPiece(event,\'{name}\')" '
                f'onclick="trySquareClick(\'{name}\')">'
                f'{coord}'
                f'<span class="piece" draggable="{draggable}" '
                f'ondragstart="dragStart(event,\'{name}\')" ondragend="onDragEnd()">{piece_char}</span>'
                f'</div>'
            )

    legal_moves_json = json.dumps(legal_moves_map)

    html = f"""
    <style>
      .board-wrap {{ display:flex; justify-content:center; font-family: -apple-system, sans-serif; }}
      .board {{ display:grid; grid-template-columns: repeat(8, 58px); grid-template-rows: repeat(8, 58px);
                border: 2px solid #3a2a1a; box-shadow: 0 2px 12px rgba(0,0,0,0.35); }}
      .sq {{ position:relative; display:flex; align-items:center; justify-content:center;
             font-size: 38px; user-select:none; }}
      .light {{ background:#f0d9b5; }}
      .dark {{ background:#b58863; }}
      .sq.selected {{ box-shadow: inset 0 0 0 4px #f6f669; }}
      .sq.last-move {{ background-image: linear-gradient(rgba(246,246,105,0.55), rgba(246,246,105,0.55)); }}
      .sq.in-check {{ background-image: linear-gradient(rgba(230,30,30,0.6), rgba(230,30,30,0.6)); }}
      .sq.target::after {{ content:""; position:absolute; width:16px; height:16px; border-radius:50%;
             background: rgba(20,110,20,0.55); pointer-events:none; }}
      .sq.target.occ::after {{ width:52px; height:52px; border-radius:50%; background:transparent;
             border:4px solid rgba(200,30,30,0.55); pointer-events:none; }}
      .piece {{ cursor: grab; z-index:2; }}
      .piece:active {{ cursor: grabbing; }}
      .coord {{ position:absolute; font-size:9px; opacity:0.6; pointer-events:none; }}
      .coord.rank {{ top:2px; left:3px; }}
      .coord.file {{ bottom:2px; right:3px; }}
    </style>
    <div class="board-wrap">
      <div class="board">
        {''.join(squares_html)}
      </div>
    </div>
    <script>
      const legalMoves = {legal_moves_json};
      let selected = null;

      function sqEl(name) {{ return document.getElementById('sq-' + name); }}

      function clearHighlights() {{
        document.querySelectorAll('.sq').forEach(el => el.classList.remove('selected', 'target'));
      }}

      function selectSquare(name) {{
        clearHighlights();
        selected = name;
        sqEl(name).classList.add('selected');
        (legalMoves[name] || []).forEach(t => sqEl(t).classList.add('target'));
      }}

      function deselect() {{
        clearHighlights();
        selected = null;
      }}

      function sendMove(from, to) {{
        const url = new URL(window.parent.location.href);
        url.searchParams.set('move', from + to);
        window.parent.location.href = url.toString();
      }}

      function trySquareClick(name) {{
        if (selected === null) {{
          if (legalMoves[name]) selectSquare(name);
        }} else if (selected === name) {{
          deselect();
        }} else if (legalMoves[selected] && legalMoves[selected].includes(name)) {{
          sendMove(selected, name);
        }} else if (legalMoves[name]) {{
          selectSquare(name);
        }} else {{
          deselect();
        }}
      }}

      function allowDrop(ev) {{ ev.preventDefault(); }}

      function dragStart(ev, name) {{
        if (!legalMoves[name]) {{ ev.preventDefault(); return; }}
        ev.dataTransfer.setData('text/plain', name);
        ev.dataTransfer.effectAllowed = 'move';
        selectSquare(name);
      }}

      function onDragEnd() {{
        deselect();
      }}

      function dropPiece(ev, name) {{
        ev.preventDefault();
        const from = ev.dataTransfer.getData('text/plain');
        if (from && legalMoves[from] && legalMoves[from].includes(name)) {{
          sendMove(from, name);
        }} else {{
          deselect();
        }}
      }}
    </script>
    """
    components.html(html, height=520)


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
        st.session_state.message = ""
        st.session_state.game_over = False
        st.rerun()

    st.divider()
    st.caption("Ziehe eine Figur per Drag & Drop, oder tippe Figur und Zielfeld nacheinander an.")

board = st.session_state.board

# Moves made via drag-and-drop / click-to-move arrive as a `move` query param
# (components.html() can't return values to Python directly, so the board's
# JS navigates the parent page with `?move=<from><to>` instead).
qp_move = st.query_params.get("move")
if qp_move:
    st.query_params.clear()
    if not st.session_state.game_over and len(qp_move) >= 4:
        try:
            from_sq = chess.parse_square(qp_move[:2])
            to_sq = chess.parse_square(qp_move[2:4])
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
        except ValueError:
            pass
    st.rerun()

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
