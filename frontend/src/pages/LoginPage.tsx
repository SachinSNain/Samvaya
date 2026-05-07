import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Eye, EyeOff, AlertCircle, Zap } from 'lucide-react';
import './LoginPage.css';

const ORANGE = '#FF6B2C';

const titleWords = ['WELCOME', 'BACK'];

interface FormState { email: string; password: string; rememberMe: boolean; }
interface FieldErrors { email?: string; password?: string; }

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>({ email: '', password: '', rememberMe: false });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const validate = (): boolean => {
    const errors: FieldErrors = {};
    if (!form.email.trim()) errors.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) errors.email = 'Enter a valid email.';
    if (!form.password) errors.password = 'Password is required.';
    else if (form.password.length < 6) errors.password = 'At least 6 characters.';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Authorised accounts — add entries here as needed
  const VALID_ACCOUNTS: Record<string, string> = {
    'admin@gov.in': 'admin123',
    'reviewer@gov.in': 'ubid@review2024',
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError('');
    if (!validate()) return;
    setLoading(true);

    // Simulate a brief network delay so it feels like a real auth call
    await new Promise(res => setTimeout(res, 600));

    const email = form.email.trim().toLowerCase();
    const expectedPassword = VALID_ACCOUNTS[email];

    if (expectedPassword && form.password === expectedPassword) {
      localStorage.setItem('ubid_authed', '1');
      localStorage.setItem('ubid_user', email);
      navigate('/dashboard');
    } else {
      setApiError('Invalid email or password.');
    }

    setLoading(false);
  };

  const handleChange = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm(prev => ({ ...prev, [field]: value }));
    if (fieldErrors[field as keyof FieldErrors]) setFieldErrors(prev => ({ ...prev, [field]: undefined }));
    setApiError('');
  };

  return (
    <div className="login-page-root" style={{
      minHeight: '100vh', position: 'relative', overflow: 'hidden', background: '#fff'
    }}>
      {/* Background layer with transparency and slight glow */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'url(/loginpage_bg.png) center/cover no-repeat',
        opacity: 0.2,
        filter: 'drop-shadow(0 0 30px rgba(255, 107, 44, 0.2)) brightness(1.02)',
        zIndex: 0, pointerEvents: 'none'
      }} />

      {/* Keyframe definitions */}
      <style>{`
        @keyframes blobDrift {
          0%,100% { transform: translate(0,0) scale(1);          opacity:0.7; }
          33%      { transform: translate(20px,-30px) scale(1.04); opacity:1;   }
          66%      { transform: translate(-15px,-20px) scale(0.97);opacity:0.6; }
        }
        @keyframes geoFloat {
          0%,100% { transform: translateY(0) rotate(0deg);    opacity:0.5; }
          50%      { transform: translateY(-18px) rotate(6deg); opacity:0.9; }
        }
        @keyframes loginSpin {
          to { transform: rotate(360deg); }
        }
      `}</style>

      {/* ═══ HEADER ═══ */}
      <header style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 20,
        background: 'transparent',
      }}>
        <div style={{
          maxWidth: 1100, margin: '0 auto', padding: '0 24px',
          height: 80, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          {/* Logo */}
          <a href="/" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
            <img src="/logo.png" alt="Logo" style={{ height: 52, width: 'auto' }} />
            <span style={{ fontFamily: '"Josefin Sans", sans-serif', fontSize: 24, fontWeight: 700, color: '#111', letterSpacing: '0.05em' }}>SAMVAYA</span>
          </a>

          {/* Nav removed per request */}
        </div>
      </header>

      {/* ═══ MAIN ═══ */}
      <main style={{
        position: 'relative', zIndex: 10,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        minHeight: '100vh', padding: '0 16px 12vh',
      }}>

        {/* Animated title */}
        <motion.h1
          initial={{ filter: 'blur(10px)', opacity: 0 }}
          animate={{ filter: 'blur(0px)', opacity: 1 }}
          transition={{ duration: 0.5 }}
          style={{
            fontFamily: 'monospace', fontSize: 40, fontWeight: 800,
            color: '#111', letterSpacing: '-0.02em', marginBottom: 8,
            display: 'flex', gap: 14,
          }}
        >
          {titleWords.map((word, i) => (
            <motion.span
              key={word}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.18, duration: 0.5 }}
              style={{ display: 'inline-block', color: i === 1 ? ORANGE : undefined }}
            >
              {word}
            </motion.span>
          ))}
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          style={{ fontFamily: 'monospace', fontSize: 13, color: '#888', marginBottom: 36, letterSpacing: '0.04em' }}
        >
          Sign in to the UBID Platform
        </motion.p>

        {/* ── Login Card ── */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.55, type: 'spring', stiffness: 100, damping: 16 }}
          style={{
            width: '100%', maxWidth: 440,
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 107, 44, 0.2)',
            borderRadius: 8,
            boxShadow: '0 8px 40px rgba(0,0,0,0.08)',
          }}
        >
          {/* Top accent bar */}
          <div style={{ height: 4, width: '100%', background: `linear-gradient(90deg, ${ORANGE}, #ffa07a)` }} />

          <div style={{ padding: '32px 32px 28px' }}>

            {/* API error */}
            {apiError && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  padding: '12px 14px', marginBottom: 20,
                  background: '#fef2f2', border: '1px solid #fecaca',
                }}
                role="alert"
              >
                <AlertCircle size={15} color="#ef4444" style={{ marginTop: 1, flexShrink: 0 }} />
                <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#dc2626' }}>{apiError}</span>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} noValidate>

              {/* Email */}
              <div style={{ marginBottom: 28 }}>
                <label htmlFor="login-email" style={{
                  display: 'block', fontSize: 11, fontWeight: 700, fontFamily: 'monospace',
                  letterSpacing: '0.1em', textTransform: 'uppercase', color: '#555', marginBottom: 6,
                }}>
                  Email Address
                </label>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={handleChange('email')}
                  disabled={loading}
                  style={{
                    width: '100%', height: 42, padding: '0 12px', boxSizing: 'border-box',
                    fontFamily: 'monospace', fontSize: 13, color: '#111',
                    background: 'rgba(255,255,255,0.85)',
                    border: `1.5px solid ${fieldErrors.email ? '#f87171' : 'rgba(255,107,44,0.3)'}`,
                    borderRadius: 6, outline: 'none',
                    boxShadow: fieldErrors.email ? '0 0 0 3px rgba(248,113,113,0.15)' : 'none',
                    transition: 'border-color 0.15s, box-shadow 0.15s, background 0.15s',
                  }}
                  onFocus={e => { e.currentTarget.style.borderColor = ORANGE; e.currentTarget.style.boxShadow = `0 0 0 3px ${ORANGE}20`; }}
                  onBlur={e => { e.currentTarget.style.borderColor = fieldErrors.email ? '#f87171' : 'rgba(255,107,44,0.3)'; e.currentTarget.style.boxShadow = 'none'; }}
                />
                {fieldErrors.email && (
                  <p style={{ fontFamily: 'monospace', fontSize: 11, color: '#ef4444', marginTop: 4 }}>{fieldErrors.email}</p>
                )}
              </div>

              {/* Password */}
              <div style={{ marginBottom: 28 }}>
                <label htmlFor="login-password" style={{
                  display: 'block', fontSize: 11, fontWeight: 700, fontFamily: 'monospace',
                  letterSpacing: '0.1em', textTransform: 'uppercase', color: '#555', marginBottom: 6,
                }}>
                  Password
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="login-password"
                    type={showPw ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={form.password}
                    onChange={handleChange('password')}
                    disabled={loading}
                    style={{
                      width: '100%', height: 42, padding: '0 40px 0 12px', boxSizing: 'border-box',
                      fontFamily: 'monospace', fontSize: 13, color: '#111',
                      background: 'rgba(255,255,255,0.85)',
                      border: `1.5px solid ${fieldErrors.password ? '#f87171' : 'rgba(255,107,44,0.3)'}`,
                      borderRadius: 6, outline: 'none',
                      boxShadow: fieldErrors.password ? '0 0 0 3px rgba(248,113,113,0.15)' : 'none',
                      transition: 'border-color 0.15s, box-shadow 0.15s, background 0.15s',
                    }}
                    onFocus={e => { e.currentTarget.style.borderColor = ORANGE; e.currentTarget.style.boxShadow = `0 0 0 3px ${ORANGE}20`; }}
                    onBlur={e => { e.currentTarget.style.borderColor = fieldErrors.password ? '#f87171' : 'rgba(255,107,44,0.3)'; e.currentTarget.style.boxShadow = 'none'; }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(p => !p)}
                    style={{
                      position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                      background: 'none', border: 'none', cursor: 'pointer', padding: 4,
                      color: '#9ca3af', display: 'flex', alignItems: 'center',
                    }}
                    aria-label={showPw ? 'Hide password' : 'Show password'}
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {fieldErrors.password && (
                  <p style={{ fontFamily: 'monospace', fontSize: 11, color: '#ef4444', marginTop: 4 }}>{fieldErrors.password}</p>
                )}
              </div>

              <div style={{ marginBottom: 22 }} />

              {/* Submit */}
              <button
                id="login-submit-btn"
                type="submit"
                disabled={loading}
                style={{
                  width: '100%', height: 44, border: 'none', borderRadius: 0,
                  background: ORANGE, color: '#fff',
                  fontFamily: 'monospace', fontSize: 12, fontWeight: 700,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.7 : 1,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  transition: 'background 0.15s, transform 0.15s, box-shadow 0.15s',
                }}
                onMouseEnter={e => { if (!loading) { e.currentTarget.style.background = '#e85a1f'; e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 4px 14px rgba(255,107,44,0.35)'; } }}
                onMouseLeave={e => { e.currentTarget.style.background = ORANGE; e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                {loading ? (
                  <>
                    <span style={{
                      width: 14, height: 14, borderRadius: '50%',
                      border: '2px solid rgba(255,255,255,0.35)', borderTopColor: '#fff',
                      animation: 'loginSpin 0.65s linear infinite', flexShrink: 0,
                      display: 'inline-block',
                    }} />
                    SIGNING IN...
                  </>
                ) : (
                  <>SIGN IN <ArrowRight size={13} /></>
                )}
              </button>
            </form>

            {/* Socials removed */}
          </div>
        </motion.div>

        {/* Auth footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.1, duration: 0.5 }}
          style={{ fontFamily: 'monospace', fontSize: 12, color: '#000', marginTop: 24, display: 'flex', alignItems: 'center', gap: 6, letterSpacing: '0.05em', fontWeight: 600 }}
        >
          <AlertCircle size={14} /> AUTHORIZED PERSONNEL ONLY
        </motion.div>

        {/* Feature chips */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.3, duration: 0.5 }}
          style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 28, marginTop: 40 }}
        >
          {['Predictive Analytics', 'Machine Learning', 'NLP Processing'].map((label, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.3 + i * 0.12, duration: 0.4 }}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Zap size={13} color={ORANGE} />
              <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#000', letterSpacing: '0.04em', fontWeight: 600 }}>{label}</span>
            </motion.div>
          ))}
        </motion.div>
      </main>
    </div>
  );
};

export default LoginPage;