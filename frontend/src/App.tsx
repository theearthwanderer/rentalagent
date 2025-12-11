import { useState, useEffect, useRef } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import { Send, User, Bot, MapPin, Bed, Bath, Search, Sparkles, Home, MessageSquare, Compass, Settings } from 'lucide-react'
import axios from 'axios'
import clsx from 'clsx'

// Types
interface ToolCall {
  type: 'tool_call'
  tool_name: string
  arguments: any
}

interface ToolResult {
  type: 'tool_result'
  tool_name: string
  result: any
}

interface Message {
  role: 'user' | 'assistant'
  content?: string
  tool_calls?: ToolCall[]
  tool_results?: ToolResult[]
}

interface Listing {
  id: string
  title: string
  price: number
  beds: number
  baths: number
  sqft: number
  city: string
  neighborhood: string
  description: string
  pets_allowed: boolean
  parking: boolean
  laundry: boolean
  air_conditioning: boolean
  vibe_score: number
  images: string[]
  external_url: string
}

function App() {
  const [sessionId, setSessionId] = useState<string>('')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<string>('')

  // State for the "Visual" side (Right Panel)
  // We'll extract listings from tool results to show on the right
  const [activeListings, setActiveListings] = useState<Listing[]>([])

  // Initialize Session
  useEffect(() => {
    const initSession = async () => {
      try {
        const res = await axios.post('http://localhost:8000/sessions', {})
        setSessionId(res.data.session_id)
      } catch (e) {
        console.error("Failed to init session", e)
      }
    }
    initSession()
  }, [])

  // WebSocket
  const { sendMessage, lastJsonMessage, readyState } = useWebSocket(
    sessionId ? `ws://localhost:8000/ws/${sessionId}` : null,
    {
      shouldReconnect: () => true,
    }
  )

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Handle Incoming Messages
  useEffect(() => {
    if (lastJsonMessage !== null) {
      const data = lastJsonMessage as any

      if (data.type === 'status') {
        setStatus(data.message)
      } else if (data.type === 'message') {
        setStatus('')
        setMessages(prev => [...prev, { role: data.role, content: data.content }])
      } else if (data.type === 'tool_call') {
        setStatus(`Executing tool: ${data.tool_name}...`)
      } else if (data.type === 'tool_result') {
        if (data.tool_name === 'search_listings') {
          // Add tool result to messagse for history tracking (optional display)
          // setMessages(prev => [...prev, { role: 'assistant', tool_results: [data] }])

          // CRITICAL: Update the "Active Listings" on the right panel
          if (Array.isArray(data.result) && data.result.length > 0) {
            setActiveListings(data.result)
          }
        }
        setStatus('')
      }
    }
  }, [lastJsonMessage])

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || readyState !== ReadyState.OPEN) return

    // Optimistic User Message
    setMessages(prev => [...prev, { role: 'user', content: input }])

    sendMessage(JSON.stringify({ type: 'message', content: input }))
    setInput('')
    setStatus('Thinking...')
  }

  return (
    <div className="flex h-screen bg-white text-gray-900 font-sans overflow-hidden">
      {/* 1. Sidebar (Navigation) */}
      <div className="w-[240px] flex flex-col py-6 border-r border-gray-100 bg-gray-50/50 flex-shrink-0">
        <div className="px-6 mb-8 flex items-center gap-3">
          <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center text-white shadow-sm">
            <Sparkles size={18} />
          </div>
          <span className="font-bold text-lg tracking-tight text-black">Havena</span>
        </div>

        <div className="flex flex-col gap-1 w-full px-3">
          <button className="flex items-center gap-3 p-3 rounded-xl bg-white text-black shadow-sm border border-gray-100 transition-all hover:bg-gray-50 group">
            <Home size={20} className="text-black" />
            <span className="font-medium">Chats</span>
          </button>
          <button className="flex items-center gap-3 p-3 rounded-xl text-gray-500 hover:bg-white hover:text-black hover:shadow-sm transition-all group">
            <MessageSquare size={20} className="group-hover:text-black" />
            <span className="font-medium">Trips</span>
          </button>
          <button className="flex items-center gap-3 p-3 rounded-xl text-gray-500 hover:bg-white hover:text-black hover:shadow-sm transition-all group">
            <Compass size={20} className="group-hover:text-black" />
            <span className="font-medium">Explore</span>
          </button>
        </div>

        <div className="mt-auto flex flex-col gap-1 w-full px-3">
          <button className="flex items-center gap-3 p-3 rounded-xl text-gray-500 hover:bg-white hover:text-black hover:shadow-sm transition-all group">
            <Settings size={20} className="group-hover:text-black" />
            <span className="font-medium">Settings</span>
          </button>
          <div className="w-full h-[1px] bg-gray-200 my-2"></div>
          <button className="flex items-center gap-3 p-3 rounded-xl text-gray-500 hover:bg-white hover:text-black hover:shadow-sm transition-all group">
            <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
              <User size={14} className="text-gray-500" />
            </div>
            <span className="font-medium">Renter</span>
          </button>
        </div>
      </div>

      {/* 2. Main Content Wrapper */}
      <div className="flex-1 flex min-w-0">
        {/* Left Panel: Chat Interface */}
        <div className="w-1/2 flex flex-col border-r border-gray-100 relative min-w-[500px]">

          {/* Header */}
          <div className="p-6 border-b border-gray-50 flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold tracking-tight text-gray-900">Rental Assistant</h1>
              <p className="text-xs text-gray-400 font-medium">Powered by Agentic AI</p>
            </div>
            <div className="px-3 py-1 bg-teal-50 text-teal-700 text-xs font-semibold rounded-full border border-teal-100">
              Beta
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-8 pb-32">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 mt-32">
                <p className="text-lg font-medium text-gray-500">How can I help you find a home?</p>
                <p className="text-sm mt-2">Try "Find a 1 bedroom in SoMa under $3500"</p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={clsx("flex gap-4 max-w-xl", msg.role === 'user' ? "ml-auto flex-row-reverse" : "")}>
                <div className={clsx("w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm",
                  msg.role === 'user' ? "bg-gray-900 text-white" : "bg-white border border-gray-200 text-teal-600")}>
                  {msg.role === 'user' ? <User size={14} /> : <Bot size={16} />}
                </div>

                <div className="space-y-2">
                  <div className={clsx("px-5 py-3.5 shadow-sm text-[15px] leading-relaxed",
                    msg.role === 'user'
                      ? "bg-gray-100/80 text-gray-900 rounded-2xl rounded-tr-sm"
                      : "bg-white border border-gray-100 text-gray-800 rounded-2xl rounded-tl-sm")}>
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}

            {status && (
              <div className="flex items-center gap-2 text-gray-400 text-sm ml-12 animate-pulse">
                <Search size={14} /> {status}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Floating Input Area */}
          <div className="absolute bottom-8 left-0 right-0 px-8">
            <form onSubmit={handleSubmit} className="relative max-w-2xl mx-auto shadow-xl rounded-full bg-white ring-1 ring-gray-200 focus-within:ring-2 focus-within:ring-teal-500 transition-all">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask anything..."
                className="w-full bg-transparent border-none text-gray-900 rounded-full pl-6 pr-14 py-4 focus:outline-none placeholder-gray-400"
                disabled={readyState !== ReadyState.OPEN && !!sessionId}
              />
              <button
                type="submit"
                disabled={!input.trim() || readyState !== ReadyState.OPEN}
                className="absolute right-2 top-2 p-2 bg-teal-500 hover:bg-teal-600 text-white rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send size={18} />
              </button>
            </form>
            <div className="text-center mt-3 text-xs text-gray-400 font-medium">
              {readyState === ReadyState.OPEN ? "AI Agent Active" : "Connecting..."}
            </div>
          </div>
        </div>

        {/* Right Panel: Visual Context (Map/Listings) */}
        <div className="w-1/2 bg-gray-50/50 p-8 overflow-y-auto">
          {activeListings.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded-3xl">
              <MapPin size={48} className="mb-4 opacity-20" />
              <p>Listings will appear here</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 content-start">
              {/* Listings Grid */}
              {activeListings.map((listing) => (
                <div key={listing.id} className="group bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden cursor-pointer flex flex-col h-full">
                  {/* Image */}
                  <div className="h-48 bg-gray-200 relative overflow-hidden">
                    {listing.images && listing.images.length > 0 ? (
                      <img src={listing.images[0]} alt={listing.title} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm font-medium">No Image</div>
                    )}
                    <div className="absolute top-3 right-3 bg-white/90 backdrop-blur px-2.5 py-1 rounded-lg text-xs font-bold text-gray-900 shadow-sm border border-gray-100/50">
                      ${listing.price.toLocaleString()}
                    </div>
                    {listing.vibe_score > 0 && (
                      <div className="absolute top-3 left-3 bg-black/70 backdrop-blur px-2 py-1 rounded-md text-[10px] font-bold text-white shadow-sm flex items-center gap-1">
                        <Sparkles size={10} className="text-yellow-400" /> {listing.vibe_score.toFixed(1)}
                      </div>
                    )}
                  </div>

                  <div className="p-5 flex flex-col flex-1">
                    <div className="flex-1">
                      <h3 className="font-bold text-gray-900 mb-1 line-clamp-1 leading-tight">{listing.title}</h3>
                      <p className="text-sm text-gray-500 mb-3 flex items-center gap-1">
                        <MapPin size={12} /> {listing.neighborhood || listing.city}
                      </p>

                      {/* Beds/Baths/Sqft */}
                      <div className="flex items-center gap-3 text-xs text-gray-700 font-medium mb-3">
                        <span className="flex items-center gap-1.5">
                          <Bed size={14} className="text-gray-400" /> {listing.beds} bd
                        </span>
                        <span className="flex items-center gap-1.5">
                          <Bath size={14} className="text-gray-400" /> {listing.baths} ba
                        </span>
                        {listing.sqft > 0 && (
                          <span className="text-gray-400">| {listing.sqft} sqft</span>
                        )}
                      </div>

                      {/* Amenities Badges */}
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {listing.pets_allowed && (
                          <span className="px-1.5 py-0.5 rounded-md bg-green-50 text-green-700 text-[10px] font-semibold border border-green-100">Pets</span>
                        )}
                        {listing.parking && (
                          <span className="px-1.5 py-0.5 rounded-md bg-blue-50 text-blue-700 text-[10px] font-semibold border border-blue-100">Parking</span>
                        )}
                        {listing.laundry && (
                          <span className="px-1.5 py-0.5 rounded-md bg-indigo-50 text-indigo-700 text-[10px] font-semibold border border-indigo-100">Laundry</span>
                        )}
                        {listing.air_conditioning && (
                          <span className="px-1.5 py-0.5 rounded-md bg-orange-50 text-orange-700 text-[10px] font-semibold border border-orange-100">AC</span>
                        )}
                      </div>
                    </div>

                    <a href={listing.external_url} target="_blank" rel="noopener" className="mt-4 block w-full text-center py-2.5 bg-gray-900 hover:bg-gray-800 text-white rounded-xl text-sm font-medium transition-colors">
                      View Details
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
