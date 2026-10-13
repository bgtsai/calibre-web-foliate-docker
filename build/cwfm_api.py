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

from flask import Blueprint, jsonify, request, abort
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
