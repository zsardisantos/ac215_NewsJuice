import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check } from 'lucide-react'

function Preferences() {
  const navigate = useNavigate()
  const [selectedTopics, setSelectedTopics] = useState([])
  const [selectedSources, setSelectedSources] = useState([])
  const [selectedVoice, setSelectedVoice] = useState('en-US-Chirp3-HD-Aoede')
  const [isSaving, setIsSaving] = useState(false)

  // Predefined topics (8 categories from plan)
  const topics = [
    'Politics',
    'Technology',
    'Health',
    'Business',
    'Sports',
    'Entertainment',
    'Campus Life',
    'Research'
  ]

  // Predefined Harvard news sources (8 sources from plan)
  const sources = [
    'Harvard Gazette',
    'Harvard Crimson',
    'Harvard Medical School',
    'Harvard SEAS',
    'Harvard Law School',
    'Harvard Business School',
    'Harvard Magazine',
    'Harvard Kennedy School'
  ]

  // API helper functions
  //const getApiUrl = () => {
  //  const isProduction = window.location.hostname.includes('newsjuiceapp.com') || window.location.hostname === '34.28.40.119'
  //  return isProduction
  //    ? 'http://136.113.170.71'
  //    : 'http://136.113.170.71'
  //}

  const getApiUrl = () => {
    const isProduction = window.location.hostname.includes('newsjuiceapp.com')
    return isProduction ? '' : 'http://localhost:8080'
  }

  const getAuthHeaders = () => {
    const token = localStorage.getItem('auth_token')
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }

  // Load existing preferences on mount
  useEffect(() => {
    loadPreferences()
  }, [])

  const loadPreferences = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/user/preferences`, {
        headers: getAuthHeaders()
      })

      if (!response.ok) {
        console.error('[preferences] Failed to load:', response.status)
        return
      }

      const data = await response.json()
      console.log('[preferences] Loaded:', data)

      // Parse preferences (they're stored as JSON strings)
      if (data.preferences) {
        const prefs = data.preferences
        if (prefs.topics) {
          const topics = typeof prefs.topics === 'string'
            ? JSON.parse(prefs.topics)
            : prefs.topics
          setSelectedTopics(topics)
        }
        if (prefs.sources) {
          const sources = typeof prefs.sources === 'string'
            ? JSON.parse(prefs.sources)
            : prefs.sources
          setSelectedSources(sources)
        }
        if (prefs.voice_preference) {
          setSelectedVoice(prefs.voice_preference)
        }
      }
    } catch (error) {
      console.error('[preferences] Error loading:', error)
    }
  }

  // Toggle topic selection
  const toggleTopic = (topic) => {
    setSelectedTopics(prev =>
      prev.includes(topic)
        ? prev.filter(t => t !== topic)
        : [...prev, topic]
    )
  }

  // Toggle source selection
  const toggleSource = (source) => {
    setSelectedSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    )
  }

  // Save preferences to backend
  const savePreferences = async () => {
    if (selectedTopics.length === 0 || selectedSources.length === 0) {
      alert('Please select at least one topic and one source')
      return
    }

    setIsSaving(true)

    try {
      console.log('[preferences] Saving:', { topics: selectedTopics, sources: selectedSources })

      const response = await fetch(`${getApiUrl()}/api/user/preferences`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          topics: selectedTopics,
          sources: selectedSources,
          voice_preference: selectedVoice
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to save preferences: ${response.status}`)
      }

      console.log('[preferences] Saved successfully')

      // Navigate back to podcast page
      navigate('/podcast')
    } catch (error) {
      console.error('[preferences] Error saving:', error)
      alert('Failed to save preferences. Please try again.')
    } finally {
      setIsSaving(false)
    }
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
          <h1 className="text-xl font-bold">News Preferences</h1>
          <div className="w-10"></div> {/* Spacer for centering */}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-10">

        {/* Topics Section */}
        <section>
          <h2 className="text-2xl font-bold mb-2">Topics</h2>
          <p className="text-gray-400 mb-6">
            Select the topics you'd like to see in your daily briefing
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {topics.map((topic) => (
              <button
                key={topic}
                onClick={() => toggleTopic(topic)}
                className={`relative px-6 py-4 rounded-2xl font-medium transition-all ${
                  selectedTopics.includes(topic)
                    ? 'bg-gradient-to-br from-primary-pink to-pink-600 text-white shadow-lg shadow-primary-pink/30'
                    : 'bg-gray-800/50 text-gray-300 hover:bg-gray-700/50 border border-gray-700'
                }`}
              >
                {selectedTopics.includes(topic) && (
                  <div className="absolute top-2 right-2">
                    <Check size={16} />
                  </div>
                )}
                {topic}
              </button>
            ))}
          </div>

          <p className="text-sm text-gray-500 mt-4">
            Selected: {selectedTopics.length} {selectedTopics.length === 1 ? 'topic' : 'topics'}
          </p>
        </section>

        {/* Sources Section */}
        <section>
          <h2 className="text-2xl font-bold mb-2">News Sources</h2>
          <p className="text-gray-400 mb-6">
            Choose which Harvard news sources to include
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sources.map((source) => (
              <button
                key={source}
                onClick={() => toggleSource(source)}
                className={`relative px-6 py-4 rounded-2xl font-medium text-left transition-all ${
                  selectedSources.includes(source)
                    ? 'bg-gradient-to-br from-primary-pink to-pink-600 text-white shadow-lg shadow-primary-pink/30'
                    : 'bg-gray-800/50 text-gray-300 hover:bg-gray-700/50 border border-gray-700'
                }`}
              >
                {selectedSources.includes(source) && (
                  <div className="absolute top-3 right-3">
                    <Check size={18} />
                  </div>
                )}
                <div className="flex items-center gap-3">
                  <span className="text-2xl">=�</span>
                  <div>
                    <p className="font-semibold">{source}</p>
                    <p className="text-xs opacity-70">
                      {source.toLowerCase().replace(/\s+/g, '')}.harvard.edu
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>

          <p className="text-sm text-gray-500 mt-4">
            Selected: {selectedSources.length} {selectedSources.length === 1 ? 'source' : 'sources'}
          </p>
        </section>

        {/* Voice Selection Section */}
        <section>
          <h2 className="text-2xl font-bold mb-2">Voice Preference</h2>
          <p className="text-gray-400 mb-6">
            Choose the voice for your podcast narration
          </p>

          <div className="max-w-md">
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              className="w-full px-6 py-4 rounded-2xl bg-gray-800/50 text-gray-300 border border-gray-700 hover:bg-gray-700/50 transition-all focus:outline-none focus:ring-2 focus:ring-primary-pink focus:border-transparent"
            >
              <option value="en-US-Chirp3-HD-Aoede">Female voice</option>
              <option value="en-US-Chirp3-HD-Alnilam">Male voice</option>
            </select>
          </div>

          <p className="text-sm text-gray-500 mt-4">
            This voice will be used for all podcast narrations, including daily briefs and Q&A responses.
          </p>
        </section>

        {/* Save Button */}
        <div className="flex gap-4 pt-6">
          <button
            onClick={savePreferences}
            disabled={isSaving || selectedTopics.length === 0 || selectedSources.length === 0}
            className="flex-1 py-4 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? 'Saving...' : 'Save Preferences'}
          </button>
          <button
            onClick={() => navigate('/podcast')}
            className="px-8 py-4 bg-transparent border border-gray-600 rounded-full text-gray-300 hover:border-gray-500 transition-colors"
          >
            Cancel
          </button>
        </div>

        {/* Info Box */}
        <div className="bg-blue-900/20 border border-blue-800/50 rounded-2xl p-6">
          <h3 className="font-semibold mb-2 flex items-center gap-2">
            <span>9</span>
            How it works
          </h3>
          <p className="text-sm text-gray-300">
            Your daily briefing will be personalized based on these preferences.
            You'll receive news from your selected sources that match your chosen topics.
            You can update your preferences anytime.
          </p>
        </div>
      </div>
    </div>
  )
}

export default Preferences
