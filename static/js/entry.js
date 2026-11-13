(function () {
  var f = document.getElementById('entryForm'); if (!f) return;
  var $ = function (i) { return document.getElementById(i); };
  var fee = $('fee'), disc = $('discount'), doc = $('doctor'), room = $('room'), other = $('other'), adv = $('advance'), op = $('op');
  function n(e) { return e ? (+e.value || 0) : 0; }
  function calc() {
    if (f.dataset.module === 'lab') {
      var s = 0; f.querySelectorAll('input[name=tests]:checked').forEach(function (c) { s += +c.dataset.price; }); fee.value = s;
    }
    var t = Math.max(n(fee) + n(room) + n(other) - n(disc), 0);
    $('total').textContent = 'Rs. ' + t;
    if ($('balance')) $('balance').textContent = 'Rs. ' + Math.max(t - n(adv), 0);
  }
  f.addEventListener('input', calc); f.addEventListener('change', calc); f.addEventListener('reset', function () { setTimeout(calc, 0); });
  if (doc && f.dataset.module === 'opd') doc.addEventListener('change', function () {
    var o = doc.options[doc.selectedIndex]; fee.value = o && o.dataset.fee ? Math.round(o.dataset.fee) : 0; calc();
  });
  if (op) op.addEventListener('change', function () {
    var o = op.options[op.selectedIndex]; fee.value = o && o.dataset.price ? Math.round(o.dataset.price) : 0; calc();
  });
  $('pid').addEventListener('change', function () {
    if (!this.value.trim()) return;
    fetch('/api/patient/' + encodeURIComponent(this.value.trim())).then(function (r) { return r.json(); }).then(function (p) {
      if (!p.pid) return alert('Patient ID not found');
      ['name', 'age_y', 'age_m', 'phone', 'address'].forEach(function (k) { $(k).value = p[k] || ''; });
    });
  });
  var ph = $('phone'), hits = $('hits');
  function fill(p) { ['pid', 'name', 'age_y', 'age_m', 'phone', 'address'].forEach(function (k) { $(k).value = p[k] == null ? '' : p[k]; }); hits.innerHTML = ''; }
  ph.addEventListener('change', function () {
    if ($('pid').value.trim()) return;
    fetch('/api/phone/' + encodeURIComponent(ph.value)).then(function (r) { return r.json(); }).then(function (list) {
      hits.innerHTML = ''; if (!list.length) return;
      var box = document.createElement('div'); box.className = 'hit-box';
      box.innerHTML = '<b>Is phone par patient pehle se hai - chunein:</b>';
      list.forEach(function (p) {
        var b = document.createElement('button'); b.type = 'button'; b.className = 'btn btn-sm';
        b.textContent = p.name + ' (' + p.pid + ') - ' + p.visits + ' visits' + (p.last ? ', last ' + p.last : '');
        b.onclick = function () { fill(p); }; box.appendChild(b);
      });
      hits.appendChild(box);
    });
  });
  calc();
})();
