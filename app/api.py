from flask import Blueprint, jsonify, request, session

from . import quiz_engine as qe

bp = Blueprint("api", __name__)


def _uid():
    return session.get("user_id")


def _wrap(res):
    data, err = res
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, **data})


@bp.before_request
def need_login():
    if not _uid():
        return jsonify({"ok": False, "error": "Not logged in."}), 401


@bp.post("/quiz/start")
def start():
    j = request.get_json(silent=True) or {}
    st, err = qe.start_quiz(_uid(), j.get("type"), j.get("key"))
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, "state": qe.public_state(st)})


@bp.get("/quiz/state")
def state():
    st = qe.get_state(_uid())
    if not st:
        return jsonify({"ok": False, "error": "No active quiz."}), 404
    return jsonify({"ok": True, "state": qe.public_state(st)})


@bp.get("/quiz/question/<int:i>")
def question(i):
    return _wrap(qe.get_question(_uid(), i))


@bp.post("/quiz/answer")
def answer():
    j = request.get_json(silent=True) or {}
    try:
        idx = int(j.get("index"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Bad index."}), 400
    return _wrap(qe.submit_answer(_uid(), idx, j.get("choice")))


@bp.post("/quiz/hint")
def hint():
    j = request.get_json(silent=True) or {}
    try:
        idx = int(j.get("index"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Bad index."}), 400
    return _wrap(qe.use_hint(_uid(), idx))


@bp.post("/quiz/finish")
def finish():
    j = request.get_json(silent=True) or {}
    return _wrap(qe.finish_and_save(_uid(), j.get("time")))


@bp.post("/quiz/exit")
def exit_():
    qe.exit_without_saving(_uid())
    return jsonify({"ok": True})
