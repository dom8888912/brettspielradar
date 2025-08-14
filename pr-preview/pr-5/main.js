// ui-version:2025-08-11-v5 – Menü-Overlay & Tooltip Toggle (inline neben Titel)
(function(){
  // Menü
  var btn = document.getElementById('nav-toggle');
  var nav = document.getElementById('main-nav');
  if (btn && nav){
    function closeNav(){ nav.classList.remove('open'); btn.setAttribute('aria-expanded','false'); }
    btn.addEventListener('click', function(e){
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      e.stopPropagation();
    });
    document.addEventListener('click', function(e){
      if (!nav.contains(e.target) && e.target !== btn){ closeNav(); }
    });
    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') closeNav();
    });
  }

  // Tooltip (für Touch/Keyboard: Toggle per Klick)
  document.addEventListener('click', function(e){
    var badge = e.target.closest('.info-badge');
    var openBadge = document.querySelector('.info-badge[aria-expanded="true"]');
    if (badge){
      var isOpen = badge.getAttribute('aria-expanded') === 'true';
      if (openBadge && openBadge !== badge){ openBadge.setAttribute('aria-expanded','false'); }
      badge.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
      e.stopPropagation();
    }else{
      if (openBadge){ openBadge.setAttribute('aria-expanded','false'); }
    }
  });
})();