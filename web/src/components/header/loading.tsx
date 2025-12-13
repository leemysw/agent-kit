"use client";

import { useEffect, useState } from "react";

export function LoadingOrb() {
  const [frame, setFrame] = useState(0);
  const frames = ["✽", "✻", "✶", "✢", "·"];

  useEffect(() => {
    const timer = setInterval(() => {
      setFrame((prev) => (prev + 1) % frames.length);
    }, 120);
    return () => clearInterval(timer);
  }, []);

  return (
    <span className="inline-block w-3 text-center text-primary leading-none select-none">
        {frames[frame]}
    </span>
  );
}