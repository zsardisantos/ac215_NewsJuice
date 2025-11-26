import { useState } from 'react'
import { ArrowLeft, Eye, EyeOff, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

function Settings() {
  const navigate = useNavigate()
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const [accountInfo, setAccountInfo] = useState({
    firstName: 'John',
    lastName: 'Johny',
    country: 'United States',
    email: 'johnyjohnson@exmail.com',
    phone: '+1 (555) 666-6666'
  })

  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: ''
  })

  const handleAccountChange = (field, value) => {
    setAccountInfo({ ...accountInfo, [field]: value })
  }

  const handlePasswordChange = (field, value) => {
    setPasswords({ ...passwords, [field]: value })
  }

  const handleSaveAccount = (e) => {
    e.preventDefault()
    alert('Account information saved!')
  }

  const handleSavePassword = (e) => {
    e.preventDefault()
    alert('Password updated!')
  }

  return (
    <div className="min-h-screen bg-primary-darker text-white">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-primary-darker/80 backdrop-blur-lg border-b border-gray-800">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/podcast')}
            className="p-2 hover:bg-gray-800 rounded-full transition-colors"
          >
            <ArrowLeft size={24} />
          </button>
          <div className="flex items-center gap-3">
            <span className="text-sm">Hello, Welcome 👋</span>
            <div className="w-10 h-10 bg-gradient-to-br from-primary-pink to-primary-purple rounded-full flex items-center justify-center">
              <User size={20} />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-8 space-y-8">
        {/* My Account Section */}
        <section>
          <h2 className="text-2xl font-bold mb-2">My Account</h2>
          <p className="text-gray-400 text-sm mb-6">
            Manage your account information, such as your email address, phone number, and personal information.
          </p>

          <form onSubmit={handleSaveAccount} className="space-y-6">
            <div className="bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-6 border border-gray-700 space-y-4">
              <h3 className="font-semibold mb-4">Basic settings</h3>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">First name</label>
                <input
                  type="text"
                  value={accountInfo.firstName}
                  onChange={(e) => handleAccountChange('firstName', e.target.value)}
                  className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white focus:outline-none focus:border-primary-pink transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Last name</label>
                <input
                  type="text"
                  value={accountInfo.lastName}
                  onChange={(e) => handleAccountChange('lastName', e.target.value)}
                  className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white focus:outline-none focus:border-primary-pink transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Country</label>
                <select
                  value={accountInfo.country}
                  onChange={(e) => handleAccountChange('country', e.target.value)}
                  className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white focus:outline-none focus:border-primary-pink transition-colors"
                >
                  <option value="United States">🇺🇸 United States</option>
                  <option value="Canada">🇨🇦 Canada</option>
                  <option value="United Kingdom">🇬🇧 United Kingdom</option>
                  <option value="Australia">🇦🇺 Australia</option>
                </select>
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  className="px-8 py-3 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all"
                >
                  Save
                </button>
                <button
                  type="button"
                  className="px-8 py-3 bg-transparent border border-gray-600 rounded-full text-gray-300 hover:border-gray-500 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>

            <div className="bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-6 border border-gray-700 space-y-4">
              <h3 className="font-semibold mb-4">Contact info</h3>
              <p className="text-gray-400 text-sm mb-4">
                Manage your contact information, including email and phone number.
              </p>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Email</label>
                <input
                  type="email"
                  value={accountInfo.email}
                  onChange={(e) => handleAccountChange('email', e.target.value)}
                  className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white focus:outline-none focus:border-primary-pink transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Phone number</label>
                <input
                  type="tel"
                  value={accountInfo.phone}
                  onChange={(e) => handleAccountChange('phone', e.target.value)}
                  className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white focus:outline-none focus:border-primary-pink transition-colors"
                />
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  className="px-8 py-3 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all"
                >
                  Save
                </button>
                <button
                  type="button"
                  className="px-8 py-3 bg-transparent border border-gray-600 rounded-full text-gray-300 hover:border-gray-500 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        </section>

        {/* Password Settings */}
        <section>
          <h2 className="text-2xl font-bold mb-2">Password settings</h2>
          <p className="text-gray-400 text-sm mb-6">
            Reset your password to keep your security. Your new password must be different from previous passwords.
          </p>

          <form onSubmit={handleSavePassword} className="bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-6 border border-gray-700 space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Current password</label>
              <div className="relative">
                <input
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={passwords.current}
                  onChange={(e) => handlePasswordChange('current', e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-pink transition-colors pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  {showCurrentPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">New password</label>
              <div className="relative">
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={passwords.new}
                  onChange={(e) => handlePasswordChange('new', e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-pink transition-colors pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Confirm password</label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={passwords.confirm}
                  onChange={(e) => handlePasswordChange('confirm', e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-pink transition-colors pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-3 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all"
            >
              Save
            </button>

            <button
              type="button"
              className="w-full py-3 bg-transparent border border-gray-600 rounded-full text-gray-300 hover:border-gray-500 transition-colors"
            >
              Reset password
            </button>
          </form>
        </section>

        {/* Time Zone Settings */}
        <section className="bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-6 border border-gray-700 space-y-4">
          <h3 className="font-semibold">Time zone settings</h3>
          <p className="text-gray-400 text-sm">
            Set your profile time zone for accurate scheduling.
          </p>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Select time zone</label>
            <select className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white focus:outline-none focus:border-primary-pink transition-colors">
              <option>Pacific Time (PST) - Seattle, San...</option>
              <option>Eastern Time (EST) - New York, Bos...</option>
              <option>Central Time (CST) - Chicago, Hou...</option>
            </select>
          </div>
          <button className="px-8 py-3 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all">
            Save
          </button>
        </section>

        {/* Language Settings */}
        <section className="bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-6 border border-gray-700 space-y-4">
          <h3 className="font-semibold">Language</h3>
          <p className="text-gray-400 text-sm">
            Select the language for your profile.
          </p>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Select language</label>
            <select className="w-full px-4 py-3 bg-primary-dark border border-gray-700 rounded-lg text-white focus:outline-none focus:border-primary-pink transition-colors">
              <option>🇺🇸 English (United States)</option>
              <option>🇪🇸 Spanish (Español)</option>
              <option>🇫🇷 French (Français)</option>
            </select>
          </div>
          <button className="px-8 py-3 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all">
            Save
          </button>
        </section>

        {/* Delete Account */}
        <section className="bg-gradient-to-br from-red-900/20 to-red-800/10 rounded-2xl p-6 border border-red-800/50 space-y-4">
          <h3 className="font-semibold text-red-400">Delete my account</h3>
          <p className="text-gray-400 text-sm">
            You have the option to delete your account. <span className="text-red-400 font-semibold">Warning:</span> This action is irreversible.
          </p>
          <button className="w-full py-3 bg-red-600 hover:bg-red-700 rounded-full text-white font-semibold transition-all">
            Delete my account
          </button>
        </section>
      </div>
    </div>
  )
}

export default Settings
