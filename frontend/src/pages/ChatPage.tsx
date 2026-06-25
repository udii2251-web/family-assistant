import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { sendMessage } from '../api'
import type { ChatResponse } from '../types'

interface Message {
  role: 'user' | 'assistant'
  content: string
  actions?: ChatResponse['actions']
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const res = await sendMessage(userMsg)
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: res.reply, actions: res.actions },
      ])
    } catch (e) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `出错了：${e instanceof Error ? e.message : '未知错误'}` },
      ])
    }
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 bg-white border-b">
        <h2 className="text-lg font-semibold">和家庭助手聊天</h2>
        <p className="text-sm text-gray-500">告诉我买了什么、用了什么，我来帮你管理</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white border shadow-sm'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
                  {msg.actions.map((a, j) => (
                    <div key={j}>
                      <span className="font-medium">{a.tool}</span>
                      <span className="ml-1">{JSON.stringify(a.args)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border shadow-sm rounded-2xl px-4 py-2">
              <p className="text-sm text-gray-400">思考中...</p>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="说点什么... 例如：刚买了5kg大米"
            className="flex-1 border rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="bg-blue-500 text-white rounded-xl px-4 py-2 disabled:opacity-50 hover:bg-blue-600 transition-colors"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
