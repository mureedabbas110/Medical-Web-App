(function () {
  var tb = document.getElementById('rows'); if (!tb) return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  var opts = '<option value="">-- medicine --</option>' + MEDS.map(function (m) {
    return '<option value="' + m.id + '">' + esc(m.name) + (m.company ? ' (' + esc(m.company) + ')' : '') + ' - Rs.' + Math.round(m.sell_price) + ' - stock ' + Math.round(m.stock) + '</option>';
  }).join('');
  function find(id) { for (var i = 0; i < MEDS.length; i++) if (String(MEDS[i].id) === String(id)) return MEDS[i]; }
  function addRow() {
    var tr = document.createElement('tr');
    tr.innerHTML = '<td><select name="med_id">' + opts + '</select></td><td><input type="number" name="qty" min="1" value="1" style="width:80px"></td><td class="p">0</td><td class="l">0</td><td><button type="button" class="btn btn-sm btn-danger rm">X</button></td>';
    tb.appendChild(tr);
  }
  function calc() {
    var sub = 0;
    tb.querySelectorAll('tr').forEach(function (tr) {
      var m = find(tr.querySelector('select').value), q = +tr.querySelector('input').value || 0, p = m ? m.sell_price : 0;
      tr.querySelector('.p').textContent = Math.round(p); tr.querySelector('.l').textContent = Math.round(p * q);
      tr.querySelector('input').style.borderColor = (m && q > m.stock) ? '#c0392b' : '';
      sub += p * q;
    });
    var d = Math.min(+document.getElementById('discount').value || 0, sub);
    document.getElementById('sub').textContent = 'Rs. ' + Math.round(sub);
    document.getElementById('total').textContent = 'Rs. ' + Math.round(sub - d);
  }
  document.getElementById('addRow').addEventListener('click', function () { addRow(); calc(); });
  document.getElementById('saleForm').addEventListener('input', calc);
  document.getElementById('saleForm').addEventListener('change', calc);
  tb.addEventListener('click', function (e) {
    if (e.target.classList.contains('rm')) { if (tb.children.length > 1) e.target.closest('tr').remove(); calc(); }
  });
  addRow(); calc();
})();
