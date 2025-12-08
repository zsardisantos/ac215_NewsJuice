import { ArrowLeft, Twitter, Linkedin, Github, Mail } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

function AboutUs() {
  const navigate = useNavigate()

  const teamMembers = [
    {
      name: 'Zac Sardi-Santos',
      role: 'AI & Machine Learning Lead',
      bio: 'Computer Science and Applied Math student at Harvard with a passion for AI, robotics, and building intelligent systems that transform how we interact with information.',
      image: '👤'
    },
    {
      name: 'Josh Rosenblum',
      role: 'Audio & UX Designer',
      bio: 'Bringing expertise in audio production and user experience design to create seamless, engaging voice interactions that feel natural and intuitive.',
      image: '👤'
    },
    {
      name: 'Khaled Aly',
      role: 'Full-Stack Developer',
      bio: 'Passionate about building scalable applications and creating elegant solutions that bridge the gap between complex technology and user-friendly experiences.',
      image: '👤'
    },
    {
      name: 'Christian Michel',
      role: 'Backend & Infrastructure',
      bio: 'Focused on building robust backend systems and cloud infrastructure that power real-time AI conversations and ensure seamless performance at scale.',
      image: '👤'
    }
  ]



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
          <h1 className="text-xl font-semibold">About Us</h1>
          <div className="w-10"></div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-12 space-y-16">
        {/* Hero Section */}
        <section className="text-center space-y-4">
          <h2 className="text-3xl md:text-4xl font-bold">AI-Powered Podcast</h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            We're building the future of interactive audio experiences. Have conversations with AI that feel natural,
            informative, and engaging.
          </p>
        </section>

        {/* Meet Our Team */}
        <section className="space-y-8">
          <h3 className="text-2xl font-bold text-center">Meet our team</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {teamMembers.map((member, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700 hover:border-primary-pink/50 transition-all"
              >
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 bg-gradient-to-br from-primary-pink to-primary-purple rounded-full flex items-center justify-center text-3xl">
                    {member.image}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-lg">{member.name}</h4>
                    <p className="text-primary-pink text-sm mb-2">{member.role}</p>
                    <p className="text-gray-400 text-sm">{member.bio}</p>
                    <div className="flex gap-3 mt-4">
                      <button className="text-gray-400 hover:text-primary-pink transition-colors">
                        <Twitter size={18} />
                      </button>
                      <button className="text-gray-400 hover:text-primary-pink transition-colors">
                        <Linkedin size={18} />
                      </button>
                      <button className="text-gray-400 hover:text-primary-pink transition-colors">
                        <Github size={18} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Mission Statement */}
        <section className="bg-gradient-to-br from-primary-purple/20 to-primary-pink/10 rounded-2xl p-8 border border-primary-purple/30">
          <h3 className="text-2xl font-bold mb-4">Our Mission</h3>
          <p className="text-gray-300 leading-relaxed">
            We believe in democratizing access to information through natural conversation. Our AI-powered podcast
            platform makes learning and discovery as simple as having a chat. Whether you're commuting, exercising,
            or relaxing at home, we bring you personalized content that adapts to your interests and questions in real-time.
          </p>
        </section>


      </div>
    </div>
  )
}

export default AboutUs
