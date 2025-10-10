
// ui-version:2025-08-23-v15 – Menü-Overlay, Preisindikator ohne Graph, Suche & Cookie-Banner unten
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

  var currencyFormatter;
  try {
    currencyFormatter = new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  } catch (err) {
    currencyFormatter = null;
  }

  function isFiniteNumber(value){
    return typeof value === 'number' && isFinite(value);
  }

  function parseNumber(value){
    if (value === undefined || value === null || value === '') return null;
    if (typeof value === 'number') return isFiniteNumber(value) ? value : null;
    var num = parseFloat(value);
    return isFinite(num) ? num : null;
  }

  function formatCurrency(value){
    if (!isFiniteNumber(value)) return null;
    if (currencyFormatter) return currencyFormatter.format(value);
    return value.toFixed(2).replace('.', ',') + ' €';
  }

  function formatDelta(value){
    if (!isFiniteNumber(value)) return null;
    var abs = Math.abs(value);
    var formatted = abs < 10 ? value.toFixed(1) : value.toFixed(0);
    var prefix = value > 0 ? '+' : '';
    return prefix + formatted.replace('.', ',') + '% vs. 7-Tage-Ø';
  }

  function updatePriceIndicators(){
    var indicators = document.querySelectorAll('.bpr-price-indicator');
    if (!indicators.length) return;

    Array.prototype.forEach.call(indicators, function(el){
      var dataset = el.dataset || {};
      var current = parseNumber(dataset.current);
      var avg7 = parseNumber(dataset.sevenDayAverage);
      var historyValues = [];

      if (dataset.history){
        try {
          var parsed = JSON.parse(dataset.history);
          if (Array.isArray(parsed)){
            parsed.forEach(function(entry){
              if (!entry) return;
              var val = parseNumber(entry.min !== undefined ? entry.min : entry.avg);
              if (val !== null) historyValues.push(val);
            });
          }
        } catch (err) {
          // ignore invalid history payloads
        }
      }

      if (!historyValues.length && current !== null){
        historyValues.push(current);
      }

      var low = historyValues.length ? Math.min.apply(null, historyValues) : null;
      var high = historyValues.length ? Math.max.apply(null, historyValues) : null;

      if (current !== null){
        var currentField = el.querySelector('[data-field="current"]');
        var formattedCurrent = formatCurrency(current);
        if (currentField && formattedCurrent) currentField.textContent = formattedCurrent;
      }

      if (avg7 !== null){
        var avg7Field = el.querySelector('[data-field="avg7"]');
        var formattedAvg = formatCurrency(avg7);
        if (avg7Field && formattedAvg) avg7Field.textContent = formattedAvg;
      }

      if (low !== null){
        var formattedLow = formatCurrency(low);
        if (formattedLow){
          el.querySelectorAll('[data-field="low30"]').forEach(function(node){
            node.textContent = formattedLow;
          });
        }
      }

      if (high !== null){
        var formattedHigh = formatCurrency(high);
        if (formattedHigh){
          el.querySelectorAll('[data-field="high30"]').forEach(function(node){
            node.textContent = formattedHigh;
          });
        }
      }

      var deltaField = el.querySelector('[data-field="delta"]');
      if (deltaField){
        if (current !== null && avg7 !== null && avg7 !== 0){
          var delta = ((current - avg7) / avg7) * 100;
          var deltaText = formatDelta(delta);
          if (deltaText){
            deltaField.textContent = deltaText;
            deltaField.setAttribute('data-delta', delta.toFixed(2));
          } else {
            deltaField.textContent = '–';
            deltaField.removeAttribute('data-delta');
          }
        } else {
          deltaField.textContent = '–';
          deltaField.removeAttribute('data-delta');
        }
      }

      var marker = el.querySelector('.bpr-gauge__marker');
      var fill = el.querySelector('.bpr-gauge__fill');
      if (marker || fill){
        if (current !== null && low !== null && high !== null){
          var range = high - low;
          var pos = range <= 0 ? 0.5 : (current - low) / range;
          pos = Math.min(1, Math.max(0, pos));
          var percent = (pos * 100) + '%';
          if (fill) fill.style.width = percent;
          if (marker){
            marker.style.left = percent;
            marker.setAttribute('aria-label', 'Preisposition ' + Math.round(pos * 100) + '% zwischen Tief und Hoch');
          }
        } else {
          if (fill) fill.style.width = '0%';
          if (marker){
            marker.style.left = '0%';
            marker.removeAttribute('aria-label');
          }
        }
      }

      var trend = dataset.trend;
      if (!trend || trend === 'null' || trend === 'undefined'){
        if (current !== null && avg7 !== null && avg7 > 0){
          var ratio = current / avg7;
          if (ratio <= 0.95){
            trend = 'good';
          } else if (ratio <= 1.05){
            trend = 'ok';
          } else {
            trend = 'high';
          }
        } else {
          trend = null;
        }
      }

      var pillLabel = el.querySelector('.bpr-pill__label');
      if (trend){
        el.dataset.trend = trend;
        if (pillLabel){
          var labelMap = {good: 'Guter Preis', ok: 'Fairer Preis', high: 'Teuer'};
          pillLabel.textContent = labelMap[trend] || 'Preis';
        }
      } else {
        delete el.dataset.trend;
        if (pillLabel) pillLabel.textContent = '–';
      }
    });
  }

  updatePriceIndicators();
})();

function click_offer(merchant, slug, price){
  if(window.gtag){
    gtag('event','click_offer',{merchant:merchant,slug:slug,price:price});
  }
}

