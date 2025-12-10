import { useState, useEffect, useRef } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import { Send, User, Bot, MapPin, Bed, Bath, Coins, Search } from 'lucide-react'
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
        // If it's a search result, we might want to display it specially
        // For now, we rely on the agent to summarize, but we could augment the chat 
        // if we detect tool results.
        // Let's store it in the last message or a new "tool" message type?
        // Simpler: Just rely on Agent text for now, but if we want cards...
        // The backend `run_turn` returns text.
        // But if `tool_result` contains listings, we can render them!
        if (data.tool_name === 'search_listings') {
          // We can add a specialized message or attach to latest
          setMessages(prev => [...prev, { role: 'assistant', tool_results: [data] }])
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
    <div className="flex h-screen bg-gray-900 text-gray-100 font-sans">
      {/* Sidebar / Info */}
      <div className="w-80 border-r border-gray-800 p-6 hidden md:block bg-gray-950">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-teal-400 bg-clip-text text-transparent mb-6">
          Rental Agent
        </h1>
        <div className="space-y-4 text-sm text-gray-400">
          <p>This agent can help you find rental properties in San Francisco.</p>
          <div className="p-4 bg-gray-900 rounded-lg border border-gray-800">
            <h3 className="font-semibold text-gray-200 mb-2">Capabilities</h3>
            <ul className="list-disc pl-4 space-y-1">
              <li>Natural Language Search</li>
              <li>Price & Amenity Filters</li>
              <li>Neighborhood Knowledge</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-20">
              <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Hello! I'm your Rental Agent.</p>
              <p className="text-sm">Ask me something like "Find me a 1bd in SoMa under $3500"</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={clsx("flex gap-4 max-w-3xl", msg.role === 'user' ? "ml-auto flex-row-reverse" : "")}>
              <div className={clsx("w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                msg.role === 'user' ? "bg-blue-600" : "bg-teal-600")}>
                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
              </div>

              <div className="space-y-2">
                {/* Text Content */}
                {msg.content && (
                  <div className={clsx("p-4 rounded-2xl",
                    msg.role === 'user' ? "bg-blue-600 text-white rounded-tr-sm" : "bg-gray-800 text-gray-100 rounded-tl-sm")}>
                    {msg.content}
                  </div>
                )}

                {/* Tool Results (Listings) */}
                {msg.tool_results?.map((tr, idx) => (
                  <div key={idx} className="space-y-3 mt-2">
                    {Array.isArray(tr.result) && tr.result.map((listing: Listing) => (
                      <div key={listing.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 w-80 hover:border-teal-500 transition-colors">
                        <h4 className="font-bold text-lg text-white mb-1">{listing.title}</h4>
                        <div className="flex items-center gap-2 text-teal-400 font-mono mb-2">
                          <Coins size={14} /> ${listing.price}/mo
                        </div>
                        <div className="flex gap-4 text-xs text-gray-400 mb-3">
                          <span className="flex items-center gap-1"><Bed size={12} /> {listing.beds} Beds</span>
                          <span className="flex items-center gap-1"><Bath size={12} /> {listing.baths} Baths</span>
                          <span className="flex items-center gap-1"><MapPin size={12} /> {listing.neighborhood}</span>
                        </div>
                        <p className="text-xs text-gray-500 line-clamp-2 mb-3">{listing.description}</p>
                        <a href={listing.external_url} target="_blank" rel="noopener" className="block w-full text-center py-2 bg-gray-700 hover:bg-gray-600 rounded text-xs font-semibold">
                          View Listing
                        </a>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          ))}

          {status && (
            <div className="flex gap-2 items-center text-gray-500 text-sm ml-12 animate-pulse">
              <Search size={14} /> {status}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-800 bg-gray-900/50 backdrop-blur">
          <form onSubmit={handleSubmit} className="flex gap-2 max-w-3xl mx-auto relative">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your ideal rental..."
              className="flex-1 bg-gray-800 border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent placeholder-gray-500"
              disabled={readyState !== ReadyState.OPEN && !!sessionId}
            />
            <button
              type="submit"
              disabled={!input.trim() || readyState !== ReadyState.OPEN}
              className="bg-teal-600 hover:bg-teal-500 text-white p-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send size={20} />
            </button>
          </form>
          <div className="text-center mt-2 text-xs text-gray-600">
            {readyState === ReadyState.OPEN ? "Connected" : "Connecting..."}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
