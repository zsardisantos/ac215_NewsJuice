import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { signInWithEmailAndPassword } from 'firebase/auth';
import { auth } from '../firebase/config';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  //below is the main login function with firebase user auth
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    try {
      // Firebase Auth login
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;

      // Get JWT token
      const token = await user.getIdToken();

      // Store token and user ID
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user_id', user.uid);

      // Create user in CloudSQL (if not exists)
      try {
       // const backendUrl = window.location.hostname.includes('newsjuiceapp.com') || window.location.hostname === '34.28.40.119'
       //   ? 'http://136.113.170.71'
        //  : 'http://136.113.170.71';

        const backendUrl = window.location.hostname.includes('newsjuiceapp.com')
          ? ''
          : 'http://localhost:8080';



        const response = await fetch(`${backendUrl}/api/user/create`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
          console.error('[login] Failed to create user in backend:', errorData);
          // Still navigate - user is created in Firebase, backend will retry later
        } else {
          const data = await response.json();
          console.log('[login] User ensured in CloudSQL:', data);
        }
      } catch (error) {
        console.error('[login] Error calling backend:', error);
        // Still navigate - user is created in Firebase
      }

      navigate('/podcast');
    } catch (error) {
      setError(error.message);
    }
  };

  return (
    <div className="min-h-screen bg-primary-darker relative overflow-hidden flex items-center justify-center px-6">
      {/* Gradient Orbs Background */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-primary-purple rounded-full filter blur-3xl opacity-30 -translate-x-1/2 -translate-y-1/2"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-primary-purple rounded-full filter blur-3xl opacity-20 translate-x-1/3 translate-y-1/3"></div>
      
      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Login</h1>
          <p className="text-gray-400">Please enter your credentials to continue.</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-500/20 border border-red-500 rounded-full text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm mb-2 text-gray-300">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="abhixyxyz@gmail.com"
              className="w-full px-6 py-4 bg-transparent border border-gray-700 rounded-full text-white placeholder-gray-500 focus:outline-none focus:border-primary-pink transition-colors"
              required
            />
          </div>

          <div>
            <label className="block text-sm mb-2 text-gray-300">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-6 py-4 bg-transparent border border-gray-700 rounded-full text-white placeholder-gray-500 focus:outline-none focus:border-primary-pink transition-colors pr-12"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <div className="text-right">
            <Link to="/register" className="text-primary-pink text-sm hover:underline">
              Forgot Password?
            </Link>
          </div>

          <button
            type="submit"
            className="w-full py-4 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all"
          >
            Login
          </button>

          <div className="text-center text-gray-400 text-sm">Or login with</div>

          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              className="py-3 px-6 bg-transparent border border-gray-700 rounded-full flex items-center justify-center gap-2 hover:border-gray-500 transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="white">
                <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
              </svg>
              <span>Apple</span>
            </button>
            <button
              type="button"
              className="py-3 px-6 bg-transparent border border-gray-700 rounded-full flex items-center justify-center gap-2 hover:border-gray-500 transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span>Google</span>
            </button>
          </div>

          <div className="text-center text-gray-400 text-sm">
            Don't have account?{' '}
            <Link to="/register" className="text-primary-pink hover:underline">
              Register
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Login
