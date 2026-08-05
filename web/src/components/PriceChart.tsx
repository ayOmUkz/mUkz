import { useEffect, useRef } from "react";
import type { Candle, SymbolPrint, Zone } from "@/lib/api";

interface Props {
  candles: Candle[];
  zones: Zone[];
  vwap: number | null;
  invalidationLevels: number[];
  prints: SymbolPrint[];
}

/** Daily price chart (lightweight-charts) with zone bands, VWAP and
 * invalidation levels drawn as price lines, and dark-pool prints as
 * markers on their session's candle, sized by how unusual they were.
 */
export function PriceChart({ candles, zones, vwap, invalidationLevels, prints }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) {
      return;
    }
    const container = containerRef.current;
    let disposed = false;
    let cleanup: (() => void) | undefined;

    // Imported inside the effect: lightweight-charts touches `window`,
    // which does not exist during server-side rendering.
    import("lightweight-charts").then(({ createChart, ColorType }) => {
      if (disposed) {
        return;
      }
      const chart = createChart(container, {
        height: 420,
        layout: {
          background: { type: ColorType.Solid, color: "#11151c" },
          textColor: "#c9d2e0",
        },
        grid: {
          vertLines: { color: "#1c2330" },
          horzLines: { color: "#1c2330" },
        },
        rightPriceScale: { borderColor: "#2a3446" },
        timeScale: { borderColor: "#2a3446" },
      });
      const series = chart.addCandlestickSeries({
        upColor: "#2f9e6e",
        downColor: "#d9534f",
        wickUpColor: "#2f9e6e",
        wickDownColor: "#d9534f",
        borderVisible: false,
      });
      series.setData(candles);

      for (const zone of zones) {
        const color =
          zone.strength_score >= 60 ? "#e0a83c" : "rgba(224, 168, 60, 0.45)";
        series.createPriceLine({
          price: zone.wavg,
          color,
          lineWidth: 2,
          title: `zone ${zone.strength_class} (${zone.status})`,
        });
        for (const edge of [zone.low, zone.high]) {
          if (edge !== zone.wavg) {
            series.createPriceLine({
              price: edge,
              color: "rgba(224, 168, 60, 0.25)",
              lineWidth: 1,
              title: "",
            });
          }
        }
      }
      if (vwap !== null) {
        series.createPriceLine({
          price: vwap,
          color: "#5b9bd5",
          lineWidth: 1,
          lineStyle: 1,
          title: "VWAP",
        });
      }
      for (const level of invalidationLevels) {
        series.createPriceLine({
          price: level,
          color: "#d9534f",
          lineWidth: 1,
          lineStyle: 2,
          title: "invalidation",
        });
      }

      const sessions = new Set(candles.map((candle) => candle.time));
      const markers = prints
        .filter((print) => sessions.has(print.session))
        .map((print) => ({
          time: print.session,
          position: "belowBar" as const,
          color:
            print.size_class === "extreme"
              ? "#d9534f"
              : print.size_class === "unusual"
                ? "#e0a83c"
                : "#5b9bd5",
          shape: "circle" as const,
          text: `${(print.size / 1000).toFixed(0)}k`,
        }));
      series.setMarkers(markers);
      chart.timeScale().fitContent();

      const resize = () => chart.applyOptions({ width: container.clientWidth });
      resize();
      window.addEventListener("resize", resize);
      cleanup = () => {
        window.removeEventListener("resize", resize);
        chart.remove();
      };
    });

    return () => {
      disposed = true;
      cleanup?.();
    };
  }, [candles, zones, vwap, invalidationLevels, prints]);

  if (candles.length === 0) {
    return <p className="muted">No candle data stored for this symbol yet.</p>;
  }
  return <div ref={containerRef} className="chart" />;
}
