/* ===========================================================================
 * NIRA Ambient Care — Authentication Client
 * ---------------------------------------------------------------------------
 * Drives the Sign In / Sign Up / Password Recovery experience served from
 * /login (Demo/app/static/login.html).
 *
 * SCOPE: authentication only. No dashboard, caregiver, EMS, medication, sensor
 * or emergency behaviour is read or written by this module.
 *
 * SECURITY CONTRACT
 *   - Raw passwords are never written to localStorage, sessionStorage, cookies
 *     or the console. They exist only in a local variable for the duration of
 *     a request and are discarded afterwards.
 *   - Demo-mode credentials are persisted only as salted PBKDF2-SHA256 digests
 *     (150 000 iterations). Plain-text demo credentials appear only in this
 *     file as published, non-secret demo values that the UI also displays.
 *   - The session record reuses the existing NIRA contract
 *     (`aegis_auth_user` in localStorage) that dashboard.js and
 *     person1_module.js already consume, so an authenticated user always
 *     lands on exactly the same destination as before this upgrade.
 *   - When the deployment exposes a real authentication API the client uses it
 *     (forwarding a CSRF token when the deployment provides one). Otherwise it
 *     degrades to the existing NIRA demo-session mode and discloses that fact
 *     in the interface instead of pretending a server verified anything.
 * =========================================================================*/

(function (global) {
  'use strict';

  /* ------------------------------------------------------------------------
   * 1. Configuration
   * ---------------------------------------------------------------------*/

  const STORAGE_KEYS = {
    session: 'aegis_auth_user',        // existing NIRA session contract
    legacySession: 'nira_demo_auth',   // existing mirror written by the legacy page
    accounts: 'nira_demo_accounts',    // browser-local demo account registry
    accessToken: 'nira_auth_token'     // session-scoped token (server mode only)
  };

  // Canonical authentication API. The client only calls a path that the running
  // deployment actually exposes (detected from the live OpenAPI document), so
  // no endpoint is ever assumed to exist.
  const AUTH_API = {
    login: '/api/v1/auth/login',
    register: '/api/v1/auth/register',
    recovery: '/api/v1/auth/password-reset'
  };

  const REQUEST_TIMEOUT_MS = 12000;
  const PBKDF2_ITERATIONS = 150000;
  const PBKDF2_KEY_LENGTH = 32;
  const MIN_PASSWORD_LENGTH = 8;
  const REDIRECT_DELAY_MS = 550;

  const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  const USERNAME_PATTERN = /^[a-z0-9._-]{3,32}$/;

  const COMMON_PASSWORDS = [
    'password', 'password1', 'password123', '123456', '12345678', '123456789',
    'qwerty', 'qwerty123', 'letmein', 'admin', 'admin123', 'welcome',
    'iloveyou', 'abc123', 'monkey', 'dragon', 'sunshine', 'princess',
    'football', 'baseball', 'trustno1', 'starwars', 'nira1234'
  ];

  /* ------------------------------------------------------------------------
   * 2. Demo personas
   * -------------------------------------------------------------------------
   * These are the three published demo profiles. Their labels, roles, icons,
   * e-mail addresses and post-login destinations are unchanged from the
   * previous login page. The `credential` block holds a salted PBKDF2-SHA256
   * digest of the published demo password so the sign-in form can verify a
   * typed credential without ever storing the password itself.
   * ---------------------------------------------------------------------*/

  const DEMO_PERSONAS = {
    senior_resident: {
      key: 'senior_resident',
      name: 'Eleanor Vance (Resident)',
      role: 'Resident / Senior View',
      roleKey: 'resident',
      email: 'eleanor.vance@beaconhill.care',
      username: 'eleanor.vance',
      avatar: '👵',
      redirect: '/#demo/homedashboard',
      credential: {
        algo: 'PBKDF2-SHA256',
        iterations: PBKDF2_ITERATIONS,
        salt: 'bmlyYV9kZW1vX3Jlc2lkZW50X3Yx',
        hash: 'LqGdGikr8oTZsfz9tn8BwFEA81SH3C/37Fyl+odz7qU='
      }
    },
    caregiver_david: {
      key: 'caregiver_david',
      name: 'David Vance (Caregiver)',
      role: 'Family Primary Caregiver',
      roleKey: 'caregiver',
      email: 'david.vance@example.com',
      username: 'david.vance',
      avatar: '👨‍💼',
      redirect: '/#demo/caregiverdashboard',
      credential: {
        algo: 'PBKDF2-SHA256',
        iterations: PBKDF2_ITERATIONS,
        salt: 'bmlyYV9kZW1vX2NhcmVnaXZlcl92MQ==',
        hash: 'VIFkS1awBF8AwdRAFC9LfXjEEfQdc3cIdn2H9Sh79tY='
      }
    },
    ems_medic: {
      key: 'ems_medic',
      name: 'Medic 14 (Boston EMS First Responder)',
      role: 'First Responder / Dispatch',
      email: 'medic14@bostonems.gov',
      username: 'medic14',
      avatar: '🚑',
      redirect: '/#demo/emergencyalert',
      credential: {
        algo: 'PBKDF2-SHA256',
        iterations: PBKDF2_ITERATIONS,
        salt: 'bmlyYV9kZW1vX2Vtc192MQ==',
        hash: 'q/qB9KBL/n0ItemzpTJbOCGzdyBFxy2kQLbQyg/SQ5E='
      }
    }
  };

  /* ------------------------------------------------------------------------
   * 3. Small helpers
   * ---------------------------------------------------------------------*/

  const $ = (id) => document.getElementById(id);

  function delay(ms) {
    return new Promise((resolve) => global.setTimeout(resolve, ms));
  }

  function truncate(text, max) {
    const value = String(text == null ? '' : text);
    return value.length > max ? value.slice(0, max - 1) + '…' : value;
  }

  function toBase64(bytes) {
    let binary = '';
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i]);
    }
    return global.btoa(binary);
  }

  function fromBase64(value) {
    const binary = global.atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }

  function constantTimeEqual(a, b) {
    const left = String(a || '');
    const right = String(b || '');
    let diff = left.length ^ right.length;
    const max = Math.max(left.length, right.length);
    for (let i = 0; i < max; i += 1) {
      diff |= (left.charCodeAt(i) || 0) ^ (right.charCodeAt(i) || 0);
    }
    return diff === 0;
  }

  function randomId(prefix) {
    const cryptoApi = global.crypto;
    let suffix = '';
    if (cryptoApi && typeof cryptoApi.getRandomValues === 'function') {
      const bytes = new Uint8Array(8);
      cryptoApi.getRandomValues(bytes);
      for (let i = 0; i < bytes.length; i += 1) {
        suffix += bytes[i].toString(16).padStart(2, '0');
      }
    } else {
      suffix = Math.random().toString(16).slice(2, 18);
    }
    return prefix + suffix;
  }

  function safeStorage(kind) {
    try {
      const store = kind === 'session' ? global.sessionStorage : global.localStorage;
      if (!store) return null;
      return store;
    } catch (error) {
      return null;
    }
  }

  /* ------------------------------------------------------------------------
   * 4. Password policy + strength
   * ---------------------------------------------------------------------*/

  function evaluatePassword(password) {
    const value = password || '';
    const checks = {
      length: value.length >= MIN_PASSWORD_LENGTH,
      letter: /[A-Za-z]/.test(value),
      number: /[0-9]/.test(value),
      symbol: /[^A-Za-z0-9]/.test(value),
      uncommon: COMMON_PASSWORDS.indexOf(value.toLowerCase()) === -1
    };

    const blockers = [];
    if (!checks.length) {
      blockers.push('Use at least ' + MIN_PASSWORD_LENGTH + ' characters.');
    }
    if (!checks.letter) {
      blockers.push('Include at least one letter.');
    }
    if (!checks.number) {
      blockers.push('Include at least one number.');
    }
    if (!checks.uncommon) {
      blockers.push('That password is too common — choose something less predictable.');
    }

    let score = 0;
    if (checks.length) score += 1;
    if (value.length >= 12) score += 1;
    if (value.length >= 16) score += 1;
    const classes = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/]
      .filter((pattern) => pattern.test(value)).length;
    score += Math.max(0, classes - 1);
    if (!checks.uncommon) score = 0;
    score = Math.min(4, score);

    const labels = ['Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'];
    return {
      checks: checks,
      blockers: blockers,
      score: score,
      label: value ? labels[score] : 'Not set',
      valid: blockers.length === 0 && value.length > 0
    };
  }

  function renderStrength(meterId, labelId, password) {
    const meter = $(meterId);
    const label = $(labelId);
    const result = evaluatePassword(password);
    if (meter) {
      const segments = meter.querySelectorAll('.strength-seg');
      for (let i = 0; i < segments.length; i += 1) {
        const active = i < result.score;
        segments[i].classList.toggle('is-on', active);
        segments[i].classList.toggle('is-current', i === result.score - 1);
      }
      meter.setAttribute('data-score', String(result.score));
    }
    if (label) {
      label.textContent = 'Password strength: ' + result.label;
      label.setAttribute('data-score', String(result.score));
    }
    return result;
  }

  function renderPolicyList(listId, password) {
    const list = $(listId);
    if (!list) return;
    const result = evaluatePassword(password);
    const items = list.querySelectorAll('[data-policy]');
    for (let i = 0; i < items.length; i += 1) {
      const key = items[i].getAttribute('data-policy');
      const met = key === 'symbol' ? result.checks.symbol : result.checks[key] === true;
      items[i].classList.toggle('is-met', met);
      items[i].setAttribute('aria-checked', met ? 'true' : 'false');
    }
  }

  /* ------------------------------------------------------------------------
   * 5. Field-level validation helpers
   * ---------------------------------------------------------------------*/

  function setFieldError(fieldId, message) {
    const field = $(fieldId);
    const errorBox = $(fieldId + 'Error');
    if (!field) return;
    if (message) {
      field.classList.add('has-error');
      field.setAttribute('aria-invalid', 'true');
      if (errorBox) {
        errorBox.textContent = message;
        errorBox.hidden = false;
      }
    } else {
      field.classList.remove('has-error');
      field.removeAttribute('aria-invalid');
      if (errorBox) {
        errorBox.textContent = '';
        errorBox.hidden = true;
      }
    }
  }

  function clearFormErrors(prefix, fieldIds) {
    fieldIds.forEach((id) => setFieldError(id, ''));
    const banner = $(prefix);
    if (banner) {
      banner.textContent = '';
      banner.style.display = 'none';
    }
  }

  function showBanner(id, message, kind) {
    const box = $(id);
    if (!box) return;
    box.textContent = message || '';
    box.classList.remove('auth-error-box', 'auth-success-box', 'auth-warning-box');
    if (kind === 'success') box.classList.add('auth-success-box');
    else if (kind === 'warning') box.classList.add('auth-warning-box');
    else box.classList.add('auth-error-box');
    box.style.display = message ? 'block' : 'none';
  }

  function focusFirstInvalid(fieldIds) {
    for (let i = 0; i < fieldIds.length; i += 1) {
      const field = $(fieldIds[i]);
      if (field && field.classList.contains('has-error')) {
        field.focus();
        return;
      }
    }
  }

  function setButtonLoading(button, loading, label) {
    if (!button) return;
    if (loading) {
      if (!button.getAttribute('data-idle-html')) {
        button.setAttribute('data-idle-html', button.innerHTML);
      }
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      button.innerHTML =
        '<span class="spinner" aria-hidden="true"></span>' +
        '<span>' + (label || 'Working…') + '</span>';
    } else {
      button.disabled = false;
      button.removeAttribute('aria-busy');
      const idle = button.getAttribute('data-idle-html');
      if (idle) {
        button.innerHTML = idle;
        button.removeAttribute('data-idle-html');
      }
    }
  }

  /* ------------------------------------------------------------------------
   * 6. Password visibility
   * ---------------------------------------------------------------------*/

  function togglePassword(inputId) {
    const input = $(inputId);
    if (!input) return;
    const reveal = input.type === 'password';
    const toggle = document.querySelector('[data-password-toggle="' + inputId + '"]');
    input.type = reveal ? 'text' : 'password';
    if (toggle) {
      toggle.setAttribute('aria-pressed', reveal ? 'true' : 'false');
      toggle.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
      toggle.setAttribute('title', reveal ? 'Hide password' : 'Show password');
    }
    const caret = input.value.length;
    input.focus();
    try {
      input.setSelectionRange(caret, caret);
    } catch (error) {
      /* selection is not supported for every input type */
    }
  }

  /* ------------------------------------------------------------------------
   * 7. Crypto helpers (PBKDF2-SHA256)
   * ---------------------------------------------------------------------*/

  function getSubtleCrypto() {
    const cryptoApi = global.crypto;
    if (!cryptoApi || !cryptoApi.subtle || typeof cryptoApi.subtle.importKey !== 'function') {
      return null;
    }
    return cryptoApi.subtle;
  }

  async function deriveCredential(password, saltB64, iterations) {
    const subtle = getSubtleCrypto();
    if (!subtle) return null;
    try {
      const encoder = new TextEncoder();
      const keyMaterial = await subtle.importKey(
        'raw',
        encoder.encode(password),
        { name: 'PBKDF2' },
        false,
        ['deriveBits']
      );
      const bits = await subtle.deriveBits(
        {
          name: 'PBKDF2',
          salt: fromBase64(saltB64),
          iterations: iterations || PBKDF2_ITERATIONS,
          hash: 'SHA-256'
        },
        keyMaterial,
        PBKDF2_KEY_LENGTH * 8
      );
      return {
        algo: 'PBKDF2-SHA256',
        iterations: iterations || PBKDF2_ITERATIONS,
        salt: saltB64,
        hash: toBase64(new Uint8Array(bits))
      };
    } catch (error) {
      return null;
    }
  }

  function newSalt() {
    const cryptoApi = global.crypto;
    if (cryptoApi && typeof cryptoApi.getRandomValues === 'function') {
      const bytes = new Uint8Array(16);
      cryptoApi.getRandomValues(bytes);
      return toBase64(bytes);
    }
    return toBase64(new Uint8Array(
      [Math.floor(Math.random() * 256), Math.floor(Math.random() * 256),
       Math.floor(Math.random() * 256), Math.floor(Math.random() * 256),
       Math.floor(Math.random() * 256), Math.floor(Math.random() * 256),
       Math.floor(Math.random() * 256), Math.floor(Math.random() * 256),
       Math.floor(Math.random() * 256), Math.floor(Math.random() * 256),
       Math.floor(Math.random() * 256), Math.floor(Math.random() * 256),
       Math.floor(Math.random() * 256), Math.floor(Math.random() * 256),
       Math.floor(Math.random() * 256), Math.floor(Math.random() * 256)]
    ));
  }

  /* ------------------------------------------------------------------------
   * 8. Account registry (browser-local, demo mode)
   * ---------------------------------------------------------------------*/

  function readStoredAccounts() {
    const store = safeStorage('local');
    if (!store) return [];
    try {
      const raw = store.getItem(STORAGE_KEYS.accounts);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function writeStoredAccounts(accounts) {
    const store = safeStorage('local');
    if (!store) return false;
    try {
      store.setItem(STORAGE_KEYS.accounts, JSON.stringify(accounts));
      return true;
    } catch (error) {
      return false;
    }
  }

  function personaRecord(key) {
    const persona = DEMO_PERSONAS[key];
    if (!persona) return null;
    return {
      id: 'demo_' + persona.key,
      name: persona.name,
      email: persona.email,
      username: persona.username,
      role: persona.role,
      roleKey: persona.roleKey,
      avatar: persona.avatar,
      redirect: persona.redirect,
      credential: persona.credential,
      source: 'demo',
      createdAt: null
    };
  }

  function buildAccountRecords() {
    const accounts = Object.keys(DEMO_PERSONAS)
      .map(personaRecord)
      .filter(Boolean);

    readStoredAccounts().forEach((stored) => {
      if (!stored || !stored.email) return;
      const email = String(stored.email).toLowerCase();
      let index = -1;
      for (let i = 0; i < accounts.length; i += 1) {
        if (String(accounts[i].email).toLowerCase() === email) {
          index = i;
          break;
        }
      }
      if (index === -1) {
        accounts.push(stored);
        return;
      }
      const merged = Object.assign({}, accounts[index], stored);
      if (!stored.credential) {
        merged.credential = accounts[index].credential;
      }
      accounts[index] = merged;
    });

    return accounts;
  }

  function findAccount(identifier) {
    const needle = String(identifier || '').trim().toLowerCase();
    if (!needle) return null;
    const accounts = buildAccountRecords();
    for (let i = 0; i < accounts.length; i += 1) {
      const account = accounts[i];
      if (account.email && String(account.email).toLowerCase() === needle) return account;
      if (account.username && String(account.username).toLowerCase() === needle) return account;
    }
    return null;
  }

  function isKnownEmail(email) {
    const needle = String(email || '').trim().toLowerCase();
    return buildAccountRecords().some(
      (account) => String(account.email).toLowerCase() === needle
    );
  }

  function upsertLocalAccount(account) {
    const accounts = readStoredAccounts();
    const email = String(account.email).toLowerCase();
    let replaced = false;
    for (let i = 0; i < accounts.length; i += 1) {
      if (String(accounts[i].email).toLowerCase() === email) {
        accounts[i] = Object.assign({}, accounts[i], account);
        replaced = true;
        break;
      }
    }
    if (!replaced) accounts.push(account);
    return writeStoredAccounts(accounts);
  }

  /* ------------------------------------------------------------------------
   * 9. Session handling (existing NIRA session contract)
   * ---------------------------------------------------------------------*/

  function persistSession(user) {
    const record = {
      name: user.name,
      role: user.role,
      roleKey: user.roleKey || '',
      email: user.email || '',
      avatar: user.avatar || '',
      redirect: user.redirect || '/',
      authMode: user.authMode || 'demo',
      issuedAt: new Date().toISOString()
    };
    const local = safeStorage('local');
    if (local) {
      try {
        local.setItem(STORAGE_KEYS.session, JSON.stringify(record));
        local.setItem(STORAGE_KEYS.legacySession, JSON.stringify(record));
      } catch (error) {
        /* storage unavailable — the sign-in still proceeds */
      }
    }
    return record;
  }

  function storeAccessToken(token) {
    if (!token) return;
    const sessionStore = safeStorage('session');
    if (!sessionStore) return;
    try {
      sessionStore.setItem(STORAGE_KEYS.accessToken, token);
    } catch (error) {
      /* ignore */
    }
  }

  /* ------------------------------------------------------------------------
   * 10. Backend capability detection
   * -------------------------------------------------------------------------
   * The client inspects the live OpenAPI document to learn whether this
   * deployment actually exposes an authentication API. Nothing is called that
   * the server does not advertise, and no endpoint is assumed to exist.
   * ---------------------------------------------------------------------*/

  let capabilitiesPromise = null;

  function detectCapabilities() {
    if (!capabilitiesPromise) {
      capabilitiesPromise = global.fetch('/openapi.json', {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        credentials: 'same-origin'
      })
        .then((response) => (response.ok ? response.json() : null))
        .then((spec) => {
          const paths = (spec && spec.paths) || {};
          return {
            login: Boolean(paths[AUTH_API.login]),
            register: Boolean(paths[AUTH_API.register]),
            recovery: Boolean(paths[AUTH_API.recovery])
          };
        })
        .catch(() => ({ login: false, register: false, recovery: false }));
    }
    return capabilitiesPromise;
  }

  /* ------------------------------------------------------------------------
   * 11. HTTP client
   * ---------------------------------------------------------------------*/

  function AuthError(message, kind, status, payload) {
    this.name = 'AuthError';
    this.message = message;
    this.kind = kind || 'unknown';
    this.status = status || 0;
    this.payload = payload || null;
  }
  AuthError.prototype = Object.create(Error.prototype);
  AuthError.prototype.constructor = AuthError;

  function readCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute('content')) {
      return meta.getAttribute('content');
    }
    const match = /(?:^|;\s*)(?:nira_csrf|csrftoken|XSRF-TOKEN)=([^;]+)/.exec(document.cookie || '');
    return match ? decodeURIComponent(match[1]) : null;
  }

  function formatValidationDetail(detail) {
    if (typeof detail === 'string' && detail) return truncate(detail, 160);
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (!item) return '';
          const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
          const message = item.msg || '';
          return field ? field + ': ' + message : message;
        })
        .filter(Boolean);
      if (messages.length) return truncate(messages.join(' '), 200);
    }
    return '';
  }

  function describeHttpError(status, payload) {
    const detail = payload && payload.detail;
    if (status === 400) return 'That request could not be processed. Please review your details.';
    if (status === 401) return 'That email or password is not recognised.';
    if (status === 403) return 'This account is not permitted to sign in right now.';
    if (status === 404) return 'The authentication service is not available in this deployment.';
    if (status === 409) return 'An account with those details already exists.';
    if (status === 422) {
      return formatValidationDetail(detail) || 'Some of the submitted details are invalid.';
    }
    if (status === 429) return 'Too many attempts. Please wait a moment before trying again.';
    if (status >= 500) return 'The authentication service is temporarily unavailable. Please try again shortly.';
    if (typeof detail === 'string' && detail) return truncate(detail, 180);
    return 'Sign-in could not be completed (HTTP ' + status + ').';
  }

  async function apiRequest(path, options) {
    const config = options || {};
    const controller = new AbortController();
    const timer = global.setTimeout(
      () => controller.abort(),
      config.timeout || REQUEST_TIMEOUT_MS
    );
    const headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-Requested-With': 'NIRA-Auth'
    };
    const csrf = readCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;

    let response;
    try {
      response = await global.fetch(path, {
        method: config.method || 'POST',
        headers: headers,
        body: config.body ? JSON.stringify(config.body) : undefined,
        credentials: 'same-origin',
        signal: controller.signal
      });
    } catch (error) {
      if (error && error.name === 'AbortError') {
        throw new AuthError(
          'The authentication service did not respond in time. Please try again.',
          'timeout'
        );
      }
      throw new AuthError(
        'We could not reach the authentication service. Check your connection and try again.',
        'network'
      );
    } finally {
      global.clearTimeout(timer);
    }

    let payload = null;
    let raw = '';
    try {
      raw = await response.text();
    } catch (error) {
      raw = '';
    }
    if (raw) {
      try {
        payload = JSON.parse(raw);
      } catch (error) {
        payload = { detail: raw };
      }
    }

    if (!response.ok) {
      throw new AuthError(
        describeHttpError(response.status, payload),
        'http',
        response.status,
        payload
      );
    }
    return payload || {};
  }

  /* ------------------------------------------------------------------------
   * 12. Demo-mode authentication
   * ---------------------------------------------------------------------*/

  async function dummyDerivation() {
    // Keeps the response time of "unknown account" and "wrong password"
    // comparable so the interface cannot be used to enumerate accounts.
    await deriveCredential('timing-equaliser', 'bmlyYV9kZW1vX3Jlc2lkZW50X3Yx', PBKDF2_ITERATIONS);
  }

  async function authenticateDemoAccount(identifier, password) {
    const account = findAccount(identifier);
    if (!account) {
      await dummyDerivation();
      return { ok: false, reason: 'unknown' };
    }
    const credential = account.credential;
    if (!credential || !credential.hash || !credential.salt) {
      await dummyDerivation();
      return { ok: false, reason: 'unverifiable' };
    }
    const derived = await deriveCredential(password, credential.salt, credential.iterations);
    if (!derived) {
      return { ok: false, reason: 'unsupported' };
    }
    const ok = constantTimeEqual(derived.hash, credential.hash);
    return { ok: ok, account: account, reason: ok ? null : 'password' };
  }

  /* ------------------------------------------------------------------------
   * 13. Sign in
   * ---------------------------------------------------------------------*/

  const LOGIN_FIELDS = ['loginEmail', 'loginPassword'];
  let loginPending = false;
  let navigationPending = false;

  function validateIdentifier(value) {
    const identifier = String(value || '').trim();
    if (!identifier) {
      return { ok: false, message: 'Enter your email address or username.' };
    }
    if (identifier.indexOf('@') !== -1) {
      if (!EMAIL_PATTERN.test(identifier)) {
        return { ok: false, message: 'Enter a valid email address, for example name@example.com.' };
      }
      return { ok: true, kind: 'email', value: identifier.toLowerCase() };
    }
    if (!USERNAME_PATTERN.test(identifier)) {
      return {
        ok: false,
        message: 'Usernames use 3–32 letters, numbers, dots, dashes or underscores.'
      };
    }
    return { ok: true, kind: 'username', value: identifier.toLowerCase() };
  }

  async function handleLoginSubmit(event) {
    if (event && typeof event.preventDefault === 'function') {
      event.preventDefault();
    }
    if (loginPending) return;
    loginPending = true;

    const form = $('loginForm');
    const button = $('btnLogin');
    if (form) form.setAttribute('aria-busy', 'true');
    setButtonLoading(button, true, 'Signing in…');
    showBanner('loginErrorMsg', '', 'error');
    showBanner('loginSuccessMsg', '', 'success');

    try {
      const identifierResult = validateIdentifier($('loginEmail') ? $('loginEmail').value : '');
      const password = $('loginPassword') ? $('loginPassword').value : '';

      setFieldError('loginEmail', identifierResult.ok ? '' : identifierResult.message);
      setFieldError('loginPassword', password ? '' : 'Enter your password.');

      if (!identifierResult.ok || !password) {
        focusFirstInvalid(LOGIN_FIELDS);
        return;
      }

      const capabilities = await detectCapabilities();

      if (capabilities.login) {
        const payload = await apiRequest(AUTH_API.login, {
          body: { identifier: identifierResult.value, email: identifierResult.value, password: password }
        });
        const account = normaliseServerUser(payload);
        if (!account) {
          throw new AuthError('The authentication service returned an unexpected response.', 'protocol');
        }
        const token = payload.access_token || payload.token || payload.id_token || null;
        if (token) storeAccessToken(token);
        await completeSignIn(account, 'server');
        return;
      }

      const result = await authenticateDemoAccount(identifierResult.value, password);
      if (!result.ok) {
        if (result.reason === 'unknown') {
          showBanner(
            'loginErrorMsg',
            'No account matches “' + identifierResult.value + '” in this deployment. ' +
            'Use one of the demo profiles below, or register a new account.',
            'error'
          );
        } else if (result.reason === 'unverifiable') {
          showBanner(
            'loginErrorMsg',
            'This account cannot be verified in the current browser session. Use a demo profile below.',
            'error'
          );
        } else if (result.reason === 'unsupported') {
          showBanner(
            'loginErrorMsg',
            'This browser blocks the secure hashing API required to verify passwords. ' +
            'Use a demo profile below or open NIRA over https:// or localhost.',
            'error'
          );
        } else {
          showBanner('loginErrorMsg', 'That password is not correct. Please try again.', 'error');
          setFieldError('loginPassword', 'That password is not correct.');
          const passwordField = $('loginPassword');
          if (passwordField) {
            passwordField.focus();
            passwordField.select();
          }
        }
        return;
      }

      await completeSignIn(result.account, 'demo');
    } catch (error) {
      showBanner(
        'loginErrorMsg',
        error && error.message ? error.message : 'Sign-in failed unexpectedly. Please try again.',
        'error'
      );
    } finally {
      loginPending = false;
      if (form) form.removeAttribute('aria-busy');
      if (!navigationPending) setButtonLoading(button, false);
    }
  }

  function normaliseServerUser(payload) {
    if (!payload) return null;
    const source = payload.user || payload.profile || payload.account || payload;
    if (!source || typeof source !== 'object') return null;
    const email = source.email || source.identifier || '';
    if (!email && !source.name) return null;
    return {
      name: source.name || source.full_name || email,
      role: source.role || source.role_label || 'NIRA User',
      roleKey: source.role_key || source.roleKey || '',
      email: email,
      username: source.username || '',
      avatar: source.avatar || '',
      redirect: source.redirect || source.destination || '/'
    };
  }

  async function completeSignIn(account, mode) {
    navigationPending = true;
    const session = persistSession(
      Object.assign({}, account, { authMode: mode || 'demo' })
    );
    showBanner('loginSuccessMsg', 'Signed in as ' + session.name + '. Opening your dashboard…', 'success');
    setButtonLoading($('btnLogin'), true, 'Opening NIRA…');
    await delay(REDIRECT_DELAY_MS);
    global.location.href = session.redirect || '/';
  }

  /* ------------------------------------------------------------------------
   * 14. Sign up
   * ---------------------------------------------------------------------*/

  const SIGNUP_FIELDS = [
    'signupName', 'signupRole', 'signupEmail', 'signupCaregiver',
    'signupPassword', 'signupConfirmPassword'
  ];
  let signupPending = false;

  function validateSignup() {
    const errors = {};

    const name = $('signupName') ? $('signupName').value.trim() : '';
    if (!name) errors.signupName = 'Enter your full name.';
    else if (name.length < 2) errors.signupName = 'Enter your full name (at least 2 characters).';
    else if (name.length > 64) errors.signupName = 'Names are limited to 64 characters.';

    const role = $('signupRole') ? $('signupRole').value : '';
    if (!role) errors.signupRole = 'Choose the type of account you are creating.';

    const email = $('signupEmail') ? $('signupEmail').value.trim() : '';
    if (!email) errors.signupEmail = 'Enter your email address.';
    else if (!EMAIL_PATTERN.test(email)) errors.signupEmail = 'Enter a valid email address, for example name@example.com.';

    const contact = $('signupCaregiver') ? $('signupCaregiver').value.trim() : '';
    if (!contact) errors.signupCaregiver = 'Add an emergency contact name and phone number.';
    else if (contact.length < 3) errors.signupCaregiver = 'Add a contact name and phone number.';

    const password = $('signupPassword') ? $('signupPassword').value : '';
    const strength = evaluatePassword(password);
    if (!password) errors.signupPassword = 'Choose a password.';
    else if (strength.blockers.length) errors.signupPassword = strength.blockers[0];

    const confirm = $('signupConfirmPassword') ? $('signupConfirmPassword').value : '';
    if (!confirm) errors.signupConfirmPassword = 'Re-enter your password.';
    else if (password && confirm !== password) errors.signupConfirmPassword = 'The two passwords do not match.';

    return { errors: errors, name: name, role: role, email: email, contact: contact, password: password, confirm: confirm };
  }

  function buildSignupAccount(form, credential) {
    const caregiver = form.role === 'caregiver';
    return {
      id: randomId('usr_'),
      name: form.name,
      email: form.email.toLowerCase(),
      username: deriveUsername(form.email),
      role: caregiver ? 'Family Caregiver' : 'Resident / Senior View',
      roleKey: caregiver ? 'caregiver' : 'resident',
      avatar: caregiver ? '👨‍💼' : '👵',
      redirect: caregiver ? '/#demo/caregiverdashboard' : '/#demo/homedashboard',
      emergencyContact: form.contact,
      credential: credential,
      source: 'local',
      createdAt: new Date().toISOString(),
      verification: 'not-applicable'
    };
  }

  function deriveUsername(email) {
    const local = String(email || '').split('@')[0] || 'user';
    const cleaned = local.toLowerCase().replace(/[^a-z0-9._-]/g, '');
    const base = USERNAME_PATTERN.test(cleaned) ? cleaned : 'nira.user';
    const accounts = buildAccountRecords();
    let candidate = base;
    let counter = 1;
    while (accounts.some((account) => String(account.username).toLowerCase() === candidate)) {
      counter += 1;
      candidate = base.slice(0, 24) + counter;
    }
    return candidate;
  }

  async function handleSignupSubmit(event) {
    if (event && typeof event.preventDefault === 'function') {
      event.preventDefault();
    }
    if (signupPending) return;
    signupPending = true;

    const form = $('signupForm');
    const button = $('btnSignup');
    if (form) form.setAttribute('aria-busy', 'true');
    setButtonLoading(button, true, 'Creating account…');
    showBanner('signupErrorMsg', '', 'error');
    showBanner('signupSuccessMsg', '', 'success');

    try {
      const values = validateSignup();
      SIGNUP_FIELDS.forEach((id) => setFieldError(id, values.errors[id] || ''));

      if (Object.keys(values.errors).length) {
        focusFirstInvalid(SIGNUP_FIELDS);
        showBanner('signupErrorMsg', 'Please correct the highlighted fields to continue.', 'error');
        return;
      }

      const capabilities = await detectCapabilities();

      if (capabilities.register) {
        const payload = await apiRequest(AUTH_API.register, {
          body: {
            name: values.name,
            email: values.email,
            password: values.password,
            role: values.role,
            emergency_contact: values.contact
          }
        });
        const serverAccount = normaliseServerUser(payload);
        if (!serverAccount) {
          throw new AuthError('The authentication service returned an unexpected response.', 'protocol');
        }
        const token = payload.access_token || payload.token || payload.id_token || null;
        if (token) storeAccessToken(token);
        if (payload.verification_required === true) {
          showBanner(
            'signupSuccessMsg',
            'Account created. Check ' + values.email + ' to verify your address before signing in.',
            'success'
          );
          setButtonLoading(button, false);
          return;
        }
        showBanner('signupSuccessMsg', 'Account created. Opening your dashboard…', 'success');
        setButtonLoading(button, false);
        await delay(REDIRECT_DELAY_MS);
        const session = persistSession(Object.assign({}, serverAccount, { authMode: 'server' }));
        global.location.href = session.redirect || '/';
        return;
      }

      if (isKnownEmail(values.email)) {
        setFieldError('signupEmail', 'An account already exists for this email address.');
        showBanner('signupErrorMsg', 'An account with that email address already exists.', 'error');
        const emailField = $('signupEmail');
        if (emailField) emailField.focus();
        return;
      }

      const credential = await deriveCredential(values.password, newSalt(), PBKDF2_ITERATIONS);
      if (!credential) {
        showBanner(
          'signupSuccessMsg',
          'Account details validated. This browser blocks the secure hashing API, so the ' +
          'account is active for this session only.',
          'warning'
        );
      } else {
        const account = buildSignupAccount(values, credential);
        const persisted = upsertLocalAccount(account);
        if (!persisted) {
          showBanner(
            'signupSuccessMsg',
            'Account details validated. Browser storage is unavailable, so the account is ' +
            'active for this session only.',
            'warning'
          );
        } else {
          showBanner('signupSuccessMsg', 'Account created. Opening your dashboard…', 'success');
        }
      }

      setButtonLoading(button, false);
      await delay(REDIRECT_DELAY_MS);

      const session = persistSession({
        name: values.name,
        role: values.role === 'caregiver' ? 'Family Caregiver' : 'Resident / Senior View',
        roleKey: values.role === 'caregiver' ? 'caregiver' : 'resident',
        email: values.email.toLowerCase(),
        avatar: values.role === 'caregiver' ? '👨‍💼' : '👵',
        redirect: values.role === 'caregiver' ? '/#demo/caregiverdashboard' : '/#demo/homedashboard',
        authMode: 'demo'
      });
      global.location.href = session.redirect || '/';
    } catch (error) {
      showBanner(
        'signupErrorMsg',
        error && error.message ? error.message : 'Registration failed unexpectedly. Please try again.',
        'error'
      );
    } finally {
      signupPending = false;
      if (form) form.removeAttribute('aria-busy');
      setButtonLoading(button, false);
    }
  }

  /* ------------------------------------------------------------------------
   * 15. Demo quick sign-in (one-click profiles)
   * ---------------------------------------------------------------------*/

  let quickLoginPending = false;

  async function quickLogin(roleKey) {
    if (quickLoginPending) return;
    const persona = DEMO_PERSONAS[roleKey];
    if (!persona) return;
    quickLoginPending = true;
    const button = document.querySelector('[data-demo-role="' + roleKey + '"]');
    showBanner('loginErrorMsg', '', 'error');
    try {
      setButtonLoading(button, true, 'Opening…');
      await delay(360);
      const record = personaRecord(roleKey);
      const session = persistSession(Object.assign({}, record, { authMode: 'demo' }));
      await delay(REDIRECT_DELAY_MS);
      global.location.href = session.redirect || '/';
    } catch (error) {
      showBanner(
        'loginErrorMsg',
        error && error.message ? error.message : 'Could not open the demo profile. Please try again.',
        'error'
      );
      setButtonLoading(button, false);
    } finally {
      quickLoginPending = false;
    }
  }

  /* ------------------------------------------------------------------------
   * 16. Password recovery
   * ---------------------------------------------------------------------*/

  let recoveryPending = false;
  let recoveryIntent = 'request';

  function openRecovery() {
    const backdrop = $('authRecoveryBackdrop');
    if (!backdrop) return;
    backdrop.hidden = false;
    backdrop.classList.add('is-open');
    setFieldError('recoveryEmail', '');
    showBanner('recoveryStatusMsg', '', 'error');
    const emailField = $('recoveryEmail');
    if (emailField) {
      emailField.value = $('loginEmail') ? $('loginEmail').value.trim() : '';
      global.setTimeout(() => emailField.focus(), 40);
    }
  }

  function closeRecovery() {
    const backdrop = $('authRecoveryBackdrop');
    if (!backdrop) return;
    backdrop.hidden = true;
    backdrop.classList.remove('is-open');
    const resetBlock = $('recoveryResetBlock');
    if (resetBlock) resetBlock.hidden = true;
  }

  async function handleRecoverySubmit(event) {
    if (event && typeof event.preventDefault === 'function') {
      event.preventDefault();
    }
    const submitter = event && event.submitter ? event.submitter : null;
    const intent = submitter && submitter.id === 'btnRecoveryReset'
      ? 'reset'
      : (submitter && submitter.id === 'btnRecoverySubmit' ? 'request' : recoveryIntent);
    if (intent === 'reset') {
      await handleRecoveryReset(event);
      return;
    }
    if (recoveryPending) return;
    recoveryPending = true;
    const button = $('btnRecoverySubmit');
    setButtonLoading(button, true, 'Checking…');

    try {
      const email = $('recoveryEmail') ? $('recoveryEmail').value.trim() : '';
      if (!email) {
        setFieldError('recoveryEmail', 'Enter the email address on your account.');
        if ($('recoveryEmail')) $('recoveryEmail').focus();
        return;
      }
      if (!EMAIL_PATTERN.test(email)) {
        setFieldError('recoveryEmail', 'Enter a valid email address, for example name@example.com.');
        if ($('recoveryEmail')) $('recoveryEmail').focus();
        return;
      }
      setFieldError('recoveryEmail', '');

      const capabilities = await detectCapabilities();
      if (capabilities.recovery) {
        await apiRequest(AUTH_API.recovery, { body: { email: email.toLowerCase() } });
        showBanner(
          'recoveryStatusMsg',
          'If an account exists for ' + email + ', a password reset link has been sent.',
          'success'
        );
        return;
      }

      const account = findAccount(email);
      if (!account) {
        showBanner(
          'recoveryStatusMsg',
          'No account matches ' + email + ' in this browser. Use a demo profile, or register a new account.',
          'error'
        );
        return;
      }

      const resetBlock = $('recoveryResetBlock');
      if (resetBlock) resetBlock.hidden = false;
      setButtonLoading(button, false);
      showBanner(
        'recoveryStatusMsg',
        'Choose a new password for ' + email + '. This demo stores the change in this browser only.',
        'warning'
      );
      const newPassword = $('recoveryNewPassword');
      if (newPassword) global.setTimeout(() => newPassword.focus(), 40);
    } catch (error) {
      showBanner(
        'recoveryStatusMsg',
        error && error.message ? error.message : 'Password recovery is unavailable right now.',
        'error'
      );
    } finally {
      setButtonLoading(button, false);
      recoveryPending = false;
    }
  }

  async function handleRecoveryReset(event) {
    if (event && typeof event.preventDefault === 'function') {
      event.preventDefault();
    }
    if (recoveryPending) return;
    recoveryPending = true;
    const button = $('btnRecoveryReset');
    setButtonLoading(button, true, 'Updating…');

    try {
      const email = $('recoveryEmail') ? $('recoveryEmail').value.trim().toLowerCase() : '';
      const password = $('recoveryNewPassword') ? $('recoveryNewPassword').value : '';
      const confirm = $('recoveryConfirmPassword') ? $('recoveryConfirmPassword').value : '';
      const strength = evaluatePassword(password);

      setFieldError('recoveryNewPassword', '');
      setFieldError('recoveryConfirmPassword', '');

      if (!password) {
        setFieldError('recoveryNewPassword', 'Choose a new password.');
        return;
      }
      if (strength.blockers.length) {
        setFieldError('recoveryNewPassword', strength.blockers[0]);
        return;
      }
      if (confirm !== password) {
        setFieldError('recoveryConfirmPassword', 'The two passwords do not match.');
        return;
      }

      const account = findAccount(email);
      if (!account) {
        showBanner('recoveryStatusMsg', 'No account matches ' + email + ' in this browser.', 'error');
        return;
      }

      const credential = await deriveCredential(password, newSalt(), PBKDF2_ITERATIONS);
      if (!credential) {
        showBanner(
          'recoveryStatusMsg',
          'This browser blocks the secure hashing API, so the password cannot be updated here.',
          'error'
        );
        return;
      }

      const updated = Object.assign({}, account, {
        credential: credential,
        source: account.source === 'demo' ? 'demo' : 'local',
        passwordUpdatedAt: new Date().toISOString()
      });
      upsertLocalAccount(updated);
      showBanner(
        'recoveryStatusMsg',
        'Password updated. You can now sign in with your new password.',
        'success'
      );
      const resetBlock = $('recoveryResetBlock');
      if (resetBlock) resetBlock.hidden = true;
      const newPassword = $('recoveryNewPassword');
      const confirmField = $('recoveryConfirmPassword');
      if (newPassword) newPassword.value = '';
      if (confirmField) confirmField.value = '';
      const loginPassword = $('loginPassword');
      if (loginPassword) loginPassword.focus();
    } catch (error) {
      showBanner(
        'recoveryStatusMsg',
        error && error.message ? error.message : 'The password could not be updated.',
        'error'
      );
    } finally {
      setButtonLoading(button, false);
      recoveryPending = false;
    }
  }

  /* ------------------------------------------------------------------------
   * 17. Tabs, mode banner and wiring
   * ---------------------------------------------------------------------*/

  function switchAuthTab(mode) {
    const signIn = mode !== 'signup';
    const tabIn = $('tabBtnSignIn');
    const tabUp = $('tabBtnSignUp');
    const panelIn = $('panelSignIn');
    const panelUp = $('panelSignUp');

    if (tabIn && tabUp) {
      tabIn.classList.toggle('active', signIn);
      tabUp.classList.toggle('active', !signIn);
      tabIn.setAttribute('aria-selected', signIn ? 'true' : 'false');
      tabUp.setAttribute('aria-selected', signIn ? 'false' : 'true');
      tabIn.setAttribute('tabindex', signIn ? '0' : '-1');
      tabUp.setAttribute('tabindex', signIn ? '-1' : '0');
    }
    if (panelIn) {
      panelIn.style.display = signIn ? 'block' : 'none';
      panelIn.setAttribute('aria-hidden', signIn ? 'false' : 'true');
    }
    if (panelUp) {
      panelUp.style.display = signIn ? 'none' : 'block';
      panelUp.setAttribute('aria-hidden', signIn ? 'true' : 'false');
    }

    const focusTarget = signIn ? $('loginEmail') : $('signupName');
    if (focusTarget) {
      global.setTimeout(() => focusTarget.focus({ preventScroll: true }), 0);
    }
  }

  function updateModeBanner(capabilities) {
    const banner = $('authModeBanner');
    if (!banner) return;
    const text = $('authModeBannerText');
    if (capabilities.login || capabilities.register || capabilities.recovery) {
      banner.setAttribute('data-mode', 'server');
      if (text) {
        text.textContent =
          'Connected to the NIRA authentication service. Credentials are verified by the server.';
      }
    } else {
      banner.setAttribute('data-mode', 'demo');
      if (text) {
        text.textContent =
          'Demo environment — this deployment has no production identity provider. ' +
          'Demo accounts and sessions stay in this browser.';
      }
    }
  }

  function bindEvents() {
    // Live validation feedback ---------------------------------------------
    const loginEmail = $('loginEmail');
    if (loginEmail) {
      loginEmail.addEventListener('blur', () => {
        if (!loginEmail.value.trim()) return;
        const result = validateIdentifier(loginEmail.value);
        setFieldError('loginEmail', result.ok ? '' : result.message);
      });
      loginEmail.addEventListener('input', () => {
        if (loginEmail.getAttribute('aria-invalid') === 'true') {
          const result = validateIdentifier(loginEmail.value);
          if (result.ok) setFieldError('loginEmail', '');
        }
      });
    }

    const loginPassword = $('loginPassword');
    if (loginPassword) {
      loginPassword.addEventListener('input', () => {
        if (loginPassword.getAttribute('aria-invalid') === 'true' && loginPassword.value) {
          setFieldError('loginPassword', '');
        }
      });
    }

    const signupPassword = $('signupPassword');
    if (signupPassword) {
      signupPassword.addEventListener('input', () => {
        renderStrength('signupStrengthMeter', 'signupStrengthLabel', signupPassword.value);
        renderPolicyList('signupPolicyList', signupPassword.value);
        if (signupPassword.getAttribute('aria-invalid') === 'true') {
          const strength = evaluatePassword(signupPassword.value);
          if (strength.valid) setFieldError('signupPassword', '');
        }
      });
      signupPassword.addEventListener('blur', () => {
        if (!signupPassword.value) return;
        const strength = evaluatePassword(signupPassword.value);
        setFieldError('signupPassword', strength.valid ? '' : strength.blockers[0]);
      });
    }

    const signupConfirm = $('signupConfirmPassword');
    if (signupConfirm) {
      signupConfirm.addEventListener('input', () => {
        const password = signupPassword ? signupPassword.value : '';
        setFieldError(
          'signupConfirmPassword',
          signupConfirm.value && signupConfirm.value === password ? '' : (
            signupConfirm.value ? 'The two passwords do not match.' : ''
          )
        );
      });
    }

    const signupEmail = $('signupEmail');
    if (signupEmail) {
      signupEmail.addEventListener('blur', () => {
        const value = signupEmail.value.trim();
        if (!value) return;
        setFieldError(
          'signupEmail',
          EMAIL_PATTERN.test(value) ? '' : 'Enter a valid email address, for example name@example.com.'
        );
      });
    }

    // Password visibility toggles ------------------------------------------
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-password-toggle]'),
      (toggle) => {
        toggle.addEventListener('click', (event) => {
          event.preventDefault();
          togglePassword(toggle.getAttribute('data-password-toggle'));
        });
      }
    );

    // Tab keyboard navigation ----------------------------------------------
    const tabList = document.querySelector('[role="tablist"]');
    if (tabList) {
      tabList.addEventListener('keydown', (event) => {
        const key = event.key;
        if (key !== 'ArrowRight' && key !== 'ArrowLeft' && key !== 'Home' && key !== 'End') return;
        event.preventDefault();
        const signInActive = $('tabBtnSignIn').classList.contains('active');
        let next = null;
        if (key === 'Home') next = 'signin';
        else if (key === 'End') next = 'signup';
        else next = signInActive ? 'signup' : 'signin';
        switchAuthTab(next);
        const target = next === 'signup' ? $('tabBtnSignUp') : $('tabBtnSignIn');
        if (target) target.focus();
      });
    }

    // Recovery dialog -------------------------------------------------------
    const openButton = $('btnForgotPassword');
    if (openButton) {
      openButton.addEventListener('click', (event) => {
        event.preventDefault();
        openRecovery();
      });
    }
    const closeButton = $('btnRecoveryClose');
    if (closeButton) {
      closeButton.addEventListener('click', (event) => {
        event.preventDefault();
        closeRecovery();
      });
    }
    const backdrop = $('authRecoveryBackdrop');
    if (backdrop) {
      backdrop.addEventListener('click', (event) => {
        if (event.target === backdrop) closeRecovery();
      });
    }
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && backdrop && !backdrop.hidden) {
        closeRecovery();
        const opener = $('btnForgotPassword');
        if (opener) opener.focus();
      }
    });

    const recoveryForm = $('recoveryForm');
    if (recoveryForm) {
      recoveryForm.addEventListener('submit', handleRecoverySubmit);
    }
    const resetTrigger = $('btnRecoveryReset');
    if (resetTrigger) {
      resetTrigger.addEventListener('click', () => { recoveryIntent = 'reset'; });
    }
    const requestTrigger = $('btnRecoverySubmit');
    if (requestTrigger) {
      requestTrigger.addEventListener('click', () => { recoveryIntent = 'request'; });
    }
    const recoveryNewPassword = $('recoveryNewPassword');
    if (recoveryNewPassword) {
      recoveryNewPassword.addEventListener('input', () => {
        renderStrength('recoveryStrengthMeter', 'recoveryStrengthLabel', recoveryNewPassword.value);
      });
    }
  }

  function init() {
    bindEvents();
    renderStrength('signupStrengthMeter', 'signupStrengthLabel', '');
    renderPolicyList('signupPolicyList', '');
    detectCapabilities().then(updateModeBanner);
  }

  /* ------------------------------------------------------------------------
   * 18. Public API (keeps the previous page's global contract intact)
   * ---------------------------------------------------------------------*/

  global.DEMO_PERSONAS = DEMO_PERSONAS;
  global.NiraAuth = {
    version: '2.0.0',
    capabilities: detectCapabilities,
    evaluatePassword: evaluatePassword,
    validateIdentifier: validateIdentifier,
    togglePassword: togglePassword,
    switchAuthTab: switchAuthTab,
    quickLogin: quickLogin,
    handleLoginSubmit: handleLoginSubmit,
    handleSignupSubmit: handleSignupSubmit,
    openRecovery: openRecovery,
    closeRecovery: closeRecovery,
    handleRecoverySubmit: handleRecoverySubmit,
    handleRecoveryReset: handleRecoveryReset
  };

  // Legacy entry points kept so the existing markup keeps working unchanged.
  global.switchAuthTab = switchAuthTab;
  global.togglePassword = togglePassword;
  global.quickLogin = quickLogin;
  global.handleLoginSubmit = handleLoginSubmit;
  global.handleSignupSubmit = handleSignupSubmit;
  global.submitUserSession = function submitUserSession(userObj) {
    const session = persistSession(userObj || {});
    global.setTimeout(() => {
      global.location.href = session.redirect || '/';
    }, 350);
    return session;
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}(window));
