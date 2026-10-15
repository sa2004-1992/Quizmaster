(function () {
  document.querySelectorAll('[data-close]').forEach(function (b) {
    b.addEventListener('click', function () { b.closest('.modal').classList.remove('open'); });
  });
  var lo = document.getElementById('btnLogout');
  if (lo) lo.addEventListener('click', function () { document.getElementById('logoutModal').classList.add('open'); });
  var dt = document.getElementById('darkToggle');
  if (dt) dt.addEventListener('change', function () {
    document.documentElement.setAttribute('data-theme', dt.checked ? 'dark' : 'light');
    fetch(window.TOGGLE_URL, { method: 'POST' });
  });
})();
