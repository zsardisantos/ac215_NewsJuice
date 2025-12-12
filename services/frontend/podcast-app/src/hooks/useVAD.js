import { useState, useEffect, useRef } from 'react'

/**
 * Custom React hook for Voice Activity Detection using @ricky0123/vad-web from CDN
 * This avoids Vite bundling issues by using the global VAD library loaded via script tag
 *
 * @param {Object} options - VAD configuration options
 * @param {Function} options.onSpeechStart - Callback when speech is detected
 * @param {Function} options.onSpeechEnd - Callback when speech ends
 * @param {Function} options.onVADMisfire - Callback for false positives
 * @param {number} options.positiveSpeechThreshold - Confidence threshold (0-1)
 * @param {boolean} options.startOnLoad - Whether to start VAD immediately
 * @returns {Object} VAD instance with start(), pause() methods and state
 */
export function useVAD(options = {}) {
  const [loading, setLoading] = useState(true)
  const [errored, setErrored] = useState(false)
  const [listening, setListening] = useState(false)
  const vadInstanceRef = useRef(null)

  useEffect(() => {
    let mounted = true
    let vad = null

    const initVAD = async () => {
      try {
        // Wait for VAD library to be available
        if (typeof window.vad === 'undefined') {
          console.error('[vad] VAD library not loaded from CDN')
          setErrored(true)
          setLoading(false)
          return
        }

        console.log('[vad] Initializing VAD from CDN...')

        // Create VAD instance using the global library
        vad = await window.vad.MicVAD.new({
          // Callbacks
          onSpeechStart: () => {
            if (mounted) {
              setListening(true)
              console.log('[vad] Speech detected')
              options.onSpeechStart?.()
            }
          },
          onSpeechEnd: () => {
            if (mounted) {
              setListening(false)
              console.log('[vad] Speech ended')
              options.onSpeechEnd?.()
            }
          },
          onVADMisfire: () => {
            console.log('[vad] False positive')
            options.onVADMisfire?.()
          },

          // Configuration
          positiveSpeechThreshold: options.positiveSpeechThreshold || 0.8,
          minSpeechFrames: options.minSpeechFrames || 3,
          redemptionFrames: options.redemptionFrames || 8,
          preSpeechPadFrames: options.preSpeechPadFrames || 1,

          // Audio constraints - CRITICAL for preventing audio feedback
          // NOTE: On iOS, getUserMedia() must be called from a user gesture first
          // (see playDailyBrief() function in Podcast.jsx which pre-requests permission)
          additionalAudioConstraints: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          },

          // Asset paths - load from public directory
          baseAssetPath: '/',
          onnxWASMBasePath: '/',

          // ONNX Runtime configuration
          ortConfig: (ort) => {
            ort.env.wasm.wasmPaths = '/'
            ort.env.wasm.numThreads = 1
          }
        })

        if (mounted) {
          vadInstanceRef.current = vad
          setLoading(false)
          console.log('[vad] VAD initialized successfully')

          // Auto-start if requested
          if (options.startOnLoad) {
            vad.start()
            setListening(true)
          }
        }
      } catch (error) {
        console.error('[vad] Error initializing VAD:', error)
        if (mounted) {
          setErrored(true)
          setLoading(false)
        }
      }
    }

    initVAD()

    // Cleanup on unmount
    return () => {
      mounted = false
      if (vad) {
        try {
          vad.destroy()
        } catch (e) {
          console.warn('[vad] Error destroying VAD:', e)
        }
      }
    }
  }, []) // Empty deps - only initialize once

  // Return VAD instance and state
  return {
    loading,
    errored,
    listening,
    start: () => {
      if (vadInstanceRef.current) {
        vadInstanceRef.current.start()
        setListening(true)
        console.log('[vad] Started listening')
      }
    },
    pause: () => {
      if (vadInstanceRef.current) {
        vadInstanceRef.current.pause()
        setListening(false)
        console.log('[vad] Paused listening')
      }
    },
    destroy: () => {
      if (vadInstanceRef.current) {
        vadInstanceRef.current.destroy()
        vadInstanceRef.current = null
        setListening(false)
        console.log('[vad] Destroyed')
      }
    }
  }
}
