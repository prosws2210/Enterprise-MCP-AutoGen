"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Bot, User, Cpu } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  role: "user" | "agent";
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });
      const data = await response.json();
      
      const agentMessage: Message = { role: "agent", content: data.response };
      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      console.error("Failed to send message:", error);
      setMessages((prev) => [...prev, { role: "agent", content: "Error connecting to backend. Ensure FastAPI is running on port 8000." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex h-screen flex-col bg-black text-cyan-50 font-sans overflow-hidden">
      {/* Dynamic Background Grid */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none" 
           style={{ backgroundImage: 'radial-gradient(circle at center, #0891b2 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

      {/* Header */}
      <header className="relative z-20 flex items-center justify-between px-8 py-4 border-b border-cyan-900/50 bg-black/50 backdrop-blur-md shadow-[0_0_20px_rgba(8,145,178,0.15)]">
        <div className="flex items-center gap-3">
          <Cpu className="w-8 h-8 text-cyan-400" />
          <h1 className="text-2xl font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600">
            J.A.R.V.I.S.
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
          </span>
          <span className="text-xs uppercase tracking-[0.2em] text-cyan-500 font-bold">Online</span>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="relative flex-1 overflow-y-auto z-10 custom-scrollbar">
        <div className="flex flex-col min-h-full max-w-5xl mx-auto px-4 py-8 justify-end">
          <AnimatePresence initial={false}>
            {messages.length === 0 ? (
              <motion.div 
                key="ai-core-empty"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.1, filter: "blur(10px)" }}
                className="flex flex-col items-center justify-center flex-1 py-20"
              >
                {/* AI Core Animation */}
                <div className="relative w-64 h-64 flex items-center justify-center">
                  {/* Outer Ring */}
                  <motion.div 
                    animate={{ rotate: 360 }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                    className="absolute inset-0 rounded-full border border-dashed border-cyan-500/30 opacity-50"
                  />
                  {/* Middle Ring */}
                  <motion.div 
                    animate={{ rotate: -360 }}
                    transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                    className="absolute inset-4 rounded-full border-2 border-dashed border-cyan-400/40"
                  />
                  {/* Inner Ring */}
                  <motion.div 
                    animate={{ rotate: 360 }}
                    transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                    className="absolute inset-10 rounded-full border border-blue-500/50"
                  />
                  {/* Core Orb */}
                  <motion.div 
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                    className="w-16 h-16 rounded-full bg-cyan-400 shadow-[0_0_50px_rgba(34,211,238,0.8)]"
                  />
                </div>
                <h2 className="mt-12 text-2xl tracking-[0.3em] font-light text-cyan-200">AWAITING DIRECTIVES</h2>
              </motion.div>
            ) : (
              <div className="flex flex-col gap-6 pt-10">
                {messages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: msg.role === "user" ? 20 : -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`flex gap-4 w-full ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                  >
                    <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded bg-black border border-cyan-500/30 shadow-[0_0_10px_rgba(8,145,178,0.2)]">
                      {msg.role === "user" ? <User className="w-5 h-5 text-cyan-100" /> : <Bot className="w-5 h-5 text-cyan-400" />}
                    </div>
                    <div className={`max-w-[80%] p-4 rounded-lg relative overflow-hidden ${
                      msg.role === "user" 
                        ? "bg-cyan-950/40 border border-cyan-800/50 text-cyan-50" 
                        : "bg-blue-950/20 border border-blue-800/30 text-blue-100"
                    }`}>
                      {/* Holographic Scanline */}
                      {msg.role === "agent" && (
                        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-500/10 to-transparent h-full w-full animate-[scan_3s_linear_infinite] pointer-events-none" />
                      )}
                      <pre className="whitespace-pre-wrap font-sans text-[15px] leading-relaxed relative z-10">{msg.content}</pre>
                    </div>
                  </motion.div>
                ))}
                
                {isLoading && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
                    <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded bg-black border border-cyan-500/50 shadow-[0_0_15px_rgba(8,145,178,0.5)]">
                      <Bot className="w-5 h-5 text-cyan-400 animate-pulse" />
                    </div>
                    <div className="p-4 rounded-lg bg-blue-950/20 border border-blue-800/30 flex items-center gap-2">
                      <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce delay-100" />
                      <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce delay-200" />
                    </div>
                  </motion.div>
                )}
              </div>
            )}
          </AnimatePresence>
          <div ref={messagesEndRef} className="h-4" />
        </div>
      </div>

      {/* Input Area */}
      <div className="relative z-20 p-6 bg-black/60 backdrop-blur-xl border-t border-cyan-900/50">
        <div className="max-w-4xl mx-auto relative group">
          {/* Glowing perimeter */}
          <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-600 to-blue-600 rounded-lg blur opacity-30 group-focus-within:opacity-60 transition duration-500"></div>
          
          <div className="relative flex items-center bg-black border border-cyan-800 rounded-lg overflow-hidden">
            <div className="pl-4 text-cyan-500">
              <span className="animate-pulse">❯</span>
            </div>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Enter command directive..."
              className="flex-1 bg-transparent border-none text-cyan-100 placeholder:text-cyan-800 focus-visible:ring-0 text-lg py-6 shadow-none"
              disabled={isLoading}
            />
            <Button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="mr-2 bg-cyan-950 text-cyan-400 hover:bg-cyan-900 hover:text-cyan-300 rounded border border-cyan-800 disabled:opacity-50"
            >
              <Send className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}
