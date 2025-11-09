import { motion } from 'framer-motion'
import { useEffect, useState, useRef } from 'react'

function AnimatedOrb({ isPlaying }) {
  const [pulseIntensity, setPulseIntensity] = useState(0)
  const [randomOffsets, setRandomOffsets] = useState({ x: 0, y: 0, scale: 1 })
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const animationFrameRef = useRef(null)

  useEffect(() => {
    if (!isPlaying) {
      setPulseIntensity(0)
      setRandomOffsets({ x: 0, y: 0, scale: 1 })
      
      // Clean up audio context
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
        audioContextRef.current = null
      }
      return
    }

    // Try to use Web Audio API for real frequency analysis
    const setupAudioAnalysis = async () => {
      try {
        // Create audio context
        const AudioContext = window.AudioContext || window.webkitAudioContext
        audioContextRef.current = new AudioContext()
        analyserRef.current = audioContextRef.current.createAnalyser()
        analyserRef.current.fftSize = 256
        
        // Try to capture audio output (this works in some browsers)
        const destination = audioContextRef.current.createMediaStreamDestination()
        analyserRef.current.connect(destination)
        
        const bufferLength = analyserRef.current.frequencyBinCount
        const dataArray = new Uint8Array(bufferLength)
        
        const updateFrequency = () => {
          if (!isPlaying) return
          
          analyserRef.current.getByteFrequencyData(dataArray)
          
          // Calculate average frequency
          const average = dataArray.reduce((a, b) => a + b, 0) / bufferLength
          const normalized = average / 255
          
          setPulseIntensity(normalized)
          
          animationFrameRef.current = requestAnimationFrame(updateFrequency)
        }
        
        updateFrequency()
      } catch (error) {
        console.log('Audio analysis not available, using simulation')
        // Fallback to simulation
        useSimulation()
      }
    }

    const useSimulation = () => {
      // More random, speech-like patterns
      const interval = setInterval(() => {
        // Simulate speech frequency patterns with bursts and pauses
        const burst = Math.random() > 0.3 ? Math.random() * 0.8 + 0.2 : Math.random() * 0.3
        setPulseIntensity(burst)
        
        // Add random movements for more organic feel
        setRandomOffsets({
          x: (Math.random() - 0.5) * 20,
          y: (Math.random() - 0.5) * 20,
          scale: 1 + (Math.random() - 0.5) * 0.1
        })
      }, 80 + Math.random() * 100) // Variable timing for more natural feel

      return () => clearInterval(interval)
    }

    setupAudioAnalysis()

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [isPlaying])

  const baseScale = 1
  const pulseScale = isPlaying ? baseScale + (pulseIntensity * 0.2) : baseScale

  return (
    <div className="relative w-72 h-72 md:w-80 md:h-80 flex items-center justify-center">
      {/* Outer glow rings */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'radial-gradient(circle, rgba(255,59,154,0.3) 0%, rgba(139,58,143,0.2) 50%, transparent 70%)',
          filter: 'blur(20px)',
        }}
        animate={{
          scale: isPlaying ? pulseScale * 1.1 : 1,
          opacity: isPlaying ? 0.5 + (pulseIntensity * 0.3) : 0.3,
          x: isPlaying ? randomOffsets.x * 0.5 : 0,
          y: isPlaying ? randomOffsets.y * 0.5 : 0,
        }}
        transition={{
          duration: 0.1,
          ease: 'easeOut',
        }}
      />

      {/* Middle ring */}
      <motion.div
        className="absolute inset-8 rounded-full border-2 border-primary-purple/30"
        animate={{
          scale: pulseScale,
          rotate: isPlaying ? 360 : 0,
        }}
        transition={{
          scale: { duration: 0.1 },
          rotate: { duration: 20, repeat: Infinity, ease: 'linear' },
        }}
      />

      {/* Main orb container */}
      <motion.div
        className="relative w-56 h-56 md:w-64 md:h-64 rounded-full overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #1a1625 0%, #2a1f3d 100%)',
          boxShadow: `0 0 ${60 + pulseIntensity * 40}px rgba(255,59,154,${0.3 + pulseIntensity * 0.3}), inset 0 0 60px rgba(139,58,143,0.2)`,
        }}
        animate={{
          scale: pulseScale * randomOffsets.scale,
          x: randomOffsets.x,
          y: randomOffsets.y,
        }}
        transition={{
          duration: 0.08,
          ease: 'easeOut',
        }}
      >
        {/* Animated gradient blobs inside orb */}
        <motion.div
          className="absolute w-full h-full"
          animate={{
            rotate: isPlaying ? 360 : 0,
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: 'linear',
          }}
        >
          {/* Pink blob */}
          <motion.div
            className="absolute w-32 h-32 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(255,59,154,0.8) 0%, rgba(255,59,154,0) 70%)',
              filter: `blur(${20 + pulseIntensity * 10}px)`,
            }}
            animate={{
              x: isPlaying ? [0, 100, 0, -100, 0] : 0,
              y: isPlaying ? [0, -100, 100, 0, 0] : 0,
              scale: isPlaying ? 1 + pulseIntensity * 0.5 : 1,
              opacity: isPlaying ? 0.6 + pulseIntensity * 0.4 : 0.8,
            }}
            transition={{
              x: { duration: 8, repeat: Infinity, ease: 'easeInOut' },
              y: { duration: 8, repeat: Infinity, ease: 'easeInOut' },
              scale: { duration: 0.1 },
              opacity: { duration: 0.1 },
            }}
          />

          {/* Blue blob */}
          <motion.div
            className="absolute w-40 h-40 rounded-full top-1/4 right-0"
            style={{
              background: 'radial-gradient(circle, rgba(100,150,255,0.6) 0%, rgba(100,150,255,0) 70%)',
              filter: `blur(${25 + pulseIntensity * 8}px)`,
            }}
            animate={{
              x: isPlaying ? [0, -80, 50, 0] : 0,
              y: isPlaying ? [0, 80, -50, 0] : 0,
              scale: isPlaying ? 0.8 + pulseIntensity * 0.6 : 1,
              opacity: isPlaying ? 0.5 + pulseIntensity * 0.4 : 0.6,
            }}
            transition={{
              x: { duration: 6, repeat: Infinity, ease: 'easeInOut' },
              y: { duration: 6, repeat: Infinity, ease: 'easeInOut' },
              scale: { duration: 0.1 },
              opacity: { duration: 0.1 },
            }}
          />

          {/* Purple blob */}
          <motion.div
            className="absolute w-36 h-36 rounded-full bottom-0 left-1/4"
            style={{
              background: 'radial-gradient(circle, rgba(139,58,143,0.7) 0%, rgba(139,58,143,0) 70%)',
              filter: `blur(${22 + pulseIntensity * 12}px)`,
            }}
            animate={{
              x: isPlaying ? [0, 60, -60, 0] : 0,
              y: isPlaying ? [0, -70, 70, 0] : 0,
              scale: isPlaying ? 0.9 + pulseIntensity * 0.4 : 1,
              opacity: isPlaying ? 0.6 + pulseIntensity * 0.3 : 0.7,
            }}
            transition={{
              x: { duration: 7, repeat: Infinity, ease: 'easeInOut' },
              y: { duration: 7, repeat: Infinity, ease: 'easeInOut' },
              scale: { duration: 0.1 },
              opacity: { duration: 0.1 },
            }}
          />

          {/* White accent blob */}
          <motion.div
            className="absolute w-24 h-24 rounded-full top-1/3 left-1/3"
            style={{
              background: 'radial-gradient(circle, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0) 60%)',
              filter: 'blur(15px)',
            }}
            animate={{
              x: isPlaying ? [0, -40, 40, 0] : 0,
              y: isPlaying ? [0, 40, -40, 0] : 0,
              scale: isPlaying ? [1, 1.3, 0.7, 1] : 1,
              opacity: isPlaying ? [0.8, 1, 0.6, 0.8] : 0.5,
            }}
            transition={{
              duration: 5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        </motion.div>

        {/* Pulse rings when playing */}
        {isPlaying && (
          <>
            <motion.div
              className="absolute inset-0 rounded-full border-2 border-white/20"
              animate={{
                scale: [1, 1.3],
                opacity: [0.5, 0],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'easeOut',
              }}
            />
            <motion.div
              className="absolute inset-0 rounded-full border-2 border-primary-pink/30"
              animate={{
                scale: [1, 1.3],
                opacity: [0.5, 0],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'easeOut',
                delay: 0.5,
              }}
            />
          </>
        )}
      </motion.div>

      {/* Outer border ring */}
      <motion.div
        className="absolute inset-0 rounded-full border-4"
        style={{
          borderColor: 'rgba(139,58,143,0.5)',
        }}
        animate={{
          scale: isPlaying ? [1, 1.02, 1] : 1,
          borderColor: isPlaying
            ? ['rgba(139,58,143,0.5)', 'rgba(255,59,154,0.5)', 'rgba(139,58,143,0.5)']
            : 'rgba(139,58,143,0.5)',
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </div>
  )
}

export default AnimatedOrb
