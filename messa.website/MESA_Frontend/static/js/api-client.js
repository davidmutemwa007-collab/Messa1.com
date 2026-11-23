/* MESA frontend-to-backend bridge.
 * Uses the original standalone Python API; no credentials are stored in browser storage.
 */
(() => {
  'use strict';
  const API_ROOT = '/api';
  async function request(path, options = {}) {
    const method = options.method || (options.body ? 'POST' : 'GET');
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    if (options.body !== undefined) headers['Content-Type'] = 'application/json';
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`${API_ROOT}${path}`, {
        method, headers, body: options.body === undefined ? undefined : JSON.stringify(options.body),
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
      });
      let payload = {};
      const raw = await response.text();
      if (raw) { try { payload = JSON.parse(raw); } catch { payload = { message: raw.slice(0, 240) }; } }
      if (!response.ok || payload.ok === false) {
        const message = payload.message || payload.error || `Request failed (${response.status}).`;
        const error = new Error(message);
        error.status = response.status;
        error.payload = payload;
        throw error;
      }
      return payload;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('The server took too long to respond. Check that MESA is running.');
      if (error instanceof TypeError) throw new Error('Could not reach the MESA backend. Make sure its Python server is running.');
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  }
  window.MESAApi = Object.freeze({
    health: () => request('/health'),
    menu: () => request('/menu'),
    deliveryZones: () => request('/delivery-zones'),
    paymentMethods: () => request('/payment-methods'),
    content: () => request('/content'),
    me: () => request('/me'),
    register: (data) => request('/register', { method: 'POST', body: data }),
    login: (data) => request('/login', { method: 'POST', body: data }),
    logout: () => request('/logout', { method: 'POST', body: {} }),
    booking: (data) => request('/bookings', { method: 'POST', body: data }),
    order: (data) => request('/orders', { method: 'POST', body: data }),
    submitPayment: (data) => request('/payments/submit', { method: 'POST', body: data }),
    changePassword: (data) => request('/password/change', { method: 'POST', body: data }),
    // Optional endpoints: the old standalone backend does not currently expose these.
    adminMe: () => request('/admin/me'),
    adminSummary: () => request('/admin/summary'),
    adminOrders: () => request('/admin/orders'),
    adminBookings: () => request('/admin/bookings'),
    adminUsers: () => request('/admin/users'),
    adminMenu: () => request('/admin/menu'),
    adminAudit: () => request('/admin/audit'),
    adminAnalytics: () => request('/admin/analytics'),
    adminRoles: () => request('/admin/roles'),
    adminPaymentMethods: () => request('/admin/payment-methods'),
    savePaymentMethod: (data) => request('/admin/payment-methods/save', { method: 'POST', body: data }),
    adminPayments: () => request('/admin/payments'),
    reviewPayment: (data) => request('/admin/payments/status', { method: 'POST', body: data }),
    adminDeliveryZones: () => request('/admin/delivery/zones'),
    saveDeliveryZone: (data) => request('/admin/delivery/zones/save', { method: 'POST', body: data }),
    deleteDeliveryZone: (id) => request('/admin/delivery/zones/delete', { method: 'POST', body: { id } }),
    adminDeliveries: () => request('/admin/deliveries'),
    adminDeliveryStaff: () => request('/admin/delivery/staff'),
    assignDelivery: (data) => request('/admin/delivery/assign', { method: 'POST', body: data }),
    updateDeliveryStatus: (data) => request('/admin/deliveries/status', { method: 'POST', body: data }),
    adminContent: () => request('/admin/content'),
    saveContent: (content) => request('/admin/content/save', { method: 'POST', body: { content } }),
    uploadImage: (data) => request('/admin/uploads/image', { method: 'POST', body: { data } }),
    assignRole: (data) => request('/admin/users/role', { method: 'POST', body: data }),
    updateOrderStatus: (data) => request('/admin/orders/status', { method: 'POST', body: data }),
    updateBookingStatus: (data) => request('/admin/bookings/status', { method: 'POST', body: data }),
    updateUserAccess: (data) => request('/admin/users/access', { method: 'POST', body: data }),
    saveMenuItem: (data) => request('/admin/menu/save', { method: 'POST', body: data }),
    archiveMenuItem: (id) => request('/admin/menu/delete', { method: 'POST', body: { id } }),
    restoreMenuItem: (id) => request('/admin/menu/restore', { method: 'POST', body: { id } }),
  });
})();
