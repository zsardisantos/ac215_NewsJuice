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
