(function () {
  var b = document.getElementById('menuBtn'), s = document.getElementById('sidebar'), c = document.getElementById('scrim');
  if (!b) return;
  function set(o) { s.classList.toggle('open', o); c.classList.toggle('show', o); b.setAttribute('aria-expanded', o); }
  b.addEventListener('click', function () { set(!s.classList.contains('open')); });
  c.addEventListener('click', function () { set(false); });
  setTimeout(function () { document.querySelectorAll('.toast.ok').forEach(function (t) { t.style.display = 'none'; }); }, 4000);
})();
