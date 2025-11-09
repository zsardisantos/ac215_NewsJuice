# Quick Start Guide

## 🚀 Your AI Podcast App is Ready!

The development server is running at: **http://localhost:3000**

## 📱 App Flow

### 1. **Login Page** (Default landing page)
- Enter any email and password (no validation - it's a mockup)
- Or click "Register" to go to the registration page
- Click "Login" to access the main podcast screen

### 2. **Main Podcast Screen**
- **Animated Orb**: The centerpiece that pulses and animates during AI playback
- **Status Message**: Shows current state ("Go ahead, I'm listening", "Listening...", "Processing...", etc.)
- **Call Button** (Pink circle):
  - **Press and hold** to start recording from your microphone
  - **Release** to stop recording and trigger AI response
  - **Press again during playback** to interrupt and start new recording
- **News Topics**: Scrollable topic buttons (decorative)
- **Sources**: Sample news articles (decorative)
- **Hamburger Menu** (top right): Access Settings, About Us, and Logout

### 3. **Settings Page**
- Account information management
- Contact info
- Password settings
- Time zone and language preferences
- Delete account option

### 4. **About Us Page**
- Team member profiles
- Mission statement
- Testimonials
- Contact form

### 5. **Registration Page**
- Full name, email, password fields
- Link back to login

## 🎨 Color Scheme

The app uses the purple/pink gradient theme from your reference images:
- **Primary Pink**: `#FF3B9A`
- **Primary Purple**: `#8B3A8F`
- **Dark Backgrounds**: `#1A1625` and `#0F0B14`

## 🎙️ How the Voice Interaction Works

1. **Press and hold** the pink call button
2. Your browser will request microphone permission (allow it)
3. Speak your question or comment
4. **Release** the button when done
5. The app will show "Processing..." briefly
6. Then it will display a simulated AI response
7. The animated orb will pulse and animate during the "playback"
8. After 3-5 seconds, it returns to listening mode

**Note**: If you press the call button while the AI is "speaking", it will immediately stop and start listening to you again.

## 🔧 Technical Notes

- **Microphone Access**: Required for recording functionality
- **Browser Compatibility**: Works best in Chrome, Edge, Firefox, Safari
- **Responsive**: Fully responsive design works on mobile, tablet, and desktop
- **Animations**: Powered by Framer Motion for smooth, performant animations
- **No Backend**: This is a pure frontend mockup - all responses are simulated

## 📂 Project Structure

```
podcast-app/
├── src/
│   ├── components/
│   │   └── AnimatedOrb.jsx       # The animated orb component
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Registration.jsx
│   │   ├── Podcast.jsx           # Main screen
│   │   ├── AboutUs.jsx
│   │   └── Settings.jsx
│   ├── App.jsx                    # Router setup
│   └── main.jsx
```

## 🛠️ Development Commands

- **Start dev server**: `npm run dev`
- **Build for production**: `npm run build`
- **Preview production build**: `npm run preview`

## 🎯 Next Steps

To connect this to a real backend:
1. Replace simulated AI responses with actual API calls
2. Add authentication logic to Login/Registration
3. Implement real audio processing and speech-to-text
4. Add text-to-speech for AI responses
5. Store user preferences and conversation history

Enjoy your interactive podcast app! 🎉
