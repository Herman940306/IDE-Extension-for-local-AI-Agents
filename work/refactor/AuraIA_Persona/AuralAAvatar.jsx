import React, { useEffect, useState } from "react";

export default function AuralAAvatar({ tone = "calm", size = 64 }) {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setPhase(p => (p + 1) % 360), 400);
    return () => clearInterval(t);
  }, []);

  const toneMap = {
    calm: "from-[#667eea] to-[#764ba2]",
    creative: "from-[#ff7eb6] to-[#7afcff]",
    technical: "from-[#00f0ff] to-[#1af0a7]",
    friendly: "from-[#7ee787] to-[#ffd166]"
  };

  const gradient = toneMap[tone] || toneMap["calm"];

  return (
    <div className="flex items-center space-x-3">
      <div
        aria-hidden="true"
        className={`rounded-full p-1 bg-gradient-to-br ${gradient} shadow-2xl`}
        style={{ width: size, height: size }}
      >
        <div
          className="rounded-full bg-white/5 backdrop-blur flex items-center justify-center"
          style={{
            width: "100%",
            height: "100%",
            transform: `scale(${1 + Math.sin(phase / 30) * 0.02})`,
            transition: "transform 300ms ease-out"
          }}
        >
          <div className="w-3/5 h-3/5 rounded-full bg-gradient-to-br from-white/30 to-white/5" />
        </div>
      </div>
      <div className="flex flex-col">
        <span className="font-semibold">AuralA</span>
        <span className="text-xs text-slate-400">Your local collaboration assistant</span>
      </div>
    </div>
  );
}
