/* Bhuarjan Website – frontend interactions */
document.addEventListener('DOMContentLoaded', function () {

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Animate stats counter
    function animateCounter(el) {
        var target = parseInt(el.getAttribute('data-count'), 10);
        var duration = 1500;
        var step = target / (duration / 16);
        var current = 0;
        var timer = setInterval(function () {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = Math.floor(current).toLocaleString('en-IN') + (el.getAttribute('data-suffix') || '');
        }, 16);
    }

    var counters = document.querySelectorAll('[data-count]');
    if (counters.length) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        counters.forEach(function (c) { observer.observe(c); });
    }

    // Navbar scroll state
    var navbar = document.querySelector('.bhu-navbar');
    if (navbar) {
        var setScrolled = function () {
            if (window.scrollY > 8) navbar.classList.add('scrolled');
            else navbar.classList.remove('scrolled');
        };
        setScrolled();
        window.addEventListener('scroll', setScrolled, { passive: true });
    }

    // Forcefully remove "Skip to Content" if it exists
    var skip = document.querySelector('.o_skip_to_content, a[href="#wrap"]');
    if (skip && skip.parentNode) skip.parentNode.removeChild(skip);
});
