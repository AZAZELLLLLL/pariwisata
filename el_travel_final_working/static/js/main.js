// ============================================================
// EL TRAVEL — Complete Animation System + Hero Slider
// ============================================================

(function () {
  'use strict';

  // ─── Easing helpers ───
  const ease = {
    outExpo:  t => t === 1 ? 1 : 1 - Math.pow(2, -10 * t),
    outQuart: t => 1 - Math.pow(1 - t, 4),
    outBack:  t => { const c = 1.70158 + 1; return 1 + c * Math.pow(t - 1, 3) + 1.70158 * Math.pow(t - 1, 2); }
  };
  function lerp(a, b, t) { return a + (b - a) * t; }

  // ─────────────────────────────────────────────
  // INJECT CSS
  // ─────────────────────────────────────────────
  function injectCSS() {
    const s = document.createElement('style');
    s.textContent = `
      /* Custom Cursor */
      @media (min-width:1024px) {
        /* custom cursor intentionally hidden only when JS adds its elements.
           Remove the global hide so system cursor remains visible when custom
           cursor is disabled. */
        /* * { cursor: none !important; } */
        .cursor-dot {
          position:fixed;z-index:2147483647;pointer-events:none;
          width:12px;height:12px;border-radius:50%;background:#e6c875;
          transform:translate(-50%,-50%) scale(1);transition:width .2s,height .2s,background .2s,filter .2s;
          will-change:transform,opacity;
          box-shadow:0 0 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.5), inset 0 0 2px rgba(255,255,255,0.6), 0 0 0 2px rgba(0,0,0,0.4), 0 0 12px rgba(230,200,117,0.6);
          border:1.5px solid rgba(0,0,0,0.5);
          opacity:1 !important;
          visibility:visible !important;
          display:block !important;
          left:0 !important;
          top:0 !important;
          margin:0 !important;
          padding:0 !important;
        }
        .cursor-dot.active{width:16px;height:16px;background:#e6c875;filter:brightness(1.2);}
        .cursor-dot.clicking{width:8px;height:8px;}
        .cursor-dot.bright{background:#e6c875;box-shadow:0 0 3px rgba(0,0,0,1),0 0 6px rgba(0,0,0,0.8),0 0 16px #e6c875,0 0 32px rgba(230,200,117,0.8),0 0 12px rgba(230,200,117,1),inset 0 0 2px rgba(255,255,255,0.8),0 0 0 2px rgba(0,0,0,0.6);filter:brightness(1.5);opacity:1 !important;width:14px;height:14px;}
        .cursor-ring {
          position:fixed;z-index:2147483646;pointer-events:none;
          width:42px;height:42px;border-radius:50%;
          border:2.5px solid rgba(230,200,117,.9);
          transform:translate(-50%,-50%);
          transition:width .3s,height .3s,border-color .3s,filter .2s;
          will-change:transform,opacity;
          box-shadow:0 0 3px rgba(0,0,0,0.6), inset 0 0 4px rgba(230,200,117,0.4), 0 0 12px rgba(230,200,117,0.3);
          opacity:1 !important;
          visibility:visible !important;
          display:block !important;
          left:0 !important;
          top:0 !important;
          margin:0 !important;
          padding:0 !important;
        }
        .cursor-ring.active{width:58px;height:58px;border-color:rgba(230,200,117,1);border-width:2px;}
        .cursor-ring.bright{border-color:#e6c875;box-shadow:0 0 3px rgba(0,0,0,0.8),0 0 20px rgba(230,200,117,1),0 0 10px rgba(230,200,117,1.0),inset 0 0 4px rgba(230,200,117,0.6),0 0 0 2px rgba(0,0,0,0.3);filter:brightness(1.3);opacity:1 !important;}
      }

      /* Ripple */
      @keyframes rippleAnim { to { transform:scale(1);opacity:0; } }

      /* Scroll progress */
      #scroll-progress {
        position:fixed;top:0;left:0;height:3px;width:0%;z-index:9999;
        background:linear-gradient(90deg,#c8a84b,#e6c875,#c8a84b);
        background-size:200% 100%;pointer-events:none;
        animation:shimBarAnim 2s linear infinite;
        transition:width .12s linear;
        box-shadow:0 0 8px rgba(200,168,75,.5);
      }
      @keyframes shimBarAnim{0%{background-position:200% center}100%{background-position:-200% center}}

      /* Loading screen */
      #el-loader {
        position:fixed;inset:0;z-index:999999;background:#1a2744;
        display:flex;align-items:center;justify-content:center;
        transition:opacity .6s ease,visibility .6s ease;
      }
      .loader-inner{text-align:center;}
      .loader-logo{font-size:2.2rem;margin-bottom:20px;}
      .loader-logo .logo-el{color:#c8a84b;font-family:'Playfair Display',serif;font-weight:700;}
      .loader-logo .logo-travel{color:#fff;font-family:'DM Sans',sans-serif;font-weight:300;}
      .loader-bar{width:200px;height:2px;background:rgba(255,255,255,.15);border-radius:2px;overflow:hidden;}
      .loader-fill{height:100%;background:linear-gradient(90deg,#c8a84b,#e6c875);border-radius:2px;
        animation:loaderFill .9s cubic-bezier(.4,0,.2,1) forwards;}
      @keyframes loaderFill{from{width:0%}to{width:100%}}

      /* Image skeleton */
      .img-loading{
        background:linear-gradient(90deg,#e8ecf0 25%,#f4f5f7 50%,#e8ecf0 75%);
        background-size:200% 100%;animation:skeletonAnim 1.4s ease infinite;
      }
      @keyframes skeletonAnim{0%{background-position:200% 0}100%{background-position:-200% 0}}

      /* Back to top */
      #back-to-top {
        position:fixed;bottom:96px;right:28px;z-index:998;
        width:46px;height:46px;border-radius:50%;
        background:rgba(26,39,68,.85);border:1px solid rgba(200,168,75,.3);
        color:#c8a84b;font-size:1rem;
        display:flex;align-items:center;justify-content:center;
        cursor:pointer;opacity:0;transform:translateY(10px);
        transition:all .4s ease;backdrop-filter:blur(8px);text-decoration:none;
      }
      #back-to-top.visible{opacity:1;transform:translateY(0);}
      #back-to-top:hover{background:#c8a84b;color:#1a2744;transform:translateY(-3px);}

      /* WA float glow */
      .wa-float{animation:waGlow 3s ease-in-out infinite;}
      @keyframes waGlow{
        0%,100%{box-shadow:0 6px 24px rgba(37,211,102,.4);}
        50%{box-shadow:0 6px 36px rgba(37,211,102,.65),0 0 0 12px rgba(37,211,102,.08);}
      }

      /* Gold shimmer on logo */
      .navbar.scrolled .logo-el{
        background:linear-gradient(90deg,#c8a84b,#e6c875,#c8a84b);
        background-size:200%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
        animation:goldShim 3s linear infinite;
      }
      @keyframes goldShim{0%{background-position:200%}100%{background-position:-200%}}

      /* Section title underline */
      .section-title::after{
        content:'';display:block;width:0;height:2px;
        background:linear-gradient(90deg,#c8a84b,transparent);
        margin-top:6px;transition:width .8s cubic-bezier(.16,1,.3,1) .3s;
      }
      .section-title.revealed::after{width:80px;}

      /* Section header top line */
      .section-header::before{
        content:'';display:block;width:40px;height:2px;
        background:#c8a84b;margin:0 auto 16px;border-radius:2px;
      }

      /* Nav mobile stagger */
      @media (max-width: 768px) {
        .nav-menu li{opacity:0;transform:translateX(20px);transition:opacity .3s ease,transform .3s ease;}
        .nav-menu.open li{opacity:1;transform:translateX(0);}
        .nav-menu.open li:nth-child(1){transition-delay:.05s;}
        .nav-menu.open li:nth-child(2){transition-delay:.10s;}
        .nav-menu.open li:nth-child(3){transition-delay:.15s;}
        .nav-menu.open li:nth-child(4){transition-delay:.20s;}
        .nav-menu.open li:nth-child(5){transition-delay:.25s;}
        .nav-menu.open li:nth-child(6){transition-delay:.30s;}
        .nav-menu.open li:nth-child(7){transition-delay:.35s;}
      }

      /* Testi quote decoration */
      .testi-card{position:relative;}
      .testi-card::before{
        content:'"';position:absolute;top:12px;right:18px;
        font-size:5rem;font-family:'Playfair Display',serif;
        color:rgba(200,168,75,.1);line-height:1;pointer-events:none;
      }

      /* Footer link arrow */
      .footer-col ul li a{display:inline-flex;align-items:center;gap:0;}
      .footer-col ul li a::before{
        content:'→';opacity:0;transform:translateX(-8px);
        transition:all .3s ease;font-size:.75rem;color:#c8a84b;margin-right:0;
      }
      .footer-col ul li a:hover::before{opacity:1;transform:translateX(0);margin-right:5px;}

      /* Input lift on focus */
      .input-wrap input:focus,.input-wrap textarea:focus{transform:translateY(-1px);}

      /* Paket card hover glow */
      .paket-card:hover{
        border-color:#c8a84b;
        box-shadow:0 4px 30px rgba(200,168,75,.18);
        transform:translateY(-4px);
      }

      /* Hero slide transitions */
      @keyframes slideInRight{ from { transform:translateX(100%); opacity:0.6; } 60% { opacity:0.85; } to { transform:translateX(0%); opacity:1; } }
      @keyframes slideOutLeft{ from { transform:translateX(0%); opacity:1; } 60% { opacity:0.85; } to { transform:translateX(-100%); opacity:0.6; } }
      @keyframes slideInLeft{ from { transform:translateX(-100%); opacity:0.6; } 60% { opacity:0.85; } to { transform:translateX(0%); opacity:1; } }
      @keyframes slideOutRight{ from { transform:translateX(0%); opacity:1; } 60% { opacity:0.85; } to { transform:translateX(100%); opacity:0.6; } }
      .hero-slide.anim-in-right {animation:slideInRight .85s cubic-bezier(.77,0,.175,1) forwards;}
      .hero-slide.anim-out-left {animation:slideOutLeft  .85s cubic-bezier(.77,0,.175,1) forwards;}
      .hero-slide.anim-in-left  {animation:slideInLeft   .85s cubic-bezier(.77,0,.175,1) forwards;}
      .hero-slide.anim-out-right{animation:slideOutRight .85s cubic-bezier(.77,0,.175,1) forwards;}

      /* Page curtain - sangat transparan agar cursor terlihat */
      #page-curtain{position:fixed;inset:0;z-index:9999997;background:rgba(26,39,68,0.5);backdrop-filter:blur(2px);pointer-events:none;}
    `;
    document.head.appendChild(s);
  }

  // ─────────────────────────────────────────────
  // LOADING SCREEN
  // ─────────────────────────────────────────────
  function initLoader() {
    const el = document.createElement('div');
    el.id = 'el-loader';
    el.innerHTML = `<div class="loader-inner">
      <div class="loader-logo"><span class="logo-el">EL</span><span class="logo-travel"> Travel</span></div>
      <div class="loader-bar"><div class="loader-fill"></div></div>
    </div>`;
    document.body.appendChild(el);
    window.addEventListener('load', () => {
      setTimeout(() => {
        el.style.opacity = '0';
        el.style.visibility = 'hidden';
        setTimeout(() => el.remove(), 600);
      }, 1000);
    });
  }

  // ─────────────────────────────────────────────
  // CUSTOM CURSOR
  // ─────────────────────────────────────────────
  function initCursor() {
    if (window.innerWidth < 1024) return;

    // Create cursor elements
    const dot  = document.createElement('div');
    const ring = document.createElement('div');

    dot.id = 'custom-cursor-dot';
    ring.id = 'custom-cursor-ring';

    // Append langsung ke body
    document.body.appendChild(dot);
    document.body.appendChild(ring);

    let mouseX = 0;
    let mouseY = 0;

    // Track mouse position
    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;

      // Update dot directly
      dot.style.left = mouseX + 'px';
      dot.style.top = mouseY + 'px';
    });

    // Ring lerp animation
    let ringX = 0;
    let ringY = 0;

    function animateRing() {
      ringX += (mouseX - ringX) * 0.12;
      ringY += (mouseY - ringY) * 0.12;

      ring.style.left = ringX + 'px';
      ring.style.top = ringY + 'px';

      requestAnimationFrame(animateRing);
    }
    animateRing();

    // Hover effects
    document.querySelectorAll('a,button,.wisata-card,.category-card,.filter-btn,.paket-card').forEach(el => {
      el.addEventListener('mouseenter', () => {
        dot.classList.add('active');
        ring.classList.add('active');
      });
      el.addEventListener('mouseleave', () => {
        dot.classList.remove('active');
        ring.classList.remove('active');
      });
    });

    // Click effect
    document.addEventListener('mousedown', () => {
      dot.classList.add('clicking');
    });
    document.addEventListener('mouseup', () => {
      dot.classList.remove('clicking');
    });

    // Scroll glow
    window.addEventListener('scroll', () => {
      dot.classList.add('bright');
      ring.classList.add('bright');
      clearTimeout(window.scrollTimeout);
      window.scrollTimeout = setTimeout(() => {
        dot.classList.remove('bright');
        ring.classList.remove('bright');
      }, 150);
    }, {passive: true});
  }

  // ─────────────────────────────────────────────
  // SMOOTH SCROLL
  // ─────────────────────────────────────────────
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(a => {
      a.addEventListener('click', function(e) {
        const t = document.querySelector(this.getAttribute('href'));
        if (!t) return; e.preventDefault();
        const start=window.scrollY, end=t.getBoundingClientRect().top+window.scrollY-80, dur=900;
        let ts=null;
        (function step(now){ if(!ts)ts=now; const p=Math.min((now-ts)/dur,1); window.scrollTo(0,lerp(start,end,ease.outExpo(p))); if(p<1)requestAnimationFrame(step); })(performance.now());
      });
    });
  }

  // ─────────────────────────────────────────────
  // NAVBAR
  // ─────────────────────────────────────────────
  function initNavbar() {
    const nav = document.getElementById('navbar');
    const menu = document.getElementById('navMenu');
    if (!nav) return;

    const hasHero = Boolean(
      document.querySelector('.hero, .page-hero, .detail-hero, .payment-hero, .review-hero, .filter-hero')
    );

    const syncNavbarState = () => {
      const menuOpen = Boolean(menu && menu.classList.contains('open'));
      const shouldSolid = !hasHero || menuOpen || window.scrollY > 60;

      nav.classList.toggle('scrolled', shouldSolid);
      nav.classList.toggle('menu-open', menuOpen);
    };

    syncNavbarState();
    window.addEventListener('scroll', syncNavbarState, {passive:true});
    window.addEventListener('resize', syncNavbarState);
    window.addEventListener('eltravel:nav-state', syncNavbarState);
  }

  // ─────────────────────────────────────────────
  // MOBILE MENU
  // ─────────────────────────────────────────────
  function initMobileMenu() {
    const hb  = document.getElementById('hamburger');
    const menu= document.getElementById('navMenu');
    if (!hb || !menu) return;
    const dropdowns = Array.from(menu.querySelectorAll('.dropdown'));

    hb.addEventListener('click', () => {
      const open = menu.classList.toggle('open');
      document.body.classList.toggle('nav-open', open);
      hb.classList.toggle('active', open);
      const spans = hb.querySelectorAll('span');
      if (open) { spans[0].style.transform='translateY(7px) rotate(45deg)'; spans[1].style.opacity='0'; spans[2].style.transform='translateY(-7px) rotate(-45deg)'; }
      else       { spans.forEach(s=>{ s.style.transform=''; s.style.opacity=''; }); }
      window.dispatchEvent(new Event('eltravel:nav-state'));
    });
    document.addEventListener('click', e => {
      if (!hb.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.remove('open'); document.body.classList.remove('nav-open'); hb.classList.remove('active');
        hb.querySelectorAll('span').forEach(s=>{ s.style.transform=''; s.style.opacity=''; });
        dropdowns.forEach(d => d.classList.remove('open'));
        window.dispatchEvent(new Event('eltravel:nav-state'));
      }
    });
    menu.querySelectorAll('.dropdown-toggle').forEach(t => {
      t.addEventListener('click', function(e) {
        const dropdown = this.closest('.dropdown');
        if (!dropdown) return;
        e.preventDefault();

        if (window.innerWidth <= 768) {
          dropdown.classList.toggle('open');
          return;
        }

        const willOpen = !dropdown.classList.contains('open');
        dropdowns.forEach(d => d.classList.remove('open'));
        if (willOpen) dropdown.classList.add('open');
      });
    });

    dropdowns.forEach(dropdown => {
      dropdown.addEventListener('mouseenter', () => {
        if (window.innerWidth > 768) dropdown.classList.add('open');
      });
      dropdown.addEventListener('mouseleave', () => {
        if (window.innerWidth > 768) dropdown.classList.remove('open');
      });
    });
  }

  // ─────────────────────────────────────────────
  // SCROLL REVEAL
  // ─────────────────────────────────────────────
  function initScrollReveal() {
    const cfg = [
      {sel:'.section-tag',     delay:0,   y:20},
      {sel:'.section-title',   delay:80,  y:28},
      {sel:'.section-sub',     delay:160, y:20},
      {sel:'.wisata-card',     delay:'stagger', y:36},
      {sel:'.category-card',   delay:'stagger', y:30},
      {sel:'.paket-card',      delay:'stagger', y:28},
      {sel:'.testi-card',      delay:'stagger', y:28},
      {sel:'.why-item',        delay:'stagger', y:24},
      {sel:'.rstat-card',      delay:'stagger', y:22},
      {sel:'.vm-card',         delay:'stagger', y:28},
      {sel:'.why-image',       delay:0,   y:40},
      {sel:'.about-img',       delay:0,   x:-40, y:0},
      {sel:'.about-content',   delay:160, x:40,  y:0},
      {sel:'.kontak-info',     delay:0,   x:-30, y:0},
      {sel:'.kontak-form-wrap',delay:160, x:30,  y:0},
      {sel:'.detail-card',     delay:'stagger', y:24},
      {sel:'.sidebar-card',    delay:'stagger', y:24},
      {sel:'.form-card',       delay:0,   y:28},
      {sel:'.paket-summary',   delay:120, y:28},
      {sel:'.table-wrap',      delay:0,   y:24},
      {sel:'.cta-content h2',  delay:0,   y:28},
      {sel:'.cta-content p',   delay:120, y:22},
      {sel:'.cta-actions',     delay:240, y:20},
      {sel:'.footer-brand',    delay:0,   y:20},
      {sel:'.footer-col',      delay:'stagger', y:20},
    ];
    const seen = new Set();
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => { if(e.isIntersecting){ e.target.style.opacity='1'; e.target.style.transform='translate(0,0) scale(1)'; obs.unobserve(e.target); } });
    }, {threshold:.08, rootMargin:'0px 0px -40px 0px'});

    cfg.forEach(({sel, delay, y=30, x=0}) => {
      document.querySelectorAll(sel).forEach((el,i) => {
        if(seen.has(el)) return; seen.add(el);
        const d = delay==='stagger' ? i*90 : delay;
        el.style.cssText += `opacity:0;transform:translate(${x}px,${y}px);transition:opacity .75s cubic-bezier(.16,1,.3,1) ${d}ms,transform .75s cubic-bezier(.16,1,.3,1) ${d}ms;will-change:opacity,transform;`;
        obs.observe(el);
      });
    });
  }

  // ─────────────────────────────────────────────
  // PARALLAX
  // ─────────────────────────────────────────────
  function initParallax() {
    const imgs = document.querySelectorAll('.page-hero-bg img,.cta-bg img,.detail-hero-bg img');
    if (!imgs.length) return;
    window.addEventListener('scroll', () => {
      const sy = window.scrollY;
      imgs.forEach(img => {
        const sec = img.closest('section')||img.parentElement.parentElement;
        const r = sec.getBoundingClientRect();
        if(r.bottom<0||r.top>window.innerHeight) return;
        img.style.transform=`translateY(${(r.top/window.innerHeight)*60}px) scale(1.08)`;
      });
    }, {passive:true});
  }

  // ─────────────────────────────────────────────
  // MAGNETIC BUTTONS
  // ─────────────────────────────────────────────
  function initMagnetic() {
    if (window.innerWidth < 1024) return;
    document.querySelectorAll('.btn-primary,.btn-wa,.btn-maps,.btn-pesan,.btn-submit,.nav-btn-wa').forEach(btn => {
      btn.addEventListener('mousemove', function(e) {
        const r=this.getBoundingClientRect();
        this.style.transform=`translate(${(e.clientX-r.left-r.width/2)*.28}px,${(e.clientY-r.top-r.height/2)*.28-3}px)`;
      });
      btn.addEventListener('mouseleave',function(){ this.style.transform=''; });
    });
  }

  // ─────────────────────────────────────────────
  // COUNTER
  // ─────────────────────────────────────────────
  function initCounters() {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if(!entry.isIntersecting) return;
        const el=entry.target, txt=el.textContent.trim();
        const m=txt.match(/[\d,.]+/); if(!m) return;
        const isRp=txt.startsWith('Rp'), end=parseInt(m[0].replace(/[,.]/g,'')), suf=txt.replace(/Rp\s?/,'').replace(/[\d,. ]+/,'');
        if(isNaN(end)) return;
        const dur=1400; let ts=null;
        (function run(now){ if(!ts)ts=now; const p=Math.min((now-ts)/dur,1), v=Math.round(ease.outExpo(p)*end);
          el.textContent=isRp?'Rp '+v.toLocaleString('id-ID'):v.toLocaleString('id-ID')+suf;
          if(p<1)requestAnimationFrame(run); })(performance.now());
        obs.unobserve(el);
      });
    },{threshold:.5});
    document.querySelectorAll('.stat-num,.rstat-num').forEach(c=>obs.observe(c));
  }

  // ─────────────────────────────────────────────
  // CARD TILT
  // ─────────────────────────────────────────────
  function initTilt() {
    if(window.innerWidth<1024) return;
    document.querySelectorAll('.wisata-card,.category-card,.testi-card').forEach(c => {
      c.style.transformStyle='preserve-3d';
      c.addEventListener('mousemove',function(e){
        const r=this.getBoundingClientRect(), x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
        this.style.transform=`perspective(800px) rotateX(${y*-10}deg) rotateY(${x*10}deg) translateZ(4px) translateY(-6px)`;
        this.style.boxShadow=`${-x*15+8}px ${y*-15+20}px 40px rgba(26,39,68,.2)`;
      });
      c.addEventListener('mouseleave',function(){ this.style.transform=''; this.style.boxShadow=''; });
    });
  }

  // ─────────────────────────────────────────────
  // RIPPLE
  // ─────────────────────────────────────────────
  function initRipple() {
    document.querySelectorAll('.btn-primary,.btn-submit,.btn-pesan,.filter-btn,.btn-detail').forEach(btn => {
      btn.style.overflow='hidden';
      btn.addEventListener('click', function(e) {
        const r=this.getBoundingClientRect(), sz=Math.max(r.width,r.height)*2;
        const rp=document.createElement('span');
        rp.style.cssText=`position:absolute;width:${sz}px;height:${sz}px;left:${e.clientX-r.left-sz/2}px;top:${e.clientY-r.top-sz/2}px;background:rgba(255,255,255,.25);border-radius:50%;transform:scale(0);animation:rippleAnim .6s ease-out forwards;pointer-events:none;`;
        this.appendChild(rp); setTimeout(()=>rp.remove(),700);
      });
    });
  }

  // ─────────────────────────────────────────────
  // FLOATING PARTICLES on hero
  // ─────────────────────────────────────────────
  function initParticles() {
    const hero=document.querySelector('.hero'); if(!hero) return;
    const cv=document.createElement('canvas');
    cv.style.cssText='position:absolute;inset:0;pointer-events:none;z-index:1;opacity:.3;';
    hero.appendChild(cv);
    const ctx=cv.getContext('2d');
    const resize=()=>{ cv.width=hero.offsetWidth; cv.height=hero.offsetHeight; };
    resize(); window.addEventListener('resize',resize);
    const N=Math.min(50,Math.floor(cv.width/24));
    const pts=Array.from({length:N},()=>({x:Math.random()*cv.width,y:Math.random()*cv.height,r:Math.random()*1.8+.4,vx:(Math.random()-.5)*.3,vy:-(Math.random()*.4+.1),a:Math.random()*.6+.2,c:Math.random()>.5?'#c8a84b':'#fff'}));
    (function draw(){
      ctx.clearRect(0,0,cv.width,cv.height);
      pts.forEach(p=>{ ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fillStyle=p.c; ctx.globalAlpha=p.a; ctx.fill(); p.x+=p.vx; p.y+=p.vy; if(p.y<-4){p.y=cv.height+4;p.x=Math.random()*cv.width;} if(p.x<0||p.x>cv.width)p.vx*=-1; });
      ctx.globalAlpha=1; requestAnimationFrame(draw);
    })();
  }

  // ─────────────────────────────────────────────
  // SCROLL PROGRESS BAR
  // ─────────────────────────────────────────────
  function initScrollProgress() {
    const bar=document.createElement('div'); bar.id='scroll-progress'; document.body.appendChild(bar);
    window.addEventListener('scroll',()=>{ const d=document.documentElement.scrollHeight-window.innerHeight; bar.style.width=(d>0?window.scrollY/d*100:0)+'%'; },{passive:true});
  }

  // ─────────────────────────────────────────────
  // PAGE TRANSITION
  // ─────────────────────────────────────────────
  function initPageTransition() {
    const c=document.createElement('div'); c.id='page-curtain';
    c.style.cssText='position:fixed;inset:0;z-index:9999997;background:rgba(26,39,68,0.5);backdrop-filter:blur(2px);pointer-events:none;opacity:1;transition:opacity .6s ease;';
    document.body.appendChild(c);
    requestAnimationFrame(()=>requestAnimationFrame(()=>c.style.opacity='0'));
    document.querySelectorAll('a[href]').forEach(a=>{
      const h=a.getAttribute('href');
      if(!h||h.startsWith('#')||h.startsWith('http')||h.startsWith('tel:')||h.startsWith('mailto:')||h.includes('wa.me')) return;
      a.addEventListener('click',function(e){
        const d=this.getAttribute('href'); if(!d||d.startsWith('#')) return;
        e.preventDefault(); c.style.opacity='1'; c.style.pointerEvents='none';
        setTimeout(()=>window.location.href=d,500);
      });
    });
  }

  // ─────────────────────────────────────────────
  // BACK TO TOP
  // ─────────────────────────────────────────────
  function initBackToTop() {
    const btn=document.createElement('a'); btn.id='back-to-top'; btn.href='#'; btn.innerHTML='<i class="fas fa-chevron-up"></i>'; btn.setAttribute('aria-label','Back to top');
    document.body.appendChild(btn);
    window.addEventListener('scroll',()=>btn.classList.toggle('visible',window.scrollY>400),{passive:true});
    btn.addEventListener('click',e=>{ e.preventDefault(); window.scrollTo({top:0,behavior:'smooth'}); });
  }

  // ─────────────────────────────────────────────
  // TITLE UNDERLINE
  // ─────────────────────────────────────────────
  function initTitleUnderline() {
    const obs=new IntersectionObserver(e=>{ e.forEach(x=>{ if(x.isIntersecting){x.target.classList.add('revealed');obs.unobserve(x.target);} }); },{threshold:.4});
    document.querySelectorAll('.section-title').forEach(t=>obs.observe(t));
  }

  // ─────────────────────────────────────────────
  // IMAGE LOADER
  // ─────────────────────────────────────────────
  function initImgLoader() {
    document.querySelectorAll('img').forEach(img=>{
      if(img.complete) return;
      const wrap=img.closest('.wisata-img-wrap,.paket-summary,.detail-hero-bg,.why-image,.about-img');
      if(wrap) wrap.classList.add('img-loading');
      img.addEventListener('load',()=>{
        if(wrap) wrap.classList.remove('img-loading');
        img.style.opacity='0'; img.style.transition='opacity .6s ease';
        requestAnimationFrame(()=>img.style.opacity='1');
      });
    });
  }

  // ─────────────────────────────────────────────
  // TYPEWRITER for hero badge
  // ─────────────────────────────────────────────
  function initTypewriter() {
    const b=document.getElementById('heroBadge'); if(!b) return;
    const txt=b.textContent.trim(); b.textContent=''; b.style.opacity='1';
    let i=0; const fn=()=>{ if(i<txt.length){b.textContent+=txt.charAt(i++); setTimeout(fn,40);} };
    setTimeout(fn,700);
  }

  // ─────────────────────────────────────────────
  // FLASH AUTO-DISMISS
  // ─────────────────────────────────────────────
  function initFlash() {
    setTimeout(()=>{
      document.querySelectorAll('.flash').forEach(f=>{ f.style.transition='opacity .5s ease,transform .5s ease'; f.style.opacity='0'; f.style.transform='translateX(110%)'; setTimeout(()=>f.remove(),500); });
    },4500);
  }

  // ─────────────────────────────────────────────
  // PRICE TICKER
  // ─────────────────────────────────────────────
  function initPriceTicker() {
    document.querySelectorAll('.paket-card').forEach(c=>{
      const h=c.querySelector('.harga-num'); if(!h) return;
      h.style.transition='transform .3s ease,color .3s ease';
      c.addEventListener('mouseenter',()=>{ h.style.transform='scale(1.06)'; h.style.color='#c8a84b'; });
      c.addEventListener('mouseleave',()=>{ h.style.transform=''; h.style.color=''; });
    });
  }

  // ─────────────────────────────────────────────
  // ═══════════════ HERO SLIDER ═══════════════
  // ─────────────────────────────────────────────
  function initHeroSlider() {
    const slider = document.getElementById('heroSlider'); if(!slider) return;
    const slides  = slider.querySelectorAll('.hero-slide');
    const dots    = document.querySelectorAll('.sdot');
    const prevBtn = document.getElementById('sliderPrev');
    const nextBtn = document.getElementById('sliderNext');
    const progBar = document.getElementById('slideProgressBar');

    const DURATION = 5500;
    const ANIM     = 850;
    const STEP     = 100 / (DURATION / 100);

    let current=0, total=slides.length, autoT=null, progT=null, progV=0, busy=false;

    function setDots(idx) {
      dots.forEach(d=>d.classList.remove('active'));
      if(dots[idx]) dots[idx].classList.add('active');
    }

    function resetProg() {
      clearInterval(progT); progV=0;
      if(progBar){ progBar.style.transition='none'; progBar.style.width='0%'; }
      requestAnimationFrame(()=>requestAnimationFrame(()=>{
        if(progBar) progBar.style.transition='width .1s linear';
        progT=setInterval(()=>{ progV=Math.min(progV+STEP,100); if(progBar)progBar.style.width=progV+'%'; if(progV>=100)clearInterval(progT); },100);
      }));
    }

    function goTo(next, dir) {
      if(busy || next===current) return; busy=true;
      const prev=current; current=(next+total)%total;
      const outCls = dir==='next'?'anim-out-left' :'anim-out-right';
      const inCls  = dir==='next'?'anim-in-right':'anim-in-left';

      slides[prev].classList.remove('active');
      slides[current].style.opacity='1';
      slides[current].style.zIndex='3';
      slides[prev].style.zIndex='2';
      slides[prev].classList.add(outCls);
      slides[current].classList.add(inCls);
      setDots(current);

      setTimeout(()=>{
        slides[prev].classList.remove(outCls);
        slides[current].classList.remove(inCls);
        slides.forEach(s=>{ s.classList.remove('active'); s.style.opacity=''; s.style.zIndex=''; });
        slides[current].classList.add('active');
        busy=false; resetProg();
      }, ANIM);
    }

    function startAuto() { clearInterval(autoT); autoT=setInterval(()=>goTo(current+1,'next'),DURATION); }
    function restart()   { startAuto(); resetProg(); }

    if(nextBtn) nextBtn.addEventListener('click',()=>{ goTo(current+1,'next'); restart(); });
    if(prevBtn) prevBtn.addEventListener('click',()=>{ goTo(current-1,'prev'); restart(); });
    dots.forEach(d=>d.addEventListener('click',function(){ const i=parseInt(this.dataset.goto); goTo(i,i>current?'next':'prev'); restart(); }));

    // Touch swipe
    let tx=0;
    slider.addEventListener('touchstart',e=>tx=e.changedTouches[0].clientX,{passive:true});
    slider.addEventListener('touchend',e=>{ const diff=tx-e.changedTouches[0].clientX; if(Math.abs(diff)>50){goTo(current+(diff>0?1:-1),diff>0?'next':'prev');restart();} });

    // Keyboard
    document.addEventListener('keydown',e=>{ if(e.key==='ArrowRight'){goTo(current+1,'next');restart();} if(e.key==='ArrowLeft'){goTo(current-1,'prev');restart();} });

    // Pause on hover
    slider.addEventListener('mouseenter',()=>{ clearInterval(autoT); clearInterval(progT); });
    slider.addEventListener('mouseleave',()=>restart());

    // Init
    slides.forEach((s,i)=>{ if(i!==0){s.style.opacity='0';} });
    slides[0].classList.add('active'); setDots(0); startAuto(); resetProg();

    // Preload images
    slider.querySelectorAll('.slide-bg img').forEach(img=>{ const p=new Image(); p.src=img.src; });
  }

  // ─────────────────────────────────────────────
  // ═══════════════ INIT ALL ═══════════════════
  // ─────────────────────────────────────────────
  injectCSS();
  initLoader();

  document.addEventListener('DOMContentLoaded', () => {
    // initCursor(); // Custom cursor disabled - using standard cursor
    initSmoothScroll();
    initNavbar();
    initMobileMenu();
    initScrollReveal();
    initParallax();
    initMagnetic();
    initCounters();
    initTilt();
    initImgLoader();
    initTypewriter();
    initPageTransition();
    initRipple();
    initParticles();
    initScrollProgress();
    initFlash();
    initBackToTop();
    initTitleUnderline();
    initPriceTicker();
    initHeroSlider();
  });

})();
