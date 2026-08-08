import React, { useEffect, useRef } from "react";

/**
 * LiquidCanvasEffect
 * High-performance fluid liquid canvas animation component featuring
 * organic wave physics, cyan/electric-blue/green gradients, and mouse interaction.
 */
export function LiquidCanvasEffect() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 800);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 420);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener("resize", handleResize);

    let mouseX = width / 2;
    let mouseY = height / 2;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    };
    canvas.addEventListener("mousemove", handleMouseMove);

    let step = 0;
    const render = () => {
      step += 0.015;
      ctx.clearRect(0, 0, width, height);

      // Create organic fluid liquid gradient layers
      const grad = ctx.createRadialGradient(
        mouseX,
        mouseY,
        20,
        width / 2,
        height / 2,
        Math.max(width, height)
      );
      grad.addColorStop(0, "rgba(0, 240, 255, 0.15)");
      grad.addColorStop(0.4, "rgba(59, 130, 246, 0.08)");
      grad.addColorStop(0.8, "rgba(16, 185, 129, 0.05)");
      grad.addColorStop(1, "transparent");

      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);

      // Draw liquid wave curves
      ctx.beginPath();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "rgba(0, 240, 255, 0.2)";

      for (let x = 0; x < width; x += 10) {
        const y =
          height / 2 +
          Math.sin(x * 0.01 + step) * 20 +
          Math.cos(x * 0.005 + step * 0.7) * 15 +
          Math.sin((x + mouseX) * 0.008) * 10;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Second liquid wave curve (green accent)
      ctx.beginPath();
      ctx.lineWidth = 1.0;
      ctx.strokeStyle = "rgba(16, 185, 129, 0.18)";
      for (let x = 0; x < width; x += 12) {
        const y =
          height / 2 + 30 +
          Math.cos(x * 0.012 - step * 1.2) * 18 +
          Math.sin(x * 0.006 + step) * 12;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      if (canvas) canvas.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "auto",
        zIndex: 2,
        borderRadius: "16px",
      }}
    />
  );
}
