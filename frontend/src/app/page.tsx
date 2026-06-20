"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Message {
  role: "user" | "agent";
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

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
      setMessages((prev) => [...prev, { role: "agent", content: "Error connecting to backend. Is the FastAPI server running?" }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-zinc-950 text-white">
      <Card className="w-full max-w-4xl h-[85vh] flex flex-col bg-zinc-900 border-zinc-800 shadow-2xl">
        <CardHeader className="border-b border-zinc-800 pb-4">
          <CardTitle className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            AI Personal Operating System
          </CardTitle>
          <p className="text-zinc-400 text-sm">Your Digital Chief of Staff connected via AutoGen & MCP</p>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col p-4 overflow-hidden gap-4">
          <ScrollArea className="flex-1 pr-4">
            <div className="flex flex-col gap-4">
              {messages.length === 0 ? (
                <div className="text-zinc-500 text-center mt-10 text-lg">
                  What would you like me to orchestrate for you today?
                </div>
              ) : (
                messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[80%] p-4 rounded-xl text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-zinc-800 text-zinc-100"
                      }`}
                      style={{ whiteSpace: "pre-wrap" }}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))
              )}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-zinc-800 text-zinc-400 p-4 rounded-xl animate-pulse text-sm">
                    Chief Agent is coordinating...
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
          <div className="flex gap-2 pt-2 border-t border-zinc-800 mt-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="e.g. Prepare me for the Deloitte interview..."
              className="bg-zinc-950 border-zinc-700 text-white text-md py-6"
              disabled={isLoading}
            />
            <Button onClick={sendMessage} disabled={isLoading || !input.trim()} className="bg-blue-600 hover:bg-blue-700 py-6 px-8 text-md font-medium">
              Send
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
