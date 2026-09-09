// Small share affordance: the .qr-btn buttons in the sidebar open a QR code
// for the site so it can be scanned in person. Plain DOM, outside the page
// runtime, so it works identically on every page.
(function () {
  var modal = null;
  function build() {
    modal = document.createElement('div');
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-label', 'QR code for alexandertbell.com');
    modal.style.cssText = 'position:fixed;inset:0;z-index:110;background:rgba(23,23,15,0.82);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;cursor:zoom-out;padding:40px';
    modal.innerHTML =
      '<div style="background:#ffffff;padding:16px;line-height:0"><img src="/media/qr.svg" alt="QR code linking to alexandertbell.com" width="240" height="240" style="display:block;width:min(240px,70vw);height:auto"></div>' +
      '<span style="font-size:12px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#eff0e6">alexandertbell.com</span>';
    modal.addEventListener('click', hide);
    document.body.appendChild(modal);
  }
  function show() { if (!modal) build(); modal.style.display = 'flex'; }
  function hide() { if (modal) modal.style.display = 'none'; }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.qr-btn');
    if (b) { e.preventDefault(); show(); }
  });
  window.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });
})();
