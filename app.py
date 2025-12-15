import os
import uuid
import random
from datetime import datetime

from flask import (
    Flask, render_template, redirect, url_for, request,
    flash, abort, send_from_directory, jsonify, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---- extensions ----
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"


# --------------------
# Models
# --------------------
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), nullable=False, default="student")
    owner_id = db.Column(db.Integer, nullable=True)

    # 게임 진행 상태
    game1_done = db.Column(db.Boolean, nullable=False, default=False)
    game2_done = db.Column(db.Boolean, nullable=False, default=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Notice(db.Model):
    __tablename__ = "notice"

    id = db.Column(db.Integer, primary_key=True)
    # URL에 쓰는 인덱스(0,1,2...) — “개발자면 0부터 찾는다” 트릭용
    idx = db.Column(db.Integer, unique=True, nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # 목록에 노출할지
    is_public = db.Column(db.Boolean, nullable=False, default=True)


class Grade(db.Model):
    __tablename__ = "grade"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    subject_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.String(8), nullable=False)  # NP / P
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Assignment(db.Model):
    __tablename__ = "assignment"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def seed_notices():
    # 이미 있으면 재시드 안 함
    if Notice.query.count() > 0:
        return

    notices = [
        # 숨김 공지: idx=0
        Notice(
            idx=0,
            title="Notice 0: Staff-only",
            content="Professors: please complete the games before requesting grade changes.",
            is_public=False,
        ),
        # 공개 공지: idx=1 (화면에는 이것만 보이게)
        Notice(
            idx=1,
            title="Welcome to Myongji CTF!",
            content="Good luck!",
            is_public=True,
        ),
    ]
    db.session.add_all(notices)
    db.session.commit()


def create_app():
    # (선택) .env 사용하고 싶으면 python-dotenv 설치 후 자동 로드
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    app = Flask(__name__)

    # 운영/로컬 공통: 환경변수 우선, 없으면 기본값
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-later")
    app.config["FLAG"] = os.environ.get("FLAG", "MJSEC{dev-flag}")

    # 힌트는 “문자열”로만 전달 (페이지에서 base64라고 말하지 않게 템플릿에서 문구만 조절)
    app.config["FINAL_HINT"] = os.environ.get(
        "FINAL_HINT",
        "VGhlcmUgaXMgYSBoaWRkZW4gZW5kcG9pbnQgd2l0aCAvZ3JhZGVzL3VwZ3JhZGU="
    )
    
    # DB
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = os.path.join(app.instance_path, "ctf.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # uploads
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    app.config["UPLOAD_SUBDIR"] = "uploads"
    app.config["ALLOWED_EXTENSIONS"] = {"hwp", "ppt", "pptx", "pdf"}

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        seed_notices()

    # --------------------
    # Helpers
    # --------------------
    def allowed_file(filename: str) -> bool:
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in app.config["ALLOWED_EXTENSIONS"]

    def upload_dir_for(student_id: int) -> str:
        root = os.path.join(app.instance_path, app.config["UPLOAD_SUBDIR"], str(student_id))
        os.makedirs(root, exist_ok=True)
        return root

    def parse_limit() -> int:
        raw = request.args.get("limit", "25")
        try:
            n = int(raw)
        except ValueError:
            n = 25
        return max(1, min(n, 999))

    # --------------------
    # ✅ 로그인 강제 (login/register/static만 예외)
    # --------------------
    @app.before_request
    def force_login_everywhere():
        if current_user.is_authenticated:
            return

        ep = request.endpoint or ""
        allowed = {"login", "register", "static", "index"}
        if ep in allowed:
            return
        if request.path.startswith("/static/"):
            return

        return redirect(url_for("login", next=request.full_path))

    # --------------------
    # Routes
    # --------------------
    @app.route("/")
    def index():
        # “처음 들어오면 회원가입부터”
        if not current_user.is_authenticated:
            return redirect(url_for("register"))
        return redirect(url_for("notices"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("notices"))

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            if not username or not password:
                flash("아이디/비밀번호를 입력하세요.")
                return redirect(url_for("register"))
            if len(username) > 50:
                flash("아이디가 너무 깁니다.")
                return redirect(url_for("register"))
            if User.query.filter_by(username=username).first():
                flash("이미 존재하는 아이디입니다.")
                return redirect(url_for("register"))

            u = User(username=username, role="student")
            u.set_password(password)
            db.session.add(u)
            db.session.commit()

            db.session.add(Grade(user_id=u.id, subject_name="채플", score="NP"))
            db.session.commit()

            flash("회원가입 완료. 로그인 해주세요.")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("notices"))

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                flash("로그인 실패. 아이디/비밀번호를 확인하세요.")
                return redirect(url_for("login"))

            login_user(user)
            flash("로그인 성공.")
            return redirect(url_for("notices"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        for k in ("puzzle_board", "puzzle_turns", "puzzle_limit", "puzzle_uid"):
            session.pop(k, None)

        logout_user()
        flash("로그아웃 되었습니다.")
        return redirect(url_for("login"))

    # ---- Notices ----
    @app.route("/notices")
    @login_required
    def notices():
        # ✅ 공개 공지는 “1개만” 보이게 (중복 시드/데이터 꼬임 방지)
        items = (
            Notice.query
            .filter_by(is_public=True)
            .order_by(Notice.created_at.desc())
            .limit(1)
            .all()
        )
        return render_template("notices.html", items=items, now=datetime.now())

    @app.route("/notices/<int:idx>")
    @login_required
    def notice_detail_idx(idx: int):
        # ✅ URL idx로 조회 (0번 숨김 공지도 여기로 접근 가능)
        item = Notice.query.filter_by(idx=idx).first()
        if not item:
            abort(404)
        return render_template("notice_detail.html", item=item)

    # ---- Grades ----
    @app.route("/grades")
    @login_required
    def grades():
        items = Grade.query.filter_by(user_id=current_user.id).order_by(Grade.subject_name.asc()).all()
        return render_template("grades.html", items=items)

    # ---- Assignments ----
    @app.route("/assignments", methods=["GET", "POST"])
    @login_required
    def assignments():
        if request.method == "POST":
            f = request.files.get("file")
            desc = (request.form.get("description") or "").strip()

            if not f or not f.filename:
                flash("파일을 선택하세요.")
                return redirect(url_for("assignments"))

            original = secure_filename(f.filename)

            # [CTF VULNERABILITY]: MIME Type Bypass
            # 확장자가 허용되지 않아도(allowed_file == False),
            # 공격자가 패킷의 Content-Type을 'application/pdf'로 조작해서 보내면 업로드를 허용함.
            if not allowed_file(original):
                # 취약한 검증 로직
                if f.content_type != "application/pdf":
                    flash("허용되지 않은 확장자입니다. (PDF, HWP, PPT만 가능)")
                    return redirect(url_for("assignments"))
                # 만약 Content-Type이 application/pdf라면, 확장자가 txt여도 통과됨

            stored = f"{uuid.uuid4().hex}_{original}"
            root = upload_dir_for(current_user.id)
            save_path = os.path.join(root, stored)
            f.save(save_path)

            # [CTF TRIGGER]: 업로드된 파일 내용을 몰래 읽어서 특정 명령어 처리
            try:
                # 방금 저장한 파일을 텍스트 모드로 읽음
                with open(save_path, "r", encoding="utf-8", errors="ignore") as ups:
                    content = ups.read()
                    
                    # "채플=P" 문자열이 포함되어 있으면 성적 조작 및 플래그 노출
                    if "채플=P" in content:
                        # 1. 성적 업데이트 (채플 -> P)
                        grade = Grade.query.filter_by(user_id=current_user.id, subject_name="채플").first()
                        if grade:
                            grade.score = "P"
                            db.session.commit()
                        
                        # 2. 플래그 지급 (Flash 메시지로 띄움)
                        flash(f"SYSTEM OVERRIDE DETECTED! FLAG: {app.config['FLAG']}")
                        
                        # (선택) 흔적을 남기지 않으려면 파일을 삭제할 수도 있음
                        # os.remove(save_path)
            except Exception as e:
                print(f"Error parsing file: {e}")

            # DB에 업로드 기록 저장
            db.session.add(Assignment(
                student_id=current_user.id,
                original_filename=original,
                stored_filename=stored,
                description=desc[:200] if desc else None
            ))
            db.session.commit()

            flash("업로드 완료.")
            return redirect(url_for("assignments"))

        items = Assignment.query.filter_by(student_id=current_user.id).order_by(Assignment.uploaded_at.desc()).all()
        return render_template("assignments.html", items=items)

    @app.route("/assignments/download/<int:assignment_id>")
    @login_required
    def assignment_download(assignment_id: int):
        a = db.session.get(Assignment, assignment_id)
        if not a or a.student_id != current_user.id:
            abort(403)

        root = upload_dir_for(a.student_id)
        return send_from_directory(root, a.stored_filename, as_attachment=True, download_name=a.original_filename)

    # ---- Games ----
    @app.route("/games")
    @login_required
    def games():
        level_raw = request.args.get("level", "1")
        try:
            level = int(level_raw)
        except ValueError:
            level = 1

        if level == 1:
            limit = parse_limit()

            reset = request.args.get("reset", "0") == "1"
            uid = session.get("puzzle_uid")
            cur_limit = session.get("puzzle_limit")
            board = session.get("puzzle_board")

            if reset or uid != current_user.id or board is None or cur_limit != limit:
                board = list(range(1, 26))
                random.shuffle(board)
                session["puzzle_board"] = board
                session["puzzle_turns"] = 0
                session["puzzle_limit"] = limit
                session["puzzle_uid"] = current_user.id

            turns = int(session.get("puzzle_turns", 0))
            solved = (board == list(range(1, 26)))
            locked = (turns >= limit and not solved)

            return render_template(
                "game_puzzle.html",
                limit=limit,
                turns=turns,
                solved=solved,
                locked=locked,
                game1_done=current_user.game1_done,
                board=board,
            )

        if level == 2:
            if not current_user.game1_done:
                flash("레벨 1을 먼저 클리어해야 합니다.")
                return redirect(url_for("games", level=1, limit=25))
            return render_template("game_volume.html")

        if level == 3:
            if not current_user.game1_done:
                return redirect(url_for("games", level=1, limit=25))
            if not current_user.game2_done:
                return redirect(url_for("games", level=2))
            return render_template("game_hint.html", cipher=app.config["FINAL_HINT"])

        abort(404)

    @app.post("/api/games/puzzle/swap")
    @login_required
    def api_puzzle_swap():
        if session.get("puzzle_uid") != current_user.id:
            return jsonify({"error": "no puzzle state"}), 400

        board = session.get("puzzle_board")
        limit = int(session.get("puzzle_limit", 25))
        turns = int(session.get("puzzle_turns", 0))

        if not isinstance(board, list) or len(board) != 25:
            return jsonify({"error": "invalid puzzle state"}), 400

        data = request.get_json(silent=True) or {}
        a = data.get("a")
        b = data.get("b")

        try:
            a = int(a)
            b = int(b)
        except (TypeError, ValueError):
            return jsonify({"error": "bad indices"}), 400

        if a < 0 or a >= 25 or b < 0 or b >= 25:
            return jsonify({"error": "out of range"}), 400

        if board == list(range(1, 26)):
            return jsonify({
                "board": board,
                "turns": turns,
                "limit": limit,
                "solved": True,
                "passed": True,
                "locked": False,
                "next": url_for("games", level=2),
            })

        if turns >= limit:
            return jsonify({
                "board": board,
                "turns": turns,
                "limit": limit,
                "solved": False,
                "passed": False,
                "locked": True,
            })

        board[a], board[b] = board[b], board[a]
        turns += 1

        session["puzzle_board"] = board
        session["puzzle_turns"] = turns

        solved = (board == list(range(1, 26)))
        passed = bool(solved and turns <= limit)

        if passed and not current_user.game1_done:
            current_user.game1_done = True
            db.session.commit()
            for k in ("puzzle_board", "puzzle_turns", "puzzle_limit", "puzzle_uid"):
                session.pop(k, None)

        locked = (turns >= limit and not solved)

        return jsonify({
            "board": board,
            "turns": turns,
            "limit": limit,
            "solved": solved,
            "passed": passed,
            "locked": locked,
            "next": url_for("games", level=2),
        })

    @app.post("/api/games/volume/complete")
    @login_required
    def api_volume_complete():
        if not current_user.game1_done:
            return jsonify({"error": "level1 required"}), 403

        if not current_user.game2_done:
            current_user.game2_done = True
            db.session.commit()

        return jsonify({"ok": True, "next": url_for("games", level=3)})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
