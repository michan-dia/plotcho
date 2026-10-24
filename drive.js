/* プロット帖 — Googleドライブ(アプリ専用フォルダ)との通信 */
(function () {
  'use strict';
  var cfg = window.PLOTCHO_CONFIG || {};
  var CID = String(cfg.googleClientId || '').trim();
  var SCOPE = 'https://www.googleapis.com/auth/drive.appdata';
  var SCOPE_MSG = 'Googleドライブへの保存が許可されていません。もう一度つないで、許可の画面で「Google ドライブに保存されている、このアプリ固有の設定データの参照、作成、削除」にチェックを入れてから「続行」を押してください。';
  var TOKEN_KEY = 'plotcho.gtoken';
  var token = null, exp = 0, gis = null;

  try {
    var saved = JSON.parse(localStorage.getItem(TOKEN_KEY) || 'null');
    if (saved && saved.exp > Date.now() + 60000) { token = saved.token; exp = saved.exp; }
  } catch (e) { /* 保存なし */ }

  function enabled() { return !!CID && !/ここに|xxxx/i.test(CID); }
  function hasToken() { return !!token && Date.now() < exp - 60000; }
  function everConnected() { try { return localStorage.getItem('plotcho.connected') === '1'; } catch (e) { return false; } }

  function loadGis() {
    if (window.google && google.accounts && google.accounts.oauth2) return Promise.resolve();
    if (gis) return gis;
    gis = new Promise(function (res, rej) {
      var s = document.createElement('script');
      s.src = 'https://accounts.google.com/gsi/client';
      s.async = true;
      s.onload = function () { res(); };
      s.onerror = function () { gis = null; rej(new Error('Googleのログイン画面を読み込めませんでした。ネットにつながっているか確認してください。')); };
      document.head.appendChild(s);
    });
    return gis;
  }

  /* ログイン(ボタンを押したときに呼ぶ。ポップアップが開きます) */
  function signIn() {
    return loadGis().then(function () {
      return new Promise(function (res, rej) {
        var client = google.accounts.oauth2.initTokenClient({
          client_id: CID,
          scope: SCOPE,
          callback: function (r) {
            if (!r || r.error) { rej(new Error(r && r.error_description || 'ログインできませんでした')); return; }
            // 許可の画面でドライブのチェックを外していると、ログインできても保存できない
            if (google.accounts.oauth2.hasGrantedAllScopes && !google.accounts.oauth2.hasGrantedAllScopes(r, SCOPE)) { rej(new Error(SCOPE_MSG)); return; }
            token = r.access_token;
            exp = Date.now() + (Number(r.expires_in) || 3600) * 1000;
            try {
              localStorage.setItem(TOKEN_KEY, JSON.stringify({ token: token, exp: exp }));
              localStorage.setItem('plotcho.connected', '1');
            } catch (e) { /* 保存できなくても続ける */ }
            res();
          },
          error_callback: function (e) {
            rej(new Error(e && e.type === 'popup_closed' ? 'ログインの画面が閉じられました' : 'ログインの画面を開けませんでした'));
          }
        });
        client.requestAccessToken({ prompt: everConnected() ? '' : 'consent' });
      });
    });
  }

  function signOut() {
    var t = token; token = null; exp = 0;
    try { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem('plotcho.connected'); } catch (e) { /* なし */ }
    if (t && window.google && google.accounts && google.accounts.oauth2) google.accounts.oauth2.revoke(t, function () {});
  }

  function dropToken() { token = null; exp = 0; try { localStorage.removeItem(TOKEN_KEY); } catch (e) { /* なし */ } }

  /* ドライブから返ってきたエラーを、分かる言葉にする */
  async function driveError(r) {
    var j = null; try { j = await r.json(); } catch (e) { /* 本文なし */ }
    var er = (j && j.error) || {};
    var reason = (er.errors && er.errors[0] && er.errors[0].reason) || er.status || '';
    var msg = er.message || '', all = reason + ' ' + msg, text, auth = false;
    if (r.status === 403 && /insufficient|SCOPE/i.test(all)) { dropToken(); auth = true; text = SCOPE_MSG; }
    else if (r.status === 403 && /accessNotConfigured|SERVICE_DISABLED|has not been used|is disabled/i.test(all)) text = 'Google Cloud のこのプロジェクトで「Google Drive API」が有効になっていません。Google Cloud Console の「APIとサービス」→「ライブラリ」で有効にしてください。';
    else if ((r.status === 403 || r.status === 429) && /rate|quota/i.test(all)) text = 'Googleドライブへの通信が多すぎました。少し待ってからもう一度お試しください。';
    else if (r.status === 413) text = '作品のデータが大きすぎて送れませんでした。';
    else text = 'ドライブとの通信に失敗しました(' + r.status + (reason ? ' ' + reason : '') + ')' + (msg ? '：' + msg : '');
    var e = new Error(text); e.auth = auth; return e;
  }

  async function api(path, opt) {
    opt = opt || {};
    var headers = Object.assign({ Authorization: 'Bearer ' + token }, opt.headers || {});
    var r;
    try { r = await fetch(/^https:/.test(path) ? path : 'https://www.googleapis.com' + path, Object.assign({}, opt, { headers: headers })); }
    catch (e) { throw new Error('Googleに接続できませんでした。インターネットにつながっているか確かめてください。'); }
    if (r.status === 401) { dropToken(); var err = new Error('ログインの期限が切れました'); err.auth = true; throw err; }
    if (r.status === 404 && opt.method === 'DELETE') return r;
    if (!r.ok) throw await driveError(r);
    return r;
  }

  /* アプリ専用フォルダの plotcho- で始まるファイルを全部 */
  function list() {
    var out = [];
    function page(pt) {
      var q = encodeURIComponent("name contains 'plotcho-' and trashed = false");
      return api('/drive/v3/files?spaces=appDataFolder&pageSize=1000&fields=nextPageToken,files(id,name,modifiedTime,appProperties)&q=' + q + (pt ? '&pageToken=' + encodeURIComponent(pt) : ''))
        .then(function (r) { return r.json(); })
        .then(function (j) { out = out.concat(j.files || []); return j.nextPageToken ? page(j.nextPageToken) : out; });
    }
    return page('');
  }

  function download(id) {
    return api('/drive/v3/files/' + encodeURIComponent(id) + '?alt=media').then(function (r) { return r.json(); });
  }

  /* 作品を1つ保存。fileId があれば上書き、なければ新しく作る */
  function upload(project, fileId) {
    var data = Object.assign({}, project);
    delete data.remoteId; delete data.syncedAt;
    var meta = { name: 'plotcho-' + project.id + '.json', mimeType: 'application/json', appProperties: { pid: project.id, updatedAt: String(project.updatedAt || 0) } };
    if (!fileId) meta.parents = ['appDataFolder'];
    var dataStr = JSON.stringify(data);
    // 大きい作品(4.5MBより大きい)は、分けて送る方式(resumable)にする
    if (new Blob([dataStr]).size > 4.5 * 1024 * 1024) {
      return api(fileId ? '/upload/drive/v3/files/' + encodeURIComponent(fileId) + '?uploadType=resumable&fields=id,modifiedTime' : '/upload/drive/v3/files?uploadType=resumable&fields=id,modifiedTime',
        { method: fileId ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json; charset=UTF-8', 'X-Upload-Content-Type': 'application/json' }, body: JSON.stringify(meta) })
        .then(function (init) {
          var loc = init.headers.get('location');
          if (!loc) throw new Error('作品のデータが大きすぎて送れませんでした。画像を減らすか、PC版で同期してください。');
          return fetch(loc, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: dataStr });
        })
        .then(async function (r) { if (!r.ok) throw await driveError(r); return r.json(); });
    }
    var b = 'plotcho' + Math.random().toString(36).slice(2);
    var body = '--' + b + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' + JSON.stringify(meta) +
      '\r\n--' + b + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' + dataStr + '\r\n--' + b + '--';
    var url = fileId
      ? '/upload/drive/v3/files/' + encodeURIComponent(fileId) + '?uploadType=multipart&fields=id,modifiedTime'
      : '/upload/drive/v3/files?uploadType=multipart&fields=id,modifiedTime';
    return api(url, { method: fileId ? 'PATCH' : 'POST', headers: { 'Content-Type': 'multipart/related; boundary=' + b }, body: body })
      .then(function (r) { return r.json(); });
  }

  function remove(id) {
    return api('/drive/v3/files/' + encodeURIComponent(id), { method: 'DELETE' }).then(function () { return true; });
  }

  /* ---------- PC版(Electron): ログインと通信はメイン側に任せる ---------- */
  var native = window.plotchoNative || null;
  if (native) {
    var st = { configured: false, signedIn: false };
    var call = function (p) {
      return p.then(function (r) {
        if (r && r.ok) return r.value;
        var e = new Error((r && r.message) || 'ドライブとの通信に失敗しました');
        if (r && r.auth) { e.auth = true; st.signedIn = false; }
        throw e;
      });
    };
    window.PlotDrive = {
      native: true,
      init: function () { return native.authStatus().then(function (s) { st = s || st; }).catch(function () {}); },
      enabled: function () { return st.configured; },
      hasToken: function () { return st.signedIn; },
      everConnected: function () { return st.signedIn; },
      signIn: function () { return call(native.signIn()).then(function () { st.signedIn = true; }); },
      signOut: function () { st.signedIn = false; return native.signOut(); },
      list: function () { return call(native.driveList()); },
      download: function (id) { return call(native.driveDownload(id)); },
      upload: function (p, fileId) { return call(native.driveUpload(JSON.parse(JSON.stringify(p)), fileId || null)); },
      remove: function (id) { return call(native.driveRemove(id)); }
    };
    return;
  }

  window.PlotDrive = {
    native: false,
    init: function () { return Promise.resolve(); },
    enabled: enabled, hasToken: hasToken, everConnected: everConnected,
    signIn: signIn, signOut: signOut, list: list, download: download, upload: upload, remove: remove
  };
})();
