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
  const [selectedOrb, setSelectedOrb] = useState(1)

  // WebSocket and audio refs
  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const processorRef = useRef(null)
  const audioBufferRef = useRef([])
  const audioPlayerRef = useRef(null)
  const isStreamingAudioRef = useRef(false)
  const isRecordingRef = useRef(false) // Use ref for audio processor to avoid state timing issues

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

  // WebSocket URL
  const getWebSocketUrl = () => {
    const isProduction = window.location.hostname.includes('newsjuiceapp.com')
    const protocol = isProduction ? 'wss' : 'ws'
    const host = isProduction 
      ? 'chatter-919568151211.us-central1.run.app'
      : 'localhost:8080'
    const token = localStorage.getItem('auth_token')
    return `${protocol}://${host}/ws/chat${token ? `?token=${token}` : ''}`
  }

  // Connect WebSocket
  const connectWebSocket = () => {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(getWebSocketUrl())
      
      ws.onopen = () => {
        console.log("[ws] Connected")
        wsRef.current = ws
        resolve()
      }
      
      ws.onerror = (error) => {
        console.error("[ws] Error:", error)
        reject(error)
      }
      
      ws.onclose = () => {
        console.log("[ws] Disconnected")
        wsRef.current = null
      }
      
      ws.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          // Received audio bytes
          handleAudioChunk(event.data)
        } else {
          // Received JSON status message
          try {
            const data = JSON.parse(event.data)
            handleStatusMessage(data)
          } catch (e) {
            console.error("[ws] Failed to parse message:", e)
          }
        }
      }
    })
  }

  // Handle status messages from backend
  const handleStatusMessage = (data) => {
    const status = data.status
    
    switch(status) {
      case "chunk_received":
        break
      case "transcribing":
        setStatusMessage("🎤 Transcribing your voice...")
        break
      case "transcribed":
        setStatusMessage(`✅ Transcribed: "${data.text}"`)
        break
      case "retrieving":
        setStatusMessage("🔍 Finding relevant news articles...")
        break
      case "generating":
        setStatusMessage("✨ Generating podcast response...")
        break
      case "podcast_generated":
        setStatusMessage("📝 Podcast text ready!")
        break
      case "converting_to_audio":
        setStatusMessage("🔊 Converting to audio...")
        break
      case "streaming_audio":
        setStatusMessage("📡 Receiving audio stream...")
        audioBufferRef.current = []
        isStreamingAudioRef.current = false
        break
      case "complete":
        setStatusMessage("✅ Complete! Playing podcast...")
        finalizeAudio()
        break
      case "error":
        setStatusMessage(`❌ Error: ${data.error}`)
        setIsRecording(false)
        break
      default:
        console.log("[ws] Status:", data)
    }
  }

  // Handle audio chunks from backend
  const handleAudioChunk = (chunk) => {
    if (!isStreamingAudioRef.current) {
      console.log("[audio] Starting to accumulate audio chunks")
      isStreamingAudioRef.current = true
    }
    
    audioBufferRef.current.push(chunk)
    console.log(`[audio] Accumulated ${audioBufferRef.current.length} chunks (${chunk.size} bytes)`)
  }

  // Finalize and play audio
  const finalizeAudio = () => {
    if (audioBufferRef.current.length === 0) {
      console.warn("[audio] No audio chunks to finalize")
      return
    }
    
    console.log(`[audio] Finalizing audio: ${audioBufferRef.current.length} chunks`)
    
    const mimeTypes = ['audio/wav', 'audio/wave', 'audio/x-wav']
    
    for (const mimeType of mimeTypes) {
      try {
        const audioBlob = new Blob(audioBufferRef.current, { type: mimeType })
        const audioUrl = URL.createObjectURL(audioBlob)
        
        // Create audio element if it doesn't exist
        if (!audioPlayerRef.current) {
          audioPlayerRef.current = new Audio()
        }
        
        audioPlayerRef.current.src = audioUrl
        audioPlayerRef.current.oncanplay = () => {
          console.log("[audio] Audio can play, attempting autoplay")
          setIsPlaying(true)
          audioPlayerRef.current.play().catch((err) => {
            console.warn("[audio] Autoplay blocked:", err)
          })
        }
        
        audioPlayerRef.current.onended = () => {
          setIsPlaying(false)
          setStatusMessage("Go ahead, I'm listening")
          URL.revokeObjectURL(audioUrl)
        }
        
        audioPlayerRef.current.onerror = (e) => {
          console.error(`[audio] Error playing audio with ${mimeType}:`, e)
        }
        
        break
      } catch (e) {
        console.warn(`[audio] Failed to create blob with ${mimeType}:`, e)
      }
    }
    
    // Reset for next recording
    audioBufferRef.current = []
    isStreamingAudioRef.current = false
  }

  // Start recording
  const startRecording = async () => {
    // Prevent starting a new recording if already recording (check both state and ref)
    if (isRecording || isRecordingRef.current) {
      console.log("[recording] Already recording, ignoring start request")
      return
    }
    
    try {
      // Stop any ongoing playback
      if (isPlaying) {
        stopPlayback()
      }

      // If WebSocket exists but is not open, close it and create a new one
      if (wsRef.current && wsRef.current.readyState !== WebSocket.OPEN) {
        console.log("[recording] WebSocket not open, closing and reconnecting...")
        wsRef.current.close()
        wsRef.current = null
      }

      // Connect WebSocket
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setStatusMessage("Connecting...")
        await connectWebSocket()
      }

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: { ideal: 44100 },
          channelCount: { ideal: 1 }
        }
      })

      mediaStreamRef.current = stream

      // Create AudioContext
      const AudioContext = window.AudioContext || window.webkitAudioContext
      const audioContext = new AudioContext()
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)

      // Create ScriptProcessorNode to capture audio
      const bufferSize = 4096
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1)

      processor.onaudioprocess = (e) => {
        // Use ref instead of state to avoid timing issues
        if (!isRecordingRef.current || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return
        }

        const inputData = e.inputBuffer.getChannelData(0)
        const pcmData = new Int16Array(inputData.length)

        // Convert float32 to int16 PCM
        for (let i = 0; i < inputData.length; i++) {
          const sample = Math.max(-1, Math.min(1, inputData[i]))
          pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
        }

        // Send audio chunk to backend
        try {
          wsRef.current.send(pcmData.buffer)
          console.log(`[recording] Sent audio chunk: ${pcmData.buffer.byteLength} bytes`)
        } catch (error) {
          console.error("[recording] Error sending audio chunk:", error)
        }
      }

      processorRef.current = processor
      source.connect(processor)
      processor.connect(audioContext.destination)

      // Set both state and ref
      isRecordingRef.current = true
      setIsRecording(true)
      setStatusMessage("Listening...")
      console.log("[recording] Started recording, audio processor active")
    } catch (error) {
      console.error('Error starting recording:', error)
      setStatusMessage("Error: " + error.message)
    }
  }

  // [Z] below is the old Stop recording function; implementing new functionality
  // // Stop recording
  // const stopRecording = () => {
  //   console.log("[recording] Stopping recording...")
    
  //   // Wait a bit to ensure last chunks are sent before stopping
  //   setTimeout(() => {
  //     // Stop the recording flag (ref) to stop sending new chunks
  //     isRecordingRef.current = false
      
  //     // Wait a bit more for any in-flight chunks to be sent
  //     setTimeout(() => {
  //       // Disconnect processor to stop audio capture
  //       if (processorRef.current) {
  //         processorRef.current.disconnect()
  //         processorRef.current = null
  //       }

  //       // Stop media stream
  //       if (mediaStreamRef.current) {
  //         mediaStreamRef.current.getTracks().forEach(track => track.stop())
  //         mediaStreamRef.current = null
  //       }

  //       // Close audio context
  //       if (audioContextRef.current) {
  //         audioContextRef.current.close()
  //         audioContextRef.current = null
  //       }

  //       // Update UI state
  //       setIsRecording(false)

  //       // Send complete signal to backend
  //       if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
  //         console.log("[recording] Sending complete signal to backend")
  //         wsRef.current.send(JSON.stringify({ type: "complete" }))
  //         setStatusMessage("Processing...")
  //       } else {
  //         console.error("[recording] WebSocket not ready! State:", wsRef.current?.readyState)
  //         setStatusMessage("Error: Connection not ready")
  //       }
  //     }, 200) // Additional delay for in-flight chunks
  //   }, 200) // Initial delay before stopping recording flag
  // }

  // [Z] new stop recording functionality
  const stopRecording = () => {
  console.log("[recording] Stopping recording...")
  
  // IMPORTANT: Set ref to false immediately so next startRecording() can proceed
  isRecordingRef.current = false
  
  // Wait a bit to ensure last chunks are sent before disconnecting audio
  setTimeout(() => {
    // Disconnect processor to stop audio capture
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }

    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop())
      mediaStreamRef.current = null
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    // Update UI state
    setIsRecording(false)

    // Send complete signal to backend ONLY if WebSocket is open
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log("[recording] Sending complete signal to backend")
      wsRef.current.send(JSON.stringify({ type: "complete" }))
      setStatusMessage("Processing...")
    } else {
      // WebSocket not ready - this might happen if you released the button too quickly
      console.warn("[recording] WebSocket not ready (state:", wsRef.current?.readyState, "), cannot send complete signal")
      
      // If there's no WebSocket or it's closed, reset to listening state
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
        setStatusMessage("Go ahead, I'm listening")
      } else if (wsRef.current.readyState === WebSocket.CONNECTING) {
        // Still connecting - wait for it to open, then send complete signal
        setStatusMessage("Connecting...")
        const originalWs = wsRef.current
        
        originalWs.addEventListener('open', () => {
          if (wsRef.current === originalWs && originalWs.readyState === WebSocket.OPEN) {
            console.log("[recording] WebSocket opened after delay, sending complete signal")
            originalWs.send(JSON.stringify({ type: "complete" }))
            setStatusMessage("Processing...")
          }
        }, { once: true })
      }
    }
  }, 200) // Single delay for cleanup
}

  // Stop playback
  const stopPlayback = () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
      audioPlayerRef.current.currentTime = 0
    }
    setIsPlaying(false)
    setStatusMessage("Go ahead, I'm listening")
  }

  // Handle call button
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (processorRef.current) {
        processorRef.current.disconnect()
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
      }
    }
  }, [])

  const handleOrbSelection = (orbId) => {
    if (orbId !== null) {
      setSelectedOrb(orbId)
    }
    setShowOrbSelector(false)
  }

  const getOrbComponent = () => {
    const orbMap = {
      1: OrbStyle1, 2: OrbStyle2, 3: OrbStyle3, 4: OrbStyle4, 5: OrbStyle5,
      6: OrbStyle6, 7: OrbStyle7, 8: OrbStyle8, 9: OrbStyle9, 10: OrbStyle10,
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
                  localStorage.removeItem('auth_token')
                  localStorage.removeItem('user_id')
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
        {/* Right Half - Orb and Controls */}
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
              onClick={handleCallButton}
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
            <p>Click the call button to start recording, click again to send</p>
          </div>
        </div>

        {/* Left Half - News and Sources */}
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
