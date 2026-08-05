import Link from "next/link";
import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { Term } from "@/components/Term";

interface LiveMessage {
  type: "print" | "alert";
  ticker: string;
  executed_at: string;
  price: number;
  size: number;
  premium: number;
  size_class: string;
  rule?: string;
}

/** Live prints/alerts over /ws/live. Shows its connection state honestly —
 * the feed only runs when the API was started with INTRADAY_ENABLED=1.
 */
export function LiveFeed() {
  const [messages, setMessages] = useState<LiveMessage[]>([]);
  const [state, setState] = useState<"connecting" | "open" | "closed">("connecting");

  useEffect(() => {
    const socket = new WebSocket(`${API_URL.replace(/^http/, "ws")}/ws/live`);
    socket.onopen = () => setState("open");
    socket.onclose = () => setState("closed");
    socket.onerror = () => setState("closed");
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as LiveMessage;
        setMessages((current) => [message, ...current].slice(0, 20));
      } catch {
        /* ignore malformed frames */
      }
    };
    return () => socket.close();
  }, []);

  return (
    <section className="card">
      <h3>
        Live feed{" "}
        <span className={state === "open" ? "badge badge-blue" : "badge"}>
          {state}
        </span>
      </h3>
      {messages.length === 0 ? (
        <p className="muted">
          {state === "open"
            ? "Connected — waiting for prints."
            : "No live connection. Start the API with INTRADAY_ENABLED=1 during market hours."}
        </p>
      ) : (
        <ul className="alert-list">
          {messages.map((message) => (
            <li key={`${message.ticker}-${message.executed_at}-${message.size}`}>
              {message.type === "alert" ? (
                <span className="badge badge-red">{message.rule}</span>
              ) : (
                <span className="badge">{message.size_class}</span>
              )}
              <Link href={`/symbol/${message.ticker}`} className="ticker">
                {message.ticker}
              </Link>
              <span className="why">
                {message.size.toLocaleString()} @ {message.price.toFixed(2)} ($
                {(message.premium / 1e6).toFixed(2)}M) ·{" "}
                <Term k="print">{message.executed_at.slice(11, 19)}Z</Term>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
