(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const money = value => `K${Number(value || 0).toLocaleString('en-ZM')}`;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const state = { menu: [], filter: 'All', cart: readCart(), user: null, role: 'customer', adminRole: null, zones: [], paymentMethods: [], currentOrderReference: '', moment: 0, momentTimer: null, momentPaused: false };

  const imageMap = {
    'mesa-smash': '/static/media/signature-burger.jpg',
    'garden-stack': '/static/media/burger-combo.jpg',
    'fire-pizza': '/static/media/mesa-food-spread.jpg',
    'market-pizza': '/static/media/zambian-food-spread.jpg',
    'golden-fries': '/static/media/golden-fries.jpg',
    'cloud-sundae': '/static/media/mesa-food-spread.jpg',
    'pink-lemonade': '/static/media/drink-fruit-blend.jpg',
    'mango-shake': '/static/media/drink-mango-product.jpg',
  };
  const moments = [
    { image: '/static/media/beef-wrap-fries.jpg', kicker: 'MADE FOR A PROPER APPETITE', title: 'A little more<br><em>to love.</em>', description: 'A hearty wrap, golden fries and all the good things on one plate.' },
    { image: '/static/media/mesa-food-spread.jpg', kicker: 'THE TABLE IS BETTER FULL', title: 'Bring everyone<br><em>together.</em>', description: 'A generous spread made for passing plates and sharing stories.' },
    { image: '/static/media/signature-burger.jpg', kicker: 'THE MESA CLASSIC', title: 'A good burger<br><em>needs no speech.</em>', description: 'A close-up of the kind of comfort food that always earns another bite.' },
    { image: '/static/media/golden-fries.jpg', kicker: 'THE LITTLE THINGS', title: 'Golden, crisp<br><em>and worth it.</em>', description: 'The perfect side has a way of becoming the main event.' },
    { image: '/static/media/grilled-fish-nshima.jpg', kicker: 'ROOTED IN GOOD FOOD', title: 'Familiar flavours.<br><em>Fresh memories.</em>', description: 'Grilled fish, nshima and greens — a plate that feels like home.' },
    { image: '/static/media/restaurant-interior.jpg', kicker: 'A PLACE AT OUR TABLE', title: 'Come in.<br><em>Stay a while.</em>', description: 'Warm light, relaxed company and a table ready when you are.' },
    { image: '/static/media/drink-mango-bottle.jpg', kicker: 'SOMETHING TO SIP', title: 'A little colour<br><em>in your day.</em>', description: 'A bright, fruity refreshment for the middle of your day.' },
    { image: '/static/media/traditional-caterpillar-stew.jpg', kicker: 'A TASTE OF ZAMBIA', title: 'Tradition on<br><em>the table.</em>', description: 'A familiar local dish, served with a generous helping of flavour.' },
    { image: '/static/media/drink-mango-product.jpg', kicker: 'FRESHNESS IN A BOTTLE', title: 'Keep it<br><em>refreshing.</em>', description: 'Fruit-forward refreshment, made for a sunny afternoon.' },
    { image: '/static/media/burger-combo.jpg', kicker: 'A FULL TABLE', title: 'Make room<br><em>for favourites.</em>', description: 'Burgers, sides and the kind of meal best shared with friends.' },
    { image: '/static/media/zambian-food-spread.jpg', kicker: 'FOOD BRINGS US HOME', title: 'A little bit<br><em>of everything.</em>', description: 'Colourful plates and familiar flavours, all gathered together.' },
    { image: '/static/media/cola-campaign.jpg', kicker: 'A CLASSIC REFRESHMENT', title: 'Take a moment.<br><em>Make it yours.</em>', description: 'A chilled drink alongside good food and good company.' },
    { image: '/static/media/garden-restaurant.jpg', kicker: 'SPACE TO GATHER', title: 'Find your<br><em>comfortable corner.</em>', description: 'A relaxed setting for lingering conversations and shared plates.' },
    { image: '/static/media/drink-fruit-blend.jpg', kicker: 'FRUITFUL LITTLE MOMENTS', title: 'Something<br><em>bright.</em>', description: 'A vivid fruit blend to add a little colour to the table.' },
    { image: '/static/media/cola-on-ice.jpg', kicker: 'CHILLED AND READY', title: 'A cool pause<br><em>in your day.</em>', description: 'A familiar cold drink served alongside the food you love.' },
    { image: '/static/media/cola-poster.jpg', kicker: 'GOOD MOMENTS, SHARED', title: 'Make a little<br><em>moment of it.</em>', description: 'Bring your people together. The table is waiting.' },
  ];

  function readCart() {
    try {
      const value = JSON.parse(localStorage.getItem('mesa-cart') || '[]');
      return Array.isArray(value) ? value.filter(x => x && typeof x.id === 'string' && Number.isInteger(x.quantity) && x.quantity > 0 && x.quantity <= 20) : [];
    } catch { return []; }
  }
  function saveCart() { localStorage.setItem('mesa-cart', JSON.stringify(state.cart)); }
  function itemImage(item) { return item.image || imageMap[item.id] || '/static/media/mesa-food-spread.jpg'; }
  function showToast(message, type = 'success') {
    const region = $('#toastRegion'); const node = document.createElement('div');
    node.className = `toast ${type}`; node.textContent = message; region.append(node);
    window.setTimeout(() => { node.remove(); }, 3800);
  }
  function setBusy(form, busy, label = 'Please wait…') {
    const button = $('button[type="submit"]', form); if (!button) return;
    if (busy) { button.dataset.original = button.innerHTML; button.disabled = true; button.textContent = label; }
    else { button.disabled = false; if (button.dataset.original) button.innerHTML = button.dataset.original; }
  }
  function localISODate() { const n = new Date(); return new Date(n.getTime() - n.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }

  // Hero videos are decorative background footage and intentionally muted.
  // The separately supplied music track only starts after the visitor presses the sound control.
  function setupSound() {
    const audio = $('#ambientAudio'), button = $('#musicToggle');
    const volume = $('#musicVolume');
    audio.volume = Number(volume.value);
    const syncMusicState = () => {
      const playing = !audio.paused && !audio.ended;
      button.setAttribute('aria-pressed', String(playing));
      $('#musicLabel').textContent = playing ? 'PAUSE MUSIC' : 'PLAY MUSIC';
      $('#soundIndicator').classList.toggle('playing', playing);
    };
    button.addEventListener('click', async () => {
      if (audio.paused) {
        try { await audio.play(); }
        catch { showToast('Music could not start. Check your sound settings and try again.', 'error'); }
      } else {
        audio.pause();
      }
    });
    volume.addEventListener('input', () => { audio.volume = Number(volume.value); });
    ['play', 'pause', 'ended'].forEach(eventName => audio.addEventListener(eventName, syncMusicState));
    audio.addEventListener('error', () => {
      button.disabled = true;
      $('#musicLabel').textContent = 'MUSIC UNAVAILABLE';
      $('#soundIndicator').classList.remove('playing');
      showToast('The supplied soundtrack could not be loaded.', 'error');
    });
    const video = $('#heroVideo');
    if (video) { video.muted = true; const p = video.play(); if (p?.catch) p.catch(() => {}); }
  }

  // Automatic full-bleed food photography. No illustrated food or animated ingredient graphics.
  function showMoment(index) {
    state.moment = (index + moments.length) % moments.length;
    const item = moments[state.moment];
    const next = $('#momentImageNext'), current = $('#momentImageCurrent');
    next.style.backgroundImage = `url("${item.image}")`;
    next.classList.add('visible');
    window.setTimeout(() => {
      current.style.backgroundImage = `url("${item.image}")`;
      next.classList.remove('visible');
    }, 760);
    $('#momentKicker').textContent = item.kicker;
    $('#momentTitle').innerHTML = item.title;
    $('#momentDescription').textContent = item.description;
    $('#momentCount').textContent = `${String(state.moment + 1).padStart(2, '0')} / ${String(moments.length).padStart(2, '0')}`;
    $$('[data-moment]').forEach(b => b.classList.toggle('active', Number(b.dataset.moment) === state.moment));
    resetMomentTimer();
  }
  function resetMomentTimer() {
    if (state.momentTimer) clearInterval(state.momentTimer);
    if (!reducedMotion && !state.momentPaused) state.momentTimer = setInterval(() => {
      if (!document.hidden && !$('#momentStage').matches(':hover') && !$('#momentStage').contains(document.activeElement)) showMoment(state.moment + 1);
    }, 6500);
  }
  function setupMoments() {
    $('#momentProgress').innerHTML = moments.map((item, i) => `<button type="button" data-moment="${i}" aria-label="Show food photograph ${i + 1}" class="${i === 0 ? 'active' : ''}"></button>`).join('');
    $('#momentPrev').addEventListener('click', () => showMoment(state.moment - 1));
    $('#momentNext').addEventListener('click', () => showMoment(state.moment + 1));
    $('#momentPause').addEventListener('click', () => {
      state.momentPaused = !state.momentPaused;
      $('#momentPause').textContent = state.momentPaused ? '▶' : 'Ⅱ';
      $('#momentPause').setAttribute('aria-label', state.momentPaused ? 'Resume automatic slideshow' : 'Pause automatic slideshow');
      resetMomentTimer();
    });
    $$('[data-moment]').forEach(b => b.addEventListener('click', () => showMoment(Number(b.dataset.moment))));
    $('#momentStage').addEventListener('mouseenter', () => { if (state.momentTimer) clearInterval(state.momentTimer); });
    $('#momentStage').addEventListener('mouseleave', resetMomentTimer);
    $('#momentStage').addEventListener('focusin', () => { if (state.momentTimer) clearInterval(state.momentTimer); });
    $('#momentStage').addEventListener('focusout', resetMomentTimer);
    showMoment(0);
  }

  async function loadMenu() {
    try {
      const result = await MESAApi.menu();
      state.menu = Array.isArray(result.items) ? result.items : [];
      renderMenu(); renderCart();
    } catch (error) {
      $('#menuGrid').innerHTML = `<div class="menu-error">${escapeHTML(error.message)}<br><button class="button button-dark" id="retryMenu" type="button">Try again</button></div>`;
      $('#retryMenu')?.addEventListener('click', loadMenu);
    }
  }
  async function loadCheckoutOptions() {
    const [zonesResult, methodsResult] = await Promise.all([
      MESAApi.deliveryZones(),
      MESAApi.paymentMethods(),
    ]);
    state.zones = Array.isArray(zonesResult.zones) ? zonesResult.zones : [];
    state.paymentMethods = Array.isArray(methodsResult.methods) ? methodsResult.methods : [];
    const zoneSelect = $('#deliveryZoneSelect');
    zoneSelect.replaceChildren(new Option('Choose an available area', ''));
    state.zones.forEach(zone => {
      const option = new Option(`${zone.name} — ${money(zone.fee)} delivery`, zone.id);
      zoneSelect.add(option);
    });
    const paymentSelect = $('#checkoutPayment');
    state.paymentMethods.forEach(method => {
      paymentSelect.add(new Option(`${method.name} — manual review`, method.id));
    });
    renderCart();
  }
  async function loadPublicContent() {
    const result = await MESAApi.content();
    const content = result.content || {};
    if (content.announcement) $('.announcement>span:nth-child(2)').textContent = content.announcement;
    if (content.hero_lede) $('.hero-lede').textContent = content.hero_lede;
    if (content.restaurant_description) $('meta[name="description"]').content = content.restaurant_description;
  }
  function escapeHTML(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function renderMenu() {
    renderMenuFilters();
    if (state.filter !== 'All' && !state.menu.some(item => item.category === state.filter)) state.filter = 'All';
    $$('[data-filter]').forEach(button => button.classList.toggle('active', button.dataset.filter === state.filter));
    const entries = state.filter === 'All' ? state.menu : state.menu.filter(p => p.category === state.filter);
    if (!entries.length) { $('#menuGrid').innerHTML = '<div class="menu-loading">No dishes in this category yet.</div>'; return; }
    $('#menuGrid').innerHTML = entries.map((item, i) => `
      <article class="menu-card" style="animation-delay:${Math.min(i * 45, 250)}ms">
        <div class="menu-card-photo"><img src="${escapeHTML(itemImage(item))}" alt="${escapeHTML(item.name)}" loading="lazy"><span class="menu-tag">${escapeHTML(item.tag || item.category || 'MESA FAVOURITE')}</span><button type="button" class="menu-add" data-add="${escapeHTML(item.id)}" aria-label="Add ${escapeHTML(item.name)} to bag">＋</button></div>
        <div class="menu-card-body"><div class="menu-card-head"><h3>${escapeHTML(item.name)}</h3><span class="menu-price">${money(item.price)}</span></div><p>${escapeHTML(item.description)}</p></div>
      </article>`).join('');
    $$('[data-add]').forEach(button => button.addEventListener('click', () => addToCart(button.dataset.add)));
  }
  function renderMenuFilters() {
    const root = $('#menuFilters');
    const preferred = ['Burgers', 'Pizza', 'Sides', 'Desserts', 'Drinks'];
    const categories = [...new Set(state.menu.map(item => item.category).filter(Boolean))];
    categories.sort((a, b) => {
      const aIndex = preferred.indexOf(a), bIndex = preferred.indexOf(b);
      return (aIndex < 0 ? preferred.length : aIndex) - (bIndex < 0 ? preferred.length : bIndex) || a.localeCompare(b);
    });
    const buttons = [{ value: 'All', label: 'All favourites' }, ...categories.map(value => ({ value, label: value }))];
    root.replaceChildren(...buttons.map(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.filter = item.value;
      button.textContent = item.label;
      button.classList.toggle('active', state.filter === item.value);
      return button;
    }));
    if (!buttons.some(item => item.value === state.filter)) state.filter = 'All';
  }
  function addToCart(id) {
    const product = state.menu.find(x => x.id === id); if (!product) return;
    const existing = state.cart.find(x => x.id === id);
    if (existing) { if (existing.quantity >= 20) return showToast('You can add up to 20 of each item.', 'error'); existing.quantity++; }
    else state.cart.push({ id, quantity: 1 });
    saveCart(); renderCart(); showToast(`${product.name} added to your bag.`);
  }
  function changeQuantity(id, delta) {
    const row = state.cart.find(x => x.id === id); if (!row) return;
    row.quantity += delta; if (row.quantity <= 0) state.cart = state.cart.filter(x => x.id !== id);
    if (row.quantity > 20) row.quantity = 20;
    saveCart(); renderCart();
  }
  function cartLines() { return state.cart.map(line => { const product = state.menu.find(x => x.id === line.id); return product ? {...product, quantity: line.quantity, lineTotal: product.price * line.quantity} : null; }).filter(Boolean); }
  function subtotal() { return cartLines().reduce((n, x) => n + x.lineTotal, 0); }
  function renderCart() {
    const rows = cartLines(), count = rows.reduce((n, x) => n + x.quantity, 0);
    $('#bagCount').textContent = count;
    $('#cartLines').innerHTML = rows.length ? rows.map(item => `
      <div class="cart-line"><img src="${escapeHTML(itemImage(item))}" alt=""><div><h4>${escapeHTML(item.name)}</h4><small>${money(item.price)} each</small><div class="quantity-control"><button type="button" data-qty="-1" data-id="${item.id}" aria-label="Remove one">−</button><span>${item.quantity}</span><button type="button" data-qty="1" data-id="${item.id}" aria-label="Add one">＋</button><button type="button" class="remove-line" data-remove="${item.id}">Remove</button></div></div><strong>${money(item.lineTotal)}</strong></div>`).join('') : '<p class="cart-empty">Your bag is waiting for something delicious.</p>';
    $$('[data-qty]').forEach(b => b.addEventListener('click', () => changeQuantity(b.dataset.id, Number(b.dataset.qty))));
    $$('[data-remove]').forEach(b => b.addEventListener('click', () => { state.cart = state.cart.filter(x => x.id !== b.dataset.remove); saveCart(); renderCart(); }));
    const zone = state.zones.find(item => item.id === $('#deliveryZoneSelect').value);
    const fee = $('#fulfilmentSelect').value === 'delivery' && count && zone
      ? (zone.free_threshold && subtotal() >= zone.free_threshold ? 0 : Number(zone.fee)) : 0;
    $('#cartSubtotal').textContent = money(subtotal());
    $('#cartDeliveryFee').textContent = money(fee);
    $('#cartTotal').textContent = money(subtotal() + fee);
  }

  function openOverlay(id) { const el = $('#' + id); el.classList.add('open'); el.setAttribute('aria-hidden', 'false'); document.body.classList.add('no-scroll'); }
  function closeOverlay(id) { const el = $('#' + id); el.classList.remove('open'); el.setAttribute('aria-hidden', 'true'); if (!$('.overlay.open')) document.body.classList.remove('no-scroll'); }
  function openAuth(role = 'customer', mode = 'login') { setRole(role); setAuthMode(mode); openOverlay('authOverlay'); }
  function setRole(role) {
    state.role = role;
    if (role === 'admin') setAuthMode('login');
    $$('[data-role]').forEach(b => b.classList.toggle('active', b.dataset.role === role));
    $('#authModeTabs').hidden = role === 'admin';
    $('#loginEyebrow').textContent = role === 'admin' ? 'ADMINISTRATOR ACCESS' : 'WELCOME BACK';
    $('#authTitle').textContent = role === 'admin' ? 'Staff sign in.' : 'Good to see you.';
    $('#authFeedback').textContent = '';
  }
  function setAuthMode(mode) {
    $('#loginPane').hidden = mode !== 'login'; $('#registerPane').hidden = mode !== 'register';
    $$('[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
    $('#authFeedback').textContent = '';
  }
  function setUser(user) {
    state.user = user || null;
    $('#accountButton').textContent = state.user ? `Hi, ${state.user.name.split(' ')[0]} · Sign out` : 'Sign in';
  }
  function showPasswordChange() {
    openOverlay('passwordChangeOverlay');
    $('#passwordChangeForm').elements.current_password.focus();
  }
  function enterStaffWorkspace(user) {
    setUser(user);
    if (user.role !== 'customer') {
      state.adminRole = user.role;
      showAdmin(user);
    }
  }
  async function refreshUser() {
    try {
      const result = await MESAApi.me();
      const user = result.user || null;
      setUser(user);
      if (user?.must_change_password) showPasswordChange();
      else if (user && user.role !== 'customer') enterStaffWorkspace(user);
    }
    catch { setUser(null); }
  }
  async function handleLogin(event) {
    event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form));
    setBusy(form, true, 'Signing in…'); $('#authFeedback').textContent = '';
    try {
      const result = await MESAApi.login({email: data.email, password: data.password});
      const user = result.user || result;
      if (state.role === 'admin' && user.role === 'customer') {
        await MESAApi.logout();
        throw new Error('This account does not have administrator access.');
      }
      if (user.must_change_password) {
        setUser(user); form.reset(); closeOverlay('authOverlay'); showPasswordChange(); return;
      }
      if (user.role !== 'customer') {
        const admin = await MESAApi.adminMe();
        const verifiedUser = admin.user || admin;
        if (verifiedUser.role === 'customer') {
          await MESAApi.logout();
          throw new Error('Administrator access could not be verified.');
        }
        form.reset(); closeOverlay('authOverlay'); showToast('Staff sign-in successful.'); enterStaffWorkspace(verifiedUser); return;
      }
      setUser(user); form.reset(); closeOverlay('authOverlay'); showToast(`Welcome back, ${(user.name || 'friend').split(' ')[0]}.`);
    } catch (error) { $('#authFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function handleRegister(event) {
    event.preventDefault(); const form = event.currentTarget; const d = Object.fromEntries(new FormData(form));
    if (d.password !== d.confirmPassword) { $('#authFeedback').textContent = 'Your passwords do not match.'; return; }
    setBusy(form, true, 'Creating account…'); $('#authFeedback').textContent = '';
    try {
      const result = await MESAApi.register({name: d.name, email: d.email, password: d.password});
      const user = result.user || result;
      setUser(user); form.reset(); closeOverlay('authOverlay'); showToast(`Your MESA account is ready, ${(user.name || 'friend').split(' ')[0]}.`);
    } catch (error) { $('#authFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function handleLogout() {
    try { await MESAApi.logout(); clearAdminData(); state.user = null; document.body.classList.remove('admin-mode'); $('#adminWorkspace').hidden = true; $('#siteMain').hidden = false; $('.site-footer').hidden = false; setUser(null); showToast('You are signed out.'); }
    catch (error) { showToast(error.message, 'error'); }
  }

  function clearAdminData() {
    ['#adminOrders', '#adminBookings', '#adminCustomers', '#adminMenu', '#adminAudit', '#adminPayments', '#paymentMethods', '#deliveryZones', '#adminDeliveries'].forEach(selector => { $(selector).textContent = 'Sign in with staff access to view this information.'; });
    ['#statOrders', '#statBookings', '#statSales', '#statCustomers'].forEach(selector => { $(selector).textContent = '—'; });
    $('#adminName').textContent = 'Administrator';
  }
  function lockAdminWorkspace(message) {
    clearAdminData();
    document.body.classList.remove('admin-mode');
    $('#adminWorkspace').hidden = true;
    $('#siteMain').hidden = false;
    $('.site-footer').hidden = false;
    setUser(null);
    showToast(message, 'error');
    MESAApi.logout().catch(error => showToast(`Could not revoke the previous session: ${error.message}`, 'error'));
  }

  function showAdmin(user) {
    document.body.classList.add('admin-mode');
    $('#siteMain').hidden = true; $('.site-footer').hidden = true; $('#adminWorkspace').hidden = false;
    $('#adminName').textContent = user.name || 'Administrator';
    const role = user.role;
    $('#adminStats').hidden = false;
    $('#paymentMethodForm').hidden = role === 'cashier';
    $$('[data-admin-roles]').forEach(button => {
      button.hidden = !button.dataset.adminRoles.split(',').includes(role);
    });
    const firstTab = $('[data-admin-tab]:not([hidden])');
    if (firstTab) firstTab.click();
    $('#ordersCsvLink').hidden = !['super_admin', 'restaurant_admin', 'manager'].includes(role);
    loadAdminData(); window.scrollTo({top: 0, behavior: 'smooth'});
  }
  async function loadAdminData() {
    $('#adminAlert').textContent = 'Loading protected restaurant data…';
    const role = state.adminRole || (state.user && state.user.role);
    const can = roles => roles.includes(role);
    const requests = [];
    if (can(['super_admin', 'restaurant_admin', 'manager', 'cashier', 'kitchen_staff'])) requests.push(['orders', MESAApi.adminOrders()]);
    if (can(['super_admin', 'restaurant_admin', 'manager'])) requests.push(['bookings', MESAApi.adminBookings()]);
    if (can(['super_admin', 'restaurant_admin', 'manager'])) requests.push(['users', MESAApi.adminUsers()]);
    if (can(['super_admin', 'restaurant_admin', 'manager'])) requests.push(['menu', MESAApi.adminMenu()]);
    if (can(['super_admin', 'restaurant_admin', 'manager'])) requests.push(['audit', MESAApi.adminAudit()]);
    if (can(['super_admin', 'restaurant_admin', 'cashier'])) {
      requests.push(['payments', MESAApi.adminPayments()]);
      requests.push(['methods', MESAApi.adminPaymentMethods()]);
    }
    if (can(['super_admin', 'restaurant_admin', 'manager', 'delivery_staff'])) {
      requests.push(['delivery', MESAApi.adminDeliveries()]);
      requests.push(['zones', MESAApi.adminDeliveryZones()]);
      if (can(['super_admin', 'restaurant_admin', 'manager'])) requests.push(['staff', MESAApi.adminDeliveryStaff()]);
    }
    if (can(['super_admin', 'restaurant_admin'])) requests.push(['content', MESAApi.adminContent()]);
    if (can(['super_admin', 'restaurant_admin', 'manager'])) {
      requests.push(['analytics', MESAApi.adminAnalytics()]);
      requests.push(['summary', MESAApi.adminSummary()]);
    }
    try {
      const results = Object.fromEntries(await Promise.all(requests.map(async ([key, request]) => [key, await request])));
      if (results.summary) {
        $('#adminStats').hidden = false;
        const stats = results.summary.summary || results.summary;
        $('#statOrders').textContent = stats.orders_today ?? stats.orders ?? '—';
        $('#statBookings').textContent = stats.bookings_today ?? stats.bookings ?? '—';
        $('#statSales').textContent = money(stats.sales_today ?? stats.sales ?? 0);
        $('#statCustomers').textContent = stats.customers ?? '—';
      } else {
        $('#adminStats').hidden = true;
      }
      if (results.orders) renderAdminOrders(results.orders.orders || []);
      if (results.bookings) renderAdminBookings(results.bookings.bookings || []);
      if (results.users) renderAdminCustomers(results.users.users || []);
      if (results.menu) renderAdminMenu(results.menu.items || []);
      if (results.audit) renderAdminAudit(results.audit.audit || []);
      if (results.payments) renderAdminPayments(results.payments.payments || []);
      if (results.methods) renderPaymentMethods(results.methods.methods || []);
      if (results.zones && results.delivery) renderDeliveryOperations(results.zones.zones || [], results.delivery.deliveries || [], results.staff?.staff || []);
      if (results.content) populateContentForm(results.content.content || {});
      if (results.analytics) renderAnalytics(results.analytics.analytics || {});
      $('#adminAlert').textContent = 'Dashboard connected.';
    } catch (error) {
      $('#adminAlert').textContent = `Could not load administrator data: ${error.message}`;
      if (error.status === 401 || error.status === 403) lockAdminWorkspace('Administrator access has expired or been revoked. Sign in again.');
    }
  }
  function makeAdminTable(target, columns, rows, emptyText, actionHeader, addActions) {
    const root = $(target);
    if (!rows.length) { root.textContent = emptyText; return; }
    const table = document.createElement('table'); table.className = 'admin-table';
    const head = document.createElement('tr');
    columns.forEach(([, label]) => { const th = document.createElement('th'); th.textContent = label; head.append(th); });
    if (addActions) { const th = document.createElement('th'); th.textContent = actionHeader || 'Actions'; head.append(th); }
    const thead = document.createElement('thead'); thead.append(head); table.append(thead);
    const tbody = document.createElement('tbody');
    rows.forEach(row => {
      const tr = document.createElement('tr');
      columns.forEach(([field]) => { const td = document.createElement('td'); td.textContent = String(row[field] ?? ''); tr.append(td); });
      if (addActions) { const td = document.createElement('td'); addActions(td, row); tr.append(td); }
      tbody.append(tr);
    });
    table.append(tbody); root.replaceChildren(table);
  }
  const orderStatuses = ['Received', 'Preparing', 'Ready', 'Completed', 'Cancelled'];
  const bookingStatuses = ['Received', 'Confirmed', 'Seated', 'Completed', 'Cancelled'];
  function addStatusControl(cell, row, endpoint, statuses) {
    const form = document.createElement('form'); form.className = 'admin-row-action';
    const select = document.createElement('select'); select.setAttribute('aria-label', `Update status for ${row.reference}`);
    statuses.forEach(status => { const option = document.createElement('option'); option.value = status; option.textContent = status; select.append(option); });
    select.value = row.status;
    const button = document.createElement('button'); button.type = 'submit'; button.textContent = 'Update';
    form.append(select, button);
    form.addEventListener('submit', async event => {
      event.preventDefault();
      try {
        await endpoint({ id: row.id, status: select.value });
        showToast(`Status updated to ${select.value}.`);
        await loadAdminData();
      } catch (error) {
        if (error.status === 401 || error.status === 403) lockAdminWorkspace('Administrator access has expired or been revoked. Sign in again.');
        else showToast(error.message, 'error');
      }
    });
    cell.append(form);
  }
  function renderAdminOrders(rows) {
    const displayRows = rows.map(row => ({
      ...row,
      items: (row.items || []).map(item => `${item.name} × ${item.quantity}`).join(', '),
      total: money(row.total),
    }));
    makeAdminTable('#adminOrders', [['reference', 'Order'], ['customer_name', 'Customer'], ['email', 'Email'], ['phone', 'Phone'], ['items', 'Items'], ['fulfilment', 'Fulfilment'], ['address', 'Delivery address'], ['payment_method', 'Payment'], ['total', 'Total'], ['status', 'Status'], ['created_at', 'Received']], displayRows, 'No recent orders.', 'Update status', (cell, row) => addStatusControl(cell, row, MESAApi.updateOrderStatus, orderStatuses));
  }
  function renderAdminBookings(rows) {
    makeAdminTable('#adminBookings', [['reference', 'Booking'], ['name', 'Customer'], ['email', 'Email'], ['phone', 'Phone'], ['booking_date', 'Date'], ['booking_time', 'Time'], ['guests', 'Guests'], ['notes', 'Notes'], ['status', 'Status']], rows, 'No reservation requests.', 'Update status', (cell, row) => addStatusControl(cell, row, MESAApi.updateBookingStatus, bookingStatuses));
  }
  function renderAdminCustomers(rows) {
    makeAdminTable('#adminCustomers', [['id', 'ID'], ['name', 'Name'], ['email', 'Email'], ['role', 'Role'], ['is_active', 'Access'], ['created_at', 'Joined']], rows, 'No customer accounts.', 'Manage access', (cell, row) => {
      if (row.role === 'customer') {
        if (!['super_admin', 'restaurant_admin'].includes(state.adminRole)) {
          cell.textContent = row.is_active ? 'Active' : 'Disabled';
          return;
        }
        const button = document.createElement('button'); button.type = 'button'; button.className = 'admin-action-button';
        button.textContent = row.is_active ? 'Disable account' : 'Enable account';
        button.addEventListener('click', async () => {
          try {
            await MESAApi.updateUserAccess({ user_id: row.id, active: !row.is_active });
            showToast('Customer access updated.');
            await loadAdminData();
          } catch (error) { showToast(error.message, 'error'); }
        });
        cell.append(button);
      } else if (state.adminRole === 'super_admin' && row.id !== state.user.id) {
        const select = document.createElement('select');
        ['super_admin', 'restaurant_admin', 'manager', 'cashier', 'kitchen_staff', 'delivery_staff'].forEach(role => select.add(new Option(role.replaceAll('_', ' '), role)));
        select.value = row.role;
        const update = document.createElement('button');
        update.type = 'button'; update.className = 'admin-action-button'; update.textContent = 'Set role';
        update.addEventListener('click', async () => {
          try { await MESAApi.assignRole({ user_id: row.id, role: select.value }); await loadAdminData(); }
          catch (error) { showToast(error.message, 'error'); }
        });
        cell.append(select, update);
      } else {
        cell.textContent = 'Staff account';
      }
    });
  }
  function renderAdminMenu(rows) {
    makeAdminTable('#adminMenu', [['id', 'ID'], ['name', 'Name'], ['description', 'Description'], ['category', 'Category'], ['price', 'Price (ZMW)'], ['tag', 'Tag'], ['active', 'Published']], rows, 'No menu items.', 'Manage item', (cell, row) => {
      const edit = document.createElement('button'); edit.type = 'button'; edit.className = 'admin-action-button'; edit.textContent = 'Edit';
      edit.addEventListener('click', () => {
        const form = $('#adminMenuForm');
        ['id', 'name', 'category', 'price', 'tag', 'description', 'prep_minutes', 'image_url'].forEach(field => { form.elements[field].value = row[field] ?? ''; });
        form.elements.vegetarian.checked = Boolean(row.vegetarian);
        form.elements.popular.checked = Boolean(row.popular);
        form.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
        form.elements.name.focus();
      });
      const toggle = document.createElement('button'); toggle.type = 'button'; toggle.className = 'admin-action-button';
      toggle.textContent = row.active ? 'Archive' : 'Restore';
      toggle.addEventListener('click', async () => {
        try {
          if (row.active) await MESAApi.archiveMenuItem(row.id);
          else await MESAApi.restoreMenuItem(row.id);
          showToast(row.active ? 'Menu item archived.' : 'Menu item restored.');
          await loadAdminData();
        } catch (error) {
          if (error.status === 401 || error.status === 403) lockAdminWorkspace('Administrator access has expired or been revoked. Sign in again.');
          else showToast(error.message, 'error');
        }
      });
      cell.append(edit, toggle);
    });
  }
  function renderAdminAudit(rows) {
    makeAdminTable('#adminAudit', [['created_at', 'Time'], ['action', 'Action'], ['target_type', 'Record'], ['target_id', 'ID'], ['details', 'Details'], ['admin_user_id', 'Administrator']], rows, 'No activity recorded yet.');
  }

  function renderAdminPayments(rows) {
    makeAdminTable('#adminPayments', [['transaction_reference', 'Transaction reference'], ['order_reference', 'Order'], ['customer_name', 'Customer'], ['method_id', 'Provider'], ['amount', 'Amount'], ['status', 'Review status'], ['submitted_at', 'Submitted']], rows, 'No payment references submitted.', 'Manual review', (cell, row) => {
      if (!['Payment Submitted', 'Verified'].includes(row.status)) return;
      const select = document.createElement('select');
      ['Verified', 'Rejected', 'Refunded'].filter(status => status !== 'Refunded' || row.status === 'Verified').forEach(status => select.add(new Option(status, status)));
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'admin-action-button'; button.textContent = 'Save review';
      button.addEventListener('click', async () => {
        try {
          await MESAApi.reviewPayment({ id: row.id, status: select.value });
          showToast('Payment review saved. It was not automatically verified.');
          await loadAdminData();
        } catch (error) { showToast(error.message, 'error'); }
      });
      cell.append(select, button);
    });
  }
  function renderPaymentMethods(methods) {
    makeAdminTable('#paymentMethods', [['name', 'Provider'], ['business_number', 'Business number'], ['registered_name', 'Registered account'], ['enabled', 'Enabled'], ['updated_at', 'Updated']], methods, 'No payment methods configured.', 'Configure', (cell, row) => {
      if (state.adminRole === 'cashier') { cell.textContent = 'Configured by an administrator'; return; }
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'admin-action-button'; button.textContent = 'Edit settings';
      button.addEventListener('click', () => {
        const form = $('#paymentMethodForm');
        ['id', 'name', 'business_number', 'registered_name', 'merchant_info', 'instructions', 'qr_image_url'].forEach(key => { form.elements[key].value = row[key] || ''; });
        form.elements.enabled.checked = Boolean(row.enabled);
      });
      cell.append(button);
    });
  }
  function renderDeliveryOperations(zones, deliveries, staff) {
    makeAdminTable('#deliveryZones', [['id', 'Zone ID'], ['name', 'Zone'], ['region', 'Region'], ['fee', 'Fee (ZMW)'], ['minimum_order', 'Minimum'], ['free_threshold', 'Free above'], ['active', 'Active'], ['estimated_minutes', 'Minutes']], zones, 'No delivery zones configured.', 'Zone actions', (cell, row) => {
      if (state.adminRole === 'delivery_staff') { cell.textContent = 'Delivery area'; return; }
      const edit = document.createElement('button');
      edit.type = 'button'; edit.className = 'admin-action-button'; edit.textContent = 'Edit';
      edit.addEventListener('click', () => {
        const form = $('#deliveryZoneForm');
        Object.keys(row).forEach(key => {
          if (form.elements[key]) {
            if (form.elements[key].type === 'checkbox') form.elements[key].checked = Boolean(row[key]);
            else form.elements[key].value = row[key] ?? '';
          }
        });
      });
      const archive = document.createElement('button');
      archive.type = 'button'; archive.className = 'admin-action-button'; archive.textContent = 'Disable';
      archive.disabled = !row.active;
      archive.addEventListener('click', async () => {
        try { await MESAApi.deleteDeliveryZone(row.id); await loadAdminData(); }
        catch (error) { showToast(error.message, 'error'); }
      });
      cell.append(edit, archive);
    });
    const deliveryRows = deliveries.map(row => ({ ...row, total: money(row.total), delivery_status: row.delivery_status || 'Unassigned' }));
    makeAdminTable('#adminDeliveries', [['reference', 'Order'], ['customer_name', 'Customer'], ['phone', 'Phone'], ['address', 'Address'], ['total', 'Total'], ['delivery_status', 'Delivery status']], deliveryRows, 'No delivery assignments.', 'Manage delivery', (cell, row) => {
      if (state.adminRole === 'delivery_staff') {
        const select = document.createElement('select');
        ['Picked up', 'Delivered'].forEach(status => select.add(new Option(status, status)));
        const update = document.createElement('button');
        update.type = 'button'; update.className = 'admin-action-button'; update.textContent = 'Update';
        update.addEventListener('click', async () => {
          try { await MESAApi.updateDeliveryStatus({ order_id: row.id, status: select.value }); await loadAdminData(); }
          catch (error) { showToast(error.message, 'error'); }
        });
        cell.append(select, update);
        return;
      }
      if (!staff.length) { cell.textContent = 'Create an active delivery staff account to assign orders.'; return; }
      const select = document.createElement('select');
      staff.forEach(person => select.add(new Option(person.name, person.id)));
      const update = document.createElement('button');
      update.type = 'button'; update.className = 'admin-action-button'; update.textContent = 'Assign';
      update.addEventListener('click', async () => {
        try { await MESAApi.assignDelivery({ order_id: row.id, staff_user_id: Number(select.value) }); await loadAdminData(); }
        catch (error) { showToast(error.message, 'error'); }
      });
      cell.append(select, update);
    });
  }
  function populateContentForm(content) {
    const form = $('#contentForm');
    Object.keys(content).forEach(key => { if (form.elements[key]) form.elements[key].value = content[key]; });
  }
  function renderAnalytics(analytics) {
    const labels = {
      revenue_today: 'Revenue today',
      revenue_week: 'Revenue this week',
      revenue_month: 'Revenue this month',
      total_revenue: 'Lifetime revenue',
      total_orders: 'Total orders',
      completed_orders: 'Completed orders',
      cancelled_orders: 'Cancelled / rejected',
      new_customers: 'New customers (7 days)',
      average_order_value: 'Average completed order',
    };
    const root = $('#adminAnalytics');
    root.replaceChildren(...Object.entries(labels).map(([key, label]) => {
      const card = document.createElement('article');
      const title = document.createElement('span');
      title.textContent = label;
      const value = document.createElement('strong');
      value.textContent = key.startsWith('revenue_') || key === 'total_revenue' || key === 'average_order_value' ? money(analytics[key]) : String(analytics[key] ?? 0);
      card.append(title, value);
      return card;
    }));
  }

  function deliveryFee() {
    if ($('#fulfilmentSelect').value !== 'delivery') return 0;
    const zone = state.zones.find(item => item.id === $('#deliveryZoneSelect').value);
    if (!zone) return 0;
    return zone.free_threshold && subtotal() >= zone.free_threshold ? 0 : Number(zone.fee);
  }
  function renderPaymentInstructions(method, reference = '', total = null) {
    const root = $('#mobilePaymentDetails');
    root.replaceChildren();
    if (!method) { root.hidden = true; return; }
    root.hidden = false;
    const title = document.createElement('strong');
    title.textContent = method.name;
    root.append(title);
    if (method.business_number) {
      const number = document.createElement('p');
      number.textContent = `Pay to ${method.registered_name || method.name}: ${method.business_number}`;
      root.append(number);
    }
    if (method.merchant_info) {
      const merchant = document.createElement('p');
      merchant.textContent = method.merchant_info;
      root.append(merchant);
    }
    if (method.instructions) {
      const instructions = document.createElement('p');
      instructions.textContent = method.instructions;
      root.append(instructions);
    }
    if (method.qr_image_url) {
      const image = document.createElement('img');
      image.src = method.qr_image_url;
      image.alt = `${method.name} payment QR code`;
      image.loading = 'lazy';
      root.append(image);
    }
    if (reference) {
      const order = document.createElement('p');
      order.textContent = `Order ${reference} — ${money(total)}. Enter your transaction reference below. This submission is not payment confirmation.`;
      root.append(order);
    }
  }
  function updateCheckoutPayment() {
    const method = state.paymentMethods.find(item => item.id === $('#checkoutPayment').value);
    renderPaymentInstructions(method);
  }
  function openCheckout() {
    if (!state.cart.length) return showToast('Your bag is empty. Add a dish first.', 'error');
    if (!state.user) { closeOverlay('cartOverlay'); openAuth('customer', 'login'); $('#authFeedback').textContent = 'Sign in or create an account to place an order.'; return; }
    if ($('#fulfilmentSelect').value === 'delivery') {
      const zone = state.zones.find(item => item.id === $('#deliveryZoneSelect').value);
      if (!zone) { $('#cartFeedback').textContent = 'Choose a currently available delivery area.'; return; }
      if (subtotal() < Number(zone.minimum_order)) {
        $('#cartFeedback').textContent = `This area has a minimum order of ${money(zone.minimum_order)}.`;
        return;
      }
    }
    const f = $('#checkoutForm');
    f.elements.name.value = state.user.name || ''; f.elements.email.value = state.user.email || '';
    const deliver = $('#fulfilmentSelect').value === 'delivery';
    $('#deliveryAddressField').hidden = !deliver; f.elements.address.required = deliver;
    $('#checkoutTotal').textContent = money(subtotal() + deliveryFee());
    f.hidden = false;
    $('#paymentSubmitForm').hidden = true;
    $('#checkoutFeedback').textContent = '';
    updateCheckoutPayment();
    closeOverlay('cartOverlay'); openOverlay('checkoutOverlay');
  }
  async function submitOrder(event) {
    event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form));
    const fulfilment = $('#fulfilmentSelect').value;
    const payload = {name: data.name, email: data.email, phone: data.phone, fulfilment, address: data.address || '', delivery_zone_id: fulfilment === 'delivery' ? $('#deliveryZoneSelect').value : '', payment: data.payment, items: state.cart.map(x => ({id: x.id, quantity: x.quantity}))};
    setBusy(form, true, 'Sending order…'); $('#checkoutFeedback').textContent = '';
    try {
      const result = await MESAApi.order(payload);
      const method = state.paymentMethods.find(item => item.id === data.payment);
      state.cart = []; saveCart(); renderCart();
      if (method) {
        state.currentOrderReference = result.reference;
        form.hidden = true;
        $('#paymentSubmitForm').hidden = false;
        renderPaymentInstructions(method, result.reference, result.total);
        $('#checkoutFeedback').textContent = result.message || 'Order received. Submit the transfer reference for manual review.';
        return;
      }
      form.reset(); closeOverlay('checkoutOverlay');
      showToast(`Order ${result.reference || ''} received for ${money(result.total)}. Our team will contact you to confirm.`);
    } catch (error) { $('#checkoutFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function submitPaymentReference(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    setBusy(form, true, 'Submitting reference…');
    try {
      const result = await MESAApi.submitPayment({
        order_reference: state.currentOrderReference,
        transaction_reference: values.transaction_reference,
        note: values.note || '',
      });
      form.reset();
      form.hidden = true;
      $('#checkoutFeedback').textContent = result.message;
      closeOverlay('checkoutOverlay');
      showToast(result.message);
    } catch (error) {
      $('#checkoutFeedback').textContent = error.message;
    } finally { setBusy(form, false); }
  }
  async function submitBooking(event) {
    event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form)); data.guests = Number(data.guests);
    setBusy(form, true, 'Sending request…'); $('#bookingFeedback').textContent = '';
    try { const result = await MESAApi.booking(data); form.reset(); $('#bookingDate').min = localISODate(); $('#bookingDate').value = localISODate(); $('#bookingFeedback').textContent = `${result.message || 'Your request has been received.'} Our team will contact you to confirm.`; }
    catch (error) { $('#bookingFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function submitAdminMenu(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    data.price = Number(data.price);
    data.prep_minutes = Number(data.prep_minutes || 0);
    data.vegetarian = form.elements.vegetarian.checked;
    data.popular = form.elements.popular.checked;
    setBusy(form, true, 'Saving item…');
    $('#adminMenuFeedback').textContent = '';
    try {
      await MESAApi.saveMenuItem(data);
      form.reset();
      $('#adminMenuFeedback').textContent = 'Menu item saved and published.';
      await loadAdminData();
    } catch (error) {
      $('#adminMenuFeedback').textContent = error.message;
    } finally { setBusy(form, false); }
  }
  async function uploadImage(file) {
    if (!file || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Choose a JPEG, PNG, or WebP image.');
    if (file.size > 4 * 1024 * 1024) throw new Error('Images must be smaller than 4 MB.');
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('The selected image could not be read.'));
      reader.readAsDataURL(file);
    });
    const result = await MESAApi.uploadImage(dataUrl);
    return result.url;
  }
  async function handleMenuImageUpload(event) {
    const input = event.currentTarget;
    if (!input.files[0]) return;
    $('#adminMenuFeedback').textContent = 'Uploading image…';
    try {
      $('#adminMenuForm').elements.image_url.value = await uploadImage(input.files[0]);
      $('#adminMenuFeedback').textContent = 'Menu image uploaded.';
    } catch (error) { $('#adminMenuFeedback').textContent = error.message; }
  }
  async function savePaymentMethod(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    data.enabled = form.elements.enabled.checked;
    setBusy(form, true, 'Saving provider…');
    try {
      await MESAApi.savePaymentMethod(data);
      $('#paymentFeedback').textContent = 'Provider settings saved. Customers see enabled providers only.';
      await loadAdminData();
    } catch (error) { $('#paymentFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function handlePaymentImageUpload(event) {
    const input = event.currentTarget;
    if (!input.files[0]) return;
    $('#paymentFeedback').textContent = 'Uploading QR image…';
    try {
      $('#paymentMethodForm').elements.qr_image_url.value = await uploadImage(input.files[0]);
      $('#paymentFeedback').textContent = 'QR image uploaded.';
    } catch (error) { $('#paymentFeedback').textContent = error.message; }
  }
  async function saveDeliveryZone(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    ['fee', 'estimated_minutes', 'minimum_order', 'free_threshold'].forEach(key => { data[key] = Number(data[key] || 0); });
    data.active = form.elements.active.checked;
    setBusy(form, true, 'Saving delivery area…');
    try {
      await MESAApi.saveDeliveryZone(data);
      $('#deliveryFeedback').textContent = 'Delivery area and server-side pricing saved.';
      await loadAdminData();
      await loadCheckoutOptions();
    } catch (error) { $('#deliveryFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function saveWebsiteContent(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setBusy(form, true, 'Saving website content…');
    try {
      await MESAApi.saveContent(data);
      $('#contentFeedback').textContent = 'Website content saved.';
      await loadPublicContent();
    } catch (error) { $('#contentFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function handleContentImageUpload(event) {
    const input = event.currentTarget;
    if (!input.files[0]) return;
    $('#contentFeedback').textContent = 'Uploading image…';
    try {
      const url = await uploadImage(input.files[0]);
      $('#contentForm').elements.hero_image.value = url;
      $('#contentImagePreview').src = url;
      $('#contentImagePreview').hidden = false;
      $('#contentFeedback').textContent = 'Image uploaded to persistent server storage.';
    } catch (error) { $('#contentFeedback').textContent = error.message; }
  }
  async function handlePasswordChange(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    if (values.new_password !== values.confirm_password) {
      $('#passwordChangeFeedback').textContent = 'The new passwords do not match.';
      return;
    }
    setBusy(form, true, 'Changing password…');
    try {
      const result = await MESAApi.changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      form.reset();
      closeOverlay('passwordChangeOverlay');
      setUser(result.user);
      if (result.user.role !== 'customer') enterStaffWorkspace(result.user);
      showToast(result.message);
    } catch (error) { $('#passwordChangeFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function uploadImage(file) {
    if (!file || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Choose a JPEG, PNG, or WebP image.');
    if (file.size > 4 * 1024 * 1024) throw new Error('Images must be smaller than 4 MB.');
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('The selected image could not be read.'));
      reader.readAsDataURL(file);
    });
    const result = await MESAApi.uploadImage(dataUrl);
    return result.url;
  }
  async function savePaymentMethod(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    data.enabled = form.elements.enabled.checked;
    setBusy(form, true, 'Saving provider…');
    try {
      await MESAApi.savePaymentMethod(data);
      $('#paymentFeedback').textContent = 'Provider settings saved. Customers see enabled providers only.';
      await loadAdminData();
    } catch (error) { $('#paymentFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function saveDeliveryZone(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    ['fee', 'estimated_minutes', 'minimum_order', 'free_threshold'].forEach(key => { data[key] = Number(data[key] || 0); });
    data.active = form.elements.active.checked;
    setBusy(form, true, 'Saving delivery area…');
    try {
      await MESAApi.saveDeliveryZone(data);
      $('#deliveryFeedback').textContent = 'Delivery area and server-side pricing saved.';
      await loadAdminData();
      await loadCheckoutOptions();
    } catch (error) { $('#deliveryFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function saveWebsiteContent(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    delete data.image_file;
    setBusy(form, true, 'Saving website content…');
    try {
      await MESAApi.saveContent(data);
      $('#contentFeedback').textContent = 'Website content saved.';
      await loadPublicContent();
    } catch (error) { $('#contentFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }
  async function handleContentImageUpload(event) {
    const input = event.currentTarget;
    const file = input.files[0];
    if (!file) return;
    $('#contentFeedback').textContent = 'Uploading image…';
    try {
      const url = await uploadImage(file);
      $('#contentForm').elements.hero_image.value = url;
      $('#contentImagePreview').src = url;
      $('#contentImagePreview').hidden = false;
      $('#contentFeedback').textContent = 'Image uploaded to persistent server storage.';
    } catch (error) { $('#contentFeedback').textContent = error.message; }
  }
  async function handlePasswordChange(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    if (values.new_password !== values.confirm_password) {
      $('#passwordChangeFeedback').textContent = 'The new passwords do not match.';
      return;
    }
    setBusy(form, true, 'Changing password…');
    try {
      const result = await MESAApi.changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      form.reset();
      closeOverlay('passwordChangeOverlay');
      const user = result.user;
      setUser(user);
      if (user.role !== 'customer') enterStaffWorkspace(user);
      showToast(result.message);
    } catch (error) { $('#passwordChangeFeedback').textContent = error.message; }
    finally { setBusy(form, false); }
  }

  function setupOverlays() {
    $('#accountButton').addEventListener('click', () => state.user ? handleLogout() : openAuth('customer', 'login'));
    $('#footerAccount').addEventListener('click', () => openAuth('customer', 'login'));
    $('#bagButton').addEventListener('click', () => openOverlay('cartOverlay'));
    $$('[data-close]').forEach(button => button.addEventListener('click', () => closeOverlay(button.dataset.close)));
    $$('.overlay').forEach(overlay => overlay.addEventListener('click', e => { if (e.target === overlay) closeOverlay(overlay.id); }));
    $$('[data-role]').forEach(button => button.addEventListener('click', () => setRole(button.dataset.role)));
    $$('[data-mode]').forEach(button => button.addEventListener('click', () => setAuthMode(button.dataset.mode)));
    $('#loginForm').addEventListener('submit', handleLogin);
    $('#registerForm').addEventListener('submit', handleRegister);
    $('#bookingForm').addEventListener('submit', submitBooking);
    $('#checkoutForm').addEventListener('submit', submitOrder);
    $('#checkoutButton').addEventListener('click', openCheckout);
    $('#fulfilmentSelect').addEventListener('change', () => {
      const delivery = $('#fulfilmentSelect').value === 'delivery';
      $('#deliveryZoneField').hidden = !delivery;
      $('#deliveryZoneSelect').required = delivery;
      $('#deliveryAddressField').hidden = !delivery;
      $('#checkoutForm').elements.address.required = delivery;
      $('#checkoutPayment').querySelector('[value="cash-on-delivery"]').disabled = !delivery;
      if (!delivery && $('#checkoutPayment').value === 'cash-on-delivery') $('#checkoutPayment').value = 'pay-at-counter';
      renderCart();
      updateCheckoutPayment();
    });
    $('#deliveryZoneSelect').addEventListener('change', renderCart);
    $('#checkoutPayment').addEventListener('change', updateCheckoutPayment);
    $('#adminLogout').addEventListener('click', handleLogout);
    $('#refreshAdmin').addEventListener('click', loadAdminData);
    $('#adminMenuForm').addEventListener('submit', submitAdminMenu);
    $('#menuImageUpload').addEventListener('change', handleMenuImageUpload);
    $('#paymentMethodForm').addEventListener('submit', savePaymentMethod);
    $('#paymentImageUpload').addEventListener('change', handlePaymentImageUpload);
    $('#deliveryZoneForm').addEventListener('submit', saveDeliveryZone);
    $('#contentForm').addEventListener('submit', saveWebsiteContent);
    $('#contentImageUpload').addEventListener('change', handleContentImageUpload);
    $('#paymentSubmitForm').addEventListener('submit', submitPaymentReference);
    $('#passwordChangeForm').addEventListener('submit', handlePasswordChange);
    $$('[data-admin-tab]').forEach(button => button.addEventListener('click', () => {
      $$('[data-admin-tab]').forEach(tab => tab.classList.toggle('active', tab === button));
      $$('[data-admin-panel]').forEach(panel => { panel.hidden = panel.dataset.adminPanel !== button.dataset.adminTab; });
    }));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') $$('.overlay.open').forEach(o => closeOverlay(o.id)); });
  }
  function setupNavigation() {
    $('#mobileNavToggle').addEventListener('click', () => { const open = $('#mainNav').classList.toggle('open'); $('#mobileNavToggle').setAttribute('aria-expanded', String(open)); });
    $$('#mainNav a').forEach(a => a.addEventListener('click', () => { $('#mainNav').classList.remove('open'); $('#mobileNavToggle').setAttribute('aria-expanded', 'false'); }));
  }
  function setupFilters() {
    $('#menuFilters').addEventListener('click', event => { const button = event.target.closest('[data-filter]'); if (!button) return; state.filter = button.dataset.filter; renderMenu(); });
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) resetMomentTimer(); });
  document.addEventListener('DOMContentLoaded', async () => {
    $('#year').textContent = new Date().getFullYear(); $('#bookingDate').min = localISODate(); $('#bookingDate').value = localISODate();
    setupSound(); setupMoments(); setupOverlays(); setupNavigation(); setupFilters();
    await Promise.all([
      loadMenu(),
      refreshUser(),
      loadCheckoutOptions().catch(error => { $('#cartFeedback').textContent = `Checkout options unavailable: ${error.message}`; }),
      loadPublicContent().catch(error => { $('#siteMain').dataset.contentStatus = error.message; }),
    ]);
    window.setTimeout(() => $('#siteLoader').classList.add('done'), 450);
  });
})();
