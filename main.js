document.addEventListener('DOMContentLoaded', () => {
    // 1. Scroll Reveal Animation Setup
    const revealElements = document.querySelectorAll('[data-reveal]');
    
    const revealOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };

    const revealOnScroll = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Determine if there's a custom delay
                const delay = entry.target.getAttribute('data-reveal-delay');
                if (delay) {
                    entry.target.style.transitionDelay = `${delay}ms`;
                }
                entry.target.classList.add('is-revealed');
                observer.unobserve(entry.target);
            }
        });
    }, revealOptions);

    revealElements.forEach(el => revealOnScroll.observe(el));

    // 2. Parallax Effect
    const parallaxElements = document.querySelectorAll('.parallax-bg');
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        parallaxElements.forEach(el => {
            const speed = el.dataset.speed || 0.4;
            // Apply a subtle Y translation based on scroll position
            el.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });

    // 3. Navbar Scroll Effect
    const nav = document.querySelector('nav');
    if (nav) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                nav.classList.add('nav-scrolled');
            } else {
                nav.classList.remove('nav-scrolled');
            }
        });
    }

    // 4. Interactive Draggable Sliders
    const sliders = document.querySelectorAll('.no-scrollbar');
    sliders.forEach(slider => {
        let isDown = false;
        let startX;
        let scrollLeft;

        slider.addEventListener('mousedown', (e) => {
            isDown = true;
            slider.style.cursor = 'grabbing';
            startX = e.pageX - slider.offsetLeft;
            scrollLeft = slider.scrollLeft;
        });
        
        slider.addEventListener('mouseleave', () => {
            isDown = false;
            slider.style.cursor = 'grab';
        });
        
        slider.addEventListener('mouseup', () => {
            isDown = false;
            slider.style.cursor = 'grab';
        });
        
        slider.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - slider.offsetLeft;
            const walk = (x - startX) * 2; // Scroll sensitivity
            slider.scrollLeft = scrollLeft - walk;
        });
        
        // Initial cursor state
        slider.style.cursor = 'grab';
    });

    // 5. Mobile Menu Initialization
    const initMobileMenu = () => {
        const navContainer = document.querySelector('nav > div');
        if (!navContainer) return;

        // Create Hamburger Button
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'md:hidden text-primary hover:text-secondary transition-colors z-[60] relative ml-4';
        toggleBtn.innerHTML = '<span class="material-symbols-outlined text-3xl">menu</span>';
        
        // Hide Book Now on mobile, place hamburger
        const bookBtn = navContainer.querySelector('button');
        if (bookBtn) {
            bookBtn.classList.add('hidden', 'md:block');
            navContainer.appendChild(toggleBtn);
        } else {
            navContainer.appendChild(toggleBtn);
        }

        // Create Menu Overlay
        const menuOverlay = document.createElement('div');
        menuOverlay.className = 'fixed inset-0 bg-surface/98 dark:bg-slate-900/98 backdrop-blur-2xl z-50 transform translate-x-full transition-transform duration-700 ease-[cubic-bezier(0.2,0,0.2,1)] flex flex-col justify-center items-center';
        
        // Grab existing desktop links to populate mobile menu
        const desktopMenu = navContainer.querySelector('.hidden.md\\:flex');
        let linksHTML = '';
        if (desktopMenu) {
            const links = desktopMenu.querySelectorAll('a');
            links.forEach((link, index) => {
                const delay = 100 + (index * 50);
                linksHTML += `<a href="${link.href}" class="mobile-link opacity-0 translate-y-4 transition-all duration-500 font-headline text-3xl md:text-5xl mb-6 text-on-surface hover:text-secondary hover:italic" style="transition-delay: ${delay}ms">${link.textContent}</a>`;
            });
        }
        
        menuOverlay.innerHTML = `
            <div class="flex flex-col items-center w-full px-6 text-center">
                <span class="font-label text-xs tracking-[0.3em] uppercase text-secondary mb-12 block mobile-link opacity-0 translate-y-4 transition-all duration-500">Navigation</span>
                ${linksHTML}
                <button class="mt-12 bg-primary text-on-primary px-12 py-4 rounded-full font-label text-sm tracking-widest uppercase hover:bg-on-primary-container transition-all w-full max-w-xs shadow-xl mobile-link opacity-0 translate-y-4 duration-500" style="transition-delay: 500ms">Book Now</button>
            </div>
        `;
        
        document.body.appendChild(menuOverlay);

        let menuOpen = false;
        const mobileLinks = menuOverlay.querySelectorAll('.mobile-link');

        toggleBtn.addEventListener('click', () => {
            menuOpen = !menuOpen;
            if (menuOpen) {
                menuOverlay.classList.remove('translate-x-full');
                toggleBtn.innerHTML = '<span class="material-symbols-outlined text-3xl">close</span>';
                document.body.style.overflow = 'hidden'; 
                // Reveal links
                setTimeout(() => {
                    mobileLinks.forEach(link => {
                        link.classList.remove('opacity-0', 'translate-y-4');
                    });
                }, 100);
            } else {
                menuOverlay.classList.add('translate-x-full');
                toggleBtn.innerHTML = '<span class="material-symbols-outlined text-3xl">menu</span>';
                document.body.style.overflow = '';
                // Hide links
                mobileLinks.forEach(link => {
                    link.classList.add('opacity-0', 'translate-y-4');
                });
            }
        });
    };
    initMobileMenu();

    // 6. Input Hover/Focus Interactions for Contact Form
    const inputFields = document.querySelectorAll('input, select, textarea');
    inputFields.forEach(input => {
        input.addEventListener('focus', () => {
            const label = input.previousElementSibling;
            if (label && label.tagName === 'LABEL') {
                label.classList.add('text-secondary', 'tracking-[0.2em]');
            }
        });
        input.addEventListener('blur', () => {
            const label = input.previousElementSibling;
            if (label && label.tagName === 'LABEL') {
                label.classList.remove('text-secondary', 'tracking-[0.2em]');
            }
        });
    });
});
