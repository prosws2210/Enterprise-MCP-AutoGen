"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  role: "user" | "agent";
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
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
    <main className="relative flex min-h-screen flex-col items-center justify-center p-0 overflow-hidden font-sans bg-black">
      {/* Animated Background Elements */}
      <div className="absolute top-[-20%] left-[-10%] w-[60vw] h-[60vw] rounded-full bg-cyan-900/20 blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[60vw] h-[60vw] rounded-full bg-violet-900/20 blur-[150px] pointer-events-none" />
      
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="w-full h-screen z-10 flex flex-col"
      >
        <div className="flex-1 flex flex-col bg-black/40 backdrop-blur-3xl overflow-hidden relative">
          
          {/* Header */}
          <header className="border-b border-white/5 py-4 px-6 md:px-8 bg-black/20 backdrop-blur-md flex items-center justify-between z-20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-cyan-400 to-violet-600 rounded-lg shadow-[0_0_20px_rgba(6,182,212,0.4)]">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                  AI-POS
                </h1>
                <p className="text-zinc-400 text-xs tracking-widest uppercase font-medium mt-1">
                  Digital Chief of Staff
                </p>
              </div>
            </div>
          </header>

          {/* Chat Content */}
          <div className="flex-1 flex flex-col overflow-hidden relative z-10">
            <ScrollArea className="flex-1 w-full">
              <div className="flex flex-col gap-6 px-4 md:px-12 lg:px-24 py-8 pb-32 max-w-5xl mx-auto w-full">
                <AnimatePresence initial={false} mode="popLayout">
                  {messages.length === 0 ? (
                    <motion.div
                      key="empty-state"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="h-full flex flex-col items-center justify-center text-center mt-32 md:mt-48"
                    >
                      <Bot className="w-20 h-20 text-zinc-700 mb-6 drop-shadow-2xl" />
                      <h3 className="text-3xl font-semibold text-zinc-200">System Ready</h3>
                      <p className="text-zinc-500 max-w-md mt-4 text-lg">
                        Your enterprise agentic platform is online. How can I orchestrate your workflow today?
                      </p>
                    </motion.div>
                  ) : (
                    messages.map((msg, i) => (
                      <motion.div
                        key={`msg-${i}`}
                        initial={{ opacity: 0, y: 15, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        transition={{ duration: 0.4, type: "spring", bounce: 0.3 }}
                        className={`flex gap-4 w-full ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                      >
                        <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-lg ${msg.role === "user" ? "bg-gradient-to-br from-cyan-400 to-blue-600" : "bg-zinc-800 border border-white/10"}`}>
                          {msg.role === "user" ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-cyan-400" />}
                        </div>
                        <div
                          className={`max-w-[85%] p-5 text-[15px] leading-relaxed ${
                            msg.role === "user"
                              ? "bg-gradient-to-br from-white/10 to-white/5 border border-white/10 rounded-3xl rounded-tr-sm text-zinc-50 shadow-md"
                              : "bg-black/40 backdrop-blur-xl border border-white/5 rounded-3xl rounded-tl-sm text-zinc-300 shadow-[inset_0_0_30px_rgba(255,255,255,0.02)]"
                          }`}
                          style={{ whiteSpace: "pre-wrap" }}
                        >
                          {msg.content}
                        </div>
                      </motion.div>
                    ))
                  )}
                  {isLoading && (
                    <motion.div
                      key="loading-state"
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="flex gap-4 w-full max-w-5xl mx-auto"
                    >
                      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-zinc-800 border border-white/10 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.4)]">
                        <Bot className="w-5 h-5 text-cyan-400 animate-pulse" />
                      </div>
                      <div className="p-5 bg-black/40 backdrop-blur-xl border border-white/5 rounded-3xl rounded-tl-sm flex items-center gap-3 shadow-md">
                        <div className="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </motion.div>
                  )}
                  <div ref={scrollRef} key="scroll-anchor" className="h-4" />
                </AnimatePresence>
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="absolute bottom-0 left-0 right-0 p-4 md:p-8 bg-gradient-to-t from-black via-black/80 to-transparent z-20">
              <div className="relative group mx-auto w-full max-w-4xl">
                <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 to-violet-500 rounded-3xl blur-lg opacity-20 group-focus-within:opacity-50 transition duration-700"></div>
                <div className="relative flex gap-3 p-2 bg-zinc-950/90 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-2xl">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    placeholder="Initialize a new project, query Notion, or analyze code..."
                    className="flex-1 bg-transparent border-none text-white focus-visible:ring-0 focus-visible:ring-offset-0 text-lg py-7 px-6 placeholder:text-zinc-600 shadow-none h-auto"
                    disabled={isLoading}
                  />
                  <Button
                    onClick={sendMessage}
                    disabled={isLoading || !input.trim()}
                    className="h-auto aspect-square rounded-2xl bg-white text-black hover:bg-zinc-200 transition-all duration-300 shadow-[0_0_20px_rgba(255,255,255,0.2)] disabled:bg-zinc-800 disabled:text-zinc-500 disabled:shadow-none p-4"
                  >
                    <Send className="w-6 h-6" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </main>
  );
}
