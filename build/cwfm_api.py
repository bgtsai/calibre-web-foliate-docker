# -*- coding: utf-8 -*-
"""cwfm 閱讀器的伺服器端資料：書籤、跳轉紀錄（跟著 Calibre-Web 使用者走）。

建置時複製到 cps/cwfm_api.py，並由 patch_calibre_web.py 在 cps/main.py 註冊。
規格見 calibre-web-foliate-mod 的 docs/spec-v1.79.md §8。

- 資料存在 /config/cwfm.db（自己的 SQLite），不動 Calibre-Web 的 app.db，
  上游升級資料庫結構時不會互相影響；/config 是使用者掛載的持久資料夾。
- 登入檢查沿用 Calibre-Web 的 user_login_required；CSRF 沿用全站的 CSRFProtect
  （前端用 X-CSRFToken 標頭送，跟閱讀進度同一套）。
- 書籤逐筆存（PUT/DELETE 一筆），多台裝置同時加書籤不會互相蓋掉；跳轉紀錄整包存。
"""
import json
import os
import re
import sqlite3
import threading
import time

from flask import Blueprint, jsonify, request, abort, Response
from .cw_login import current_user

from .usermanagement import user_login_required

cwfm_api = Blueprint('cwfm_api', __name__, url_prefix='/cwfm/api')

MAX_BODY = 256 * 1024
BM_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,40}$')
_lock = threading.Lock()


def _db_path():
    # 跟 Calibre-Web 的 app.db 放在同一個資料夾（linuxserver image 是 /config）
    base = os.environ.get('CWFM_DB_DIR')
    if not base:
        try:
            from . import cli_param
            base = os.path.dirname(cli_param.settings_path or '')
        except Exception:
            base = ''
    return os.path.join(base or '/config', 'cwfm.db')


def _conn():
    con = sqlite3.connect(_db_path(), timeout=10)
    con.execute('CREATE TABLE IF NOT EXISTS bookmarks (user_id INTEGER NOT NULL, book_id INTEGER NOT NULL, '
                'bm_id TEXT NOT NULL, data TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY (user_id, book_id, bm_id))')
    con.execute('CREATE TABLE IF NOT EXISTS navhist (user_id INTEGER NOT NULL, book_id INTEGER NOT NULL, '
                'data TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY (user_id, book_id))')
    con.execute('CREATE TABLE IF NOT EXISTS errlog (user_id INTEGER NOT NULL, session TEXT NOT NULL, book_id INTEGER NOT NULL, '
                'text TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY (user_id, session))')
    return con


def _uid():
    return int(current_user.id)


def _json_body():
    if request.content_length is not None and request.content_length > MAX_BODY:
        abort(413)
    raw = request.get_data(cache=False, as_text=True)
    if len(raw) > MAX_BODY:
        abort(413)
    try:
        return json.loads(raw)
    except ValueError:
        abort(400)


@cwfm_api.route('/', methods=['GET'])
@user_login_required
def base():
    return jsonify(ok=True, version=1)


@cwfm_api.route('/book/<int:book_id>', methods=['GET'])
@user_login_required
def get_book(book_id):
    with _lock:
        con = _conn()
        try:
            rows = con.execute('SELECT data FROM bookmarks WHERE user_id=? AND book_id=? ORDER BY updated',
                               (_uid(), book_id)).fetchall()
            nav = con.execute('SELECT data FROM navhist WHERE user_id=? AND book_id=?', (_uid(), book_id)).fetchone()
        finally:
            con.close()
    bookmarks = []
    for (data,) in rows:
        try:
            bookmarks.append(json.loads(data))
        except ValueError:
            pass
    navhist = None
    if nav:
        try:
            navhist = json.loads(nav[0])
        except ValueError:
            navhist = None
    return jsonify(bookmarks=bookmarks, navhist=navhist)


@cwfm_api.route('/book/<int:book_id>/bookmark/<bm_id>', methods=['PUT'])
@user_login_required
def put_bookmark(book_id, bm_id):
    if not BM_ID_RE.match(bm_id):
        abort(400)
    data = _json_body()
    if not isinstance(data, dict) or not isinstance(data.get('cfi'), str):
        abort(400)
    data['id'] = bm_id
    with _lock:
        con = _conn()
        try:
            con.execute('INSERT OR REPLACE INTO bookmarks (user_id, book_id, bm_id, data, updated) VALUES (?,?,?,?,?)',
                        (_uid(), book_id, bm_id, json.dumps(data, ensure_ascii=False), time.time()))
            con.commit()
        finally:
            con.close()
    return jsonify(ok=True)


@cwfm_api.route('/book/<int:book_id>/bookmark/<bm_id>', methods=['DELETE'])
@user_login_required
def delete_bookmark(book_id, bm_id):
    if not BM_ID_RE.match(bm_id):
        abort(400)
    with _lock:
        con = _conn()
        try:
            con.execute('DELETE FROM bookmarks WHERE user_id=? AND book_id=? AND bm_id=?', (_uid(), book_id, bm_id))
            con.commit()
        finally:
            con.close()
    return jsonify(ok=True)


@cwfm_api.route('/book/<int:book_id>/navhist', methods=['PUT'])
@user_login_required
def put_navhist(book_id):
    data = _json_body()
    if not isinstance(data, dict):
        abort(400)
    with _lock:
        con = _conn()
        try:
            con.execute('INSERT OR REPLACE INTO navhist (user_id, book_id, data, updated) VALUES (?,?,?,?)',
                        (_uid(), book_id, json.dumps(data, ensure_ascii=False), time.time()))
            con.commit()
        finally:
            con.close()
    return jsonify(ok=True)


# ---- v1.80 錯誤紀錄 ----
# 閱讀頁的錯誤面板在「這一次開書出現任何錯誤或提示」時，把整份紀錄（步驟＋錯誤）送上來；
# 同一次開書（session）重送會覆蓋。每個使用者只留最近 ERRLOG_KEEP 次，避免資料庫無限長大。
# 檢視：登入後打開 /cwfm/api/errlog（只看自己的，新的在前）。
ERRLOG_KEEP = 50
SESSION_RE = re.compile(r'^[0-9]{1,20}$')
ERRLOG_MAX_TEXT = 200 * 1000


@cwfm_api.route('/errlog', methods=['POST'])
@user_login_required
def put_errlog():
    data = _json_body()
    if not isinstance(data, dict):
        abort(400)
    session = str(data.get('session', ''))
    text = data.get('text')
    try:
        book_id = int(data.get('book') or 0)
    except (TypeError, ValueError):
        book_id = 0
    if not SESSION_RE.match(session) or not isinstance(text, str):
        abort(400)
    text = text[:ERRLOG_MAX_TEXT]
    with _lock:
        con = _conn()
        try:
            con.execute('INSERT OR REPLACE INTO errlog (user_id, session, book_id, text, updated) VALUES (?,?,?,?,?)',
                        (_uid(), session, book_id, text, time.time()))
            con.execute('DELETE FROM errlog WHERE user_id=? AND session NOT IN '
                        '(SELECT session FROM errlog WHERE user_id=? ORDER BY updated DESC LIMIT ?)',
                        (_uid(), _uid(), ERRLOG_KEEP))
            con.commit()
        finally:
            con.close()
    return jsonify(ok=True)


@cwfm_api.route('/errlog', methods=['GET'])
@user_login_required
def get_errlog():
    with _lock:
        con = _conn()
        try:
            rows = con.execute('SELECT book_id, text, updated FROM errlog WHERE user_id=? ORDER BY updated DESC',
                               (_uid(),)).fetchall()
        finally:
            con.close()
    tz = time.strftime  # 顯示用伺服器時間（容器通常設 TZ=Asia/Taipei）
    parts = ['cwfm 錯誤紀錄（最近 %d 次出錯的開書，新的在前；共 %d 筆）' % (ERRLOG_KEEP, len(rows))]
    for i, (book_id, text, updated) in enumerate(rows, 1):
        parts.append('=' * 60 + '\n#%d  書號 %s  最後更新 %s\n' % (i, book_id, tz('%Y-%m-%d %H:%M:%S', time.localtime(updated)))
                     + '=' * 60 + '\n' + text)
    return Response('\n\n'.join(parts) + '\n', mimetype='text/plain; charset=utf-8')
