import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useMotionValue, useTransform, useSpring } from 'framer-motion';
import {
  Zap, Database, Activity, ShieldCheck, BarChart2,
  ArrowRight, ChevronRight, Link2, Search, Brain, Globe,
  UploadCloud, Cpu, GitMerge, Share2,
} from 'lucide-react';

const ORANGE = '#FF6B2C';

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 28 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, delay, ease: [0.16, 1, 0.3, 1] },
});

const Feature3DCard = ({ f }: { f: any }) => {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const rotateX = useTransform(mouseY, [-150, 150], [8, -8]);
  const rotateY = useTransform(mouseX, [-150, 150], [-8, 8]);

  const springX = useSpring(rotateX, { stiffness: 200, damping: 25 });
  const springY = useSpring(rotateY, { stiffness: 200, damping: 25 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    mouseX.set(e.clientX - centerX);
    mouseY.set(e.clientY - centerY);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  return (
    <div
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ perspective: 1000, height: '100%' }}
    >
      <motion.div
        style={{
          background: '#fff', border: '1px solid #ebebeb',
          padding: '28px 26px', borderRadius: 4,
          rotateX: springX, rotateY: springY,
          transformStyle: 'preserve-3d',
          height: '100%',
          display: 'flex', flexDirection: 'column'
        }}
        whileHover={{
          scale: 1.03,
          boxShadow: '0 20px 40px rgba(0,0,0,0.08)',
          borderColor: 'rgba(0,0,0,0.1)'
        }}
        initial={{ boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}
        transition={{ duration: 0.2 }}
      >
        <div style={{ transform: 'translateZ(30px)' }}>
          <h3 style={{
            fontFamily: 'monospace', fontSize: 14, fontWeight: 800,
            color: '#111', margin: '0 0 10px', letterSpacing: '-0.01em',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: f.accent, display: 'inline-block' }} />
            {f.title}
          </h3>
        </div>
        <div style={{ transform: 'translateZ(15px)', flex: 1 }}>
          <p style={{ fontSize: 13.5, color: '#666', lineHeight: 1.65, margin: 0 }}>
            {f.desc}
          </p>
        </div>
      </motion.div>
    </div>
  );
};

const Step3DCard = ({ s, i }: { s: any, i: number }) => {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const rotateX = useTransform(mouseY, [-150, 150], [8, -8]);
  const rotateY = useTransform(mouseX, [-150, 150], [-8, 8]);

  const springX = useSpring(rotateX, { stiffness: 200, damping: 25 });
  const springY = useSpring(rotateY, { stiffness: 200, damping: 25 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    mouseX.set(e.clientX - centerX);
    mouseY.set(e.clientY - centerY);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  return (
    <div
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ perspective: 1000, height: '100%' }}
    >
      <motion.div
        style={{
          background: '#fff',
          padding: '36px 28px',
          borderTop: `4px solid #e0e0e0`,
          borderRadius: 4,
          boxShadow: '0 2px 10px rgba(0,0,0,0.03)',
          rotateX: springX, rotateY: springY,
          transformStyle: 'preserve-3d',
          height: '100%',
          display: 'flex', flexDirection: 'column'
        }}
        whileHover={{
          scale: 1.03,
          boxShadow: '0 20px 40px rgba(0,0,0,0.08)',
          borderColor: ORANGE,
        }}
        transition={{ duration: 0.2 }}
      >
        <div style={{ transform: 'translateZ(30px)' }}>
          <div style={{
            fontFamily: 'monospace', fontSize: 13, fontWeight: 700,
            color: '#aaa', letterSpacing: '0.1em', marginBottom: 16,
          }}>
            STEP {s.step}
          </div>
          <h3 style={{ fontFamily: 'monospace', fontSize: 20, fontWeight: 800, color: '#111', margin: '0 0 12px' }}>
            {s.title}
          </h3>
        </div>
        <div style={{ transform: 'translateZ(15px)', flex: 1 }}>
          <p style={{ fontSize: 16, color: '#555', lineHeight: 1.6, margin: 0 }}>
            {s.desc}
          </p>
        </div>
      </motion.div>
    </div>
  );
};

const InteractiveMapVisualizer = () => {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouseX.set(e.clientX - window.innerWidth / 2);
      mouseY.set(e.clientY - window.innerHeight / 2);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const rotateX = useTransform(mouseY, [-window.innerHeight / 2, window.innerHeight / 2], [8, -8]);
  const rotateY = useTransform(mouseX, [-window.innerWidth / 2, window.innerWidth / 2], [-8, 8]);

  const springX = useSpring(rotateX, { stiffness: 100, damping: 30 });
  const springY = useSpring(rotateY, { stiffness: 100, damping: 30 });

  const floatY = {
    animate: { y: [0, -15, 0] },
    transition: { repeat: Infinity, duration: 6, ease: 'easeInOut' }
  };

  const nodes = [
    { id: 1, cx: '45%', cy: '35%' },
    { id: 2, cx: '60%', cy: '25%' },
    { id: 3, cx: '35%', cy: '50%' },
    { id: 4, cx: '70%', cy: '55%' },
    { id: 5, cx: '50%', cy: '75%' },
    { id: 6, cx: '55%', cy: '45%' },
  ];

  return (
    <div style={{
      position: 'absolute', top: 0, left: 0, width: '100%', height: '100vh',
      perspective: 1200, pointerEvents: 'none', zIndex: 0,
      overflow: 'hidden'
    }}>
      <motion.div
        style={{
          width: '100%', height: '100%',
          rotateX: springX, rotateY: springY,
          transformStyle: 'preserve-3d',
          position: 'relative'
        }}
        {...floatY}
      >
        <div style={{
          position: 'absolute', top: '50%', right: '8%',
          width: '70vh', height: '70vh', transform: 'translateY(-50%)',
        }}>
          {/* Base Map Image */}
          <img src="/bg.png" alt="" style={{
            width: '100%', height: '100%', objectFit: 'contain',
            opacity: 0.15,
            filter: `drop-shadow(0 0 10px rgba(255,107,44,0.15))`,
          }} />

          {/* SVG Overlay */}
          <svg style={{
            position: 'absolute', top: 0, left: 0,
            width: '100%', height: '100%', overflow: 'visible'
          }}>
            <defs>
              <radialGradient id="nodeGlow">
                <stop offset="0%" stopColor="#FF6B2C" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#FF6B2C" stopOpacity="0" />
              </radialGradient>
            </defs>

            {/* Network Lines */}
            <g stroke="#FF6B2C" strokeWidth="1.5" strokeDasharray="4 6" opacity="0.3">
              <line x1="45%" y1="35%" x2="60%" y2="25%" />
              <line x1="45%" y1="35%" x2="35%" y2="50%" />
              <line x1="45%" y1="35%" x2="55%" y2="45%" />
              <line x1="55%" y1="45%" x2="70%" y2="55%" />
              <line x1="35%" y1="50%" x2="50%" y2="75%" />
              <line x1="55%" y1="45%" x2="50%" y2="75%" />
            </g>

            {/* Animated Data Pulses */}
            <motion.g stroke="#FF6B2C" strokeWidth="2" strokeDasharray="10 100" opacity="0.7"
              animate={{ strokeDashoffset: [0, -110] }}
              transition={{ repeat: Infinity, duration: 2.5, ease: 'linear' }}
            >
              <line x1="45%" y1="35%" x2="60%" y2="25%" />
              <line x1="45%" y1="35%" x2="35%" y2="50%" />
              <line x1="55%" y1="45%" x2="70%" y2="55%" />
            </motion.g>

            {/* Nodes */}
            {nodes.map((node) => (
              <g key={node.id}>
                <motion.circle cx={node.cx} cy={node.cy} r="14" fill="url(#nodeGlow)"
                  animate={{ scale: [1, 2], opacity: [0.5, 0] }}
                  transition={{ repeat: Infinity, duration: 3, delay: node.id * 0.3 }}
                />
                <circle cx={node.cx} cy={node.cy} r="3" fill="#fff" />
                <circle cx={node.cx} cy={node.cy} r="5" fill="transparent" stroke="#FF6B2C" strokeWidth="1.5" opacity="0.8" />
              </g>
            ))}
          </svg>
        </div>
      </motion.div>
    </div>
  );
};

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div style={{ 
      minHeight: '100vh', 
      position: 'relative', 
      fontFamily: 'system-ui, sans-serif',
      background: `
        radial-gradient(circle at 10% 20%, rgba(255, 107, 44, 0.05) 0%, transparent 35%),
        radial-gradient(circle at 85% 60%, rgba(255, 107, 44, 0.04) 0%, transparent 40%),
        radial-gradient(circle at 25% 85%, rgba(255, 107, 44, 0.05) 0%, transparent 45%),
        linear-gradient(145deg, #ffffff 0%, #fffaf7 40%, #ffefe6 100%)
      `
    }}>
      {/* Background Interactive Map Layer */}
      <InteractiveMapVisualizer />

      {/* Keyframes */}
      <style>{`
        @keyframes homeBlob {
          0%,100% { transform: translate(0,0) scale(1);            opacity:0.6; }
          40%      { transform: translate(30px,-40px) scale(1.06);  opacity:0.9; }
          70%      { transform: translate(-20px,-25px) scale(0.96); opacity:0.5; }
        }
        @keyframes homeGeo {
          0%,100% { transform: translateY(0) rotate(0deg);     opacity:0.4; }
          50%      { transform: translateY(-20px) rotate(8deg); opacity:0.8; }
        }
        @keyframes homePulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(255,107,44,0.4); }
          50%      { box-shadow: 0 0 0 12px rgba(255,107,44,0); }
        }
        .home-nav-link { color:#555; text-decoration:none; font-family:monospace; font-size:12px; font-weight:600; transition:color 0.15s; }
        .home-nav-link:hover { color:${ORANGE}; }
        .home-card { transition: transform 0.2s, box-shadow 0.2s; }
        .home-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,0.10) !important; }
        .home-stat-card { transition: transform 0.2s; }
        .home-stat-card:hover { transform: translateY(-3px); }
      `}</style>

      {/* ══ NAVBAR ══ */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        height: 80,
        background: scrolled ? 'rgba(255,255,255,0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(10px)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(0,0,0,0.06)' : 'none',
        transition: 'all 0.25s',
      }}>
        <div style={{
          maxWidth: 1140, margin: '0 auto', padding: '0 28px',
          height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src="/logo.png" alt="Logo" style={{ height: 52, width: 'auto' }} />
            <span style={{ fontFamily: '"Josefin Sans", sans-serif', fontSize: 24, fontWeight: 700, color: '#111', letterSpacing: '0.05em' }}>SAMVAYA</span>
          </div>

          {/* Links */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
            <a href="#features" className="home-nav-link">FEATURES</a>
            <a href="#how" className="home-nav-link">HOW IT WORKS</a>
            <a href="#stats" className="home-nav-link">IMPACT</a>
            <a href="#about" className="home-nav-link">ABOUT</a>
          </div>

          {/* CTA */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={() => navigate('/login')}
              style={{
                background: ORANGE, border: 'none', color: '#fff',
                fontFamily: 'monospace', fontSize: 13, fontWeight: 700,
                letterSpacing: '0.06em', padding: '10px 20px', cursor: 'pointer',
                borderRadius: 0, display: 'flex', alignItems: 'center', gap: 8,
                transition: 'all 0.15s',
                boxShadow: `0 4px 20px ${ORANGE}40, 0 0 35px ${ORANGE}40`,
              }}
              onMouseEnter={e => { e.currentTarget.style.background = '#e85a1f'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = ORANGE; e.currentTarget.style.transform = 'none'; }}
            >
              LOG IN
            </button>
          </div>
        </div>
      </nav>

      {/* ══ HERO ══ */}
      <section style={{
        position: 'relative', overflow: 'hidden',
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        background: 'transparent',
        paddingTop: 64,
      }}>
        {/* Background grid */}
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          backgroundImage: `linear-gradient(rgba(255,107,44,0.035) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(255,107,44,0.035) 1px, transparent 1px)`,
          backgroundSize: '52px 52px',
        }} />

        {/* Blobs */}
        <div style={{
          position: 'absolute', pointerEvents: 'none',
          width: 600, height: 600, borderRadius: '50%',
          background: `radial-gradient(circle, ${ORANGE}26 0%, transparent 70%)`,
          top: -150, right: -100, filter: 'blur(60px)',
          animation: 'homeBlob 20s ease-in-out infinite',
        }} />
        <div style={{
          position: 'absolute', pointerEvents: 'none',
          width: 400, height: 400, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,107,44,0.05) 0%, transparent 70%)',
          bottom: -80, left: -80, filter: 'blur(50px)',
          animation: 'homeBlob 24s ease-in-out infinite reverse',
        }} />

        {/* Floating geo */}
        {[
          { w: 90, h: 90, top: '15%', left: '6%', delay: '0s', dur: '12s' },
          { w: 50, h: 50, bottom: '20%', left: '10%', delay: '4s', dur: '9s', circle: true },
          { w: 65, h: 65, top: '30%', right: '7%', delay: '7s', dur: '14s' },
          { w: 35, h: 35, top: '60%', right: '18%', delay: '2s', dur: '10s', circle: true },
        ].map((g, i) => (
          <div key={i} style={{
            position: 'absolute', pointerEvents: 'none',
            width: g.w, height: g.h,
            border: '1.5px solid rgba(255,107,44,0.12)',
            borderRadius: (g as any).circle ? '50%' : 0,
            ...g,
            animation: `homeGeo ${g.dur} ease-in-out infinite ${g.delay}`,
          }} />
        ))}

        <div style={{ maxWidth: 1140, margin: '0 auto', padding: '0 28px', position: 'relative', zIndex: 2, width: '100%', marginTop: '-10vh' }}>
          <div style={{ maxWidth: 720 }}>

            {/* Headline */}
            <motion.h1 {...fadeUp(0.1)} style={{
              fontFamily: 'monospace', fontSize: 58, fontWeight: 900,
              color: '#0a0a0a', lineHeight: 1.05, letterSpacing: '-0.03em',
              margin: '0 0 24px',
            }}>
              Every Business<br />
              <span style={{ color: ORANGE, textShadow: `0 0 40px ${ORANGE}50` }}>One Identity.</span>
            </motion.h1>

            {/* Sub */}
            <motion.p {...fadeUp(0.2)} style={{
              fontSize: 18, color: '#555', lineHeight: 1.7, margin: '0 0 36px',
              maxWidth: 560,
            }}>
              The <strong style={{ color: '#111' }}>Unified Business Identifier (UBID)</strong> platform
              links fragmented records across Karnataka's government departments into a single,
              AI-verified identity for every registered business.
            </motion.p>

            {/* CTAs */}
            <motion.div {...fadeUp(0.3)} style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
              <button
                onClick={() => navigate('/login')}
                style={{
                  background: ORANGE, border: 'none', color: '#fff',
                  fontFamily: 'monospace', fontSize: 13, fontWeight: 700,
                  letterSpacing: '0.06em', padding: '14px 28px', cursor: 'pointer',
                  borderRadius: 0, display: 'flex', alignItems: 'center', gap: 8,
                  transition: 'all 0.15s',
                  boxShadow: `0 4px 20px ${ORANGE}40, 0 0 35px ${ORANGE}40`,
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#e85a1f'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = ORANGE; e.currentTarget.style.transform = 'none'; }}
              >
                ACCESS PLATFORM <ArrowRight size={15} />
              </button>
              <button
                onClick={() => { const el = document.getElementById('how'); el?.scrollIntoView({ behavior: 'smooth' }); }}
                style={{
                  background: 'transparent', border: '1.5px solid #d0d0d0', color: '#444',
                  fontFamily: 'monospace', fontSize: 13, fontWeight: 600,
                  letterSpacing: '0.04em', padding: '14px 28px', cursor: 'pointer',
                  borderRadius: 0, display: 'flex', alignItems: 'center', gap: 8,
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = ORANGE; e.currentTarget.style.color = ORANGE; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#d0d0d0'; e.currentTarget.style.color = '#444'; }}
              >
                SEE HOW IT WORKS <ChevronRight size={15} />
              </button>
            </motion.div>

            {/* Trust bar */}
            <motion.div {...fadeUp(0.45)} style={{ display: 'flex', alignItems: 'center', gap: 24, marginTop: 48, flexWrap: 'wrap' }}>
              {[
                { text: '40+ Dept. Sources' },
                { text: 'AI-Verified Links' },
                { text: 'Live Activity Scores' },
              ].map(item => (
                <div key={item.text} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#000' }}>{item.text}</span>
                </div>
              ))}
            </motion.div>
          </div>
        </div>

        {/* Scroll Cue */}
        <motion.div {...fadeUp(0.6)} style={{
          position: 'absolute', bottom: 100, left: '50%', transform: 'translateX(-50%)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, cursor: 'pointer', zIndex: 10
        }} onClick={() => { const el = document.getElementById('stats'); el?.scrollIntoView({ behavior: 'smooth' }); }}>
          <span style={{ fontFamily: 'monospace', fontSize: 10, fontWeight: 700, color: '#000', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Explore Platform
          </span>
          <motion.div animate={{ y: [0, 6, 0] }} transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}>
            <ArrowRight size={14} color="#000" style={{ transform: 'rotate(90deg)' }} />
          </motion.div>
        </motion.div>

        {/* Floating Eyebrow (Bottom Right) */}
        <motion.div {...fadeUp(0.5)} style={{
          position: 'absolute', bottom: 100, right: 40, zIndex: 10,
        }}>
          <span style={{
            fontFamily: 'monospace', fontSize: 11, fontWeight: 700,
            color: ORANGE, letterSpacing: '0.12em', textTransform: 'uppercase',
            background: `${ORANGE}10`, border: `1px solid ${ORANGE}30`,
            padding: '5px 12px', borderRadius: 2,
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: ORANGE, display: 'inline-block' }} />
            Government of Karnataka · Unified Business Registry
          </span>
        </motion.div>
      </section>

      {/* ══ STATS BAND ══ */}
      <section id="stats" style={{ background: '#0a0a0a', padding: '56px 28px' }}>
        <div style={{ maxWidth: 1140, margin: '0 auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2 }}>
            {[
              { value: '50,000+', label: 'Businesses Registered', color: ORANGE },
              { value: '40+', label: 'Govt. Dept. Sources', color: '#52c41a' },
              { value: '97%', label: 'Auto-Link Accuracy', color: '#1677ff' },
              { value: '< 1s', label: 'Lookup Response Time', color: '#722ed1' },
            ].map(s => (
              <div key={s.label} className="home-stat-card" style={{
                padding: '32px 28px',
                background: '#111', border: '1px solid #1a1a1a',
                textAlign: 'center',
              }}>
                <div style={{
                  fontFamily: 'monospace', fontWeight: 900, fontSize: 42,
                  color: s.color, lineHeight: 1, marginBottom: 8,
                }}>
                  {s.value}
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#666', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ FEATURES ══ */}
      <section id="features" style={{ padding: '100px 28px', background: 'transparent' }}>
        <div style={{ maxWidth: 1140, margin: '0 auto' }}>
          <motion.div {...fadeUp()} style={{ textAlign: 'center', marginBottom: 60 }}>
            <span style={{
              fontFamily: 'monospace', fontSize: 18, fontWeight: 700,
              color: ORANGE, letterSpacing: '0.12em', textTransform: 'uppercase',
            }}>
              Platform Capabilities
            </span>
            <h2 style={{
              fontFamily: 'monospace', fontSize: 38, fontWeight: 900,
              color: '#0a0a0a', margin: '10px 0 16px', letterSpacing: '-0.02em',
            }}>
              Built for scale. Built for trust.
            </h2>
            <p style={{ color: '#777', fontSize: 16, maxWidth: 520, margin: '0 auto', lineHeight: 1.65 }}>
              Every feature is designed to turn fragmented government data into actionable, verified business intelligence.
            </p>
          </motion.div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 32 }}>
            {[
              {
                title: 'Cross-Department Linking',
                desc: 'Automatically matches records from Shop Establishment, Factories, Labour, and KSPCB using a trained LightGBM model with SHAP-explainable scores.',
                accent: ORANGE,
              },
              {
                title: 'AI-Powered Verification',
                desc: 'Every link is scored, calibrated, and explained. Ambiguous cases are routed to a human reviewer queue with full context.',
                accent: '#722ed1',
              },
              {
                title: 'Live Activity Intelligence',
                desc: 'Track business activity through compliance filings, electricity consumption, inspection visits, and more — with time-decay weighted signals.',
                accent: '#52c41a',
              },
              {
                title: 'Natural Language Search',
                desc: 'Query the UBID directory using plain English. The NLP layer translates intent into structured filters across all department sources.',
                accent: '#1677ff',
              },
              {
                title: 'PAN & GSTIN Anchoring',
                desc: 'Businesses with matching tax identifiers are anchored automatically, creating a trust hierarchy from verified financial identity.',
                accent: ORANGE,
              },
              {
                title: 'Analytics & Reporting',
                desc: 'Real-time dashboards showing model health, queue depth, auto-link rates, and entity resolution progress — all in one view.',
                accent: '#faad14',
              },
            ].map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, x: -80, rotateY: 25, scale: 0.9 }}
                whileInView={{ opacity: 1, x: 0, rotateY: 0, scale: 1 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ delay: i * 0.12, duration: 0.65, type: 'spring', bounce: 0.3 }}
                style={{ height: '100%' }}
              >
                <Feature3DCard f={f} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ HOW IT WORKS ══ */}
      <section id="how" style={{ padding: '100px 28px', background: '#0a0a0a', overflow: 'hidden' }}>
        <div style={{ maxWidth: 1140, margin: '0 auto' }}>

          {/* Heading */}
          <motion.div {...fadeUp()} style={{ textAlign: 'center', marginBottom: 80 }}>
            <span style={{
              fontFamily: 'monospace', fontSize: 18, fontWeight: 700,
              color: ORANGE, letterSpacing: '0.12em', textTransform: 'uppercase',
            }}>
              How It Works
            </span>
            <h2 style={{
              fontFamily: 'monospace', fontSize: 36, fontWeight: 900,
              color: '#fff', margin: '10px 0 0', letterSpacing: '-0.02em',
            }}>
              From raw data to verified identity
            </h2>
          </motion.div>

          {/* Flow diagram */}
          <div style={{ position: 'relative' }}>

            {/* Animated connecting line */}
            <div style={{
              position: 'absolute', top: 56, left: '12.5%', right: '12.5%',
              height: 2, background: '#1e1e1e', zIndex: 0,
            }}>
              <motion.div
                initial={{ scaleX: 0 }}
                whileInView={{ scaleX: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
                style={{
                  position: 'absolute', inset: 0,
                  background: `linear-gradient(90deg, ${ORANGE}, #ff9a6c, ${ORANGE})`,
                  transformOrigin: 'left',
                }}
              />
              {/* Animated pulse dot */}
              <motion.div
                animate={{ left: ['0%', '100%'] }}
                transition={{ repeat: Infinity, duration: 2.5, ease: 'linear', delay: 1.5 }}
                style={{
                  position: 'absolute', top: '50%', transform: 'translateY(-50%)',
                  width: 10, height: 10, borderRadius: '50%',
                  background: '#fff',
                  boxShadow: `0 0 12px 4px ${ORANGE}`,
                }}
              />
            </div>

            {/* Step cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24, position: 'relative', zIndex: 1 }}>
              {[
                {
                  step: '01', title: 'Ingest', icon: UploadCloud,
                  desc: 'Records from 40+ govt. department databases are ingested and normalised daily.',
                  color: '#1677ff',
                },
                {
                  step: '02', title: 'Score', icon: Cpu,
                  desc: 'Each record pair is scored by a LightGBM model across 13 features with SHAP explanations.',
                  color: '#722ed1',
                },
                {
                  step: '03', title: 'Assign UBID', icon: GitMerge,
                  desc: 'High-confidence matches receive a UBID automatically. Borderline cases go to human review.',
                  color: ORANGE,
                },
                {
                  step: '04', title: 'Publish', icon: Share2,
                  desc: 'The verified UBID registry is available for lookup, analytics, and downstream integrations.',
                  color: '#52c41a',
                },
              ].map((s, i) => {
                const Icon = s.icon;
                return (
                  <motion.div
                    key={s.step}
                    initial={{ opacity: 0, y: 50 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ delay: i * 0.18, duration: 0.6, type: 'spring', bounce: 0.3 }}
                  >
                    {/* Icon circle on the line */}
                    <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 28 }}>
                      <motion.div
                        whileHover={{ scale: 1.12 }}
                        style={{
                          width: 56, height: 56, borderRadius: '50%',
                          background: '#111',
                          border: `2px solid ${s.color}`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          boxShadow: `0 0 20px ${s.color}40`,
                          position: 'relative', zIndex: 2,
                        }}
                      >
                        <Icon size={22} color={s.color} />
                      </motion.div>
                    </div>

                    {/* Card */}
                    <motion.div
                      whileHover={{ y: -6, boxShadow: `0 24px 48px rgba(0,0,0,0.4), 0 0 0 1px ${s.color}40` }}
                      transition={{ duration: 0.2 }}
                      style={{
                        background: '#111',
                        border: `1px solid #1e1e1e`,
                        borderTop: `3px solid ${s.color}`,
                        borderRadius: 4,
                        padding: '28px 24px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                      }}
                    >
                      <div style={{
                        fontFamily: 'monospace', fontSize: 11, fontWeight: 700,
                        color: s.color, letterSpacing: '0.15em', marginBottom: 10,
                      }}>
                        STEP {s.step}
                      </div>
                      <h3 style={{
                        fontFamily: 'monospace', fontSize: 20, fontWeight: 800,
                        color: '#fff', margin: '0 0 12px', letterSpacing: '-0.01em',
                      }}>
                        {s.title}
                      </h3>
                      <p style={{
                        fontSize: 13.5, color: '#888', lineHeight: 1.65, margin: 0,
                      }}>
                        {s.desc}
                      </p>
                    </motion.div>
                  </motion.div>
                );
              })}
            </div>

            {/* Bottom "result" banner */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.9, duration: 0.6 }}
              style={{
                marginTop: 48,
                background: `linear-gradient(135deg, ${ORANGE}18, ${ORANGE}08)`,
                border: `1px solid ${ORANGE}40`,
                borderRadius: 4,
                padding: '20px 32px',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16,
              }}
            >
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
                style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: ORANGE,
                  boxShadow: `0 0 10px ${ORANGE}`,
                }}
              />
              <span style={{
                fontFamily: 'monospace', fontSize: 13, fontWeight: 700,
                color: ORANGE, letterSpacing: '0.1em', textTransform: 'uppercase',
              }}>
                Output: Unified UBID Registry
              </span>
              <span style={{ fontFamily: 'monospace', fontSize: 13, color: '#666' }}>
                — one verified identity per business, available across all departments
              </span>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ══ ABOUT / MISSION ══ */}
      <section id="about" style={{ padding: '100px 28px', background: '#0a0a0a' }}>
        <div style={{ maxWidth: 1140, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'center' }}>
          <div>
            <span style={{
              fontFamily: 'monospace', fontSize: 11, fontWeight: 700,
              color: ORANGE, letterSpacing: '0.12em', textTransform: 'uppercase', display: 'block', marginBottom: 14,
            }}>
              Our Mission
            </span>
            <h2 style={{
              fontFamily: 'monospace', fontSize: 38, fontWeight: 900,
              color: '#fff', margin: '0 0 20px', letterSpacing: '-0.02em', lineHeight: 1.1,
            }}>
              Samvaya —<br />
              <span style={{ color: ORANGE }}>bringing it all together.</span>
            </h2>
            <p style={{ color: '#888', fontSize: 15, lineHeight: 1.75, margin: '0 0 28px' }}>
              Karnataka's businesses register with multiple government departments independently — each issuing a different ID,
              storing different data, with no shared link. <strong style={{ color: '#ccc' }}>Samvaya</strong> solves this
              by building a unified identity layer on top of existing systems, without replacing them.
            </p>
            <p style={{ color: '#888', fontSize: 15, lineHeight: 1.75, margin: 0 }}>
              Every UBID is a verified, AI-constructed link between a real business entity and its presence
              across all departments — enabling better compliance tracking, fraud detection, and policy analysis.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { label: 'Shop & Establishment', color: '#1677ff', count: 'Dept 1' },
              { label: 'Factories Act', color: ORANGE, count: 'Dept 2' },
              { label: 'Labour Department', color: '#722ed1', count: 'Dept 3' },
              { label: 'KSPCB Pollution', color: '#52c41a', count: 'Dept 4' },
            ].map(d => (
              <div key={d.label} style={{
                background: '#111', border: `1px solid ${d.color}30`,
                padding: '20px 18px', borderRadius: 2,
                borderTop: `3px solid ${d.color}`,
              }}>
                <div style={{
                  fontFamily: 'monospace', fontSize: 10, color: d.color,
                  letterSpacing: '0.1em', fontWeight: 700, marginBottom: 8,
                }}>
                  {d.count}
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: 13, color: '#ddd', fontWeight: 600 }}>
                  {d.label}
                </div>
              </div>
            ))}
            <div style={{
              gridColumn: '1 / -1',
              background: `${ORANGE}10`, border: `1px solid ${ORANGE}30`,
              padding: '18px',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <div>
                <div style={{ fontFamily: 'monospace', fontSize: 11, color: ORANGE, fontWeight: 700, letterSpacing: '0.08em' }}>
                  UBID REGISTRY
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#ddd', marginTop: 2 }}>
                  One verified identity across all sources
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══ WHY TRUST US BAND ══ */}
      <section id="trust" style={{
        padding: '64px 28px',
        background: '#fff', borderTop: '1px solid #f0f0f0',
        perspective: 1000
      }}>
        <div style={{ maxWidth: 1140, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <h2 style={{
              fontFamily: 'monospace', fontSize: 34, fontWeight: 900,
              color: ORANGE, letterSpacing: '-0.02em',
            }}>
              Why trust us?
            </h2>
            <div style={{ width: 60, height: 4, background: '#0a0a0a', margin: '8px auto 0' }} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 32 }}>
            {[
              {
                title: 'Your Business Identity, Verified Once and Trusted Everywhere',
                desc: 'One AI-verified UBID replaces years of fragmented paperwork across every government touchpoint.'
              },
              {
                title: 'Built to Never Break What Already Works',
                desc: 'Every connection is read-only — your department systems stay untouched, unaware, and uninterrupted.'
              },
              {
                title: 'Every Decision Explained, Logged, and Reversible',
                desc: 'No black boxes. Every AI match shows its reasoning — and can be undone with a full audit trail.'
              },
              {
                title: 'Live Intelligence, Not Stale Records From Six Months Ago',
                desc: 'Every licence, inspection, and filing — updated in real time, so your status is never in question.'
              }
            ].map((point, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -80, rotateY: 25, scale: 0.9 }}
                whileInView={{ opacity: 1, x: 0, rotateY: 0, scale: 1 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ delay: i * 0.2, duration: 0.7, type: 'spring', bounce: 0.3 }}
                style={{
                  background: '#fafafa',
                  border: '1px solid #eaeaea',
                  padding: 32,
                  borderRadius: 12,
                  transformStyle: 'preserve-3d',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.03)'
                }}
              >
                <h3 style={{
                  fontFamily: 'monospace', fontSize: 18, fontWeight: 800,
                  color: '#111', margin: '0 0 12px', lineHeight: 1.4
                }}>
                  <span style={{ color: ORANGE, marginRight: 8 }}>0{i+1}.</span>
                  {point.title}
                </h3>
                <p style={{
                  color: '#111', fontSize: 15, lineHeight: 1.6, margin: 0,
                  fontFamily: 'sans-serif'
                }}>
                  {point.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ FOOTER ══ */}
      <footer style={{ background: '#0a0a0a', padding: '32px 28px', borderTop: '1px solid #1a1a1a' }}>
        <div style={{
          maxWidth: 1140, margin: '0 auto',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src="/logo.png" alt="Logo" style={{ height: 40, width: 'auto' }} />
            <span style={{ fontFamily: '"Josefin Sans", sans-serif', fontSize: 24, fontWeight: 700, color: '#fff', letterSpacing: '0.05em' }}>SAMVAYA</span>
          </div>
          <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#fff' }}>
            © 2026 Government of Karnataka. All rights reserved.
          </span>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;