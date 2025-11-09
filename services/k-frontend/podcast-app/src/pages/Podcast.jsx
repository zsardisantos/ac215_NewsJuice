import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Menu, Phone, PhoneOff, Mic, MicOff, Settings as SettingsIcon, Info, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import AnimatedOrb from '../components/AnimatedOrb'
import OrbSelector, { OrbStyle1, OrbStyle2, OrbStyle3, OrbStyle4, OrbStyle5, OrbStyle6, OrbStyle7, OrbStyle8, OrbStyle9, OrbStyle10 } from '../components/OrbSelector'

function Podcast() {
  const navigate = useNavigate()
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [statusMessage, setStatusMessage] = useState("Go ahead, I'm listening")
  const [menuOpen, setMenuOpen] = useState(false)
  const [showOrbSelector, setShowOrbSelector] = useState(false)
  const [selectedOrb, setSelectedOrb] = useState(1) // Default to original orb
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const playbackTimeoutRef = useRef(null)
  const speechSynthesisRef = useRef(null)

  // Simulated AI responses
  const aiResponses = [
    "That's a great question! Let me share some insights about that topic...",
    "Interesting point! Based on recent developments, I can tell you that...",
    "I understand what you're asking. Here's what you need to know...",
    "Excellent question! Let me break this down for you...",
    "That's fascinating! From my knowledge, I can explain that..."
  ]

  const newsTopics = [
    "Women's Volleyball",
    "Cutting-Edge AI",
    "Job Market Trends",
    "Climate Action",
    "Space Exploration"
  ]

  const sources = [
    {
      title: "Trump Administration Bars Harvard from Enrolling Foreign Students",
      source: "AP",
      domain: "apnews.com",
      date: "August 12th, 2025"
    },
    {
      title: "Harvard Students Protest the Admissions Office Protesting the New Legislation",
      source: "CNN",
      domain: "thecnn.com",
      date: "August 7th, 2024"
    }
  ]

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (playbackTimeoutRef.current) {
        clearTimeout(playbackTimeoutRef.current)
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  const startRecording = async () => {
    try {
      // Stop any ongoing playback
      if (isPlaying) {
        stopPlayback()
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      audioChunksRef.current = []

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data)
      }

      mediaRecorderRef.current.onstop = () => {
        // When recording stops, simulate AI response playback
        simulateAIResponse()
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
      setStatusMessage("Listening...")
    } catch (error) {
      console.error('Error accessing microphone:', error)
      setStatusMessage("Microphone access denied")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const simulateAIResponse = () => {
    // Simulate processing time
    setStatusMessage("Processing...")
    
    setTimeout(() => {
      // Pick a random AI response
      const response = aiResponses[Math.floor(Math.random() * aiResponses.length)]
      setStatusMessage(response)
      setIsPlaying(true)

      // Use Web Speech API to actually speak the response
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(response)
        utterance.rate = 1.0
        utterance.pitch = 1.0
        utterance.volume = 1.0
        
        // When speech ends, return to listening state
        utterance.onend = () => {
          stopPlayback()
        }
        
        utterance.onerror = (event) => {
          console.error('Speech synthesis error:', event)
          stopPlayback()
        }
        
        speechSynthesisRef.current = utterance
        window.speechSynthesis.speak(utterance)
      } else {
        // Fallback if speech synthesis not available
        const duration = 3000 + Math.random() * 2000
        playbackTimeoutRef.current = setTimeout(() => {
          stopPlayback()
        }, duration)
      }
    }, 500)
  }

  const stopPlayback = () => {
    if (playbackTimeoutRef.current) {
      clearTimeout(playbackTimeoutRef.current)
    }
    // Cancel any ongoing speech
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    setIsPlaying(false)
    setStatusMessage("Go ahead, I'm listening")
  }

  const handleCallButton = () => {
    if (isRecording) {
      stopRecording()
    } else if (isPlaying) {
      stopPlayback()
      startRecording()
    } else {
      startRecording()
    }
  }

  const handleOrbSelection = (orbId) => {
    if (orbId !== null) {
      setSelectedOrb(orbId)
    }
    setShowOrbSelector(false)
  }

  const getOrbComponent = () => {
    const orbMap = {
      1: OrbStyle1,
      2: OrbStyle2,
      3: OrbStyle3,
      4: OrbStyle4,
      5: OrbStyle5,
      6: OrbStyle6,
      7: OrbStyle7,
      8: OrbStyle8,
      9: OrbStyle9,
      10: OrbStyle10,
    }
    return orbMap[selectedOrb] || OrbStyle1
  }

  const SelectedOrbComponent = getOrbComponent()

  return (
    <div className="min-h-screen bg-primary-darker text-white relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary-purple/20 via-primary-darker to-primary-darker"></div>

      {/* Header */}
      <div className="relative z-10 px-6 py-4 flex items-center justify-between">
        <button
          onClick={() => navigate('/login')}
          className="p-2 hover:bg-gray-800 rounded-full transition-colors"
        >
          <ArrowLeft size={24} />
        </button>
        <h1 className="text-lg font-semibold">Hi, I'm NJ</h1>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="p-2 hover:bg-gray-800 rounded-full transition-colors"
        >
          <Menu size={24} />
        </button>
      </div>

      {/* Hamburger Menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.3 }}
            className="fixed top-0 right-0 h-full w-64 bg-primary-dark border-l border-gray-800 z-50 shadow-2xl"
          >
            <div className="p-6 space-y-6">
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-xl font-bold">Menu</h2>
                <button
                  onClick={() => setMenuOpen(false)}
                  className="p-2 hover:bg-gray-800 rounded-full transition-colors"
                >
                  ✕
                </button>
              </div>
              <button
                onClick={() => {
                  navigate('/settings')
                  setMenuOpen(false)
                }}
                className="w-full flex items-center gap-3 p-3 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <SettingsIcon size={20} />
                <span>Settings</span>
              </button>
              <button
                onClick={() => {
                  navigate('/about')
                  setMenuOpen(false)
                }}
                className="w-full flex items-center gap-3 p-3 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <Info size={20} />
                <span>About Us</span>
              </button>
              <button
                onClick={() => {
                  navigate('/login')
                  setMenuOpen(false)
                }}
                className="w-full flex items-center gap-3 p-3 hover:bg-red-900/30 text-red-400 rounded-lg transition-colors"
              >
                <ArrowLeft size={20} />
                <span>Logout</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content - Split Screen Layout */}
      <div className="relative z-10 flex flex-col lg:flex-row lg:h-[calc(100vh-80px)]">
        {/* Right Half - Orb and Controls (First on mobile, Right on desktop) */}
        <div className="w-full lg:w-1/2 flex flex-col items-center justify-center px-6 py-6 lg:py-12 relative lg:order-2 min-h-[80vh] lg:min-h-0">
          {/* Status Message */}
          <motion.div
            key={statusMessage}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 px-6 py-3 bg-gray-800/50 rounded-full border border-gray-700 backdrop-blur-sm max-w-md text-center"
          >
            <p className="text-sm text-gray-300">{statusMessage}</p>
          </motion.div>

          {/* Animated Orb */}
          <div className="mb-12 relative">
            <SelectedOrbComponent isPlaying={isPlaying} size="large" />
            <button
              onClick={() => setShowOrbSelector(true)}
              className="absolute -bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-gray-800/80 hover:bg-gray-700/80 rounded-full text-xs flex items-center gap-2 border border-gray-600 transition-all"
            >
              <Sparkles size={14} />
              <span>Change Style</span>
            </button>
          </div>

          {/* Call Button */}
          <div className="flex items-center gap-6 mt-8">
            <motion.button
              whileTap={{ scale: 0.95 }}
              className="w-16 h-16 bg-gray-800/50 hover:bg-red-900/50 rounded-full flex items-center justify-center border border-gray-700 hover:border-red-500 transition-all"
            >
              <PhoneOff size={24} className="text-red-400" />
            </motion.button>

            <motion.button
              onMouseDown={handleCallButton}
              whileTap={{ scale: 0.95 }}
              className={`w-24 h-24 rounded-full flex items-center justify-center transition-all shadow-lg ${
                isRecording
                  ? 'bg-red-600 shadow-red-500/50'
                  : 'bg-gradient-to-br from-primary-pink to-pink-600 shadow-primary-pink/50'
              }`}
            >
              {isRecording ? <Mic size={32} className="animate-pulse" /> : <Phone size={32} />}
            </motion.button>

            <motion.button
              whileTap={{ scale: 0.95 }}
              className="w-16 h-16 bg-gray-800/50 hover:bg-gray-700/50 rounded-full flex items-center justify-center border border-gray-700 transition-all"
            >
              <MicOff size={24} className="text-gray-400" />
            </motion.button>
          </div>

          {/* Instructions */}
          <div className="mt-8 text-center text-gray-500 text-sm max-w-md">
            <p>Press and hold the call button to speak, release to hear AI response</p>
          </div>
        </div>

        {/* Left Half - News and Sources (Second on mobile, Left on desktop) */}
        <div className="w-full lg:w-1/2 px-6 py-6 overflow-y-auto lg:order-1">
          {/* News Topics */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">News</h2>
            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
              {newsTopics.map((topic, index) => (
                <button
                  key={index}
                  className="px-6 py-3 bg-gray-800/50 hover:bg-gray-700/50 rounded-full text-sm whitespace-nowrap border border-gray-700 transition-colors"
                >
                  {topic}
                </button>
              ))}
            </div>
          </div>

          {/* Sources */}
          <div>
            <h2 className="text-2xl font-semibold mb-6">Sources</h2>
            <div className="space-y-4 pb-6">
              {sources.map((source, index) => (
                <div
                  key={index}
                  className="bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-5 border border-gray-700 hover:border-primary-pink/30 transition-all cursor-pointer"
                >
                  <h3 className="font-semibold mb-2 leading-snug">{source.title}</h3>
                  <div className="flex items-center gap-3 text-sm text-gray-400">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-red-600 rounded flex items-center justify-center text-xs font-bold">
                        {source.source}
                      </div>
                      <span>{source.domain}</span>
                    </div>
                    <span>•</span>
                    <span>{source.date}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Orb Selector Modal */}
      {showOrbSelector && (
        <OrbSelector 
          onSelect={handleOrbSelection}
          currentSelection={selectedOrb}
        />
      )}
    </div>
  )
}

export default Podcast
