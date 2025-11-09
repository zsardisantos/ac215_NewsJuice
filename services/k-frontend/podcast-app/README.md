# AI Podcast Interactive App

An interactive podcast application built with React, featuring voice interaction, animated visualizations, and a modern UI design.

## Features

- 🎙️ **Voice Recording**: Press and hold to record your voice
- 🤖 **AI Responses**: Simulated AI podcast responses
- 🎨 **Animated Orb**: Beautiful Framer Motion animations that react to audio playback
- 📱 **Responsive Design**: Works on mobile, tablet, and desktop
- 🎯 **Multiple Pages**: Login, Registration, About Us, Settings, and Main Podcast screen
- 🎨 **Modern UI**: Purple/pink gradient color scheme with smooth transitions

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **Framer Motion** - Animation library
- **React Router** - Client-side routing
- **Lucide React** - Icon library

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

1. Navigate to the project directory:
```bash
cd podcast-app
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser and navigate to `http://localhost:3000`

## Usage

### Main Podcast Screen

1. **Press and hold** the pink call button to start recording your voice
2. **Release** the button to stop recording
3. The app will simulate an AI response and play it back
4. The animated orb will pulse and animate during playback
5. **Press the button again** during playback to interrupt and start a new recording

### Navigation

- Use the hamburger menu (top right) to access:
  - Settings
  - About Us
  - Logout

### Pages

- **Login** (`/login`) - Authentication page with email/password
- **Registration** (`/register`) - User registration form
- **Podcast** (`/podcast`) - Main interactive podcast screen
- **About Us** (`/about`) - Team information and testimonials
- **Settings** (`/settings`) - User account and preferences

## Color Scheme

- **Primary Pink**: `#FF3B9A`
- **Primary Purple**: `#8B3A8F`
- **Dark Background**: `#1A1625`
- **Darker Background**: `#0F0B14`

## Project Structure

```
podcast-app/
├── src/
│   ├── components/
│   │   └── AnimatedOrb.jsx       # Animated orb component
│   ├── pages/
│   │   ├── Login.jsx              # Login page
│   │   ├── Registration.jsx       # Registration page
│   │   ├── Podcast.jsx            # Main podcast screen
│   │   ├── AboutUs.jsx            # About us page
│   │   └── Settings.jsx           # Settings page
│   ├── App.jsx                    # Main app component with routing
│   ├── main.jsx                   # App entry point
│   └── index.css                  # Global styles
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── README.md
```

## Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Preview Production Build

```bash
npm run preview
```

## Notes

- This is a **mockup/prototype** - no backend integration
- Audio recording uses the Web Audio API (requires HTTPS or localhost)
- **Audio playback uses Web Speech API** - you will hear actual spoken responses
- Microphone permissions are required for recording functionality
- AI responses are simulated with random text but spoken aloud using text-to-speech

## Future Enhancements

- Backend integration for real AI responses
- User authentication and data persistence
- Podcast history and saved conversations
- Real-time audio visualization with frequency data
- Multiple AI voice personalities
- Transcript generation

## License

MIT
