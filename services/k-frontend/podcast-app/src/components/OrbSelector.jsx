import { motion } from 'framer-motion'
import { useState } from 'react'
import { X } from 'lucide-react'

// Orb Style 1: Original with gradient blobs
const OrbStyle1 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div
        className={`relative ${dimensions} rounded-full overflow-hidden`}
        style={{
          background: 'linear-gradient(135deg, #1a1625 0%, #2a1f3d 100%)',
          boxShadow: '0 0 40px rgba(255,59,154,0.3)',
        }}
        animate={{ scale: isPlaying ? [1, 1.05, 1] : 1 }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        <motion.div
          className="absolute w-16 h-16 rounded-full top-1/4 left-1/4"
          style={{
            background: 'radial-gradient(circle, rgba(255,59,154,0.8) 0%, rgba(255,59,154,0) 70%)',
            filter: 'blur(15px)',
          }}
          animate={isPlaying ? { x: [0, 30, -30, 0], y: [0, -30, 30, 0] } : {}}
          transition={{ duration: 4, repeat: Infinity }}
        />
        <motion.div
          className="absolute w-20 h-20 rounded-full top-1/3 right-1/4"
          style={{
            background: 'radial-gradient(circle, rgba(100,150,255,0.6) 0%, rgba(100,150,255,0) 70%)',
            filter: 'blur(18px)',
          }}
          animate={isPlaying ? { x: [0, -20, 20, 0], y: [0, 20, -20, 0] } : {}}
          transition={{ duration: 5, repeat: Infinity }}
        />
      </motion.div>
    </div>
  )
}

// Orb Style 2: Hexagonal Grid
const OrbStyle2 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div
        className={`relative ${dimensions} rounded-full`}
        style={{
          background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)',
          boxShadow: '0 0 40px rgba(0,255,255,0.4)',
        }}
      >
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
          <defs>
            <pattern id="hexGrid" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M10 0 L15 5 L15 15 L10 20 L5 15 L5 5 Z" fill="none" stroke="rgba(0,255,255,0.3)" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <circle cx="50" cy="50" r="45" fill="url(#hexGrid)"/>
          <motion.circle
            cx="50"
            cy="50"
            r="30"
            fill="none"
            stroke="rgba(0,255,255,0.6)"
            strokeWidth="2"
            animate={isPlaying ? { r: [30, 40, 30], opacity: [0.6, 0.2, 0.6] } : {}}
            transition={{ duration: 2, repeat: Infinity }}
          />
        </svg>
      </motion.div>
    </div>
  )
}

// Orb Style 3: Particle Ring
const OrbStyle3 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  const particles = Array.from({ length: 12 })
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div
        className={`relative ${dimensions} rounded-full`}
        style={{
          background: 'radial-gradient(circle, #1a0a2e 0%, #0a0a0a 100%)',
          boxShadow: '0 0 40px rgba(138,43,226,0.5)',
        }}
      >
        {particles.map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-purple-400 rounded-full"
            style={{
              top: '50%',
              left: '50%',
              transformOrigin: '0 0',
            }}
            animate={isPlaying ? {
              rotate: 360,
              scale: [1, 1.5, 1],
            } : { rotate: 0 }}
            transition={{
              rotate: { duration: 3, repeat: Infinity, ease: 'linear' },
              scale: { duration: 1, repeat: Infinity, delay: i * 0.1 },
            }}
            initial={{ rotate: i * 30, x: size === 'small' ? 50 : 100 }}
          />
        ))}
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.div
            className={`${size === 'small' ? 'w-16 h-16' : 'w-32 h-32'} rounded-full bg-gradient-to-br from-purple-600 to-pink-500`}
            animate={isPlaying ? { scale: [1, 1.1, 1] } : {}}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        </div>
      </motion.div>
    </div>
  )
}

// Orb Style 4: Neon Rings
const OrbStyle4 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div className={`relative ${dimensions}`}>
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute inset-0 rounded-full border-2"
            style={{
              borderColor: i === 0 ? '#00ffff' : i === 1 ? '#ff00ff' : '#ffff00',
              boxShadow: `0 0 20px ${i === 0 ? '#00ffff' : i === 1 ? '#ff00ff' : '#ffff00'}`,
            }}
            animate={isPlaying ? {
              scale: [1, 1.2, 1],
              rotate: i % 2 === 0 ? 360 : -360,
              opacity: [0.8, 0.3, 0.8],
            } : {}}
            transition={{
              duration: 3 + i,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        ))}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className={`${size === 'small' ? 'w-20 h-20' : 'w-40 h-40'} rounded-full bg-black`} />
        </div>
      </motion.div>
    </div>
  )
}

// Orb Style 5: Holographic
const OrbStyle5 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div
        className={`relative ${dimensions} rounded-full`}
        style={{
          background: 'linear-gradient(45deg, #00f5ff, #ff00ff, #00ff00, #ff00ff, #00f5ff)',
          backgroundSize: '400% 400%',
        }}
        animate={isPlaying ? {
          backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
        } : {}}
        transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
      >
        <div className="absolute inset-1 rounded-full bg-black" />
        <motion.div
          className="absolute inset-4 rounded-full"
          style={{
            background: 'linear-gradient(135deg, rgba(0,245,255,0.3), rgba(255,0,255,0.3))',
            filter: 'blur(10px)',
          }}
          animate={isPlaying ? { rotate: 360 } : {}}
          transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
        />
      </motion.div>
    </div>
  )
}

// Orb Style 6: Digital Matrix
const OrbStyle6 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div
        className={`relative ${dimensions} rounded-full bg-black border-2 border-green-500`}
        style={{
          boxShadow: '0 0 30px rgba(0,255,0,0.5), inset 0 0 30px rgba(0,255,0,0.2)',
        }}
      >
        <div className="absolute inset-0 overflow-hidden rounded-full">
          {Array.from({ length: 8 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute h-px bg-green-400"
              style={{
                width: '100%',
                top: `${(i + 1) * 12}%`,
                opacity: 0.3,
              }}
              animate={isPlaying ? {
                x: ['-100%', '100%'],
              } : {}}
              transition={{
                duration: 2,
                repeat: Infinity,
                delay: i * 0.2,
                ease: 'linear',
              }}
            />
          ))}
        </div>
        <motion.div
          className="absolute inset-0 flex items-center justify-center text-green-400 font-mono text-xs"
          animate={isPlaying ? { opacity: [0.3, 1, 0.3] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        >
          {size === 'large' && '01010101'}
        </motion.div>
      </motion.div>
    </div>
  )
}

// Orb Style 7: Plasma Ball
const OrbStyle7 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div
        className={`relative ${dimensions} rounded-full`}
        style={{
          background: 'radial-gradient(circle, #4a0080 0%, #1a0030 100%)',
          boxShadow: '0 0 50px rgba(138,43,226,0.6)',
        }}
      >
        {Array.from({ length: 6 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full"
            style={{
              width: '2px',
              height: size === 'small' ? '60px' : '120px',
              background: 'linear-gradient(to bottom, rgba(138,43,226,0.8), rgba(255,0,255,0))',
              top: '50%',
              left: '50%',
              transformOrigin: 'top center',
            }}
            animate={isPlaying ? {
              rotate: [i * 60, i * 60 + 360],
              scaleY: [1, 1.2, 0.8, 1],
            } : { rotate: i * 60 }}
            transition={{
              rotate: { duration: 4, repeat: Infinity, ease: 'linear' },
              scaleY: { duration: 1, repeat: Infinity, delay: i * 0.1 },
            }}
          />
        ))}
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.div
            className={`${size === 'small' ? 'w-12 h-12' : 'w-24 h-24'} rounded-full bg-white`}
            style={{ boxShadow: '0 0 30px rgba(255,255,255,0.8)' }}
            animate={isPlaying ? { scale: [1, 1.2, 1] } : {}}
            transition={{ duration: 1, repeat: Infinity }}
          />
        </div>
      </motion.div>
    </div>
  )
}

// Orb Style 8: Quantum Field
const OrbStyle8 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div className={`relative ${dimensions}`}>
        <motion.div
          className={`absolute ${dimensions} rounded-full`}
          style={{
            background: 'radial-gradient(circle, rgba(0,150,255,0.3) 0%, transparent 70%)',
            filter: 'blur(20px)',
          }}
          animate={isPlaying ? { scale: [1, 1.3, 1] } : {}}
          transition={{ duration: 2, repeat: Infinity }}
        />
        {Array.from({ length: 20 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-blue-300 rounded-full"
            style={{
              top: `${Math.random() * 100}%`,
              left: `${Math.random() * 100}%`,
            }}
            animate={isPlaying ? {
              scale: [0, 1, 0],
              opacity: [0, 1, 0],
            } : {}}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
          />
        ))}
        <motion.div
          className={`absolute inset-0 ${dimensions} rounded-full border-2 border-blue-400`}
          style={{ boxShadow: '0 0 30px rgba(0,150,255,0.5)' }}
          animate={isPlaying ? { rotate: 360 } : {}}
          transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
        />
      </motion.div>
    </div>
  )
}

// Orb Style 9: Crystalline
const OrbStyle9 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      <motion.div
        className={`relative ${dimensions}`}
        animate={isPlaying ? { rotate: 360 } : {}}
        transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
      >
        <svg className="w-full h-full" viewBox="0 0 100 100">
          <defs>
            <linearGradient id="crystalGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00ffff" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#ff00ff" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#ffff00" stopOpacity="0.8" />
            </linearGradient>
          </defs>
          {[0, 60, 120, 180, 240, 300].map((angle, i) => (
            <motion.polygon
              key={i}
              points="50,50 50,20 60,35"
              fill="url(#crystalGrad)"
              stroke="rgba(255,255,255,0.5)"
              strokeWidth="0.5"
              style={{ transformOrigin: '50px 50px' }}
              transform={`rotate(${angle} 50 50)`}
              animate={isPlaying ? {
                opacity: [0.6, 1, 0.6],
              } : {}}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: i * 0.1,
              }}
            />
          ))}
          <circle cx="50" cy="50" r="8" fill="white" opacity="0.9" />
        </svg>
      </motion.div>
    </div>
  )
}

// Orb Style 10: Organic Halo
const OrbStyle10 = ({ isPlaying, size = 'small' }) => {
  const dimensions = size === 'small' ? 'w-32 h-32' : 'w-64 h-64'
  const containerSize = size === 'small' ? 128 : 256
  
  return (
    <div className={`relative ${dimensions} flex items-center justify-center`}>
      {/* Outer organic halo rings */}
      {[0, 1, 2, 3].map((index) => (
        <motion.div
          key={`halo-${index}`}
          className="absolute rounded-full"
          style={{
            width: `${containerSize + (index * 20)}px`,
            height: `${containerSize + (index * 20)}px`,
            border: `${2 - index * 0.3}px solid rgba(255, 200, 150, ${0.3 - index * 0.05})`,
            boxShadow: `0 0 ${20 + index * 10}px rgba(255, 180, 120, ${0.4 - index * 0.08})`,
          }}
          animate={isPlaying ? {
            scale: [1, 1.05 + index * 0.02, 1],
            opacity: [0.6 - index * 0.1, 0.8 - index * 0.1, 0.6 - index * 0.1],
            rotate: index % 2 === 0 ? [0, 360] : [360, 0],
          } : {
            opacity: 0.3 - index * 0.05,
          }}
          transition={{
            scale: { duration: 3 + index * 0.5, repeat: Infinity, ease: 'easeInOut' },
            opacity: { duration: 2 + index * 0.3, repeat: Infinity, ease: 'easeInOut' },
            rotate: { duration: 40 + index * 10, repeat: Infinity, ease: 'linear' },
          }}
        />
      ))}

      {/* Flowing energy particles around halo */}
      {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
        <motion.div
          key={`particle-${i}`}
          className="absolute w-1.5 h-1.5 rounded-full"
          style={{
            background: `radial-gradient(circle, rgba(255, 220, 180, 0.9), rgba(255, 180, 120, 0))`,
            boxShadow: '0 0 8px rgba(255, 200, 150, 0.8)',
            top: '50%',
            left: '50%',
          }}
          animate={isPlaying ? {
            x: [
              Math.cos((i * Math.PI * 2) / 8) * (containerSize * 0.6),
              Math.cos((i * Math.PI * 2) / 8 + 0.5) * (containerSize * 0.65),
              Math.cos((i * Math.PI * 2) / 8 + 1) * (containerSize * 0.6),
            ],
            y: [
              Math.sin((i * Math.PI * 2) / 8) * (containerSize * 0.6),
              Math.sin((i * Math.PI * 2) / 8 + 0.5) * (containerSize * 0.65),
              Math.sin((i * Math.PI * 2) / 8 + 1) * (containerSize * 0.6),
            ],
            opacity: [0.4, 0.9, 0.4],
            scale: [1, 1.5, 1],
          } : {
            x: Math.cos((i * Math.PI * 2) / 8) * (containerSize * 0.6),
            y: Math.sin((i * Math.PI * 2) / 8) * (containerSize * 0.6),
            opacity: 0.3,
          }}
          transition={{
            duration: 4 + (i * 0.2),
            repeat: Infinity,
            ease: 'easeInOut',
            delay: i * 0.2,
          }}
        />
      ))}

      {/* Central core orb */}
      <motion.div
        className={`relative ${dimensions} rounded-full overflow-hidden`}
        style={{
          background: 'radial-gradient(circle at 30% 30%, rgba(255, 240, 220, 0.9), rgba(255, 200, 150, 0.7), rgba(139, 58, 143, 0.5))',
          boxShadow: '0 0 40px rgba(255, 200, 150, 0.6), inset 0 0 30px rgba(255, 255, 255, 0.3)',
        }}
        animate={isPlaying ? {
          scale: [1, 1.08, 1],
          boxShadow: [
            '0 0 40px rgba(255, 200, 150, 0.6), inset 0 0 30px rgba(255, 255, 255, 0.3)',
            '0 0 60px rgba(255, 200, 150, 0.9), inset 0 0 40px rgba(255, 255, 255, 0.5)',
            '0 0 40px rgba(255, 200, 150, 0.6), inset 0 0 30px rgba(255, 255, 255, 0.3)',
          ],
        } : {}}
        transition={{
          duration: 2.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        {/* Inner glow blobs */}
        <motion.div
          className="absolute w-16 h-16 rounded-full top-1/4 left-1/4"
          style={{
            background: 'radial-gradient(circle, rgba(255, 255, 255, 0.8) 0%, rgba(255, 255, 255, 0) 70%)',
            filter: 'blur(12px)',
          }}
          animate={isPlaying ? {
            x: [0, 20, -10, 0],
            y: [0, -15, 20, 0],
            scale: [1, 1.3, 0.9, 1],
            opacity: [0.7, 1, 0.6, 0.7],
          } : {}}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className="absolute w-12 h-12 rounded-full bottom-1/3 right-1/4"
          style={{
            background: 'radial-gradient(circle, rgba(255, 220, 180, 0.7) 0%, rgba(255, 220, 180, 0) 70%)',
            filter: 'blur(10px)',
          }}
          animate={isPlaying ? {
            x: [0, -15, 15, 0],
            y: [0, 20, -10, 0],
            scale: [1, 0.8, 1.2, 1],
            opacity: [0.6, 0.9, 0.5, 0.6],
          } : {}}
          transition={{
            duration: 3.5,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 0.5,
          }}
        />
      </motion.div>

      {/* Subtle outer glow */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'radial-gradient(circle, rgba(255, 200, 150, 0.2) 0%, transparent 70%)',
          filter: 'blur(30px)',
        }}
        animate={isPlaying ? {
          scale: [1, 1.2, 1],
          opacity: [0.4, 0.7, 0.4],
        } : {
          opacity: 0.3,
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </div>
  )
}

// Main Selector Component
function OrbSelector({ onSelect, currentSelection }) {
  const [previewOrb, setPreviewOrb] = useState(null)
  
  const orbStyles = [
    { id: 1, name: 'Gradient Blobs', component: OrbStyle1, description: 'Original flowing design' },
    { id: 2, name: 'Hexagonal Grid', component: OrbStyle2, description: 'Tech grid pattern' },
    { id: 3, name: 'Particle Ring', component: OrbStyle3, description: 'Orbiting particles' },
    { id: 4, name: 'Neon Rings', component: OrbStyle4, description: 'Spinning neon hoops' },
    { id: 5, name: 'Holographic', component: OrbStyle5, description: 'Rainbow shimmer' },
    { id: 6, name: 'Digital Matrix', component: OrbStyle6, description: 'Binary code style' },
    { id: 7, name: 'Plasma Ball', component: OrbStyle7, description: 'Electric arcs' },
    { id: 8, name: 'Quantum Field', component: OrbStyle8, description: 'Particle field' },
    { id: 9, name: 'Crystalline', component: OrbStyle9, description: 'Crystal facets' },
    { id: 10, name: 'Organic Halo', component: OrbStyle10, description: 'Natural flowing halo' },
  ]

  return (
    <div className="fixed inset-0 bg-black/95 z-50 flex items-center justify-center p-6 overflow-y-auto">
      <div className="max-w-6xl w-full">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-3xl font-bold mb-2">Choose Your Orb Style</h2>
            <p className="text-gray-400">Select a futuristic design for your AI assistant</p>
          </div>
          <button
            onClick={() => onSelect(null)}
            className="p-2 hover:bg-gray-800 rounded-full transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {orbStyles.map((style) => {
            const OrbComponent = style.component
            const isSelected = currentSelection === style.id
            
            return (
              <motion.div
                key={style.id}
                className={`relative bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl p-6 cursor-pointer border-2 transition-all ${
                  isSelected 
                    ? 'border-primary-pink shadow-lg shadow-primary-pink/50' 
                    : 'border-gray-700 hover:border-gray-600'
                }`}
                onClick={() => onSelect(style.id)}
                onMouseEnter={() => setPreviewOrb(style.id)}
                onMouseLeave={() => setPreviewOrb(null)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {isSelected && (
                  <div className="absolute top-4 right-4 w-6 h-6 bg-primary-pink rounded-full flex items-center justify-center">
                    <span className="text-white text-xs">✓</span>
                  </div>
                )}
                
                <div className="flex flex-col items-center">
                  <div className="mb-4 flex items-center justify-center h-40">
                    <OrbComponent isPlaying={previewOrb === style.id} size="small" />
                  </div>
                  
                  <h3 className="text-lg font-semibold mb-1">{style.name}</h3>
                  <p className="text-sm text-gray-400 text-center">{style.description}</p>
                </div>
              </motion.div>
            )
          })}
        </div>

        <div className="text-center text-gray-500 text-sm">
          <p>Hover over an orb to see it animate • Click to select</p>
        </div>
      </div>
    </div>
  )
}

export default OrbSelector
export { OrbStyle1, OrbStyle2, OrbStyle3, OrbStyle4, OrbStyle5, OrbStyle6, OrbStyle7, OrbStyle8, OrbStyle9, OrbStyle10 }
