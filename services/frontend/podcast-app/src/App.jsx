import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Registration from './pages/Registration'
import Podcast from './pages/Podcast'
import AboutUs from './pages/AboutUs'
import Settings from './pages/Settings'
import Preferences from './pages/Preferences'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Registration />} />
        <Route path="/podcast" element={<Podcast />} />
        <Route path="/about" element={<AboutUs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/preferences" element={<Preferences />} />
      </Routes>
    </Router>
  )
}

export default App
