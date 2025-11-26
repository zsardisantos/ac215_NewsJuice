import { useState } from 'react'
import { createUserWithEmailAndPassword } from 'firebase/auth';
import { auth } from '../firebase/config';
import { useNavigate, Link } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'

"How this works"
"1. User fills out registration form (on Registration.jsx) "
"2. Firebase Authenticates their form data, user email and pwd with the createUserWithEmailandPassword() helper"

function Registration() {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    repeatPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showRepeatPassword, setShowRepeatPassword] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    // Validate passwords match
    if (formData.password !== formData.repeatPassword) {
      setError('Passwords do not match');
      return;
    }

    // Validate password length
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    try {
      // Firebase Auth signup
      const userCredential = await createUserWithEmailAndPassword(auth, formData.email, formData.password);
      const user = userCredential.user;
      
      // Get token
      const token = await user.getIdToken();
      
      // Store token and user ID
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user_id', user.uid);

      // Create user in CloudSQL
      try {
        const backendUrl = window.location.hostname.includes('newsjuiceapp.com')
          ? 'https://chatter-919568151211.us-central1.run.app'
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
          console.error('[registration] Failed to create user in backend:', errorData);
          // Still navigate - user is created in Firebase, just not in CloudSQL yet
        } else {
          const data = await response.json();
          console.log('[registration] User created in CloudSQL:', data);
        }
      } catch (error) {
        console.error('[registration] Error calling backend:', error);
        // Still navigate - user is created in Firebase, just not in CloudSQL yet
      }
      
      navigate('/podcast');
    } catch (error) {
      setError(error.message);
    }
  };

  return (
    <div className="min-h-screen bg-primary-darker relative overflow-hidden flex items-center justify-center px-6 py-12">
      {/* Gradient Orbs Background */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-primary-purple rounded-full filter blur-3xl opacity-30 -translate-x-1/2 -translate-y-1/2"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-primary-purple rounded-full filter blur-3xl opacity-20 translate-x-1/3 translate-y-1/3"></div>
      
      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Registration</h1>
          <p className="text-gray-400">Please fill in the details to create your account.</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-500/20 border border-red-500 rounded-full text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-6">
          <div>
            <label className="block text-sm mb-2 text-gray-300">Full Name</label>
            <input
              type="text"
              name="fullName"
              value={formData.fullName}
              onChange={handleChange}
              placeholder="Abhishek Patel"
              className="w-full px-6 py-4 bg-transparent border border-gray-700 rounded-full text-white placeholder-gray-500 focus:outline-none focus:border-primary-pink transition-colors"
              required
            />
          </div>

          <div>
            <label className="block text-sm mb-2 text-gray-300">Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
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
                name="password"
                value={formData.password}
                onChange={handleChange}
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

          <div>
            <label className="block text-sm mb-2 text-gray-300">Repeat Password</label>
            <div className="relative">
              <input
                type={showRepeatPassword ? 'text' : 'password'}
                name="repeatPassword"
                value={formData.repeatPassword}
                onChange={handleChange}
                placeholder="••••••••"
                className="w-full px-6 py-4 bg-transparent border border-gray-700 rounded-full text-white placeholder-gray-500 focus:outline-none focus:border-primary-pink transition-colors pr-12"
                required
              />
              <button
                type="button"
                onClick={() => setShowRepeatPassword(!showRepeatPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
              >
                {showRepeatPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-4 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all"
          >
            Register
          </button>

          <div className="text-center text-gray-400 text-sm">
            I have account?{' '}
            <Link to="/login" className="text-primary-pink hover:underline">
              Log in
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Registration
