(function () {
  var root = document.getElementById('play');
  var TYPE = root.dataset.type, KEY = root.dataset.key;
  var $ = function (id) { return document.getElementById(id); };
  var idx = 0, last = null, elapsed = 0, paused = false, busy = false, maxQ = null, timer = null;

  function api(path, method, body) {
    return fetch('/api/quiz/' + path, {
      method: method || 'GET', headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    }).then(function (r) { return r.json(); });
  }
  function msg(t) { $('msgText').textContent = t; $('msgModal').classList.add('open'); }
  function clock(s) { return ('0' + Math.floor(s / 60)).slice(-2) + ':' + ('0' + (s % 60)).slice(-2); }
  function tick() { if (!paused) { elapsed++; $('sT').textContent = clock(elapsed); } }

  function setState(s) {
    $('sH').textContent = s.hints_left; $('sC').textContent = s.correct;
    $('sW').textContent = s.wrong; $('sS').textContent = s.score;
    maxQ = s.total;
  }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; }

  function render(q) {
    last = q; idx = q.index;
    $('sQ').textContent = maxQ ? q.number + ' of ' + maxQ : q.number;
    $('qText').textContent = q.question;
    var html = '';
    ['A', 'B', 'C', 'D'].forEach(function (L) {
      html += '<button type="button" class="opt" data-l="' + L + '"><span class="badge">' + L + '</span><span>' + esc(q.options[L]) + '</span></button>';
    });
    $('opts').innerHTML = html;
    setState(q.state);
    var reveal = q.answered || q.hinted;
    if (reveal) paint(q.correct_option, q.choice, q.explanation);
    else { $('solBox').hidden = true; }
    $('opts').querySelectorAll('.opt').forEach(function (b) {
      if (reveal) b.disabled = true;
      b.addEventListener('click', function () { answer(b.dataset.l); });
    });
    $('bPrev').disabled = idx === 0;
    $('bHint').disabled = TYPE === 'daily';
    if (TYPE === 'daily') $('bHint').style.display = 'none';
  }

  function paint(correct, choice, expl) {
    $('opts').querySelectorAll('.opt').forEach(function (b) {
      b.disabled = true;
      if (b.dataset.l === correct) b.classList.add('right');
      else if (b.dataset.l === choice) b.classList.add('wrong');
    });
    $('solText').textContent = expl || '';
    $('solBox').hidden = false;
  }

  function load(i) {
    return api('question/' + i).then(function (r) {
      if (!r.ok) { msg(r.error); return; }
      render(r);
    });
  }

  function answer(L) {
    if (busy || last.answered || last.hinted) return;
    busy = true;
    api('answer', 'POST', { index: idx, choice: L }).then(function (r) {
      busy = false;
      if (!r.ok) { msg(r.error); return; }
      last.answered = true; last.choice = L;
      setState(r.state);
      paint(r.correct_option, L, r.explanation);
    });
  }

  $('bHint').addEventListener('click', function () {
    if (last.answered || last.hinted) return;
    api('hint', 'POST', { index: idx }).then(function (r) {
      if (!r.ok) { msg(r.error); return; }
      last.hinted = true; setState(r.state);
      paint(r.correct_option, null, r.explanation);
    });
  });
  $('bPrev').addEventListener('click', function () { if (idx > 0) load(idx - 1); });
  $('bNext').addEventListener('click', function () {
    if (!last.answered && !last.hinted) { msg('Please answer the question (or use a hint) before continuing.'); return; }
    if (maxQ && idx + 1 >= maxQ) { msg('That was the last question for today. Click Finish & Save.'); return; }
    load(idx + 1);
  });
  $('bPause').addEventListener('click', function () { paused = true; $('pauseModal').classList.add('open'); });
  $('bResume').addEventListener('click', function () { paused = false; $('pauseModal').classList.remove('open'); });
  $('bExit').addEventListener('click', function () { $('exitModal').classList.add('open'); });
  $('bExitYes').addEventListener('click', function () {
    api('exit', 'POST').then(function () { location.href = root.dataset.home; });
  });
  $('bFinish').addEventListener('click', function () {
    api('finish', 'POST', { time: elapsed }).then(function (r) {
      if (!r.ok) { msg(r.error); return; }
      clearInterval(timer);
      $('rHome').href = root.dataset.home; $('rHist').href = root.dataset.after;
      if (!r.saved) { $('rTitle').textContent = 'Nothing to save'; $('rBody').innerHTML = '<p>' + esc(r.message) + '</p>'; }
      else {
        $('rTitle').textContent = 'Quiz Saved! 🎉';
        $('rBody').innerHTML = '<p>Questions: <b>' + r.questions + '</b></p><p>Correct: <b>' + r.correct +
          '</b> &nbsp; Wrong: <b>' + r.wrong + '</b></p><p>Score: <b>' + r.score + '</b></p><p>Time: <b>' + clock(r.time) + '</b></p>';
      }
      $('resultModal').classList.add('open');
    });
  });

  api('start', 'POST', { type: TYPE, key: KEY }).then(function (r) {
    if (!r.ok) { msg(r.error); $('qText').textContent = r.error; return; }
    setState(r.state);
    timer = setInterval(tick, 1000);
    load(0);
  });
})();
