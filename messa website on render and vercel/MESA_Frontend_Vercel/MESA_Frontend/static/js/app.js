(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const API_BASE = String(window.MESA_API_BASE || '').replace(/\/+$/, '');
  const currency = value => `K${Number(value || 0).toLocaleString('en-ZM')}`;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const state = { menu: [], filter: 'All', cart: readCart(), user: null, heroIndex: 0, heroTimer: null };
  const heroSlides = [
    { id: 'mesa-smash', name: 'MESA Smash Burger', price: 88, image: '/static/media/mesa-burger.jpg', kicker: 'THE ONE THAT STARTED IT', title: 'Big flavour. No fuss.' },
    { id: 'beef-wrap', name: 'Beef Wrap & Fries', price: 76, image: '/static/media/beef-wrap-fries.jpg', kicker: 'FRESH FROM THE KITCHEN', title: 'A proper little feast.' },
    { id: 'grilled-fish', name: 'Grilled Fish & Nshima', price: 148, image: '/static/media/grilled-fish-nshima.jpg', kicker: 'A TASTE OF HOME', title: 'Good food. Good company.' },
    { id: 'caterpillar-stew', name: 'Traditional Caterpillar Stew', price: 32, image: '/static/media/caterpillar-stew.jpg', kicker: 'ROOTED IN ZAMBIAN FLAVOUR', title: 'A taste worth sharing.' },
  ];

  function readCart() {
    try {
      const parsed = JSON.parse(localStorage.getItem('mesa-cart') || '[]');
      return Array.isArray(parsed) ? parsed.filter(item => item && typeof item.id === 'string' && Number.isInteger(item.quantity) && item.quantity > 0 && item.quantity <= 20) : [];
    } catch { return []; }
  }
  function saveCart() { localStorage.setItem('mesa-cart', JSON.stringify(state.cart)); }
  async function api(path, payload) {
    const response = await fetch(`${API_BASE}${path}`, {
      method: payload === undefined ? 'GET' : 'POST',
      headers: payload === undefined ? { 'Accept': 'application/json' } : { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: payload === undefined ? undefined : JSON.stringify(payload),
      credentials: 'include',
    });
    let result;
    try { result = await response.json(); } catch { throw new Error('The server returned an unreadable response. Please try again.'); }
    if (!response.ok || !result.ok) throw new Error(result.message || 'Something went wrong. Please try again.');
    return result;
  }
  function toast(message, type = 'success') {
    const region = $('#toastRegion');
    const el = document.createElement('div');
    el.className = `toast ${type === 'error' ? 'error' : ''}`;
    el.textContent = message;
    region.append(el);
    window.setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(8px)'; window.setTimeout(() => el.remove(), 260); }, 3600);
  }
  function setBusy(form, busy, label) {
    const button = $('button[type="submit"]', form);
    if (!button) return;
    if (busy) { button.dataset.originalText = button.innerHTML; button.disabled = true; button.innerHTML = '<span class="loader"></span> Please wait…'; }
    else { button.disabled = false; if (button.dataset.originalText) button.innerHTML = button.dataset.originalText; }
  }
  function imageFor(item) {
    const id = item?.id || '';
    if (id.includes('burger') || id.includes('garden')) return '/static/media/mesa-burger.jpg';
    if (id.includes('pizza')) return '/static/media/beef-wrap-fries.jpg';
    if (id.includes('fries')) return '/static/media/beef-wrap-fries.jpg';
    if (id.includes('sundae') || id.includes('shake') || id.includes('lemonade')) return '/static/media/caterpillar-stew.jpg';
    return '/static/media/grilled-fish-nshima.jpg';
  }

  async function loadMenu() {
    try {
      const result = await api('/api/menu');
      state.menu = result.items;
      renderMenu();
      renderCart();
      renderHero();
    } catch (error) {
      $('#menuGrid').innerHTML = `<div class="menu-loading">We couldn't load the menu. ${escapeHTML(error.message)} <button class="text-link" id="retryMenu">Try again ↗</button></div>`;
      $('#retryMenu')?.addEventListener('click', loadMenu);
    }
  }
  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  }
  function renderMenu() {
    const products = state.filter === 'All' ? state.menu : state.menu.filter(item => item.category === state.filter);
    $('#menuGrid').innerHTML = products.map((item, index) => `
      <article class="menu-card" style="animation-delay:${index * 55}ms">
        <div class="menu-card-art" role="img" aria-label="${escapeHTML(item.name)}" style="background-image:linear-gradient(0deg,rgba(12,16,13,.28),rgba(12,16,13,.02)),url('${imageFor(item)}')"><span class="menu-card-tag">${escapeHTML(item.tag)}</span></div>
        <div class="menu-card-content">
          <div class="menu-card-title-row"><h3>${escapeHTML(item.name)}</h3><span class="menu-card-price">${currency(item.price)}</span></div>
          <p>${escapeHTML(item.description)}</p>
          <button class="add-button" type="button" data-add="${escapeHTML(item.id)}">Add to bag <span>＋</span></button>
        </div>
      </article>`).join('');
    $$('#menuGrid [data-add]').forEach(button => button.addEventListener('click', () => addToCart(button.dataset.add)));
  }
  function addToCart(id) {
    const product = state.menu.find(item => item.id === id);
    if (!product) return;
    const line = state.cart.find(item => item.id === id);
    if (line) {
      if (line.quantity >= 20) return toast('You can add up to 20 of each item.', 'error');
      line.quantity += 1;
    } else state.cart.push({ id, quantity: 1 });
    saveCart(); renderCart(); toast(`${product.name} added to your bag.`);
  }
  function changeQuantity(id, delta) {
    const line = state.cart.find(item => item.id === id);
    if (!line) return;
    line.quantity += delta;
    if (line.quantity <= 0) state.cart = state.cart.filter(item => item.id !== id);
    if (line.quantity > 20) line.quantity = 20;
    saveCart(); renderCart();
  }
  function cartProducts() {
    return state.cart.map(line => {
      const product = state.menu.find(item => item.id === line.id);
      return product ? { ...product, quantity: line.quantity, lineTotal: product.price * line.quantity } : null;
    }).filter(Boolean);
  }
  function cartSubtotal() { return cartProducts().reduce((sum, item) => sum + item.lineTotal, 0); }
  function renderCart() {
    const products = cartProducts();
    const count = products.reduce((sum, item) => sum + item.quantity, 0);
    $('#cartCount').textContent = count;
    $('#drawerItemCount').textContent = `(${count})`;
    if (!products.length) {
      $('#cartItems').innerHTML = '<div class="empty-cart"><span>✳</span><h3>Your bag is looking hungry.</h3><p>Pick something lovely from the menu.</p><button class="button button-dark" id="browseMenu">Explore the menu ↗</button></div>';
      $('#browseMenu')?.addEventListener('click', () => { closeCart(); $('#menu').scrollIntoView({ behavior: 'smooth' }); });
      $('#cartSummary').hidden = true;
      return;
    }
    $('#cartItems').innerHTML = products.map(item => `
      <div class="cart-line">
        <div class="cart-line-art">${artFor(item.art)}</div>
        <div><h4>${escapeHTML(item.name)}</h4><small>${currency(item.price)} each</small>
          <div class="quantity-control"><button type="button" data-qty="-1" data-id="${item.id}" aria-label="Remove one ${escapeHTML(item.name)}">−</button><span>${item.quantity}</span><button type="button" data-qty="1" data-id="${item.id}" aria-label="Add one ${escapeHTML(item.name)}">＋</button><button class="remove-line" type="button" data-remove="${item.id}">Remove</button></div>
        </div><strong class="cart-line-price">${currency(item.lineTotal)}</strong>
      </div>`).join('');
    $$('[data-qty]', $('#cartItems')).forEach(button => button.addEventListener('click', () => changeQuantity(button.dataset.id, Number(button.dataset.qty))));
    $$('[data-remove]', $('#cartItems')).forEach(button => button.addEventListener('click', () => { state.cart = state.cart.filter(item => item.id !== button.dataset.remove); saveCart(); renderCart(); }));
    $('#cartSummary').hidden = false;
    $('#cartSubtotal').textContent = currency(cartSubtotal());
    $('#cartFee').textContent = 'At checkout';
    $('#cartTotal').textContent = currency(cartSubtotal());
  }
  function openCart() {
    $('#cartOverlay').hidden = false;
    requestAnimationFrame(() => { $('#cartOverlay').classList.add('visible'); $('#cartDrawer').classList.add('open'); });
    $('#cartDrawer').setAttribute('aria-hidden', 'false');
    document.body.classList.add('no-scroll');
  }
  function closeCart() {
    $('#cartOverlay').classList.remove('visible'); $('#cartDrawer').classList.remove('open');
    $('#cartDrawer').setAttribute('aria-hidden', 'true');
    document.body.classList.remove('no-scroll');
    window.setTimeout(() => { $('#cartOverlay').hidden = true; }, 310);
  }

  function renderHero() {
    const slide = heroSlides[state.heroIndex];
    $('#heroArt').innerHTML = `<img class="hero-food-photo" src="${slide.image}" alt="${escapeHTML(slide.name)}">`;
    $('#heroFoodName').textContent = slide.name;
    $('#heroPrice').textContent = currency(slide.price);
    $('#heroKicker').textContent = slide.kicker;
    $('#heroDescription').textContent = slide.title + ' ' + (state.heroIndex === 0 ? 'Our signature stack, layered with the good stuff.' : 'Made with fresh ingredients and a little MESA magic.');
    $('#heroPagination').innerHTML = heroSlides.map((item, index) => `<button type="button" class="${index === state.heroIndex ? 'active' : ''}" data-slide="${index}" aria-label="Show ${escapeHTML(item.name)}" ${index === state.heroIndex ? 'aria-current="true"' : ''}></button>`).join('');
    $$('[data-slide]', $('#heroPagination')).forEach(button => button.addEventListener('click', () => setHero(Number(button.dataset.slide))));
  }
  function setHero(index) { state.heroIndex = (index + heroSlides.length) % heroSlides.length; renderHero(); resetHeroTimer(); }
  function resetHeroTimer() {
    if (state.heroTimer) clearInterval(state.heroTimer);
    if (!reduceMotion) state.heroTimer = setInterval(() => { if (!document.hidden) { state.heroIndex = (state.heroIndex + 1) % heroSlides.length; renderHero(); } }, 6500);
  }

  const gallerySlides = [
    { image: '/static/media/beef-wrap-fries.jpg', alt: 'Beef wrap with golden fries', title: 'The perfect little feast.', caption: 'A hearty wrap, crisp fries and all the good things on one plate.' },
    { image: '/static/media/grilled-fish-nshima.jpg', alt: 'Grilled fish served with nshima and vegetables', title: 'A taste of home.', caption: 'Grilled fish, nshima and fresh vegetables — simple, generous and satisfying.' },
    { image: '/static/media/mesa-burger.jpg', alt: 'Freshly prepared MESA burger', title: 'Stacked with flavour.', caption: 'A juicy burger made for the first bite and the last crumb.' },
    { image: '/static/media/caterpillar-stew.jpg', alt: 'Traditional caterpillar stew', title: 'Zambian roots. MESA heart.', caption: 'A familiar favourite, served with care and a little extra.' },
  ];
  let galleryIndex = 0, galleryTimer = null;
  function showGallery(index) {
    galleryIndex = (index + gallerySlides.length) % gallerySlides.length;
    const slide = gallerySlides[galleryIndex], photo = $('#galleryPhoto');
    photo.classList.add('changing');
    window.setTimeout(() => { photo.src = slide.image; photo.alt = slide.alt; photo.classList.remove('changing'); }, 140);
    $('#galleryTitle').textContent = slide.title;
    $('#galleryCaption').textContent = slide.caption;
    $('#galleryCount').textContent = `${String(galleryIndex + 1).padStart(2, '0')} / 04`;
    resetGalleryTimer();
  }
  function resetGalleryTimer() {
    if (galleryTimer) clearInterval(galleryTimer);
    if (!reduceMotion) galleryTimer = setInterval(() => { if (!document.hidden) showGallery(galleryIndex + 1); }, 6500);
  }
  function setupKitchenMedia() {
    const film = $('#mesaFilm');
    const heroFilm = $('#heroFilm');
    const soundButton = $('#filmSound');
    [film, heroFilm].filter(Boolean).forEach(video => {
      video.muted = true;
      const attempt = video.play();
      if (attempt && typeof attempt.catch === 'function') attempt.catch(() => {});
    });
    soundButton.addEventListener('click', async () => {
      const nextMuted = !film.muted;
      film.muted = nextMuted;
      if (heroFilm) heroFilm.muted = true;
      if (!nextMuted) {
        try { await film.play(); if (heroFilm) { heroFilm.muted = true; await heroFilm.play(); } }
        catch { film.muted = true; if (heroFilm) heroFilm.muted = true; return toast('Your browser requires another tap before playing sound.', 'error'); }
      }
      soundButton.setAttribute('aria-pressed', String(!nextMuted));
      soundButton.innerHTML = nextMuted ? 'Enable video sound <span>＋</span>' : 'Mute video sound <span>−</span>';
    });
    $('#galleryPrev').addEventListener('click', () => showGallery(galleryIndex - 1));
    $('#galleryNext').addEventListener('click', () => showGallery(galleryIndex + 1));
    showGallery(0);
  }

  function openAuth(mode = 'login') {
    $('#authBackdrop').hidden = false;
    $('#authBackdrop').classList.toggle('register-mode', mode === 'register');
    document.body.classList.add('no-scroll');
    window.setTimeout(() => $(mode === 'register' ? '#registerForm input' : '#loginForm input')?.focus(), 80);
  }
  function closeAuth() { $('#authBackdrop').hidden = true; document.body.classList.remove('no-scroll'); }
  function switchAuth(mode) { $('#authBackdrop').classList.toggle('register-mode', mode === 'register'); }
  function setUser(user) {
    state.user = user;
    $('#accountLabel').textContent = user ? `Hi, ${user.name.split(' ')[0]}` : 'Sign in';
    $('#accountButton').title = user ? 'Click to sign out' : 'Sign in or create an account';
  }
  async function refreshUser() {
    try { const result = await api('/api/me'); setUser(result.user); } catch { setUser(null); }
  }
  async function handleAuth(form, endpoint) {
    const data = Object.fromEntries(new FormData(form).entries());
    setBusy(form, true);
    try {
      const result = await api(endpoint, data);
      setUser(result.user); closeAuth(); form.reset(); toast(result.message || 'You are signed in.');
    } catch (error) { toast(error.message, 'error'); }
    finally { setBusy(form, false); }
  }
  async function logout() {
    try { const result = await api('/api/logout', {}); setUser(null); toast(result.message); }
    catch (error) { toast(error.message, 'error'); }
  }

  function openCheckout() {
    if (!state.cart.length) return toast('Your bag is empty. Add a dish first.', 'error');
    closeCart();
    const form = $('#checkoutForm');
    if (state.user) {
      form.elements.name.value = state.user.name;
      form.elements.email.value = state.user.email;
    }
    $('#checkoutTotal').textContent = currency(cartSubtotal());
    $('#checkoutBackdrop').hidden = false;
    document.body.classList.add('no-scroll');
    updateDeliveryFields();
  }
  function closeCheckout() { $('#checkoutBackdrop').hidden = true; document.body.classList.remove('no-scroll'); }
  function updateDeliveryFields() {
    const isDelivery = $('#fulfilmentSelect').value === 'delivery';
    $('#addressField').hidden = !isDelivery;
    $('#addressField').querySelector('textarea').required = isDelivery;
    $('#checkoutTotal').textContent = currency(cartSubtotal() + (isDelivery ? 12 : 0));
    const paymentSelect = $('#checkoutForm').elements.payment;
    const cashDelivery = [...paymentSelect.options].find(option => option.value === 'cash-on-delivery');
    cashDelivery.disabled = !isDelivery;
    if (!isDelivery && paymentSelect.value === 'cash-on-delivery') paymentSelect.value = 'pay-at-counter';
  }
  async function handleCheckout(form) {
    const data = Object.fromEntries(new FormData(form).entries());
    data.items = state.cart.map(item => ({ id: item.id, quantity: item.quantity }));
    setBusy(form, true);
    try {
      const result = await api('/api/orders', data);
      state.cart = []; saveCart(); renderCart(); closeCheckout(); form.reset(); updateDeliveryFields();
      toast(`Order ${result.reference} received — total ${currency(result.total)}.`, 'success');
    } catch (error) { toast(error.message, 'error'); }
    finally { setBusy(form, false); }
  }
  async function handleBooking(form) {
    const data = Object.fromEntries(new FormData(form).entries());
    data.guests = Number(data.guests);
    setBusy(form, true);
    try {
      const result = await api('/api/bookings', data);
      form.reset(); $('#bookingDate').min = todayISO();
      toast(`Request ${result.reference} received. We'll be in touch!`);
    } catch (error) { toast(error.message, 'error'); }
    finally { setBusy(form, false); }
  }
  function todayISO() {
    const now = new Date();
    const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  }
  function setupReveal() {
    const elements = $$('.reveal');
    if (!('IntersectionObserver' in window) || reduceMotion) { elements.forEach(el => el.classList.add('in-view')); return; }
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('in-view'); observer.unobserve(entry.target); }
    }), { threshold: .12 });
    elements.forEach(el => observer.observe(el));
  }
  function setupEvents() {
    $('#cartButton').addEventListener('click', openCart);
    $('#closeCart').addEventListener('click', closeCart);
    $('#cartOverlay').addEventListener('click', closeCart);
    $('#checkoutButton').addEventListener('click', openCheckout);
    $('#closeCheckout').addEventListener('click', closeCheckout);
    $('#checkoutBackdrop').addEventListener('click', event => { if (event.target === $('#checkoutBackdrop')) closeCheckout(); });
    $('#fulfilmentSelect').addEventListener('change', updateDeliveryFields);
    $('#checkoutForm').addEventListener('submit', event => { event.preventDefault(); handleCheckout(event.currentTarget); });
    $('#bookingForm').addEventListener('submit', event => { event.preventDefault(); handleBooking(event.currentTarget); });
    $('#loginForm').addEventListener('submit', event => { event.preventDefault(); handleAuth(event.currentTarget, '/api/login'); });
    $('#registerForm').addEventListener('submit', event => { event.preventDefault(); handleAuth(event.currentTarget, '/api/register'); });
    $('#accountButton').addEventListener('click', () => state.user ? logout() : openAuth('login'));
    $('#closeAuth').addEventListener('click', closeAuth);
    $('#authBackdrop').addEventListener('click', event => { if (event.target === $('#authBackdrop')) closeAuth(); });
    $$('[data-auth-switch]').forEach(button => button.addEventListener('click', () => switchAuth(button.dataset.authSwitch)));
    $('#menuFilters').addEventListener('click', event => {
      const button = event.target.closest('[data-filter]');
      if (!button) return;
      state.filter = button.dataset.filter;
      $$('.filter-button').forEach(item => item.classList.toggle('active', item === button));
      renderMenu();
    });
    $('#heroPrev').addEventListener('click', () => setHero(state.heroIndex - 1));
    $('#heroNext').addEventListener('click', () => setHero(state.heroIndex + 1));
    $('#mobileMenuToggle').addEventListener('click', () => {
      const nav = $('#mainNav'); const open = nav.classList.toggle('mobile-open');
      $('#mobileMenuToggle').setAttribute('aria-expanded', String(open));
    });
    $$('#mainNav a').forEach(link => link.addEventListener('click', () => { $('#mainNav').classList.remove('mobile-open'); $('#mobileMenuToggle').setAttribute('aria-expanded', 'false'); }));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') { closeCart(); closeAuth(); closeCheckout(); $('#mainNav').classList.remove('mobile-open'); }
    });
    document.addEventListener('visibilitychange', () => { if (!document.hidden) resetHeroTimer(); });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    $('#yearNow').textContent = new Date().getFullYear();
    $('#bookingDate').min = todayISO();
    setupEvents(); setupReveal(); setupKitchenMedia();
    await Promise.all([loadMenu(), refreshUser()]);
    resetHeroTimer();
  });
})();
