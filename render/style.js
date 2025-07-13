// Enhanced Mastodon Digest JavaScript with Modern Interactions
class MastodonDigest {
    constructor() {
        this.dateFormat = { 
            minute: 'numeric', 
            hour: 'numeric', 
            day: 'numeric', 
            month: 'long' 
        };
        
        this.init();
    }

    async init() {
        // Wait for DOM to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        this.formatDates();
        this.setupLazyLoading();
        this.setupKeyboardNavigation();
        this.setupTouchGestures();
        this.setupThemeDetection();
        this.setupIntersectionObserver();
        this.setupErrorHandling();
        this.announcePageLoad();
    }

    // Enhanced date formatting with error handling and time zones
    formatDates() {
        try {
            const dateElements = document.querySelectorAll('.date');
            const now = new Date();
            
            dateElements.forEach(element => {
                try {
                    const dateString = element.dataset.date;
                    if (!dateString) {
                        console.warn('Date element missing data-date attribute:', element);
                        return;
                    }
                    
                    const date = new Date(dateString);
                    
                    if (isNaN(date.getTime())) {
                        console.error('Invalid date:', dateString);
                        element.textContent = 'Invalid date';
                        element.setAttribute('aria-label', 'Invalid date');
                        return;
                    }
                    
                    // Calculate relative time
                    const diffMs = now - date;
                    const diffMins = Math.floor(diffMs / 60000);
                    const diffHours = Math.floor(diffMins / 60);
                    const diffDays = Math.floor(diffHours / 24);
                    
                    let relativeTime;
                    let fullDate;
                    
                    if (diffMins < 1) {
                        relativeTime = 'just now';
                    } else if (diffMins < 60) {
                        relativeTime = `${diffMins}m ago`;
                    } else if (diffHours < 24) {
                        relativeTime = `${diffHours}h ago`;
                    } else if (diffDays < 7) {
                        relativeTime = `${diffDays}d ago`;
                    } else {
                        relativeTime = date.toLocaleString('en-US', this.dateFormat);
                    }
                    
                    fullDate = date.toLocaleString();
                    
                    element.textContent = relativeTime;
                    element.title = fullDate;
                    element.setAttribute('aria-label', `Posted ${relativeTime} on ${fullDate}`);
                    element.setAttribute('datetime', date.toISOString());
                    
                } catch (error) {
                    console.error('Error formatting individual date:', error, element);
                    element.textContent = 'Date error';
                    element.setAttribute('aria-label', 'Date formatting error');
                }
            });
            
        } catch (error) {
            console.error('Error formatting dates:', error);
        }
    }

    // Lazy loading for images and media
    setupLazyLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            img.classList.remove('loading');
                        }
                        observer.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                img.classList.add('loading');
                imageObserver.observe(img);
            });
        }
    }

    // Enhanced keyboard navigation
    setupKeyboardNavigation() {
        const posts = Array.from(document.querySelectorAll('.post'));
        let currentPostIndex = -1;

        const focusPost = (index) => {
            if (index >= 0 && index < posts.length) {
                currentPostIndex = index;
                posts[index].focus();
                posts[index].scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
                
                // Announce to screen readers
                this.announceToScreenReader(`Focused on post ${index + 1} of ${posts.length}`);
            }
        };

        document.addEventListener('keydown', (e) => {
            // Only handle navigation when not in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            switch (e.key) {
                case 'j': // Next post
                case 'ArrowDown':
                    e.preventDefault();
                    focusPost(currentPostIndex + 1);
                    break;
                case 'k': // Previous post
                case 'ArrowUp':
                    e.preventDefault();
                    focusPost(currentPostIndex - 1);
                    break;
                case 'o': // Open original link
                case 'Enter':
                    if (currentPostIndex >= 0) {
                        e.preventDefault();
                        const originalLink = posts[currentPostIndex].querySelector('.links a:first-child');
                        if (originalLink) {
                            window.open(originalLink.href, '_blank', 'noopener');
                        }
                    }
                    break;
                case 'h': // Open home link
                    if (currentPostIndex >= 0) {
                        e.preventDefault();
                        const homeLink = posts[currentPostIndex].querySelector('.links a:last-child');
                        if (homeLink) {
                            window.open(homeLink.href, '_blank', 'noopener');
                        }
                    }
                    break;
            }
        });

        // Make posts focusable
        posts.forEach((post, index) => {
            post.setAttribute('tabindex', '0');
            post.setAttribute('role', 'article');
            post.addEventListener('focus', () => {
                currentPostIndex = index;
            });
        });
    }

    // Touch gesture support
    setupTouchGestures() {
        if (!('ontouchstart' in window)) return;

        let startX, startY, endX, endY;

        document.addEventListener('touchstart', (e) => {
            const touch = e.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;

            const touch = e.changedTouches[0];
            endX = touch.clientX;
            endY = touch.clientY;

            const deltaX = endX - startX;
            const deltaY = endY - startY;
            const minSwipeDistance = 50;

            // Horizontal swipe
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
                if (deltaX > 0) {
                    // Swipe right - go to previous section
                    this.navigateSection(-1);
                } else {
                    // Swipe left - go to next section
                    this.navigateSection(1);
                }
            }

            startX = startY = endX = endY = null;
        }, { passive: true });
    }

    // Theme detection and system preference handling
    setupThemeDetection() {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
        const prefersContrast = window.matchMedia('(prefers-contrast: high)');
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

        const updateTheme = () => {
            document.documentElement.setAttribute('data-theme', prefersDark.matches ? 'dark' : 'light');
            document.documentElement.setAttribute('data-contrast', prefersContrast.matches ? 'high' : 'normal');
            document.documentElement.setAttribute('data-motion', prefersReducedMotion.matches ? 'reduced' : 'normal');
        };

        updateTheme();
        prefersDark.addEventListener('change', updateTheme);
        prefersContrast.addEventListener('change', updateTheme);
        prefersReducedMotion.addEventListener('change', updateTheme);
    }

    // Intersection observer for animations and analytics
    setupIntersectionObserver() {
        if (!('IntersectionObserver' in window)) return;

        const animationObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    // Optional: Track post visibility for analytics
                    this.trackPostView(entry.target);
                }
            });
        }, { threshold: 0.5 });

        document.querySelectorAll('.post').forEach(post => {
            animationObserver.observe(post);
        });
    }

    // Global error handling
    setupErrorHandling() {
        window.addEventListener('error', (e) => {
            console.error('JavaScript error:', e.error);
            this.showErrorMessage('Something went wrong. Please refresh the page.');
        });

        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            this.showErrorMessage('A network error occurred. Please check your connection.');
        });
    }

    // Utility methods
    navigateSection(direction) {
        const sections = document.querySelectorAll('.stream');
        const currentSection = document.querySelector('.stream:hover, .stream:focus-within') || sections[0];
        const currentIndex = Array.from(sections).indexOf(currentSection);
        const nextIndex = currentIndex + direction;

        if (nextIndex >= 0 && nextIndex < sections.length) {
            sections[nextIndex].scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
        }
    }

    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }

    announcePageLoad() {
        const postCount = document.querySelectorAll('.post').length;
        const streamCount = document.querySelectorAll('.stream').length;
        
        this.announceToScreenReader(
            `Mastodon digest loaded with ${postCount} posts across ${streamCount} sections. Use J and K keys to navigate posts.`
        );
    }


    showErrorMessage(message) {
        // Create a toast notification
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--error);
            color: white;
            padding: 1rem;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    trackPostView(post) {
        // Optional: Analytics tracking
        const postId = post.querySelector('[data-post-id]')?.dataset.postId;
        if (postId) {
            console.log('Post viewed:', postId);
            // Send to analytics service
        }
    }
}

// Initialize when DOM is ready
new MastodonDigest();