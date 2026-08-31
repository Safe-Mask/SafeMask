/* ============================================================
   SafeMask Brand System — micro-interactions
   Leve, sem dependencias. Carregar depois do config.js.
   ============================================================ */
(function () {
    'use strict';

    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* Failsafe: marca o html com "js" para o CSS poder ocultar os .reveal
       apenas quando o JS estiver ativo. Evita tela em branco. */
    document.documentElement.classList.add('js');

    /* ---------- 1) Scroll reveal com cascade ---------- */
    function initReveal() {
        var items = document.querySelectorAll('.reveal');
        if (!items.length) return;

        if (reduced) {
            items.forEach(function (el) { el.classList.add('in'); });
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

        items.forEach(function (el, i) {
            el.style.transitionDelay = ((i % 8) * 55) + 'ms';
            observer.observe(el);
        });
    }

    /* ---------- 2) Contadores animados (count up) ---------- */
    function animateCount(el, target, suffix) {
        var duration = 950;
        var start = performance.now();

        function frame(now) {
            var t = Math.min(1, (now - start) / duration);
            var eased = 1 - Math.pow(1 - t, 3);
            var value = Math.round(eased * target);
            el.textContent = (suffix == null ? value : value + suffix);
            if (t < 1) requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
    }

    function initCounters() {
        var holders = document.querySelectorAll('[data-count]');
        if (!holders.length) return;

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                var el = entry.target;
                var raw = el.getAttribute('data-count');
                var target = parseInt(raw, 10);
                var suffix = el.getAttribute('data-suffix') || '';
                if (Number.isFinite(target)) {
                    if (reduced) {
                        el.textContent = target + suffix;
                    } else {
                        animateCount(el, target, suffix);
                    }
                }
                observer.unobserve(el);
            });
        }, { threshold: 0.5 });

        holders.forEach(function (el) {
            observer.observe(el);
        });
    }

    /* ---------- 3) Escurecer/limpar o menu lateral em mobile ---------- */
    function initSidebarGuard() {
        var sidebar = document.getElementById('sidebar');
        var toggle = document.getElementById('menuToggle');
        if (!sidebar) return;

        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 860 && sidebar.classList.contains('open')) {
                if (!sidebar.contains(e.target) && !(toggle && toggle.contains(e.target))) {
                    sidebar.classList.remove('open');
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initReveal();
        initCounters();
        initSidebarGuard();
    });
})();
