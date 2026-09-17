/* AirBridge — proof of concept.
   Rules-based field reading is represented by predefined fields in the markup:
   no network requests, no storage, no external libraries. */
(function () {
  'use strict';

  var views = {
    record: document.getElementById('view-record'),
    review: document.getElementById('view-review'),
    overview: document.getElementById('view-overview')
  };
  var navButtons = Array.prototype.slice.call(document.querySelectorAll('.steps .step'));
  var live = document.getElementById('liveRegion');
  var docScroll = document.getElementById('docScroll');

  function announce(text) { live.textContent = text; }

  function showView(name) {
    closeSourceView();
    Object.keys(views).forEach(function (key) {
      var active = key === name;
      views[key].classList.toggle('is-active', active);
      views[key].hidden = !active;
    });
    navButtons.forEach(function (btn) {
      var active = btn.dataset.view === name;
      btn.classList.toggle('is-current', active);
      if (active) { btn.setAttribute('aria-current', 'step'); } else { btn.removeAttribute('aria-current'); }
    });
    window.scrollTo(0, 0);
  }
  function enableStep(name) {
    navButtons.forEach(function (btn) { if (btn.dataset.view === name) btn.disabled = false; });
  }
  navButtons.forEach(function (btn) {
    btn.addEventListener('click', function () { if (!btn.disabled) showView(btn.dataset.view); });
  });

  /* ---------- source highlighting ---------- */
  var sourceButtons = Array.prototype.slice.call(document.querySelectorAll('[data-source]'));
  var smallScreen = window.matchMedia('(max-width: 760px)');
  var closeSourceBtn = document.getElementById('closeSource');
  var lastSourceBtn = null;

  function openSourceView(trigger) {
    if (!smallScreen.matches) return;
    lastSourceBtn = trigger || null;
    document.body.classList.add('source-open');
    closeSourceBtn.focus();
  }
  function closeSourceView() {
    if (!document.body.classList.contains('source-open')) return;
    document.body.classList.remove('source-open');
    if (lastSourceBtn) { lastSourceBtn.focus(); lastSourceBtn = null; }
  }
  closeSourceBtn.addEventListener('click', closeSourceView);
  smallScreen.addEventListener('change', function () { if (!smallScreen.matches) closeSourceView(); });

  function clearHighlights() {
    docScroll.querySelectorAll('.is-highlight').forEach(function (el) { el.classList.remove('is-highlight'); });
    sourceButtons.forEach(function (b) { b.classList.remove('is-active'); });
  }
  sourceButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var wasActive = btn.classList.contains('is-active');
      clearHighlights();
      if (wasActive) { announce('Source highlight cleared.'); return; }
      btn.classList.add('is-active');
      var ids = btn.dataset.source.split(' ');
      var first = null;
      ids.forEach(function (id) {
        var el = document.getElementById(id);
        if (!el) return;
        el.classList.add('is-highlight');
        if (!first) first = el;
      });
      if (first) {
        if (smallScreen.matches) {
          openSourceView(btn);
          first.scrollIntoView({ block: 'center' });
        } else {
          var top = first.offsetTop - docScroll.clientHeight / 3;
          docScroll.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
        }
        announce('Supporting sentence highlighted in the source document.');
      }
    });
  });

  /* ---------- collapsible detail ---------- */
  function wireToggle(buttonId, listId, labels) {
    var btn = document.getElementById(buttonId);
    var list = document.getElementById(listId);
    btn.addEventListener('click', function () {
      var open = list.hidden;
      list.hidden = !open;
      btn.setAttribute('aria-expanded', String(open));
      btn.textContent = open ? labels[1] : labels[0];
    });
  }
  wireToggle('medToggle', 'medList', ['Show 5 entries', 'Hide entries']);
  wireToggle('recToggle', 'recList', ['Show 4 further recommendations', 'Hide further recommendations']);

  /* ---------- review actions ---------- */
  var openDoc = document.getElementById('openDoc');
  var verifyBtn = document.getElementById('verifyBtn');
  var continueBtn = document.getElementById('continueBtn');
  var createBtn = document.getElementById('createBtn');
  var followupBox = document.getElementById('followupBox');
  var reviewStatus = document.getElementById('reviewStatus');
  var queueStatus = document.getElementById('queueStatus');
  var reviewNote = document.getElementById('reviewNote');
  var otherBtn = document.getElementById('otherBtn');
  var otherMenu = document.getElementById('otherMenu');
  var sheetMeta = document.getElementById('sheetMeta');
  var sheetStamp = document.getElementById('sheetStamp');
  var savedMsg = document.getElementById('savedMsg');

  openDoc.addEventListener('click', function () {
    enableStep('review');
    showView('review');
    announce('Hospital discharge report opened for review.');
  });

  function setStatus(el, text, done) {
    el.textContent = text;
    el.classList.toggle('status-done', done);
    el.classList.toggle('status-pending', !done);
  }

  function stamp() {
    var d = new Date();
    var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
      'August', 'September', 'October', 'November', 'December'];
    var hh = String(d.getHours()).padStart(2, '0');
    var mm = String(d.getMinutes()).padStart(2, '0');
    return d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear() + ', ' + hh + ':' + mm;
  }

  verifyBtn.addEventListener('click', function () {
    var when = stamp();
    setStatus(reviewStatus, 'Reviewed', true);
    setStatus(queueStatus, 'Reviewed', true);
    verifyBtn.hidden = true;
    continueBtn.hidden = false;
    reviewNote.textContent = 'Fields verified by the GP against the source document on ' + when + '.';
    sheetMeta.textContent = 'Fields verified by the GP · ' + when;
    sheetStamp.textContent = 'Fields read from the listed sources and verified by the GP on ' + when
      + ' in this demo session. AirBridge added no clinical interpretation.';
    continueBtn.focus();
    announce('Fields verified. You can continue with GP follow-up.');
  });

  continueBtn.addEventListener('click', function () {
    followupBox.hidden = false;
    continueBtn.hidden = true;
    createBtn.focus();
    announce('GP follow-up recorded in this demo session.');
  });

  createBtn.addEventListener('click', function () {
    enableStep('overview');
    showView('overview');
    announce('COPD overview created.');
  });

  /* alternative actions: one restrained menu */
  function closeMenu() {
    otherMenu.hidden = true;
    otherBtn.setAttribute('aria-expanded', 'false');
  }
  otherBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    var open = otherMenu.hidden;
    otherMenu.hidden = !open;
    otherBtn.setAttribute('aria-expanded', String(open));
  });
  otherMenu.querySelectorAll('button').forEach(function (item) {
    item.addEventListener('click', function () {
      closeMenu();
      reviewNote.textContent = item.dataset.alt + ' — recorded in this demo session. The GP decides how the episode continues.';
      announce(item.dataset.alt + ' recorded in this demo session.');
      reviewNote.focus && reviewNote.focus();
    });
  });
  document.addEventListener('click', function (e) {
    if (!otherMenu.hidden && !e.target.closest('.menu-wrap')) closeMenu();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (!otherMenu.hidden) { closeMenu(); otherBtn.focus(); return; }
    closeSourceView();
  });

  /* ---------- overview actions ---------- */
  document.getElementById('saveBtn').addEventListener('click', function () {
    savedMsg.hidden = false;
    announce('Overview saved in this demo session.');
  });
  document.getElementById('printBtn').addEventListener('click', function () { window.print(); });

  /* ---------- start over ---------- */
  function reset() {
    closeSourceView();
    clearHighlights();
    ['medList', 'recList'].forEach(function (id) { document.getElementById(id).hidden = true; });
    document.getElementById('medToggle').textContent = 'Show 5 entries';
    document.getElementById('medToggle').setAttribute('aria-expanded', 'false');
    document.getElementById('recToggle').textContent = 'Show 4 further recommendations';
    document.getElementById('recToggle').setAttribute('aria-expanded', 'false');
    setStatus(reviewStatus, 'Pending review', false);
    setStatus(queueStatus, 'Pending review', false);
    verifyBtn.hidden = false;
    continueBtn.hidden = true;
    followupBox.hidden = true;
    savedMsg.hidden = true;
    closeMenu();
    reviewNote.textContent = 'Check each field against the source document, then verify the fields.';
    sheetMeta.textContent = 'Reviewed in demo session';
    sheetStamp.textContent = 'Fields read from the listed sources and reviewed by the GP in this demo session.';
    docScroll.scrollTop = 0;
    navButtons.forEach(function (btn) { if (btn.dataset.view !== 'record') btn.disabled = true; });
    showView('record');
    openDoc.focus();
    announce('Demo reset. Patient record shown.');
  }
  document.getElementById('startOver').addEventListener('click', reset);
  document.getElementById('restartBtn').addEventListener('click', reset);
})();
