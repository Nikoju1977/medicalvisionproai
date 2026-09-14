// Lightweight Node host for integration tests. Real app JS, WebCrypto, image
// decoding and Canvas run here; this is not a browser/layout conformance test.
const fs = require('node:fs');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const { File } = require('node:buffer');
const canvas = require('@napi-rs/canvas');

function runtime(file = 'index.html') {
    const errors = [], timers = new Set();
    const html = fs.readFileSync(file, 'utf8');
    class Element {
        constructor(tag) {
            this.tagName = tag.toUpperCase(); this.children = []; this.attributes = {};
            this.style = {}; this.value = ''; this.checked = false; this.disabled = false;
            this.hidden = false; this.listeners = {}; this._text = ''; this._html = '';
            if (tag === 'canvas') this._canvas = canvas.createCanvas(300, 150);
        }
        get className() { return this.attributes.class || ''; }
        set className(value) { this.attributes.class = value; }
        get classList() {
            const el = this;
            return {
                contains(x) { return el.className.split(/\s+/).includes(x); },
                add(...xs) { el.className = [...new Set([...el.className.split(/\s+/).filter(Boolean), ...xs])].join(' '); },
                remove(...xs) { el.className = el.className.split(/\s+/).filter(x => !xs.includes(x)).join(' '); },
                toggle(x, force) { const add = force == null ? !this.contains(x) : force; add ? this.add(x) : this.remove(x); return add; }
            };
        }
        setAttribute(k, v) { this.attributes[k] = String(v); if (k === 'value') this.value = String(v); if (k === 'checked') this.checked = true; }
        getAttribute(k) { return this.attributes[k] ?? null; }
        removeAttribute(k) { delete this.attributes[k]; }
        get id() { return this.attributes.id; } set id(v) { this.attributes.id = v; }
        get textContent() { return this._text + this.children.map(c => c.textContent).join(''); }
        set textContent(v) { this._text = String(v); this._html = String(v); this.children = []; }
        get innerHTML() { return this._html; }
        set innerHTML(v) { this._html = String(v); this._text = ''; this.children = []; parse(String(v), this); }
        appendChild(child) { this.children.push(child); child.parentNode = this; return child; }
        removeChild(child) { this.children.splice(this.children.indexOf(child), 1); child.parentNode = null; }
        get lastChild() { return this.children.at(-1); }
        get options() { return descendants(this).filter(e => e.tagName === 'OPTION'); }
        get width() { return this._canvas ? this._canvas.width : 600; }
        set width(v) { if (this._canvas) this._canvas.width = v; }
        get height() { return this._canvas ? this._canvas.height : 600; }
        set height(v) { if (this._canvas) this._canvas.height = v; }
        get clientWidth() { return this.tagName === 'CANVAS' ? this.width : 800; }
        get clientHeight() { return this.tagName === 'CANVAS' ? this.height : 400; }
        getBoundingClientRect() { return { x: 0, y: 0, left: 0, top: 0, width: this.clientWidth, height: this.clientHeight }; }
        getContext(type) {
            const ctx = this._canvas.getContext(type);
            return new Proxy(ctx, {
                get(target, key) {
                    if (key === 'drawImage') return (source, ...args) => target.drawImage(source._canvas || source, ...args);
                    const value = Reflect.get(target, key, target);
                    return typeof value === 'function' ? value.bind(target) : value;
                },
                set(target, key, value) { Reflect.set(target, key, value, target); return true; }
            });
        }
        toDataURL(...args) { return this._canvas.toDataURL(...args); }
        addEventListener(type, cb) { (this.listeners[type] ||= []).push(cb); }
        removeEventListener(type, cb) { this.listeners[type] = (this.listeners[type] || []).filter(x => x !== cb); }
        dispatchEvent(event) { event.target = this; for (const fn of this.listeners[event.type] || []) fn.call(this, event); }
        click() { this.onclick?.({ target: this, stopPropagation() {} }); this.dispatchEvent({ type: 'click' }); }
        querySelectorAll(selector) { return descendants(this).filter(e => matches(e, selector)); }
        querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
        scrollIntoView() {} focus() {}
    }
    function descendants(el) { return el.children.flatMap(c => [c, ...descendants(c)]); }
    function matches(el, selector) {
        const parts = selector.trim().split(/\s+(?![^\[]*\])/);
        const last = parts.pop();
        const attrs = [...last.matchAll(/\[([^=\]]+)(?:=["']?([^"'\]]+)["']?)?\]/g)];
        if (attrs.some(m => m[2] == null ? el.getAttribute(m[1]) == null : el.getAttribute(m[1]) !== m[2])) return false;
        const base = last.replace(/\[[^\]]+\]/g, '');
        const id = base.match(/#([\w-]+)/); if (id && el.id !== id[1]) return false;
        if ([...base.matchAll(/\.([\w-]+)/g)].some(m => !el.classList.contains(m[1]))) return false;
        const tag = base.match(/^[a-z][\w-]*/i); if (tag && el.tagName !== tag[0].toUpperCase()) return false;
        if (parts.length) { let parent = el.parentNode; while (parent) { if (matches(parent, parts.join(' '))) return true; parent = parent.parentNode; } return false; }
        return true;
    }
    function parse(source, root) {
        const stack = [root];
        source = source.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '').replace(/<!--[\s\S]*?-->/g, '');
        for (const m of source.matchAll(/<\/?([a-z][\w-]*)([^>]*)>|([^<]+)/gi)) {
            if (m[3]) { stack.at(-1)._text += m[3]; continue; }
            const tag = m[1].toLowerCase();
            if (m[0].startsWith('</')) { while (stack.length > 1) { if (stack.pop().tagName === tag.toUpperCase()) break; } continue; }
            const el = new Element(tag);
            for (const a of m[2].matchAll(/([\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)) el.setAttribute(a[1], a[2] ?? a[3] ?? a[4] ?? '');
            el.checked = 'checked' in el.attributes; el.hidden = 'hidden' in el.attributes;
            stack.at(-1).appendChild(el);
            if (!['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'wbr'].includes(tag)) stack.push(el);
        }
        for (const el of descendants(root).filter(e => e.tagName === 'SELECT')) {
            const option = el.options.find(o => 'selected' in o.attributes) || el.options[0];
            if (option) el.value = option.getAttribute('value') ?? option.textContent;
        }
    }
    const document = new Element('document'); parse(html, document);
    document.readyState = 'loading'; document.hidden = false;
    document.documentElement = document.querySelector('html');
    document.getElementById = id => descendants(document).find(e => e.id === id) || null;
    document.createElement = tag => new Element(tag);
    const stored = new Map();
    const localStorage = { getItem: k => stored.get(k) ?? null, setItem: (k, v) => stored.set(k, String(v)), removeItem: k => stored.delete(k), clear: () => stored.clear() };
    const window = {
        document, localStorage, console: { ...console, error: (...args) => errors.push(args.join(' ')) },
        location: { protocol: 'https:', hostname: 'nikoju1977.github.io', origin: 'https://nikoju1977.github.io', reload() {} },
        navigator: { language: 'fr-FR', languages: ['fr-FR'], userAgent: 'MedVision test host', onLine: true },
        devicePixelRatio: 1, crypto: webcrypto, TextEncoder, TextDecoder,
        AbortController, URL, Blob, File, Image: canvas.Image,
        Uint8Array, Uint32Array, Uint8ClampedArray, Float32Array, Float64Array,
        btoa: x => Buffer.from(x, 'binary').toString('base64'), atob: x => Buffer.from(x, 'base64').toString('binary'),
        setTimeout(fn, ms, ...args) { const id = setTimeout(() => { timers.delete(id); try { fn(...args); } catch(e) { errors.push(e.stack); } }, ms); timers.add(id); return id; },
        clearTimeout(id) { clearTimeout(id); timers.delete(id); },
        requestAnimationFrame: fn => setTimeout(fn, 0),
        addEventListener() {}, prompt() { return null; }, confirm() { return false; },
        getComputedStyle: () => ({ getPropertyValue: () => '0' })
    };
    window.FileReader = class {
        async readAsDataURL(file) { try { const result = 'data:' + file.type + ';base64,' + Buffer.from(await file.arrayBuffer()).toString('base64'); this.onload?.({ target: { result } }); } catch (error) { this.onerror?.(error); } }
    };
    window.window = window;
    const context = vm.createContext(window);
    const exposed = ['S','VAULT','RL','PP','init','hFile','mkItem','setActive','delItem','stashAnn','finish','normalizeEndpoint','visionModels','mchat','mcall','discoverModels','prepareModels','retryDelay','buildImageChunks','renderGeneral','renderReport','setBusy'];
    for (const script of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
        let code = script[1];
        if (code.includes('const S =')) code = code.replace(/\}\)\(\);\s*$/, 'window.__test = {' + exposed.join(',') + '};\n})();');
        vm.runInContext(code, context, { filename: file });
    }
    window.__test.init();
    return { w: window, api: window.__test, errors, canvas, close() { for (const id of timers) clearTimeout(id); } };
}
module.exports = { runtime };
