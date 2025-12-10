import { useState, useEffect, useRef } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import { Send, User, Bot, MapPin, Bed, Bath, Search, Sparkles } from 'lucide-react'
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
  city: string
  neighborhood: string
  description: string
  vector?: number[]
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
      {/* Left Panel: Chat Interface */}
      <div className="w-1/2 flex flex-col border-r border-gray-100 relative">

        {/* Header */}
        <div className="p-6 border-b border-gray-50 flex items-center gap-2">
          <div className="w-8 h-8 bg-teal-500 rounded-lg flex items-center justify-center text-white">
            <Sparkles size={18} />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-gray-900">Rental Agent</h1>
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
            {activeListings.map((listing) => (
              <div key={listing.id} className="group bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden cursor-pointer">
                {/* Image Placeholder */}
                <div className="h-40 bg-gray-200 relative">
                  <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm font-medium">
                    See on Zillow
                  </div>
                  <div className="absolute top-3 right-3 bg-white/90 backdrop-blur px-2 py-1 rounded-md text-xs font-bold text-gray-900 shadow-sm">
                    ${listing.price}
                  </div>
                </div>

                <div className="p-5">
                  <h3 className="font-semibold text-gray-900 mb-1 line-clamp-1">{listing.title}</h3>
                  <p className="text-sm text-gray-500 mb-4 flex items-center gap-1">
                    <MapPin size={12} /> {listing.city}, {listing.neighborhood}
                  </p>

                  <div className="flex items-center gap-4 text-xs text-gray-600 font-medium">
                    <span className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
                      <Bed size={14} className="text-gray-400" /> {listing.beds}
                    </span>
                    <span className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
                      <Bath size={14} className="text-gray-400" /> {listing.baths}
                    </span>
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
  )
}

export default App
