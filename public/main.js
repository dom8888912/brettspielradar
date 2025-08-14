// ui-version:2025-08-11-v8 – Menü-Overlay, Tooltip Toggle, Cookie-Banner & GA
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

  // Cookie-Banner & Google Analytics
  var gaId = window.GA_TRACKING_ID;
  function loadAnalytics(){
    if(!gaId) return;
    var s1 = document.createElement('script');
    s1.src = 'https://www.googletagmanager.com/gtag/js?id=' + gaId;
    s1.async = true;
    document.head.appendChild(s1);
    var s2 = document.createElement('script');
    s2.innerHTML = "window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js', new Date());gtag('config', '" + gaId + "');";
    document.head.appendChild(s2);
  }
  var consent = localStorage.getItem('ga_consent');
  var banner = document.getElementById('cookie-banner');
  var accept = document.getElementById('cookie-accept');
  var reject = document.getElementById('cookie-reject');
  if(consent === 'granted'){
    loadAnalytics();
  }
  if(consent === 'granted' || consent === 'denied'){
    if(banner) banner.classList.add('hidden');
  }
  if(banner){
    if(accept) accept.addEventListener('click', function(){
      localStorage.setItem('ga_consent','granted');
      banner.classList.add('hidden');
      loadAnalytics();
    });
    if(reject) reject.addEventListener('click', function(){
      localStorage.setItem('ga_consent','denied');
      banner.classList.add('hidden');
    });
  }
})();
