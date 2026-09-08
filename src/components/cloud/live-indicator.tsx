import { motion } from "motion/react";

/** Small Apple-style pill showing the Socket.IO stream state. */
export function LiveIndicator({ connected, label }: { connected: boolean; label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-glass-border bg-card/70 px-3 py-1 text-[12px] text-muted-foreground">
      <span className="relative flex size-2">
        {connected && (
          <motion.span
            className="absolute inline-flex size-full rounded-full bg-success"
            animate={{ opacity: [0.7, 0, 0.7], scale: [1, 2.2, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        <span
          className={`relative inline-flex size-2 rounded-full ${connected ? "bg-success" : "bg-muted-foreground"}`}
        />
      </span>
      {label ?? (connected ? "Live · 1s" : "Reconnecting…")}
    </span>
  );
}
