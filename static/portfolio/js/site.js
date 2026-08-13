/* Portfolio — site behaviour.
   Everything here is progressive enhancement: with JS off the page is still
   fully readable and navigable. */
(function () {
    'use strict';

    var root = document.documentElement;

    /* ---------- Theme ---------- */
    var toggle = document.getElementById('theme-toggle');
    var icon = document.getElementById('theme-icon');

    function paintTheme(theme) {
        root.setAttribute('data-bs-theme', theme);
        if (icon) icon.setAttribute('href', theme === 'dark' ? '#i-moon' : '#i-sun');
        if (toggle) {
            var next = theme === 'dark' ? '라이트' : '다크';
            toggle.setAttribute('aria-label', next + ' 모드로 전환');
            toggle.setAttribute('title', next + ' 모드로 전환');
        }
    }

    paintTheme(root.getAttribute('data-bs-theme') || 'light');

    if (toggle) {
        toggle.addEventListener('click', function () {
            var next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
            try { localStorage.setItem('theme', next); } catch (e) { }
            paintTheme(next);
        });
    }

    /* ---------- Mobile nav ---------- */
    var navToggle = document.getElementById('nav-toggle');
    var nav = document.getElementById('site-nav');
    var navIcon = document.getElementById('nav-icon');

    function setNav(open) {
        if (!nav || !navToggle) return;
        nav.classList.toggle('is-open', open);
        navToggle.setAttribute('aria-expanded', String(open));
        navToggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
        if (navIcon) navIcon.setAttribute('href', open ? '#i-close' : '#i-menu');
    }

    if (navToggle && nav) {
        navToggle.addEventListener('click', function () {
            setNav(!nav.classList.contains('is-open'));
        });
        nav.addEventListener('click', function (e) {
            if (e.target.tagName === 'A') setNav(false);
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && nav.classList.contains('is-open')) {
                setNav(false);
                navToggle.focus();
            }
        });
    }

    /* ---------- Back to top ---------- */
    var topBtn = document.getElementById('to-top');
    if (topBtn) {
        var onScroll = function () {
            topBtn.classList.toggle('is-on', window.scrollY > 600);
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
        topBtn.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
            var first = document.querySelector('.skip-link');
            if (first) first.focus({ preventScroll: true });
        });
    }

    /* ---------- Reveal on scroll ----------
       `js-anim` is only on <html> when motion is allowed, so content is never
       hidden from reduced-motion users, crawlers, print, or a JS failure.
       A plain scroll check (rather than IntersectionObserver) is used on
       purpose: it is idempotent and cannot strand an element at opacity 0. */
    if (root.classList.contains('js-anim')) {
        // head 의 안전장치를 해제하고 여기서 책임집니다.
        clearTimeout(window.__revealFailsafe);

        var pending = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
        var revealTick = false;

        var sweep = function () {
            revealTick = false;
            var limit = window.innerHeight * 0.94;
            pending = pending.filter(function (el) {
                if (el.getBoundingClientRect().top < limit) {
                    el.classList.add('is-in');
                    return false;
                }
                return true;
            });
            if (!pending.length) window.removeEventListener('scroll', onScrollReveal);
        };

        var onScrollReveal = function () {
            if (!revealTick) { revealTick = true; requestAnimationFrame(sweep); }
        };

        window.addEventListener('scroll', onScrollReveal, { passive: true });
        window.addEventListener('resize', onScrollReveal, { passive: true });
        sweep();

        /* Last-resort net: never leave anything invisible for long. */
        setTimeout(function () {
            pending.forEach(function (el) { el.classList.add('is-in'); });
        }, 2500);
    }

    /* ---------- Section highlighting in the header nav ---------- */
    var navLinks = Array.prototype.slice.call(
        document.querySelectorAll('.site-nav a[href*="#"]')
    );
    var sections = navLinks
        .map(function (a) {
            var id = a.getAttribute('href').split('#')[1];
            var el = id && document.getElementById(id);
            return el ? { link: a, el: el } : null;
        })
        .filter(Boolean);

    if (sections.length) {
        var spyTick = false;
        var spy = function () {
            spyTick = false;
            var line = window.scrollY + window.innerHeight * 0.32;
            var current = null;
            sections.forEach(function (s) {
                if (s.el.offsetTop <= line) current = s;
            });
            /* Above the first section (hero) nothing is current. */
            if (window.scrollY < 120) current = null;
            sections.forEach(function (s) {
                if (s === current) {
                    s.link.setAttribute('aria-current', 'true');
                } else {
                    s.link.removeAttribute('aria-current');
                }
            });
        };
        window.addEventListener('scroll', function () {
            if (!spyTick) { spyTick = true; requestAnimationFrame(spy); }
        }, { passive: true });
        spy();
    }

    /* ---------- Project progressive disclosure ----------
       No filtering any more (that lives on each skill's own page) — this
       just keeps a long project list from dumping everything at once. */
    var list = document.getElementById('project-list');
    if (list) {
        var cards = Array.prototype.slice.call(list.children);
        var moreBtn = document.getElementById('project-more');
        var STEP = 6;
        var shown = STEP;

        function render() {
            cards.forEach(function (c, i) { c.hidden = i >= shown; });
            if (moreBtn) {
                var rest = cards.length - shown;
                moreBtn.hidden = rest <= 0;
                moreBtn.textContent = '프로젝트 ' + Math.max(rest, 0) + '개 더 보기';
            }
        }

        if (moreBtn) {
            moreBtn.addEventListener('click', function () {
                var firstNew = cards[shown];
                shown += STEP;
                render();
                if (firstNew) {
                    var link = firstNew.querySelector('a');
                    if (link) link.focus({ preventScroll: true });
                }
            });
        }

        render();
    }
})();
