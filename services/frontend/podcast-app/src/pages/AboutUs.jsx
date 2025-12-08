import { ArrowLeft, Twitter, Linkedin, Github, Mail } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

function AboutUs() {
  const navigate = useNavigate()

  const teamMembers = [
    {
      name: 'Zac',
      role: 'Frontend Master of the Universe I',
      bio: 'I\'m not just here to talk, I\'m here to listen. I believe in the power of conversation to change the world.',
      image: '👤'
    },
    {
      name: 'Josh',
      role: 'Frontend Master of the Universe II',
      bio: 'I\'m not just here to talk, I\'m here to listen. I believe in the power of conversation to change the world.',
      image: '👤'
    },
    {
      name: 'Khaled',
      role: 'Master Scraper, Tester and Gitter',
      bio: 'I\'m not just here to talk, I\'m here to listen. I believe in the power of conversation to change the world.',
      image: '👤'
    },
    {
      name: 'Chris',
      role: 'Deploying is my mission',
      bio: 'I\'m not just here to talk, I\'m here to listen. I believe in the power of conversation to change the world.',
      image: '👤'
    }
  ]

  const testimonials = [
    {
      name: 'Sarah Johnson',
      text: 'This podcast app has completely transformed how I consume content. The AI interactions feel so natural!',
      rating: 5
    },
    {
      name: 'Michael Chen',
      text: 'I love how personalized the experience is. It\'s like having a conversation with a knowledgeable friend.',
      rating: 5
    },
    {
      name: 'Emily Rodriguez',
      text: 'The voice interaction is seamless and the content is always relevant. Highly recommend!',
      rating: 5
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

        {/* Testimonials */}
        <section className="space-y-8">
          <h3 className="text-2xl font-bold text-center">Testimonials</h3>
          <div className="space-y-4">
            {testimonials.map((testimonial, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-6 border border-gray-700"
              >
                <div className="flex gap-1 mb-3">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <span key={i} className="text-primary-pink text-xl">★</span>
                  ))}
                </div>
                <p className="text-gray-300 mb-4">{testimonial.text}</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-primary-pink to-primary-purple rounded-full flex items-center justify-center">
                    👤
                  </div>
                  <span className="font-semibold">{testimonial.name}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Contact CTA */}
        <section className="text-center space-y-6 py-8">
          <h3 className="text-2xl font-bold">Get in touch</h3>
          <p className="text-gray-400">Have questions or feedback? We'd love to hear from you!</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <input
              type="email"
              placeholder="Enter your e-mail address and get started"
              className="w-full sm:w-96 px-6 py-4 bg-transparent border border-gray-700 rounded-full text-white placeholder-gray-500 focus:outline-none focus:border-primary-pink transition-colors"
            />
            <button className="px-8 py-4 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all whitespace-nowrap">
              Get Started
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

export default AboutUs
