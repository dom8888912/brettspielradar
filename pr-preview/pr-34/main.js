// ui-version:2025-08-11-v8 – Menü-Overlay, Tooltip Toggle, Suche & Cookie-Banner unten
(function(){
  // Menü
  var btn = document.getElementById('nav-toggle');
  var nav = document.getElementById('main-nav');
  if (btn && nav){
    function closeNav(){ nav.classList.remove('open'); btn.classList.remove('open'); btn.setAttribute('aria-expanded','false'); }
    btn.addEventListener('click', function(e){
      var open = nav.classList.toggle('open');
      btn.classList.toggle('open', open);
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

  // Suche & Filter
  var q = document.getElementById('q');
  var list = document.querySelector('[data-list]');
  var pFilter = document.getElementById('filter-players');
  var aFilter = document.getElementById('filter-age');
  var tFilter = document.getElementById('filter-theme');

  function applyFilters(){
    if (!list) return;
    var term = q ? q.value.toLowerCase() : '';
    var players = pFilter && pFilter.value ? parseInt(pFilter.value,10) : null;
    var age = aFilter && aFilter.value ? parseInt(aFilter.value,10) : null;
    var theme = tFilter && tFilter.value ? tFilter.value : null;
    list.querySelectorAll('li').forEach(function(li){
      var textMatch = !term || li.textContent.toLowerCase().indexOf(term) !== -1;
      var pMatch = true;
      var aMatch = true;
      var tMatch = true;
      if (players !== null){
        var min = parseInt(li.dataset.minPlayers,10);
        var max = parseInt(li.dataset.maxPlayers,10);
        if (!isNaN(min) && !isNaN(max)){
          pMatch = players >= min && players <= max;
        }else{
          pMatch = false;
        }
      }
      if (age !== null){
        var gAge = parseInt(li.dataset.age,10);
        if (!isNaN(gAge)){
          aMatch = gAge <= age;
        }else{
          aMatch = false;
        }
      }
      if (theme){
        var themes = li.dataset.themes ? li.dataset.themes.split(',') : [];
        tMatch = themes.indexOf(theme) !== -1;
      }
      li.style.display = (textMatch && pMatch && aMatch && tMatch) ? '' : 'none';
    });
  }
  [q, pFilter, aFilter, tFilter].forEach(function(el){
    if (el){
      el.addEventListener('input', applyFilters);
      el.addEventListener('change', applyFilters);
    }
  });
  applyFilters();

  // Cookie Banner
  var banner = document.getElementById('cookie-banner');
  var accept = document.getElementById('cookie-accept');
  var decline = document.getElementById('cookie-decline');
  var settingsAccept = document.getElementById('settings-accept');
  var settingsDecline = document.getElementById('settings-decline');
  var status = document.getElementById('consent-status');

  function showStatus(msg){
    if (status){
      status.textContent = msg;
      status.style.display = 'block';
      setTimeout(function(){ status.style.display='none'; }, 3000);
    }
  }

  function consentAccept(){
    localStorage.setItem('cookie-consent','accepted');
    document.documentElement.classList.remove('cookies-pending');
    document.documentElement.classList.add('cookies-accepted');
    if (banner) banner.style.display='none';
    if (typeof loadAnalytics === 'function'){ loadAnalytics(); }
  }
  function consentDecline(){
    localStorage.setItem('cookie-consent','declined');
    document.documentElement.classList.remove('cookies-pending');
    document.documentElement.classList.add('cookies-declined');
    if (banner) banner.style.display='none';
  }

  if (accept) accept.addEventListener('click', consentAccept);
  if (decline) decline.addEventListener('click', consentDecline);
  if (settingsAccept) settingsAccept.addEventListener('click', function(){
    consentAccept();
    showStatus('Einstellungen gespeichert.');
  });
  if (settingsDecline) settingsDecline.addEventListener('click', function(){
    consentDecline();
    showStatus('Einstellungen gespeichert.');
  });
})();
